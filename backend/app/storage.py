import json
import sqlite3
import uuid
from datetime import datetime, timezone

from .config import DB_PATH
from .schemas import SellerProfile


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    with _conn() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS profiles ("
            "seller_id TEXT PRIMARY KEY, profile TEXT NOT NULL, created_at TEXT NOT NULL)"
        )


def new_seller_id() -> str:
    return "s_" + uuid.uuid4().hex[:8]


def save_profile(seller_id: str, profile: SellerProfile) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO profiles VALUES (?, ?, ?)",
            (seller_id, profile.model_dump_json(), datetime.now(timezone.utc).isoformat()),
        )


def get_profile(seller_id: str) -> SellerProfile | None:
    with _conn() as conn:
        row = conn.execute("SELECT profile FROM profiles WHERE seller_id = ?", (seller_id,)).fetchone()
    return SellerProfile(**json.loads(row[0])) if row else None
