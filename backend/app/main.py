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
from fastapi import FastAPI, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from . import storage
from .auth import router as auth_router, user_id_from_header
from .bundle import build_bundles
from .config import BACKEND_DIR, DEFAULT_MARGIN_MULTIPLE, FIXTURES_DIR, INVENTORY_PATH
from .connectors.mock_shop import mock_shop_data
from .connectors.shopify import ShopifyClient, ShopifyOAuth
from .economics import filter_viable
from .ingest import (
    aggregate_for_llm,
    compute_price_band,
    compute_stats,
    infer_budget,
    parse_orders,
    shopify_orders_to_df,
)
from .profile import build_profile
from .rank import rank
from .rationale import write_rationales
from .schemas import InventoryItem, OnboardResponse, RecommendationsResponse
from .search import find_candidates
from .story import generate_story
from .voice import transcribe as transcribe_voice

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Fleek Sourcing Copilot")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # hackathon: frontend runs on assorted localhost ports
    allow_methods=["*"],
    allow_headers=["*"],
)

storage.init_db()
app.include_router(auth_router)


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
    if not shopify_oauth.api_key or not shopify_oauth.api_secret:
        raise HTTPException(
            status_code=503,
            detail="Shopify OAuth not configured: set SHOPIFY_API_KEY and SHOPIFY_API_SECRET "
            "in backend/.env (VEND app in the Partners dashboard), or use shop=mock",
        )
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
    return {
        "shop": shop,
        "connected": connected,
        "oauth_configured": bool(shopify_oauth.api_key and shopify_oauth.api_secret),
    }


@app.get("/shopify/preview")
def shopify_preview(shop: str) -> dict:
    """Order/listing counts for the frontend's import step."""
    data = _fetch_shop_data(shop)
    return {
        "shop": shop,
        "orders": data.total_orders_fetched,
        "items": data.total_items_fetched,
        "shop_name": data.profile.username if data.profile else shop,
    }


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
    voice: UploadFile | None = None,
    shopify_shop: str | None = Form(default=None),
    description: str | None = Form(default=None),
    budget: float | None = Form(default=None),
    margin_multiple: float = Form(default=DEFAULT_MARGIN_MULTIPLE),
    authorization: str | None = Header(default=None),
) -> OnboardResponse:
    """Sources merge: connected Shopify shop and/or an orders file (CSV/Excel),
    plus optional free-text and voice-note descriptions of the shop.
    At least one order source required."""
    frames = []
    active_listings: list[str] = []

    if voice is not None:
        transcript = transcribe_voice(await voice.read(), voice.content_type)
        if transcript:
            description = f"{description} {transcript}".strip() if description else transcript

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
    profile.stats = compute_stats(df)
    profile.stats.active_listings = len(active_listings)

    seller_id = storage.new_seller_id()
    storage.save_profile(seller_id, profile)
    user_id = user_id_from_header(authorization)
    if user_id:
        storage.set_user_seller(user_id, seller_id)  # session -> dashboard survives refresh
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


@app.get("/seller/{seller_id}/story")
def seller_story(seller_id: str) -> dict:
    """AI-written seller profile for the profile page — generated once, cached."""
    profile = storage.get_profile(seller_id)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"unknown seller_id {seller_id!r}")
    story = storage.get_story(seller_id)
    if story is None:
        story = generate_story(profile)
        storage.save_story(seller_id, story)
    return {"seller_id": seller_id, "profile": profile.model_dump(), "story": story}


@app.get("/inventory")
def browse_inventory(
    category: str | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=24, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict:
    """Marketplace browse for the home page — filterable, paginated."""
    items = list(inventory().values())
    if category:
        items = [i for i in items if i.category.lower() == category.lower()]
    if q:
        needle = q.lower()
        items = [i for i in items if needle in f"{i.title} {i.brand} {i.category} {i.description}".lower()]
    return {"total": len(items), "items": [i.model_dump() for i in items[offset : offset + limit]]}


@app.get("/inventory/categories")
def inventory_categories() -> dict:
    """Category tiles for the home page: name, count, cover image."""
    tiles: dict[str, dict] = {}
    for item in inventory().values():
        tile = tiles.setdefault(item.category, {"category": item.category, "count": 0, "image_url": item.image_url})
        tile["count"] += 1
    return {"categories": sorted(tiles.values(), key=lambda t: -t["count"])}


@app.get("/health")
def health() -> dict:
    return {"ok": True}


# Serve the frontend (repo-root frontend/) when present, so one server runs the
# whole demo at http://localhost:8000/ — API routes above take precedence.
_frontend_dir = BACKEND_DIR.parent / "frontend"
if _frontend_dir.is_dir():
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")
