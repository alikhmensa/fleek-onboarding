# Fleek Seller Onboarding

**Fleek x a16z Hackathon, London 2026**

## The Problem

Secondhand fashion sellers already run shops on Shopify, Vinted, and eBay. When they join Fleek's wholesale marketplace, they have to manually describe what they sell, what price points they work at, and what brands they carry — then browse hundreds of wholesale bundles to find ones that actually match their shop. This takes hours, most sellers drop off before finishing, and the ones who stay often pick the wrong inventory.

## The Solution

One-click onboarding. A seller connects their existing store, and the system does the rest:

1. **Pulls their real sales data** — items, orders, prices, brands — directly from Shopify (Vinted and eBay coming soon)
2. **Builds a seller profile using AI** — Gemini analyses their sales history to extract price bands, brand affinities, category focus, and selling style
3. **Recommends wholesale bundles** — vector search matches the profile against Fleek's supplier inventory, filters by economics (margin, MOQ), and returns ranked bundles with plain-English rationales explaining why each bundle fits their shop

What used to be a manual, error-prone process that lost sellers at every step becomes a 60-second flow that ends with personalised, margin-safe restock recommendations.

## What this branch adds over AM-backend

The `AM-backend` branch (17 commits by Ali) built the core pipeline and frontend. This branch (`Pre_Deployment`) adds one commit on top that fixes critical blockers found during E2E testing:

| Problem on AM-backend | Fix on Pre_Deployment |
|---|---|
| Shopify OAuth requires API key/secret config and a consent screen redirect — too much friction for a hackathon demo | **Direct admin token flow**: backend reads `SHOPIFY_ADMIN_TOKEN` from `.env`, frontend only asks for the store name |
| Shop domain input breaks if user types `https://` prefix or omits `.myshopify.com` | **`_clean_shop()` helper** normalises input across all endpoints |
| Stores with 0 orders (e.g. new dev stores with only listings) crash the pipeline with a 422 | **Listings fallback**: active listings are used as pseudo-orders so the profile pipeline always runs |
| No way to see what was imported from Shopify | **Items dashboard**: `/shopify/items` endpoint + inventory grid with photos, prices, and brands on the results page |
| Auth note says "Secure OAuth" even when OAuth is not configured | Updated to **"Secure connection — or type 'mock' to try the demo"** |

## Architecture

```
frontend/          Vanilla HTML/CSS/JS — multi-step onboarding wizard
  index.html       Register → Connect → Enrich → Import → Results
  app.js           API calls, state management, UI rendering
  style.css        Fleek-branded responsive styles

backend/           FastAPI (Python 3.13)
  app/main.py      API server — all endpoints
  app/ingest.py    Stage 1: parse orders CSV / Shopify data → DataFrame
  app/profile.py   Stage 2: Gemini Flash Lite → seller profile
  app/search.py    Stage 3: vector search (Pinecone or local numpy)
  app/economics.py Stage 4: margin filter with progressive relaxation
  app/rank.py      Stage 5: diversify + re-rank
  app/bundle.py    Stage 6: per-supplier MOQ bundles
  app/rationale.py Stage 7: batched rationale generation
  app/connectors/  Shopify client, schemas, mock shop
  app/storage.py   SQLite for tokens and profiles

seller-integration/  Standalone Shopify/Vinted connector (reference)
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/connect/shopify/direct` | Connect store using admin token from `.env` |
| GET | `/connect/shopify?shop=` | OAuth flow (requires API key/secret) |
| GET | `/callback/shopify` | OAuth callback |
| GET | `/shopify/status?shop=` | Check connection status |
| GET | `/shopify/preview?shop=` | Item/order counts for import step |
| GET | `/shopify/items?shop=` | Full item + order data for dashboard |
| POST | `/onboard` | Ingest orders → build seller profile (stages 1-2) |
| GET | `/recommendations?seller_id=` | Profile → ranked bundles (stages 3-7) |
| GET | `/health` | Health check |

## Quick Start

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Create `backend/.env`:
```
GOOGLE_API_KEY=your-gemini-key
SHOPIFY_ADMIN_TOKEN=your-shopify-admin-token
SHOPIFY_API_KEY=optional-for-oauth
SHOPIFY_API_SECRET=optional-for-oauth
PINECONE_API_KEY=optional-uses-local-numpy-fallback
```

```bash
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend

The backend serves the frontend as static files at `http://localhost:8000/`. No separate frontend server needed.

### 3. Demo Mode

Type **"mock"** as the store name to run the full pipeline with built-in demo data — no API keys required.

## E2E Flow

1. **Register** — name and email
2. **Connect** — enter Shopify store name (or "mock")
3. **Enrich** — optional CSV upload and shop description
4. **Import** — pulls items/orders from Shopify, progress overlay
5. **Results** — seller profile DNA, imported inventory grid, recommended wholesale bundles with rationales

## Environment Variables

All secrets must be in `backend/.env` (gitignored). For CI/CD, store them as GitHub Repository Secrets under Settings → Secrets and variables → Actions.

## Tech Stack

- **Backend**: FastAPI, Pydantic, pandas, numpy
- **AI**: Google Gemini Flash Lite (profile inference + embeddings)
- **Vector Search**: Pinecone (production) / numpy (local fallback)
- **Storage**: SQLite
- **Frontend**: Vanilla JS, CSS Grid, no framework
- **Platform**: Shopify Admin API (direct token)
