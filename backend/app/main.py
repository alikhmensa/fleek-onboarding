"""Fleek Sourcing Copilot backend.

POST /onboard          — Shopify orders CSV → seller profile (stages 1-2)
GET  /recommendations  — profile → ranked per-supplier bundles (stages 3-7)

`?mock=true` on /recommendations serves the committed fixture — frontend contract
works before (and independently of) the live pipeline.
"""

import json
import logging
from functools import lru_cache

from fastapi import FastAPI, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from . import storage
from .bundle import build_bundles
from .config import DEFAULT_MARGIN_MULTIPLE, FIXTURES_DIR, INVENTORY_PATH
from .economics import filter_viable
from .ingest import aggregate_for_llm, compute_price_band, infer_budget, parse_orders
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


@app.post("/onboard", response_model=OnboardResponse)
async def onboard(
    file: UploadFile,
    budget: float | None = Form(default=None),
    margin_multiple: float = Form(default=DEFAULT_MARGIN_MULTIPLE),
) -> OnboardResponse:
    try:
        df = parse_orders(await file.read())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    price_band = compute_price_band(df)
    if budget is None:
        budget = infer_budget(df, margin_multiple)
    profile = build_profile(aggregate_for_llm(df), price_band, budget, margin_multiple)

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
