"""Seed a Shopify development store with backdated order history (and optionally
products), so the demo runs against a REAL store with a real (imported) history.

Shiv's store already has products (seed_shopify.py on his branch), so by default
this creates ORDERS ONLY — pass --products for a fresh empty store.
The orders are the StreetWear Vault persona (premium, £45-195) and deliberately
DISJOINT from data/streetwear_vault_orders.xlsx (the "other channel" upload) so
connecting the store and uploading the sheet never double-counts a sale.

Setup (one-time, in the dev store admin):
  Settings -> Apps and sales channels -> Develop apps -> Create app
  -> Admin API scopes: write_products, read_products, write_orders, read_orders
  -> Install app -> reveal Admin API access token (shpat_...)

Run from backend/:
  SHOP_DOMAIN=yourstore.myshopify.com SHOPIFY_ADMIN_TOKEN=shpat_xxx \
    .venv/bin/python -m scripts.populate_shop

Orders are created with `processed_at` backdated over the past ~10 weeks — this is
the supported way to import historical orders (Shopify sets created_at itself).
Idempotence: safe-ish to re-run; it will create duplicates, so run once (or wipe
orders/products in the store admin first).
"""

import os
import random
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

SHOP = os.getenv("SHOP_DOMAIN", "")
TOKEN = os.getenv("SHOPIFY_ADMIN_TOKEN", "")
API = "2024-10"

if not SHOP or not TOKEN:
    sys.exit("set SHOP_DOMAIN and SHOPIFY_ADMIN_TOKEN (see docstring)")

random.seed(7)
session = requests.Session()
session.headers["X-Shopify-Access-Token"] = TOKEN


def post(endpoint: str, payload: dict) -> dict:
    resp = session.post(f"https://{SHOP}/admin/api/{API}/{endpoint}.json", json=payload, timeout=30)
    if not resp.ok:
        sys.exit(f"{endpoint} failed: {resp.status_code} {resp.text[:300]}")
    time.sleep(0.6)  # REST admin API allows ~2 req/s
    return resp.json()


# --- Current stock: what the shop is listing right now (heavy on workwear/sportswear,
# --- deliberately NO knitwear or footwear -> those become the profile's gaps)
PRODUCTS = [
    ("Carhartt Detroit Jacket - Duck Brown", "Carhartt", "Jackets", 58, "Classic blanket-lined Detroit. Size L. Honest fade."),
    ("Carhartt Double Knee Pants - Hamilton", "Carhartt", "Workwear", 45, "W34 L32. The staple. Minor paint fleck on left knee."),
    ("Carhartt Chore Coat - Faded Black", "Carhartt", "Jackets", 55, "Size M. Beautifully broken in."),
    ("Nike 90s Embroidered Sweatshirt - Navy", "Nike", "Sweatshirts", 38, "Small embroidered swoosh. Size L. 90s made-in-UK."),
    ("Nike Y2K Nylon Windbreaker - Silver", "Nike", "Jackets", 40, "Shiny Y2K shell, packable hood. Size M."),
    ("Adidas Vintage Track Jacket - Red", "Adidas", "Sportswear", 34, "3-stripe firebird. Size M. 80s tag."),
    ("Champion Reverse Weave Crew - Burgundy", "Champion", "Sweatshirts", 36, "Size L. Proper heavyweight reverse weave."),
    ("Umbro 90s Drill Top - Teal", "Umbro", "Sportswear", 25, "Size M. Peak 90s terrace."),
    ("Levi's 501 - Stonewash", "Levi's", "Jeans", 42, "W32 L30. USA-made, nicely worn in."),
    ("Dickies 874 Work Pants - Black", "Dickies", "Workwear", 30, "W32 L32. Dead stock feel."),
]

# --- Past sales: same taste, sold over the last ~10 weeks (custom line items,
# --- so no inventory juggling needed)
# StreetWear Vault sales on Shopify — echoes the store's actual product wall.
# Keep DISJOINT from scripts/generate_demo_xlsx.py (the other-channel upload).
SOLD = [
    ("Nike Air Max 90 - Triple White", 85), ("Carhartt WIP Michigan Coat - Black", 120),
    ("Stussy Logo Hoodie - Navy", 65), ("Vintage Levi's 501 - Light Wash", 55),
    ("The North Face Nuptse 700 - Black", 195), ("Adidas Samba OG - White/Black", 78),
    ("New Balance 550 - White/Green", 88), ("Palace Tri-Ferg Hoodie - Black", 90),
    ("Carhartt WIP Detroit Jacket - Blacksmith", 110), ("Nike Air Force 1 - White", 75),
    ("Stussy World Tour Crewneck - Grey", 70), ("Supreme Small Box Hoodie - Red", 125),
]


def main() -> None:
    print(f"Seeding {SHOP} ...")

    if "--products" not in sys.argv:
        print("skipping product creation (store already has products; pass --products to create)")
    else:
        _create_products()

    _create_orders()


def _create_products() -> None:
    for title, vendor, ptype, price, body in PRODUCTS:
        post("products", {
            "product": {
                "title": title,
                "vendor": vendor,
                "product_type": ptype,
                "body_html": body,
                "status": "active",
                "tags": "vintage, secondhand",
                "variants": [{"price": str(price), "inventory_management": None}],
            }
        })
    print(f"created {len(PRODUCTS)} active products")


def _create_orders() -> None:
    now = datetime.now(timezone.utc)
    n_orders = 0
    for week in range(10):
        for _ in range(random.randint(3, 5)):
            title, base_price = random.choice(SOLD)
            price = round(base_price * random.uniform(0.85, 1.15), 2)
            sold_at = now - timedelta(days=week * 7 + random.randint(0, 6), hours=random.randint(1, 20))
            post("orders", {
                "order": {
                    "line_items": [{"title": title, "price": str(price), "quantity": 1}],
                    "processed_at": sold_at.isoformat(),
                    "financial_status": "paid",
                    "currency": "GBP",
                    "tags": "seeded-demo",
                    "send_receipt": False,
                    "send_fulfillment_receipt": False,
                    "inventory_behaviour": "bypass",
                }
            })
            n_orders += 1
    print(f"created {n_orders} paid orders backdated over 10 weeks")
    print("Done — connect via /connect/shopify?shop=" + SHOP)


if __name__ == "__main__":
    main()
