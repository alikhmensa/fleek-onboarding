"""Stage 2 — one gemini-2.5-flash-lite call infers aesthetic + saturation.

Everything numeric (price_band, budget, margin) is deterministic and merged in here.
Falls back to a heuristic profile if the LLM is unreachable, so the demo never dies.
"""

import logging

from .config import LLM_MODEL, genai_client
from .schemas import PriceBand, Saturation, SellerProfile

log = logging.getLogger(__name__)

PROMPT = """You are profiling a secondhand-clothing reseller from a summary of their Shopify sales history.

Sales summary (JSON):
{aggregate}

Return:
- aesthetic: 2-5 short style tags describing what this seller's shop is about
  (e.g. "Y2K", "vintage workwear", "90s branded sportswear"). Base them on the
  product titles and vendors actually sold.
- saturation.oversupplied: 1-3 categories/brands this seller already sells heavily
  (they do NOT need more of these).
- saturation.gaps: 2-4 adjacent categories their buyers would plausibly want but the
  seller barely stocks (e.g. "knitwear", "footwear"). Must NOT overlap oversupplied.
"""

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "aesthetic": {"type": "array", "items": {"type": "string"}},
        "saturation": {
            "type": "object",
            "properties": {
                "oversupplied": {"type": "array", "items": {"type": "string"}},
                "gaps": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["oversupplied", "gaps"],
        },
    },
    "required": ["aesthetic", "saturation"],
}


def _infer_taste(aggregate: dict) -> dict:
    from google.genai import types

    resp = genai_client().models.generate_content(
        model=LLM_MODEL,
        contents=PROMPT.format(aggregate=aggregate),
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=RESPONSE_SCHEMA,
        ),
    )
    import json

    return json.loads(resp.text)


def _heuristic_taste(aggregate: dict) -> dict:
    vendors = list(aggregate.get("units_by_vendor", {}))[:3]
    return {
        "aesthetic": vendors or ["vintage streetwear"],
        "saturation": {"oversupplied": vendors[:1], "gaps": ["knitwear", "footwear"]},
    }


def build_profile(aggregate: dict, price_band: PriceBand, budget: float, margin_multiple: float) -> SellerProfile:
    try:
        taste = _infer_taste(aggregate)
    except Exception:
        log.exception("profile LLM call failed — using heuristic fallback")
        taste = _heuristic_taste(aggregate)
    return SellerProfile(
        aesthetic=taste["aesthetic"],
        price_band=price_band,
        saturation=Saturation(**taste["saturation"]),
        assumed_margin_multiple=margin_multiple,
        budget=budget,
    )
