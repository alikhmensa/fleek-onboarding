import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"
DB_PATH = DATA_DIR / "app.db"
INVENTORY_PATH = DATA_DIR / "inventory.json"
EMBEDDINGS_PATH = DATA_DIR / "embeddings.json"
FIXTURES_DIR = DATA_DIR / "fixtures"

load_dotenv(BACKEND_DIR / ".env")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
PINECONE_INDEX = os.getenv("PINECONE_INDEX", "fleek-inventory")

LLM_MODEL = "gemini-3.1-flash-lite"
EMBED_MODEL = "gemini-embedding-001"
EMBED_DIM = 768

# Stage 4 — economics filter
DEFAULT_MARGIN_MULTIPLE = 3.0
BAND_TOLERANCE = 0.25  # gaps are adjacent categories; exact band would exclude them
MIN_VIABLE = 5
# (margin_multiple_scale, band_tolerance) steps tried until MIN_VIABLE items survive
RELAXATION_LADDER = [(1.0, BAND_TOLERANCE), (0.85, BAND_TOLERANCE), (0.7, BAND_TOLERANCE), (0.7, BAND_TOLERANCE * 2)]

# Stage 5 — score = W_FIT*fit + W_MARGIN*norm_margin + W_SPEED*norm_speed
W_FIT, W_MARGIN, W_SPEED = 0.5, 0.3, 0.2
CATEGORY_CAP = 2
GAP_BOOST = 0.15
OVERSUPPLY_PENALTY = 0.15

# Stage 3
TOP_K_PER_INTENT = 15

# Stage 6
MAX_BUNDLES = 4
BUNDLE_EXTRA_ITEMS = 2  # take up to MOQ + this many per supplier

# Budget inference fallback (GBP)
DEFAULT_BUDGET = 500.0
BUDGET_MIN, BUDGET_MAX = 200.0, 2000.0


@lru_cache
def genai_client():
    from google import genai

    return genai.Client(api_key=GOOGLE_API_KEY)
