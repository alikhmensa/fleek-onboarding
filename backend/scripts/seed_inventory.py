"""Embed data/inventory.json and seed the vector search.

Always writes data/embeddings.json (local fallback backend).
If PINECONE_API_KEY is set, also creates/updates the Pinecone index.

Run from backend/:  python -m scripts.seed_inventory
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import EMBED_DIM, EMBEDDINGS_PATH, INVENTORY_PATH, PINECONE_API_KEY, PINECONE_INDEX
from app.search import embed_texts


def item_text(item: dict) -> str:
    return (
        f"{item['title']}. {item['brand']} {item['category']}, condition {item['condition_grade']}. "
        f"{item['description']}"
    )


def main() -> None:
    items = json.loads(INVENTORY_PATH.read_text())
    print(f"Embedding {len(items)} inventory items...")

    vectors = {}
    batch_size = 50  # embed_content batch limit headroom
    for start in range(0, len(items), batch_size):
        batch = items[start : start + batch_size]
        vecs = embed_texts([item_text(i) for i in batch], task_type="RETRIEVAL_DOCUMENT")
        for item, vec in zip(batch, vecs):
            vectors[item["id"]] = [round(float(x), 6) for x in vec]

    EMBEDDINGS_PATH.write_text(json.dumps(vectors))
    print(f"Wrote {EMBEDDINGS_PATH} (local fallback backend)")

    if not PINECONE_API_KEY:
        print("PINECONE_API_KEY not set — skipping Pinecone upsert (local backend will be used)")
        return

    from pinecone import Pinecone, ServerlessSpec

    pc = Pinecone(api_key=PINECONE_API_KEY)
    if not pc.has_index(PINECONE_INDEX):
        print(f"Creating Pinecone index {PINECONE_INDEX}...")
        pc.create_index(
            name=PINECONE_INDEX,
            dimension=EMBED_DIM,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
    index = pc.Index(PINECONE_INDEX)
    index.upsert(vectors=[{"id": item_id, "values": vec} for item_id, vec in vectors.items()])
    print(f"Upserted {len(vectors)} vectors to Pinecone index {PINECONE_INDEX}")


if __name__ == "__main__":
    main()
