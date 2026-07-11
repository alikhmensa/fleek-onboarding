# Fleek Seller Integration

Pull seller data from external platforms (Vinted, eBay, Shopify) into Fleek through a unified API. Built for the Fleek x a16z hackathon.

## What it does

When a seller wants to onboard to Fleek, this module pulls their existing listings, order history, and profile from other platforms into a single normalized format. Your frontend/backend calls these endpoints and gets consistent data regardless of source.

### Platform support

| Platform | Auth method | What you get | Status |
|---|---|---|---|
| **Vinted** | None (paste profile URL) | Items, photos, prices, brands, sizes, condition | Working now |
| **eBay** | OAuth (seller clicks "Connect") | Items, full order history, tracking, profile | Ready (needs API credentials) |
| **Shopify** | OAuth (seller clicks "Connect") | Products, orders, fulfillment data, profile | Ready (needs API credentials) |

### Data pulled per item

- Title, description, price, currency
- Brand, condition (New/Very good/Good), size, color
- Multiple photo URLs (full resolution)
- Item URL, listing status

### Data pulled per order (eBay/Shopify only)

- Order ID, item details, sale price
- Buyer info, sale date
- Fulfillment status, tracking number

## Setup

```bash
cd seller-integration
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

For eBay/Shopify, copy `.env.example` to `.env` and fill in your API credentials:

```bash
cp .env.example .env
```

## Usage

### API server (for frontend/backend integration)

```bash
python server.py
```

Runs on `http://localhost:5000`.

### API endpoints

**List available platforms:**
```
GET /api/platforms
```

**Connect a seller:**
```
# Vinted - just post the profile URL
POST /connect/vinted
{"profile_url": "https://www.vinted.co.uk/member/12345-username"}

# eBay - redirects seller to OAuth login
GET /connect/ebay

# Shopify - redirects seller to OAuth login
GET /connect/shopify?shop=mystore.myshopify.com
```

**Fetch seller data from one platform:**
```
GET /api/seller/vinted/12345?items_limit=50
GET /api/seller/ebay/user_id?items_limit=50&orders_limit=50
GET /api/seller/shopify/store.myshopify.com?items_limit=50
```

**Onboard from all connected platforms at once:**
```
POST /api/onboard
{
    "vinted_url": "https://www.vinted.co.uk/member/12345-username",
    "ebay_user_id": "ebay_user",
    "shopify_shop": "mystore.myshopify.com"
}
```

### CLI (for testing/scripts)

```bash
# Pull a Vinted seller's listings
python main.py vinted 12345678

# Limit items and choose export format
python main.py vinted 12345678 --items-limit 20 --format json

# Different Vinted country
python main.py vinted 12345678 --domain https://www.vinted.fr
```

Exports go to `output/` as JSON and/or CSV.

## How the onboarding flow works

1. Seller signs up on Fleek
2. Frontend shows "Connect your existing stores"
3. **Vinted**: seller pastes their Vinted profile URL. Backend extracts seller ID, pulls all public listings instantly. No auth needed.
4. **eBay/Shopify**: seller clicks "Connect". Gets redirected to eBay/Shopify OAuth. Authorizes Fleek. Callback stores access token. Backend pulls items + full order history.
5. All data comes back in the same unified format regardless of platform

## Getting eBay/Shopify credentials

**eBay:**
1. Create account at [developer.ebay.com](https://developer.ebay.com)
2. Create an application in the dashboard
3. Copy Client ID and Client Secret to `.env`
4. Sandbox access is instant and free for testing

**Shopify:**
1. Create account at [partners.shopify.com](https://partners.shopify.com)
2. Create an app in the Partners Dashboard
3. Copy API Key and API Secret to `.env`
4. Create a free development store for testing

## Project structure

```
seller-integration/
├── server.py                  # Flask API server
├── main.py                    # CLI entry point
├── requirements.txt
├── .env.example               # Credentials template
├── integrations/
│   ├── base.py                # Abstract interface all platforms implement
│   ├── vinted.py              # Vinted scraper integration
│   ├── ebay.py                # eBay REST API integration
│   ├── shopify.py             # Shopify Admin API integration
│   └── oauth.py               # OAuth flows for eBay + Shopify
├── models/
│   └── schemas.py             # Unified data models (SellerProfile, SellerItem, SellerOrder)
└── utils/
    └── export.py              # JSON/CSV export
```

## Adding a new platform

1. Create `integrations/newplatform.py` implementing `BaseIntegration`
2. Implement `get_profile()`, `get_items()`, `get_orders()`
3. Register it in `integrations/__init__.py` PLATFORMS dict
4. Add OAuth flow in `oauth.py` and routes in `server.py` if needed
