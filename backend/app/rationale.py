"""Stage 7 — one batched gemini-2.5-flash-lite call writes a one-line rationale per bundle.

Falls back to a deterministic template if the LLM is unreachable.
"""

import json
import logging

from .config import LLM_MODEL, genai_client
from .schemas import Bundle, SellerProfile

log = logging.getLogger(__name__)

PROMPT = """A secondhand-clothing reseller has this profile:
{profile}

We are recommending them these wholesale bundles:
{bundles}

For each bundle, in order, write ONE short sentence explaining why it fits this
seller's business — reference their gaps, aesthetic or price band where relevant.
Sound like a knowledgeable sourcing advisor, not a search engine.
Example tone: "You've sold out of workwear but have no knitwear — this lot fills
that gap in your usual £30-50 band."
"""

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {"rationales": {"type": "array", "items": {"type": "string"}}},
    "required": ["rationales"],
}


def _bundle_summary(b: Bundle) -> dict:
    return {
        "supplier_id": b.supplier_id,
        "items": [f"{i.brand} {i.title} ({i.category}, resale ~£{i.predicted_resale:.0f})" for i in b.items],
        "total_cost": b.total_cost,
        "est_margin": b.est_margin,
        "est_clear_days": b.est_clear_days,
    }


def _fallback(b: Bundle, profile: SellerProfile) -> str:
    cats = sorted({i.category for i in b.items})
    band = profile.price_band
    return (
        f"{len(b.items)} pieces across {', '.join(cats)} at a {b.est_margin}x estimated margin, "
        f"inside your usual £{band.min:.0f}-{band.max:.0f} range."
    )


def write_rationales(bundles: list[Bundle], profile: SellerProfile) -> None:
    if not bundles:
        return
    try:
        from google.genai import types

        resp = genai_client().models.generate_content(
            model=LLM_MODEL,
            contents=PROMPT.format(
                profile=profile.model_dump_json(),
                bundles=json.dumps([_bundle_summary(b) for b in bundles]),
            ),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=RESPONSE_SCHEMA,
            ),
        )
        rationales = json.loads(resp.text)["rationales"]
    except Exception:
        log.exception("rationale LLM call failed — using template fallback")
        rationales = []
    for i, b in enumerate(bundles):
        b.rationale = rationales[i] if i < len(rationales) else _fallback(b, profile)
