"""Stage 4 — economics filter (teal box #1). Pure Python, no LLM.

Taste-fit alone isn't a recommendation: items must also clear the seller's margin
threshold and sit near their price band. Filters relax progressively rather than
ever returning an empty result silently — every relaxation is reported.
"""

from .config import MIN_VIABLE, RELAXATION_LADDER
from .schemas import Candidate, SellerProfile


def _passes(c: Candidate, profile: SellerProfile, budget: float, margin_scale: float, tolerance: float) -> bool:
    if c.fleek_cost <= 0 or c.fleek_cost > budget:
        return False
    if c.est_margin < profile.assumed_margin_multiple * margin_scale:
        return False
    band = profile.price_band
    return band.min * (1 - tolerance) <= c.predicted_resale <= band.max * (1 + tolerance)


def filter_viable(
    candidates: list[Candidate], profile: SellerProfile, budget: float
) -> tuple[list[Candidate], list[str]]:
    for c in candidates:
        c.est_margin = round(c.predicted_resale / c.fleek_cost, 2) if c.fleek_cost > 0 else 0.0

    relaxations: list[str] = []
    viable: list[Candidate] = []
    for margin_scale, tolerance in RELAXATION_LADDER:
        viable = [c for c in candidates if _passes(c, profile, budget, margin_scale, tolerance)]
        if len(viable) >= MIN_VIABLE:
            break
    base_scale, base_tol = RELAXATION_LADDER[0]
    if margin_scale != base_scale:
        relaxations.append(
            f"margin threshold relaxed to {profile.assumed_margin_multiple * margin_scale:.1f}x"
        )
    if tolerance != base_tol:
        relaxations.append(f"price band tolerance widened to ±{int(tolerance * 100)}%")
    return viable, relaxations
