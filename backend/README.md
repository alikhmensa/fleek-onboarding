# Fleek Sourcing Copilot — backend

Cold-start fix for new resellers: upload their Shopify orders CSV at onboarding,
infer their taste/price-band/gaps, recommend Fleek stock as per-supplier bundles
that clear their margin threshold and fill gaps (never "more of the same").

## Quick start

```bash
cd backend
python3.13 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env          # add GOOGLE_API_KEY (+ optionally PINECONE_API_KEY)
.venv/bin/python -m scripts.seed_inventory   # embed inventory -> Pinecone + local fallback
.venv/bin/uvicorn app.main:app --reload      # http://localhost:8000/docs
```

Runs degraded but alive with **no keys at all**: heuristic profile, keyword-overlap
search, template rationales. Every fallback logs loudly, so you can tell.

## Endpoints (frontend contract)

```
GET  /connect/shopify?shop=mystore.myshopify.com   # redirects to Shopify OAuth
GET  /callback/shopify                             # OAuth callback (registered in the VEND app);
                                                   # redirects to FRONTEND_URL if set, else JSON
GET  /shopify/status?shop=...                      # { shop, connected } — poll after the OAuth popup

POST /onboard — all sources optional, at least one order source required:
  multipart form:
    shopify_shop=<connected shop domain, or "mock" for the demo shop>
    file=<orders .csv or .xlsx>
    description=<free text: the seller describing their own shop>
    budget=<optional float>  margin_multiple=<optional, default 3.0>
  -> { "seller_id": "s_ab12", "profile": { aesthetic, price_band, saturation, ... } }

  Shopify orders + file rows merge into one sales history; the shop's ACTIVE
  listings feed the saturation analysis; the description is injected into the
  profile prompt as the seller's own words.

GET /recommendations?seller_id=...&budget=...
  -> { "bundles": [ { supplier_id, items[], total_cost, est_margin, est_clear_days, rationale } ],
       "relaxations": [] }   # non-empty if filters had to loosen to find stock

GET /recommendations?mock=true   # serves data/fixtures/bundles.json — build the UI against this
```

Try it: `curl -F "file=@data/demo_orders.csv" localhost:8000/onboard`
Or the full multi-source flow with zero credentials:
`curl -F "shopify_shop=mock" -F "description=I sell 90s sportswear, no shoes" localhost:8000/onboard`

Real Shopify OAuth needs `SHOPIFY_API_KEY`/`SHOPIFY_API_SECRET` in `.env` (the "VEND"
app in the Partners dashboard — Shiv has it; its registered callback is
`http://localhost:8000/callback/shopify`, which this server hosts). Without the
`read_all_orders` scope Shopify returns only ~60 days of orders — fine for a fresh
dev store.

## Pipeline (app/, one file per stage)

1. `ingest.py` — pandas CSV parse; price_band + budget computed deterministically, never by the LLM
2. `profile.py` — gemini-2.5-flash-lite infers aesthetic + saturation (oversupplied/gaps)
3. `search.py` — Gemini embeddings -> Pinecone (or local numpy fallback), gaps added as search intents
4. `economics.py` — margin >= threshold, resale in price band ±25%, budget; relaxes progressively, reports it
5. `rank.py` — score = 0.5·fit + 0.3·margin + 0.2·speed; category cap, gap boost, oversupply penalty
6. `bundle.py` — per-supplier, diversified picks lead, viable items pad MOQ; sub-MOQ bundles dropped
7. `rationale.py` — one batched flash-lite call writes a one-liner per bundle

Stages 4 and 5 are the point of the product — do not collapse them into plain vector search.

## For the dataset owner

Replace `data/demo_orders.csv` and `data/inventory.json` (schema: see any item), then
re-run `scripts/seed_inventory.py`. Keep it **winnable**: for each demo seller CSV,
>=15 items must clear 3x margin with resale inside the seller's price band ±25%,
across >=3 categories and >=3 suppliers, including the profile's gap categories —
otherwise the economics filter empties the funnel on stage.
