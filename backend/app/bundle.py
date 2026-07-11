"""Stage 6 — group ranked items into per-supplier bundles.

MOQ and shipping are per-supplier. Diversified picks (stage 5) lead each bundle;
if they don't reach the supplier's MOQ, the bundle is padded with that supplier's
next-best viable items — MOQ is the supplier's rule, not ours. A bundle either
meets MOQ within the remaining budget or is dropped entirely; never emit sub-MOQ.
"""

from .config import BUNDLE_EXTRA_ITEMS, MAX_BUNDLES
from .schemas import Bundle, Candidate


def build_bundles(ranked: list[Candidate], viable: list[Candidate], budget: float) -> list[Bundle]:
    ranked_ids = {c.id for c in ranked}
    pools: dict[str, list[Candidate]] = {}
    for c in ranked:  # diversified picks first, in rank order
        pools.setdefault(c.supplier_id, []).append(c)
    for c in sorted(viable, key=lambda x: x.score, reverse=True):  # then MOQ backfill
        if c.id not in ranked_ids and c.supplier_id in pools:
            pools[c.supplier_id].append(c)

    # Suppliers in order of their best-ranked item
    suppliers = sorted(pools, key=lambda s: ranked.index(pools[s][0]))

    bundles: list[Bundle] = []
    remaining = budget
    for supplier_id in suppliers:
        if len(bundles) >= MAX_BUNDLES:
            break
        pool = pools[supplier_id]
        moq = pool[0].moq
        take: list[Candidate] = []
        cost = 0.0
        for item in pool:
            if len(take) >= moq + BUNDLE_EXTRA_ITEMS:
                break
            if cost + item.fleek_cost > remaining:
                continue
            take.append(item)
            cost += item.fleek_cost
        if len(take) < moq:
            continue  # MOQ unreachable within budget — drop the whole bundle
        remaining -= cost
        total_resale = sum(i.predicted_resale for i in take)
        bundles.append(
            Bundle(
                supplier_id=supplier_id,
                items=take,
                total_cost=round(cost, 2),
                est_margin=round(total_resale / cost, 2),
                est_clear_days=max(i.predicted_days_to_clear for i in take),
            )
        )
    return bundles
