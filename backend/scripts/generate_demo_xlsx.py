"""Generate data/streetwear_vault_orders.xlsx — the demo upload spreadsheet.

StreetWear Vault's sales from their OTHER channel (eBay/Depop) — same premium
streetwear persona as the Shopify dev store, heavy on jackets/hoodies/sneakers,
but a deliberately DISJOINT set of line items from scripts/populate_shop.py so
store-connect + upload merge without double-counting a single sale.
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
    ("Carhartt WIP OG Chore Coat - Dearborn", "Carhartt WIP", 105),
    ("Carhartt WIP Nimbus Pullover - Purple", "Carhartt WIP", 75),
    ("Carhartt WIP Active Jacket - Moss", "Carhartt WIP", 95),
    ("Nike Air Max 95 - Neon", "Nike", 90),
    ("Nike Dunk Low - Panda", "Nike", 95),
    ("Nike Vintage Windrunner - Silver/Blue", "Nike", 55),
    ("Nike Tech Fleece Hoodie - Grey", "Nike", 60),
    ("Stussy 8-Ball Hoodie - Black", "Stussy", 80),
    ("Stussy Logo Crewneck - Navy", "Stussy", 65),
    ("Palace Tri-Ferg Hoodie - Grey", "Palace", 85),
    ("Adidas Gazelle - Navy", "Adidas", 72),
    ("Adidas Firebird Track Jacket - Red", "Adidas", 48),
    ("New Balance 2002R - Protection Pack", "New Balance", 115),
    ("New Balance 990v3 - Grey", "New Balance", 110),
    ("Salomon XT-6 - Black/Phantom", "Salomon", 105),
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
