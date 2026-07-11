# Fleek Sourcing Copilot

**Personalised wholesale sourcing for new resellers, from their first minute on Fleek.**

New sellers are a cold-start: Fleek knows nothing about their shop, so it can't
recommend stock. This project fixes that at onboarding — the seller connects their
Shopify store, uploads an order export, or simply *talks about their shop* — and we
build a seller profile, then recommend wholesale bundles that fit their taste,
clear their margin target, and fill the gaps in their range.

> Similarity search alone would recommend sellers more of what they already have.
> The point of this system is the opposite: **fit × economics × diversification** —
> only the intersection gets recommended.

## Demo quick start

```bash
cd backend
python3.13 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env      # add GOOGLE_API_KEY; optionally PINECONE_API_KEY + SHOPIFY_ADMIN_TOKEN
.venv/bin/python -m scripts.seed_inventory    # embed inventory -> Pinecone + local fallback
.venv/bin/uvicorn app.main:app --reload       # serves API + frontend
```

Open **http://localhost:8000** — register, then either connect a store
(type `mock` for the built-in demo shop, or a real dev store name if
`SHOPIFY_ADMIN_TOKEN` is set), upload `backend/data/demo_orders.csv` /
`streetwear_vault_orders.xlsx`, or just type/record what you sell.
Runs degraded-but-alive with no API keys at all (every external call has a fallback).

## How it works

**Onboarding → profile**
- Sources merge: Shopify orders + live listings (listings stand in when a store has
  no orders), Excel/CSV exports, typed description, voice note (transcribed by Gemini)
- Deterministic maths in pandas: price band, revenue, sales velocity — never the LLM
- LLM (`gemini-3.1-flash-lite`) infers only what needs inference: aesthetic tags and
  saturation (oversupplied vs gaps); words-only onboarding also extracts a price band
  from spoken clues

**Profile → recommendations** (`backend/app/`, one file per stage)
1. `search.py` — aesthetic + gap intents → Gemini embeddings → Pinecone (local numpy fallback)
2. `economics.py` — margin ≥ target, resale within band ±25%, budget; relaxes
   progressively and reports it, never silently returns nothing
3. `rank.py` — score = fit + margin + sell-through speed; category cap, gap boost,
   oversupply penalty (the "no sixth Carhartt jacket" rule)
4. `bundle.py` — per-supplier bundles honouring MOQ within budget, or dropped entirely
5. `rationale.py` — one batched LLM call writes a one-line why-this-fits per bundle

**Product surface** (`frontend/`, vanilla JS served by the backend)
- Fleek-branded onboarding: register/login (PBKDF2 + JWT), tell-us-about-your-shop
  (type or record), optional store/spreadsheet connect
- Marketplace home: picked-for-your-shop bundles, collections, searchable product grid
- Profile page (avatar): AI-written seller story + business-size stats, the order
  history the profile was built from (source-tagged), and the exact words/transcript
  the AI received

## Repo layout

| Path | What |
|---|---|
| `backend/app/` | FastAPI app — pipeline stages, auth, connectors, storage (SQLite) |
| `backend/scripts/` | Inventory generator/seeder, Shopify dev-store populator, demo xlsx |
| `backend/data/` | 200-item mock inventory, demo order files, `SCENARIO.md` (demo personas) |
| `frontend/` | Onboarding + marketplace UI (served at `/` by the backend) |
| `seller-integration/` (Shiv branch) | Original platform connectors this grew from |

## Keys (all optional except Google)

| Env var | Enables | Without it |
|---|---|---|
| `GOOGLE_API_KEY` | Profile/rationale LLM, embeddings, voice transcription | heuristic profile, keyword search |
| `PINECONE_API_KEY` | Vector search | local numpy over `embeddings.json` |
| `SHOPIFY_ADMIN_TOKEN` | One-click direct connect to the demo dev store | OAuth flow (needs VEND app secret) |
| `SHOPIFY_API_KEY/SECRET` | OAuth store connect | direct token or `mock` |
