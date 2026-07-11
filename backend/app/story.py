"""AI-written seller story for the profile page — one flash-lite call, cached.

Turns the structured SellerProfile into a human profile: who this seller is,
who buys from them, what's working and where to grow. Template fallback keeps
the page alive if the LLM is unreachable.
"""

import json
import logging

from .config import LLM_MODEL, genai_client
from .schemas import SellerProfile

log = logging.getLogger(__name__)

PROMPT = """You are Fleek's sourcing advisor. Write a seller profile from this data:

{profile}

Rules: UK English, concrete and confident, grounded ONLY in the data given —
never invent sales numbers. Sound like an advisor who has studied their shop,
not a horoscope. Keep every field short.

- headline: one punchy line describing the shop (max 10 words)
- about: 2-3 sentences describing what this seller is about
- size_estimate: 1-2 sentences sizing the business from its stats (monthly revenue,
  sales velocity) — e.g. "an established side-hustle moving ~8 pieces a week"
- buyer_persona: 2 sentences describing who shops with them and why
- strengths: 3 short bullets — what's working in their range and pricing
- opportunities: 3 short bullets — the gaps worth stocking and why they'll sell
- strategy: 2-3 sentences of sourcing advice referencing their budget and margin target
"""

SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {"type": "string"},
        "about": {"type": "string"},
        "size_estimate": {"type": "string"},
        "buyer_persona": {"type": "string"},
        "strengths": {"type": "array", "items": {"type": "string"}},
        "opportunities": {"type": "array", "items": {"type": "string"}},
        "strategy": {"type": "string"},
    },
    "required": ["headline", "about", "size_estimate", "buyer_persona", "strengths", "opportunities", "strategy"],
}


def _fallback(p: SellerProfile) -> dict:
    band = p.price_band
    return {
        "headline": f"{' & '.join(p.aesthetic[:2])} specialist",
        "about": f"A curated secondhand shop built around {', '.join(p.aesthetic)}, "
                 f"selling in the £{band.min:.0f}-£{band.max:.0f} range.",
        "size_estimate": (
            f"Moving ~{p.stats.items_per_week:.0f} pieces a week at roughly "
            f"£{p.stats.est_monthly_revenue:,.0f}/month." if p.stats else "An active independent reseller."
        ),
        "buyer_persona": f"Buyers hunting {p.aesthetic[0]} pieces around £{band.median:.0f}.",
        "strengths": [f"Strong, focused range in {a}" for a in p.aesthetic[:3]],
        "opportunities": [f"Stock {g} — your buyers already want it" for g in p.saturation.gaps[:3]],
        "strategy": f"Source at or below 1/{p.assumed_margin_multiple:.0f} of expected resale, "
                    f"keeping restocks within your ~£{p.budget:.0f} budget.",
    }


def generate_story(profile: SellerProfile) -> dict:
    try:
        from google.genai import types

        resp = genai_client().models.generate_content(
            model=LLM_MODEL,
            contents=PROMPT.format(profile=profile.model_dump_json()),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=SCHEMA,
            ),
        )
        return json.loads(resp.text)
    except Exception:
        log.exception("story LLM call failed — using template fallback")
        return _fallback(profile)
