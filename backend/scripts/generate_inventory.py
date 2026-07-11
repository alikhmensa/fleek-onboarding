"""Generate the 200-item mock Fleek inventory (see data/SCENARIO.md).

Deterministic (seeded) so the dataset is reproducible. After running:
    python -m scripts.generate_inventory
    python -m scripts.seed_inventory      # re-embed -> Pinecone + local fallback
"""

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import INVENTORY_PATH

random.seed(11)

SUPPLIERS = {
    "s_01": ("Northern Knits", 4),
    "s_02": ("Sole Archive", 3),
    "s_03": ("Duck & Dungaree", 5),
    "s_04": ("Terrace Classics", 4),
    "s_05": ("Indigo House", 3),
    "s_06": ("Peak Outerwear", 3),
    "s_07": ("Rosewood Vintage", 4),
    "s_08": ("Archive Street Supply", 4),
}

# category -> (supplier, count, style_tags, [(brand, piece, tier)...])
# tier: 'b' budget (resale ~£25-60) | 'p' premium (resale ~£60-150)
CATALOG = {
    "knitwear": ("s_01", 26, "cosy vintage knitwear, 90s preppy, romantic layering", [
        ("Unbranded", "chunky cable-knit fisherman jumper", "b"), ("Benetton", "striped lambswool jumper", "b"),
        ("Gap", "Y2K zip-through knit cardigan", "b"), ("St Michael", "80s grandad cardigan", "b"),
        ("Unbranded", "hand-knit Fair Isle vest", "b"), ("Jaeger", "merino roll-neck", "b"),
        ("Ralph Lauren", "cotton cable crewneck with pony", "p"), ("Lacoste", "vintage knit polo jumper", "p"),
        ("COS", "oversized wool jumper", "p"), ("Missoni", "zigzag knit polo", "p"),
        ("Pringle", "argyle golf jumper", "b"), ("Woolrich", "chunky shawl-collar cardigan", "p"),
        ("Unbranded", "mohair-blend oversized jumper", "b"),
    ]),
    "footwear": ("s_02", 26, "retro trainers and boots, 90s streetwear staples", [
        ("Nike", "Air Max 95 OG", "p"), ("Nike", "Dunk Low panda", "p"), ("Adidas", "Samba OG", "p"),
        ("Adidas", "Gazelle suede", "b"), ("New Balance", "574 trainers", "b"), ("New Balance", "550 court", "p"),
        ("Converse", "Chuck 70 hi-top", "b"), ("Vans", "Old Skool checkerboard", "b"),
        ("Dr Martens", "1460 leather boots", "p"), ("Timberland", "6-inch wheat boots", "p"),
        ("Reebok", "Classic leather", "b"), ("Puma", "Suede classic", "b"), ("Clarks", "Wallabees", "p"),
    ]),
    "denim": ("s_05", 20, "vintage denim, Y2K and 90s Americana", [
        ("Levi's", "501 straight-leg jeans", "b"), ("Levi's", "Type 3 trucker jacket", "p"),
        ("Wrangler", "cowboy-cut jeans", "b"), ("Lee", "90s carpenter jeans", "b"),
        ("Diesel", "Y2K low-rise flares", "p"), ("Levi's", "505 orange tab", "p"),
        ("Calvin Klein", "90s dad jeans", "b"), ("Carhartt", "double-front denim pants", "p"),
        ("Unbranded", "acid-wash denim jacket", "b"), ("Tommy Hilfiger", "flag-patch denim shirt", "b"),
    ]),
    "sportswear": ("s_04", 20, "90s branded sportswear, terrace and track style", [
        ("Nike", "90s embroidered-swoosh sweatshirt", "b"), ("Nike", "Y2K nylon windbreaker", "b"),
        ("Adidas", "firebird track jacket", "b"), ("Adidas", "3-stripe popper pants", "b"),
        ("Umbro", "90s drill top", "b"), ("Kappa", "banda track jacket", "b"),
        ("Fila", "colour-block half-zip", "b"), ("Reebok", "vintage windbreaker", "b"),
        ("Nike", "vintage swoosh track suit", "p"), ("Sergio Tacchini", "80s tennis track top", "p"),
    ]),
    "workwear": ("s_03", 18, "rugged vintage workwear and utility", [
        ("Carhartt", "Detroit jacket duck", "p"), ("Carhartt", "double-knee work pants", "b"),
        ("Carhartt", "chore coat", "p"), ("Dickies", "874 work pants", "b"),
        ("Dickies", "Eisenhower jacket", "b"), ("Ben Davis", "half-zip work shirt", "b"),
        ("Pointer Brand", "hickory stripe overalls", "b"), ("Wrangler", "blanket-lined ranch jacket", "p"),
        ("Red Kap", "mechanic work shirt", "b"),
    ]),
    "outerwear": ("s_06", 20, "statement vintage outerwear and technical shells", [
        ("The North Face", "Nuptse 700 puffer", "p"), ("The North Face", "Denali fleece", "p"),
        ("Patagonia", "Synchilla snap-T fleece", "p"), ("Columbia", "Y2K fleece-lined shell", "b"),
        ("Barbour", "waxed field jacket", "p"), ("Burberry", "vintage trench coat", "p"),
        ("Unbranded", "90s suede bomber", "b"), ("Berghaus", "retro colour-block shell", "b"),
        ("Helly Hansen", "sailing jacket", "b"), ("Schott", "leather biker jacket", "p"),
    ]),
    "hoodies": ("s_08", 18, "streetwear hoodies and heavyweight sweats", [
        ("Champion", "reverse-weave hoodie", "b"), ("Champion", "reverse-weave crewneck", "b"),
        ("Stussy", "script-logo hoodie", "p"), ("Carhartt WIP", "chase hoodie", "p"),
        ("Nike", "centre-swoosh hoodie", "p"), ("Russell Athletic", "90s college sweatshirt", "b"),
        ("Gap", "Y2K arc-logo hoodie", "b"), ("The North Face", "drew peak hoodie", "b"),
    ]),
    "tees": ("s_04", 16, "graphic tees, band tees and Y2K prints", [
        ("Unbranded", "90s band tour tee", "p"), ("Harley-Davidson", "dealer graphic tee", "p"),
        ("Nike", "vintage centre-swoosh tee", "b"), ("Unbranded", "Y2K flame-print tee", "b"),
        ("Stussy", "8-ball graphic tee", "b"), ("Hard Rock Cafe", "city souvenir tee", "b"),
        ("Disney", "90s cartoon tee", "b"), ("NFL", "single-stitch sports tee", "b"),
    ]),
    "dresses": ("s_07", 16, "romantic vintage dresses and Y2K going-out pieces", [
        ("Unbranded", "90s floral slip dress", "b"), ("Laura Ashley", "cottagecore tea dress", "b"),
        ("Karen Millen", "Y2K corset dress", "p"), ("Unbranded", "velvet babydoll dress", "b"),
        ("Betsey Johnson", "00s party dress", "p"), ("Monsoon", "embroidered maxi dress", "b"),
        ("Whistles", "silk slip dress", "p"), ("Unbranded", "gingham summer dress", "b"),
    ]),
    "accessories": ("s_07", 14, "vintage accessories, bags, caps and silk", [
        ("Unbranded", "leather belt bag", "b"), ("Nike", "vintage mini-swoosh cap", "b"),
        ("Unbranded", "90s silk scarf baroque print", "b"), ("Dickies", "canvas work tote", "b"),
        ("Coach", "vintage leather shoulder bag", "p"), ("Burberry", "nova-check bucket hat", "p"),
        ("Levi's", "leather western belt", "b"), ("Kangol", "furgora bucket hat", "p"),
    ]),
}

GRAILS = [  # s_08 — deliberately hard to justify economically
    ("Moncler", "Maya down jacket", "outerwear", 260, 420), ("Evisu", "painted-seagull jeans", "denim", 90, 180),
    ("Maison Margiela", "GAT trainers", "footwear", 120, 210), ("Missoni", "space-dye knit cardigan", "knitwear", 95, 170),
    ("Stone Island", "badge overshirt", "hoodies", 110, 200), ("Vivienne Westwood", "orb tee", "tees", 60, 115),
]

COLOURS = ["black", "cream", "forest green", "burgundy", "navy", "washed grey", "chocolate", "ecru",
           "faded red", "sky blue", "moss", "lilac", "sand", "charcoal", "off-white", "rust"]
CONDITIONS = ["A", "A", "B", "B", "B", "C"]
ERAS = ["80s", "90s", "90s", "Y2K", "Y2K", "00s", "vintage"]

# resale ranges per tier
TIER_RESALE = {"b": (25, 60), "p": (60, 150)}


def margin_for(i: int) -> float:
    """Mix of margins so the economics filter has real work: index-stable."""
    r = random.random()
    if i % 3 == 0 or r < 0.45:
        return round(random.uniform(3.0, 4.2), 2)  # clearly viable
    if r < 0.8:
        return round(random.uniform(2.4, 3.0), 2)  # viable only after relaxation
    return round(random.uniform(1.8, 2.4), 2)      # should be filtered out


def main() -> None:
    items, n = [], 0
    for category, (supplier, count, style, pool) in CATALOG.items():
        moq = SUPPLIERS[supplier][1]
        for k in range(count):
            n += 1
            brand, piece, tier = pool[k % len(pool)]
            colour, era = random.choice(COLOURS), random.choice(ERAS)
            resale = round(random.uniform(*TIER_RESALE[tier]), 0)
            # guarantee winnability: first half of each category clears 3x
            margin = round(random.uniform(3.0, 4.0), 2) if k < count // 2 else margin_for(n)
            cost = round(resale / margin, 2)
            title = f"{brand} {piece} - {colour}".replace("Unbranded ", "").strip()
            iid = f"i_{n:03d}"
            items.append({
                "id": iid,
                "title": title[0].upper() + title[1:],
                "description": f"{era} {brand} {piece} in {colour}. Authentic secondhand, condition grade "
                               f"{random.choice(CONDITIONS)}. Style: {style}.",
                "image_url": f"https://picsum.photos/seed/{iid}/400/500",
                "brand": brand, "category": category,
                "condition_grade": random.choice(CONDITIONS),
                "fleek_cost": cost, "predicted_resale": float(resale),
                "predicted_days_to_clear": random.randint(5, 21),
                "supplier_id": supplier, "moq": moq,
                "rating": round(random.uniform(4.1, 4.9), 1),
            })

    for brand, piece, category, cost, resale in GRAILS:
        n += 1
        iid = f"i_{n:03d}"
        items.append({
            "id": iid, "title": f"{brand} {piece}",
            "description": f"Grail-tier {brand} {piece}. Archive piece, condition grade A. "
                           f"Style: hyped designer archive, collector streetwear.",
            "image_url": f"https://picsum.photos/seed/{iid}/400/500",
            "brand": brand, "category": category, "condition_grade": "A",
            "fleek_cost": float(cost), "predicted_resale": float(resale),
            "predicted_days_to_clear": random.randint(20, 45),
            "supplier_id": "s_08", "moq": SUPPLIERS["s_08"][1],
            "rating": round(random.uniform(4.5, 5.0), 1),
        })

    INVENTORY_PATH.write_text(json.dumps(items, indent=1))

    # winnability report for both personas
    for name, lo, hi in [("StreetWear Vault (£45-120)", 45, 120), ("Budget Y2K (£22-62)", 22, 62)]:
        band = [i for i in items if lo * 0.75 <= i["predicted_resale"] <= hi * 1.25]
        winners = [i for i in band if i["predicted_resale"] / i["fleek_cost"] >= 3.0]
        cats = sorted({i["category"] for i in winners})
        print(f"{name}: {len(winners)} items >=3x in band across {len(cats)} categories: {cats}")
    print(f"total: {len(items)} items")
    assert len(items) == 200


if __name__ == "__main__":
    main()
