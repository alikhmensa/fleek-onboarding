"""Fleek Sourcing Copilot backend.

POST /onboard          — Shopify orders CSV → seller profile (stages 1-2)
GET  /recommendations  — profile → ranked per-supplier bundles (stages 3-7)

`?mock=true` on /recommendations serves the committed fixture — frontend contract
works before (and independently of) the live pipeline.
"""

import json
import logging
import os
from functools import lru_cache

import pandas as pd
from fastapi import FastAPI, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from . import storage
from .bundle import build_bundles
from .config import DEFAULT_MARGIN_MULTIPLE, FIXTURES_DIR, INVENTORY_PATH
from .connectors.mock_shop import mock_shop_data
from .connectors.shopify import ShopifyClient, ShopifyOAuth
from .economics import filter_viable
from .ingest import aggregate_for_llm, compute_price_band, infer_budget, parse_orders, shopify_orders_to_df
from .profile import build_profile
from .rank import rank
from .rationale import write_rationales
from .schemas import InventoryItem, OnboardResponse, RecommendationsResponse
from .search import find_candidates

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Fleek Sourcing Copilot")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # hackathon: frontend runs on assorted localhost ports
    allow_methods=["*"],
    allow_headers=["*"],
)

storage.init_db()


@lru_cache
def inventory() -> dict[str, InventoryItem]:
    items = json.loads(INVENTORY_PATH.read_text())
    return {i["id"]: InventoryItem(**i) for i in items}


shopify_oauth = ShopifyOAuth()
FRONTEND_URL = os.getenv("FRONTEND_URL", "")


@app.get("/connect/shopify")
def connect_shopify(shop: str = Query(description="e.g. mystore.myshopify.com")):
    if shop == "mock":
        return {"status": "connected", "shop": "mock"}
    return RedirectResponse(shopify_oauth.get_login_url(shop))


@app.get("/callback/shopify")
def callback_shopify(request: Request):
    params = dict(request.query_params)
    code, shop = params.get("code"), params.get("shop")
    if not code or not shop:
        raise HTTPException(status_code=400, detail="missing code or shop parameter")
    if shopify_oauth.api_secret and not shopify_oauth.verify_hmac(params):
        raise HTTPException(status_code=403, detail="invalid hmac signature")
    tokens = shopify_oauth.exchange_code(shop, code)
    storage.save_shop_token("shopify", shop, tokens["access_token"])
    if FRONTEND_URL:
        return RedirectResponse(f"{FRONTEND_URL}?shopify=connected&shop={shop}")
    return {"status": "connected", "platform": "shopify", "shop": shop}


@app.get("/shopify/status")
def shopify_status(shop: str) -> dict:
    connected = shop == "mock" or storage.get_shop_token("shopify", shop) is not None
    return {"shop": shop, "connected": connected}


def _fetch_shop_data(shop: str):
    if shop == "mock":
        return mock_shop_data()
    token = storage.get_shop_token("shopify", shop)
    if token is None:
        raise HTTPException(status_code=401, detail=f"{shop} not connected — visit /connect/shopify?shop={shop}")
    try:
        return ShopifyClient(shop, token).get_all()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Shopify fetch failed for {shop}: {e}")


@app.post("/onboard", response_model=OnboardResponse)
async def onboard(
    file: UploadFile | None = None,
    shopify_shop: str | None = Form(default=None),
    description: str | None = Form(default=None),
    budget: float | None = Form(default=None),
    margin_multiple: float = Form(default=DEFAULT_MARGIN_MULTIPLE),
) -> OnboardResponse:
    """Sources merge: connected Shopify shop and/or an orders file (CSV/Excel),
    plus an optional free-text shop description. At least one order source required."""
    frames = []
    active_listings: list[str] = []

    if shopify_shop:
        shop_data = _fetch_shop_data(shopify_shop)
        frames.append(shopify_orders_to_df(shop_data.orders, shop_data.items))
        active_listings = [
            f"{i.title} ({i.category or 'uncategorised'}, £{i.price:.0f})" for i in shop_data.items
        ]
    if file is not None:
        try:
            frames.append(parse_orders(await file.read(), file.filename or ""))
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

    frames = [f for f in frames if not f.empty]
    if not frames:
        raise HTTPException(status_code=422, detail="provide a connected shopify_shop and/or an orders file")
    df = pd.concat(frames, ignore_index=True)

    price_band = compute_price_band(df)
    if budget is None:
        budget = infer_budget(df, margin_multiple)
    profile = build_profile(
        aggregate_for_llm(df), price_band, budget, margin_multiple,
        description=description, active_listings=active_listings or None,
    )

    seller_id = storage.new_seller_id()
    storage.save_profile(seller_id, profile)
    return OnboardResponse(seller_id=seller_id, profile=profile)


@app.get("/recommendations", response_model=RecommendationsResponse)
def recommendations(
    seller_id: str = Query(default=""),
    budget: float | None = Query(default=None),
    mock: bool = Query(default=False),
) -> RecommendationsResponse:
    if mock:
        return RecommendationsResponse(**json.loads((FIXTURES_DIR / "bundles.json").read_text()))

    profile = storage.get_profile(seller_id)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"unknown seller_id {seller_id!r} — run /onboard first")
    budget = budget if budget is not None else profile.budget

    candidates = find_candidates(profile, inventory())          # stage 3
    viable, relaxations = filter_viable(candidates, profile, budget)  # stage 4
    ranked = rank(viable, profile)                               # stage 5
    bundles = build_bundles(ranked, viable, budget)              # stage 6
    write_rationales(bundles, profile)                           # stage 7
    return RecommendationsResponse(bundles=bundles, relaxations=relaxations)


@app.get("/health")
def health() -> dict:
    return {"ok": True}
