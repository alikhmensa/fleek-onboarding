# Fleek Sourcing Copilot

# LIVE at: https://fleek-onboarding.onrender.com/

**Personalised wholesale sourcing for resellers, from their first minute on Fleek.**

A seller connects their Shopify store, uploads an order export, or simply *talks
about their shop* — and gets a full seller profile plus wholesale bundles picked
to fit their taste, clear their margin target, and fill the gaps in their range.

> Similarity search alone would recommend sellers more of what they already have.
> This system recommends the intersection of **fit × economics × diversification**.

## Tech stack

| Layer | Tech |
|---|---|
| API & pipeline | Python · FastAPI · pandas |
| AI | Gemini 3.1 Flash-Lite (profiling, rationales, voice transcription) · Gemini embeddings (768-d) |
| Vector search | Pinecone (serverless, cosine) |
| Data | SQLite (users, profiles, order history, AI stories) · 200-item embedded inventory |
| Integrations | Shopify Admin API (OAuth + direct token) · Excel/CSV ingest · browser voice capture |
| Auth | PBKDF2 password hashing · JWT sessions |
| Frontend | Vanilla JS SPA, Fleek-branded, served by the backend |

## The logic

**Onboarding → seller profile**
- Sources merge into one sales history: Shopify orders + live listings, spreadsheet
  exports, typed notes, and a voice note transcribed by Gemini
- Deterministic maths in pandas: price band, est. monthly revenue, sales velocity
- The LLM infers only what needs inference: aesthetic tags and saturation —
  what the shop is **oversupplied** in vs its **gaps**. Words-only onboarding even
  extracts a price band from spoken clues ("around thirty to fifty pounds" → £30–50)

**Profile → recommendations** — a 5-stage pipeline (`backend/app/`, one file per stage)
1. **Vector search** — aesthetic *and gap* intents → Gemini embeddings → Pinecone,
   so adjacent categories enter the candidate pool at all
2. **Economics filter** — pure Python: predicted resale ÷ cost ≥ the seller's margin
   target, resale within their price band ±25%, budget respected. Thresholds relax
   progressively and report themselves — never a silent empty result
3. **Diversify + re-rank** — `score = 0.5·fit + 0.3·margin + 0.2·sell-through speed`,
   then a category cap, a boost for gap categories and a penalty for oversupplied
   ones: never a sixth Carhartt jacket
4. **Bundling** — grouped per supplier, honouring MOQ within budget or dropped entirely
5. **Rationales** — one batched LLM call explains each bundle in the seller's terms

**The product surface**
- Fleek-branded onboarding: register/login, describe-or-record your shop,
  one-click store connect
- Marketplace home: picked-for-your-shop bundles, collections, searchable inventory grid
- Profile page: an AI-written seller story grounded in computed stats, the exact
  source-tagged order history the profile was built from, and the verbatim
  words/transcript the AI received — full provenance, nothing hidden

**Resilience** — every external dependency has a live fallback: keyword search if
embeddings are unreachable, local numpy vectors if Pinecone is, template profiles
and rationales if the LLM is. The demo cannot be killed by a single outage.

## Run it

```bash
cd backend
python3.13 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env      # add GOOGLE_API_KEY; optionally PINECONE_API_KEY + SHOPIFY_ADMIN_TOKEN
.venv/bin/python -m scripts.seed_inventory    # embed inventory -> Pinecone
.venv/bin/uvicorn app.main:app --reload       # serves API + frontend
```

Open **http://localhost:8000** — register, connect a store (`mock` works out of the
box), upload `backend/data/demo_orders.csv`, or just say what you sell.
