"""Stage 5 — diversify + re-rank (teal box #2). Pure Python, no LLM.

Blended score, then diversity: cap per category, boost gap categories, penalise
oversupplied ones — so we recommend adjacent stock, never more of what they oversell.
"""

from collections import Counter

from .config import CATEGORY_CAP, GAP_BOOST, OVERSUPPLY_PENALTY, W_FIT, W_MARGIN, W_SPEED
from .schemas import Candidate, SellerProfile


def _normalise(values: list[float]) -> list[float]:
    lo, hi = min(values), max(values)
    if hi == lo:
        return [1.0] * len(values)
    return [(v - lo) / (hi - lo) for v in values]


_STOPWORDS = {"and", "the", "of", "for", "vintage", "retro", "branded", "y2k", "90s", "80s"}


def _matches(item: Candidate, tags: list[str]) -> bool:
    """Profile tags are free text ("branded track jackets") — match on token overlap
    with the item, not whole-phrase containment, so "track jacket" items still hit."""
    item_tokens = set(f"{item.brand} {item.category} {item.title}".lower().replace("-", " ").split())
    item_tokens |= {t.rstrip("s") for t in item_tokens}
    for tag in tags:
        tag_tokens = {t.rstrip("s") for t in tag.lower().replace("-", " ").split()} - _STOPWORDS
        if tag_tokens & item_tokens:
            return True
    return False


def rank(viable: list[Candidate], profile: SellerProfile) -> list[Candidate]:
    if not viable:
        return []

    margins = _normalise([c.est_margin for c in viable])
    speeds = _normalise([1.0 / max(c.predicted_days_to_clear, 1) for c in viable])
    for c, nm, ns in zip(viable, margins, speeds):
        c.score = W_FIT * c.fit + W_MARGIN * nm + W_SPEED * ns
        if _matches(c, profile.saturation.gaps):
            c.score += GAP_BOOST
        if _matches(c, profile.saturation.oversupplied):
            c.score -= OVERSUPPLY_PENALTY
        c.score = round(c.score, 4)

    picked: list[Candidate] = []
    per_category: Counter = Counter()
    for c in sorted(viable, key=lambda x: x.score, reverse=True):
        if per_category[c.category] >= CATEGORY_CAP:
            continue
        picked.append(c)
        per_category[c.category] += 1
    return picked
