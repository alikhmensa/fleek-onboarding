# Seller Integration — Backend Technical Reference

## Architecture

```
Frontend (your app)
    │
    ├── Vinted: POST /connect/vinted {profile_url}
    ├── Shopify: GET /connect/shopify?shop=store.myshopify.com → OAuth redirect
    ├── eBay: GET /connect/ebay → OAuth redirect
    │
    ▼
server.py (Flask, port 8000)
    │
    ├── Handles OAuth callbacks (/callback/shopify, /callback/ebay)
    ├── Stores access tokens per user
    ├── Exposes unified data endpoints
    │
    ▼
integrations/ (platform-specific logic)
    │
    ▼
models/schemas.py (unified output format)
```

## How each platform connects

### Vinted (no auth)

No OAuth. No API key. Seller pastes their profile URL, we scrape public listings.

```
POST /connect/vinted
Content-Type: application/json

{"profile_url": "https://www.vinted.co.uk/member/12345-username"}
```

Response:
```json
{"status": "connected", "platform": "vinted", "seller_id": "12345"}
```

Then fetch data:
```
GET /api/seller/vinted/12345?items_limit=50
```

Limitations:
- Items and profile only. No order history (requires Vinted Pro API — allowlisted business accounts only).
- Scraper may get rate-limited under heavy use. Add delays between requests in production.
- Vinted runs Datadome bot detection. Works reliably for moderate usage.

### Shopify (OAuth)

Requires app credentials in `.env`:
```
SHOPIFY_API_KEY=your_client_id
SHOPIFY_API_SECRET=your_client_secret
SHOPIFY_REDIRECT_URI=http://localhost:8000/callback/shopify
SHOPIFY_SCOPES=read_orders,read_products,read_inventory
```

OAuth flow:
1. Frontend redirects user to `GET /connect/shopify?shop=store.myshopify.com`
2. Server redirects to Shopify OAuth consent screen
3. User approves → Shopify redirects to `/callback/shopify?code=xxx&shop=store.myshopify.com`
4. Server exchanges code for access token
5. Token stored, ready to fetch data

Fetch data:
```
GET /api/seller/shopify/store.myshopify.com?items_limit=50&orders_limit=50
```

Data available: products, orders (with line items, fulfillment status, tracking), shop profile.

### eBay (OAuth)

Requires app credentials in `.env`:
```
EBAY_CLIENT_ID=your_client_id
EBAY_CLIENT_SECRET=your_client_secret
EBAY_REDIRECT_URI=http://localhost:8000/callback/ebay
EBAY_SANDBOX=true
```

OAuth flow: same pattern as Shopify.
1. `GET /connect/ebay` → redirects to eBay login
2. User approves → `/callback/ebay?code=xxx`
3. Token stored

Fetch data:
```
GET /api/seller/ebay/user_id?items_limit=50&orders_limit=50
```

Data available: inventory items, orders (with tracking numbers, buyer info), seller profile.

## Multi-platform onboard (single call)

Pull from all connected platforms at once:

```
POST /api/onboard
Content-Type: application/json

{
    "vinted_url": "https://www.vinted.co.uk/member/12345-username",
    "shopify_shop": "store.myshopify.com",
    "ebay_user_id": "ebay_user"
}
```

Response contains data from each connected platform. Unconnected platforms return `{"error": "Not connected"}`.

## Unified data models

All platforms return the same format. See `models/schemas.py`.

### SellerProfile
```json
{
    "platform": "vinted",
    "seller_id": "12345",
    "username": "seller_name",
    "rating": null,
    "total_items_sold": null,
    "member_since": null,
    "location": null,
    "profile_url": "https://..."
}
```

### SellerItem
```json
{
    "platform": "shopify",
    "item_id": "123",
    "title": "Nike Air Max 90",
    "description": "Worn twice, excellent condition",
    "price": 85.0,
    "currency": "GBP",
    "category": "Shoes",
    "brand": "Nike",
    "condition": "Very good",
    "size": "UK 10",
    "color": "White",
    "photos": ["https://...jpg", "https://...jpg"],
    "status": "active",
    "listed_at": "2025-01-15T10:30:00+00:00",
    "url": "https://..."
}
```

### SellerOrder
```json
{
    "platform": "shopify",
    "order_id": "ORD-001",
    "item_id": "123",
    "title": "Nike Air Max 90",
    "price": 85.0,
    "currency": "GBP",
    "buyer_username": "buyer@email.com",
    "sold_at": "2025-02-01T14:20:00+00:00",
    "status": "fulfilled",
    "tracking_number": "RM123456789GB"
}
```

## Token storage — MUST CHANGE FOR PRODUCTION

Currently tokens are stored in-memory:
```python
token_store = {}  # dies when server restarts
```

For production, replace with your database. The token store needs:
- Key: `"{platform}:{user_identifier}"` (e.g. `"shopify:store.myshopify.com"`)
- Value: `{"access_token": "...", "refresh_token": "...", "shop_domain": "..."}`
- Should be tied to the Fleek user ID from your auth system

eBay tokens expire (2 hours). Use the refresh token to get new ones — see `EbayOAuth.refresh_token()` in `oauth.py`.

Shopify tokens don't expire unless the user uninstalls the app.

## Testing without real credentials

Mock data is available for testing without connecting real stores:
```
GET /api/mock/shopify
GET /api/mock/ebay
GET /api/mock/vinted
```

These return realistic fake data in the same format as real endpoints.

Vinted works with real data immediately — no credentials needed:
```
GET /api/seller/vinted/82993401?items_limit=5
```

## API reference

| Endpoint | Method | Auth needed | Returns |
|---|---|---|---|
| `/api/platforms` | GET | None | List of supported platforms |
| `/connect/vinted` | POST | None | Connects via profile URL |
| `/connect/shopify` | GET | Shopify creds in .env | OAuth redirect |
| `/connect/ebay` | GET | eBay creds in .env | OAuth redirect |
| `/callback/shopify` | GET | — | OAuth callback (Shopify calls this) |
| `/callback/ebay` | GET | — | OAuth callback (eBay calls this) |
| `/api/seller/<platform>/<id>` | GET | Token must exist | Seller data |
| `/api/onboard` | POST | Tokens for each platform | Multi-platform data |
| `/api/mock/<platform>` | GET | None | Mock test data |

## Environment variables

| Variable | Required for | Example |
|---|---|---|
| `SHOPIFY_API_KEY` | Shopify | Client ID from Partners dashboard |
| `SHOPIFY_API_SECRET` | Shopify | Client Secret (keep secret) |
| `SHOPIFY_REDIRECT_URI` | Shopify | `http://localhost:8000/callback/shopify` |
| `SHOPIFY_SCOPES` | Shopify | `read_orders,read_products,read_inventory` |
| `EBAY_CLIENT_ID` | eBay | App ID from developer.ebay.com |
| `EBAY_CLIENT_SECRET` | eBay | Cert ID (keep secret) |
| `EBAY_REDIRECT_URI` | eBay | `http://localhost:8000/callback/ebay` |
| `EBAY_SANDBOX` | eBay | `true` for testing, `false` for production |
| `FLASK_SECRET_KEY` | Server | Random string for session signing |

## Running locally

```bash
cd seller-integration
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your credentials
python server.py       # runs on port 8000
```

## File structure

```
integrations/
  base.py       — Abstract class. All platforms implement get_profile(), get_items(), get_orders()
  vinted.py     — Uses vinted-scraper library. No auth.
  shopify.py    — Shopify Admin API. Needs OAuth token.
  ebay.py       — eBay REST API. Needs OAuth token.
  oauth.py      — OAuth helpers for Shopify and eBay (login URLs, token exchange, refresh)
  __init__.py   — Platform registry. get_integration("vinted") returns the right class.

models/
  schemas.py    — Pydantic models: SellerProfile, SellerItem, SellerOrder, OnboardingData

utils/
  export.py     — Export to JSON/CSV files

server.py       — Flask API. All endpoints.
main.py         — CLI for manual testing.
```

## Adding a new platform

1. Create `integrations/newplatform.py` — implement `BaseIntegration` (get_profile, get_items, get_orders)
2. Add OAuth class in `oauth.py` if needed
3. Register in `integrations/__init__.py` PLATFORMS dict
4. Add connect/callback routes in `server.py`
5. Add env vars to `.env.example`
