"""Generate data/streetwear_vault_orders.xlsx — the demo upload spreadsheet.

Order history for the "StreetWear Vault" persona (Shiv's dev store): branded
streetwear sold at £45-120, heavy on jackets, hoodies and sneakers, so the
inferred gaps are knitwear / denim / accessories / tees per data/SCENARIO.md.
Dates are spread over the last 10 weeks from today — re-run before the demo
so the history looks current.

Run from backend/:  python -m scripts.generate_demo_xlsx
"""

import random
from datetime import datetime, timedelta

import pandas as pd

from app.config import DATA_DIR

random.seed(11)

# (line item title, vendor, base price) — what this shop actually sells
SOLD = [
    ("Carhartt WIP Detroit Jacket - Hamilton Brown", "Carhartt WIP", 115),
    ("Carhartt WIP Michigan Chore Coat - Black", "Carhartt WIP", 105),
    ("Carhartt WIP Nimbus Pullover - Purple", "Carhartt WIP", 75),
    ("Carhartt WIP Active Jacket - Moss", "Carhartt WIP", 95),
    ("Nike Air Max 95 - Neon", "Nike", 90),
    ("Nike Dunk Low - Panda", "Nike", 95),
    ("Nike Vintage Windrunner - Silver/Blue", "Nike", 55),
    ("Nike Tech Fleece Hoodie - Grey", "Nike", 60),
    ("Stussy 8-Ball Hoodie - Black", "Stussy", 80),
    ("Stussy Logo Crewneck - Navy", "Stussy", 65),
    ("Palace Tri-Ferg Hoodie - Grey", "Palace", 85),
    ("Adidas Samba OG - White/Green", "Adidas", 80),
    ("Adidas Firebird Track Jacket - Red", "Adidas", 48),
    ("New Balance 550 - White/Green", "New Balance", 88),
    ("New Balance 990v3 - Grey", "New Balance", 110),
    ("The North Face Nuptse 700 - Black", "The North Face", 120),
    ("The North Face Denali Fleece - Purple", "The North Face", 70),
    ("Levi's Type 3 Sherpa Trucker - Mid Blue", "Levi's", 62),
]


def main() -> None:
    rows, order_no = [], 2001
    now = datetime.now()
    for week in range(10):
        for _ in range(random.randint(4, 6)):
            title, vendor, base = random.choice(SOLD)
            sold_at = now - timedelta(days=week * 7 + random.randint(0, 6), hours=random.randint(1, 22))
            rows.append(
                {
                    "Name": f"#{order_no}",
                    "Created at": sold_at.strftime("%Y-%m-%d %H:%M:%S +0100"),
                    "Lineitem name": title,
                    "Lineitem price": round(base * random.uniform(0.9, 1.1), 2),
                    "Lineitem quantity": 1,
                    "Vendor": vendor,
                    "Financial Status": "paid",
                    "Fulfillment Status": "fulfilled",
                }
            )
            order_no += 1

    df = pd.DataFrame(rows).sort_values("Created at", ascending=False)
    out = DATA_DIR / "streetwear_vault_orders.xlsx"
    df.to_excel(out, index=False, sheet_name="Orders")
    prices = df["Lineitem price"]
    print(f"{out}: {len(df)} line items, £{prices.min():.0f}–£{prices.max():.0f}, median £{prices.median():.0f}")


if __name__ == "__main__":
    main()
