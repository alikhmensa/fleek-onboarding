"""Stage 2 — one gemini-2.5-flash-lite call infers aesthetic + saturation.

Everything numeric (price_band, budget, margin) is deterministic and merged in here.
Falls back to a heuristic profile if the LLM is unreachable, so the demo never dies.
"""

import logging

from .config import LLM_MODEL, genai_client
from .schemas import PriceBand, Saturation, SellerProfile

log = logging.getLogger(__name__)

PROMPT = """You are profiling a secondhand-clothing reseller from a summary of their sales history.

Sales summary (JSON):
{aggregate}
{description_section}{listings_section}
Return:
- aesthetic: 2-5 short style tags describing what this seller's shop is about
  (e.g. "Y2K", "vintage workwear", "90s branded sportswear"). Base them on the
  product titles and vendors actually sold.
- saturation.oversupplied: 1-3 categories/brands this seller already sells heavily
  or currently stocks in depth (they do NOT need more of these). Weigh current
  active listings at least as heavily as past sales here.
- saturation.gaps: 2-4 adjacent categories their buyers would plausibly want but the
  seller barely stocks (e.g. "knitwear", "footwear"). Must NOT overlap oversupplied.

If the seller described their shop in their own words, treat that as strong signal
for aesthetic and gaps.
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


def _infer_taste(aggregate: dict, description: str | None, active_listings: list[str] | None) -> dict:
    from google.genai import types

    description_section = (
        f"\nThe seller describes their shop in their own words:\n\"{description}\"\n" if description else ""
    )
    listings_section = (
        "\nTheir CURRENT active listings (what they stock right now):\n- " + "\n- ".join(active_listings) + "\n"
        if active_listings
        else ""
    )
    resp = genai_client().models.generate_content(
        model=LLM_MODEL,
        contents=PROMPT.format(
            aggregate=aggregate,
            description_section=description_section,
            listings_section=listings_section,
        ),
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


def build_profile(
    aggregate: dict,
    price_band: PriceBand,
    budget: float,
    margin_multiple: float,
    description: str | None = None,
    active_listings: list[str] | None = None,
) -> SellerProfile:
    try:
        taste = _infer_taste(aggregate, description, active_listings)
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
