"""
Seed your Shopify development store with mock product data.

This pushes realistic secondhand fashion items into your real Shopify store
so that the OAuth flow pulls back convincing demo data.

Usage:
    python seed_shopify.py --shop yourstore.myshopify.com --token your_access_token

To get your access token:
    1. Go to your Shopify store admin → Settings → Apps and sales channels → Develop apps
    2. Click your app → API credentials → Install app
    3. Copy the Admin API access token
"""

import argparse
import requests
import time

PRODUCTS = [
    {
        "title": "Nike Air Max 90 - Triple White",
        "body_html": "<p>Worn twice, excellent condition. UK 10. Comes with original box. Classic Air Max 90 silhouette in clean triple white colourway.</p>",
        "vendor": "Nike",
        "product_type": "Sneakers",
        "tags": "condition:very-good, secondhand, sneakers, nike, streetwear",
        "variants": [{"price": "85.00", "sku": "SKU-SW-001", "option1": "UK 10", "inventory_quantity": 1}],
        "options": [{"name": "Size"}],
        "images": [
            {"src": "https://images.unsplash.com/photo-1600185365926-3a2ce3cdb9eb?w=800"},
            {"src": "https://images.unsplash.com/photo-1515955656352-a1fa3ffcd111?w=800"},
            {"src": "https://images.unsplash.com/photo-1514989940723-e8e51635b782?w=800"},
        ],
    },
    {
        "title": "Carhartt WIP Michigan Coat - Black",
        "body_html": "<p>Classic chore coat in black. Size L. Light fading on the seams adds character. Heavyweight cotton duck canvas.</p>",
        "vendor": "Carhartt WIP",
        "product_type": "Jackets",
        "tags": "condition:good, secondhand, jacket, carhartt, workwear",
        "variants": [{"price": "120.00", "sku": "SKU-SW-002", "option1": "L", "inventory_quantity": 1}],
        "options": [{"name": "Size"}],
        "images": [
            {"src": "https://images.unsplash.com/photo-1591047139829-d91aecb6caea?w=800"},
            {"src": "https://images.unsplash.com/photo-1548126032-079a0fb0099d?w=800"},
        ],
    },
    {
        "title": "Stussy Logo Hoodie - Navy",
        "body_html": "<p>2024 collection. Worn a handful of times. Size M. Heavyweight fleece with embroidered Stussy script logo.</p>",
        "vendor": "Stussy",
        "product_type": "Hoodies",
        "tags": "condition:very-good, secondhand, hoodie, stussy, streetwear",
        "variants": [{"price": "65.00", "sku": "SKU-SW-003", "option1": "M", "inventory_quantity": 1}],
        "options": [{"name": "Size"}],
        "images": [
            {"src": "https://images.unsplash.com/photo-1556821840-3a63f95609a7?w=800"},
            {"src": "https://images.unsplash.com/photo-1620799140408-edc6dcb6d633?w=800"},
        ],
    },
    {
        "title": "Vintage Levi's 501 - Light Wash",
        "body_html": "<p>W32 L32. Classic straight leg. Authentic vintage 90s pair. Natural fading and whiskering. Button fly.</p>",
        "vendor": "Levi's",
        "product_type": "Jeans",
        "tags": "condition:good, secondhand, jeans, levis, vintage, denim",
        "variants": [{"price": "55.00", "sku": "SKU-SW-004", "option1": "W32 L32", "inventory_quantity": 1}],
        "options": [{"name": "Size"}],
        "images": [
            {"src": "https://images.unsplash.com/photo-1582552938357-32b906df40cb?w=800"},
            {"src": "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=800"},
            {"src": "https://images.unsplash.com/photo-1475178626620-a4d074967571?w=800"},
        ],
    },
    {
        "title": "The North Face Nuptse 700 - Black",
        "body_html": "<p>2023 model. Barely worn. Size S. 700-fill goose down puffer in perfect condition. Stows into its own pocket.</p>",
        "vendor": "The North Face",
        "product_type": "Jackets",
        "tags": "condition:new-without-tags, secondhand, jacket, north-face, puffer",
        "variants": [{"price": "195.00", "sku": "SKU-SW-005", "option1": "S", "inventory_quantity": 1}],
        "options": [{"name": "Size"}],
        "images": [
            {"src": "https://images.unsplash.com/photo-1547624643-3bf667907e21?w=800"},
            {"src": "https://images.unsplash.com/photo-1611312449408-fcece27cdbb7?w=800"},
            {"src": "https://images.unsplash.com/photo-1609803384069-19f3e5a70e75?w=800"},
        ],
    },
    {
        "title": "Adidas Samba OG - White/Black",
        "body_html": "<p>UK 9. Worn a few times, minimal sole wear. Classic gum sole Samba in white leather with black suede T-toe.</p>",
        "vendor": "Adidas",
        "product_type": "Sneakers",
        "tags": "condition:very-good, secondhand, sneakers, adidas, classic",
        "variants": [{"price": "72.00", "sku": "SKU-SW-006", "option1": "UK 9", "inventory_quantity": 1}],
        "options": [{"name": "Size"}],
        "images": [
            {"src": "https://images.unsplash.com/photo-1520256862855-398228c41684?w=800"},
            {"src": "https://images.unsplash.com/photo-1595950653106-6c9ebd614d3a?w=800"},
        ],
    },
    {
        "title": "Palace Tri-Ferg Tee - White",
        "body_html": "<p>Size L. Classic Tri-Ferg logo on front. 100% cotton. No stains or damage.</p>",
        "vendor": "Palace",
        "product_type": "T-Shirts",
        "tags": "condition:very-good, secondhand, tshirt, palace, streetwear",
        "variants": [{"price": "45.00", "sku": "SKU-SW-007", "option1": "L", "inventory_quantity": 1}],
        "options": [{"name": "Size"}],
        "images": [
            {"src": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=800"},
            {"src": "https://images.unsplash.com/photo-1583743814966-8936f5b7be1a?w=800"},
        ],
    },
    {
        "title": "New Balance 550 - Green/White",
        "body_html": "<p>UK 8. 2024 colourway. Worn twice. Leather upper with green accents. Immaculate condition.</p>",
        "vendor": "New Balance",
        "product_type": "Sneakers",
        "tags": "condition:new-without-tags, secondhand, sneakers, new-balance",
        "variants": [{"price": "95.00", "sku": "SKU-SW-008", "option1": "UK 8", "inventory_quantity": 1}],
        "options": [{"name": "Size"}],
        "images": [
            {"src": "https://images.unsplash.com/photo-1539185441755-769473a23570?w=800"},
            {"src": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=800"},
        ],
    },
]


def seed(shop_domain: str, access_token: str):
    url = f"https://{shop_domain}/admin/api/2024-10/products.json"
    headers = {"X-Shopify-Access-Token": access_token, "Content-Type": "application/json"}

    print(f"Seeding {len(PRODUCTS)} products into {shop_domain}...")

    for i, product in enumerate(PRODUCTS, 1):
        resp = requests.post(url, headers=headers, json={"product": product})
        if resp.ok:
            created = resp.json()["product"]
            print(f"  [{i}/{len(PRODUCTS)}] Created: {created['title']} (ID: {created['id']})")
        else:
            print(f"  [{i}/{len(PRODUCTS)}] FAILED: {product['title']} — {resp.status_code} {resp.text[:200]}")
        time.sleep(0.5)

    print(f"\nDone. Visit https://{shop_domain}/admin/products to see them.")


def clear(shop_domain: str, access_token: str):
    url = f"https://{shop_domain}/admin/api/2024-10/products.json"
    headers = {"X-Shopify-Access-Token": access_token}

    resp = requests.get(url, headers=headers, params={"limit": 250})
    products = resp.json().get("products", [])

    print(f"Deleting {len(products)} products from {shop_domain}...")
    for p in products:
        del_url = f"https://{shop_domain}/admin/api/2024-10/products/{p['id']}.json"
        requests.delete(del_url, headers=headers)
        print(f"  Deleted: {p['title']}")
        time.sleep(0.3)

    print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Shopify dev store with mock products")
    parser.add_argument("--shop", required=True, help="Your Shopify store domain (e.g. mystore.myshopify.com)")
    parser.add_argument("--token", required=True, help="Shopify Admin API access token")
    parser.add_argument("--clear", action="store_true", help="Delete all products instead of seeding")
    args = parser.parse_args()

    if args.clear:
        clear(args.shop, args.token)
    else:
        seed(args.shop, args.token)
