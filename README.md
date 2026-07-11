# Fleek Onboarding - Companion App & Integrations

A comprehensive onboarding system for [Fleek](https://joinfleek.com/). This project consists of two parts:
1. **The Companion App (UI)**: A sleek frontend interface that guides sellers through setting up their profile, verifying emails, connecting external storefronts, and dynamically generating a curated "Fleek Persona" dashboard.
2. **The Backend Integrations (seller-integration)**: A Python-based backend architecture that seamlessly scrapes and pulls OAuth data from external marketplaces (eBay, Shopify, Vinted).

---

## Part 1: The Companion App (Frontend UI)

### 🚀 Features

- **Multi-step Onboarding Flow:** Seamlessly animated step-by-step UI to gather user information.
- **Simulated Store Integration:** UI flows for connecting stores and simulating product imports.
- **Dynamic Persona Generation:** Analyzes uploaded files, voice notes, or text inputs to dynamically generate the seller's curated profile and recommend wholesale bundles.
- **Smart Settings Modal:** A comprehensive, interactive settings page to edit personal details, security settings, and sourcing preferences.
- **System-Aware Theming:** Automatically adapts to the user's operating system preferences, gracefully switching between Fleek's signature Light Mode and a deep, low-contrast Dark Mode.
- **Responsive Design:** Completely mobile-friendly.

### 💻 How to Run Locally

You don't need any complex build steps or node modules to run the frontend. 

1. Clone the repository.
2. Open a terminal in the root folder (`fleek-companion`).
3. Start a local Python HTTP server:
   ```bash
   python3 -m http.server 8080
   ```
4. Open your browser and navigate to `http://localhost:8080`.

*(Alternatively, you can use `npx serve .` or the VSCode Live Server extension).*

### 🔌 Integrating a Pinecone Backend (AI Vector Search)

Currently, the "Recommended Bundles" generated on the Persona Page are powered by simulated mock data in the frontend. To turn this into a powerful, AI-driven recommendation engine, we can integrate a **Pinecone Vector Database**.

#### Why Pinecone?
Because sellers define their sourcing preferences using unstructured data (e.g. "I sell Y2K aesthetics and 90s hip-hop vintage"), standard SQL queries struggle to match them to relevant wholesale bundles. Pinecone allows us to perform **semantic search**, matching the *meaning* of their preferences to the *descriptions* of wholesale bundles.

#### Implementation Strategy

1. **Vectorizing User Preferences (Embedding):**
   - When a user submits their sourcing preferences on step 5 (via text, voice transcript, or CSV), the backend server will pass this text to an LLM embedding model (such as OpenAI's `text-embedding-3-small`).
   - The model will convert the text into a high-dimensional vector array.

2. **Storing Bundles in Pinecone:**
   - Every wholesale bundle listed on Fleek will have its description, brand tags, and categories embedded into vectors and stored as records in a Pinecone Index.
   - Example Pinecone Record: 
     ```json
     {
       "id": "bundle-1234",
       "values": [0.012, -0.054, ...], 
       "metadata": { "brands": ["Carhartt", "Dickies"], "category": "Workwear" }
     }
     ```

3. **Querying Recommendations:**
   - Once the user's persona is generated, the backend will query Pinecone using the user's specific preference vector.
   - Pinecone will return the Top-K (e.g. top 4) bundles that mathematically share the highest cosine similarity to the user's vector.
   - The frontend will receive these IDs and render the exact, dynamically matched bundles on the Persona page.

#### Example API Architecture
- **Frontend** -> `POST /api/onboard` (sends preferences)
- **Node/Python Backend** -> Calls OpenAI API to generate Vector `V`.
- **Backend** -> Calls Pinecone `index.query({ vector: V, topK: 4 })`
- **Backend** -> Returns the matched bundles to the Frontend.

---

## Part 2: Backend Integrations (`seller-integration`)

Unified interface for importing seller data (profile, items, orders) from multiple platforms into Fleek.

### Supported platforms

| Platform | Auth Method | Data Available | Status |
| :--- | :--- | :--- | :--- |
| **Vinted** | No auth needed (public scraper) | Items, profile | Ready |
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

### Setup

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

### Usage

#### API server (for frontend/backend integration)

```bash
python server.py
```

Runs on `http://localhost:5000`.

#### API endpoints

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

#### CLI (for testing/scripts)

```bash
# Pull a Vinted seller's listings
python main.py vinted 12345678

# Limit items and choose export format
python main.py vinted 12345678 --items-limit 20 --format json

# Different Vinted country
python main.py vinted 12345678 --domain https://www.vinted.fr
```

Exports go to `output/` as JSON and/or CSV.

### How the onboarding flow works

1. Seller signs up on Fleek
2. Frontend shows "Connect your existing stores"
3. **Vinted**: seller pastes their Vinted profile URL. Backend extracts seller ID, pulls all public listings instantly. No auth needed.
4. **eBay/Shopify**: seller clicks "Connect". Gets redirected to eBay/Shopify OAuth. Authorizes Fleek. Callback stores access token. Backend pulls items + full order history.
5. All data comes back in the same unified format regardless of platform

### Getting eBay/Shopify credentials

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

### Project structure

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

### Adding a new platform

1. Create `integrations/newplatform.py` implementing `BaseIntegration`
2. Implement `get_profile()`, `get_items()`, `get_orders()`
3. Register it in `integrations/__init__.py` PLATFORMS dict
4. Add OAuth flow in `oauth.py` and routes in `server.py` if needed
