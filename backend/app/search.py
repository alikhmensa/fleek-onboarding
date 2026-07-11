"""Stage 3 — embed search intents (Gemini) and pull candidates from the inventory.

Backends are swappable: Pinecone when configured, otherwise a local numpy
cosine-similarity search over data/embeddings.json (seeded by scripts/seed_inventory.py).
Each candidate carries its best cosine score as `fit` — stage 5 reads it, never recomputes.
"""

import json
import logging

import numpy as np

from .config import (
    EMBED_DIM,
    EMBED_MODEL,
    EMBEDDINGS_PATH,
    PINECONE_API_KEY,
    PINECONE_INDEX,
    TOP_K_PER_INTENT,
    genai_client,
)
from .schemas import Candidate, InventoryItem, SellerProfile

log = logging.getLogger(__name__)


def embed_texts(texts: list[str], task_type: str) -> np.ndarray:
    from google.genai import types

    resp = genai_client().models.embed_content(
        model=EMBED_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(output_dimensionality=EMBED_DIM, task_type=task_type),
    )
    vecs = np.array([e.values for e in resp.embeddings], dtype=np.float32)
    # gemini-embedding-001 vectors are only pre-normalised at 3072 dims
    return vecs / np.linalg.norm(vecs, axis=1, keepdims=True)


class LocalBackend:
    """Numpy cosine search over the embeddings file — no network, demo insurance."""

    def __init__(self):
        data = json.loads(EMBEDDINGS_PATH.read_text())
        self.ids = list(data)
        matrix = np.array([data[i] for i in self.ids], dtype=np.float32)
        self.matrix = matrix / np.linalg.norm(matrix, axis=1, keepdims=True)

    def search(self, vector: np.ndarray, k: int) -> list[tuple[str, float]]:
        sims = self.matrix @ vector
        top = np.argsort(sims)[::-1][:k]
        return [(self.ids[i], float(sims[i])) for i in top]


class PineconeBackend:
    def __init__(self):
        from pinecone import Pinecone

        self.index = Pinecone(api_key=PINECONE_API_KEY).Index(PINECONE_INDEX)

    def search(self, vector: np.ndarray, k: int) -> list[tuple[str, float]]:
        res = self.index.query(vector=vector.tolist(), top_k=k)
        return [(m["id"], float(m["score"])) for m in res["matches"]]


_backend = None


def get_backend():
    global _backend
    if _backend is None:
        if PINECONE_API_KEY:
            try:
                _backend = PineconeBackend()
                log.info("vector search: Pinecone (%s)", PINECONE_INDEX)
            except Exception:
                log.exception("Pinecone unavailable — falling back to local numpy search")
        if _backend is None:
            _backend = LocalBackend()
            log.info("vector search: local numpy backend")
    return _backend


def build_intents(profile: SellerProfile) -> list[str]:
    # Aesthetic drives fit; gaps are added as intents so gap items enter the
    # candidate pool at all — stage 5 can only boost what stage 3 retrieved.
    style = profile.aesthetic[0] if profile.aesthetic else "vintage"
    intents = [f"{a} secondhand clothing" for a in profile.aesthetic]
    intents += [f"{style} {gap}" for gap in profile.saturation.gaps]
    return intents


def find_candidates(profile: SellerProfile, inventory: dict[str, InventoryItem]) -> list[Candidate]:
    intents = build_intents(profile)
    try:
        vectors = embed_texts(intents, task_type="RETRIEVAL_QUERY")
        backend = get_backend()
    except Exception:
        log.exception("vector search unavailable — falling back to keyword-overlap fit")
        return _keyword_candidates(intents, inventory)

    best_fit: dict[str, float] = {}
    for vec in vectors:
        for item_id, score in backend.search(vec, TOP_K_PER_INTENT):
            if item_id in inventory:
                best_fit[item_id] = max(best_fit.get(item_id, 0.0), score)

    return [Candidate(**inventory[i].model_dump(), fit=fit) for i, fit in best_fit.items()]


def _keyword_candidates(intents: list[str], inventory: dict[str, InventoryItem]) -> list[Candidate]:
    """Last-resort fit scoring when embeddings are unreachable: token overlap per intent."""
    candidates = []
    for item in inventory.values():
        item_tokens = set(f"{item.title} {item.brand} {item.category} {item.description}".lower().split())
        fit = max(
            len(set(intent.lower().split()) & item_tokens) / len(intent.split()) for intent in intents
        )
        if fit > 0:
            candidates.append(Candidate(**item.model_dump(), fit=round(fit, 3)))
    candidates.sort(key=lambda c: c.fit, reverse=True)
    return candidates[: TOP_K_PER_INTENT * 3]
