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
        conn.execute(
            "CREATE TABLE IF NOT EXISTS shop_tokens ("
            "platform TEXT NOT NULL, shop TEXT NOT NULL, access_token TEXT NOT NULL, "
            "created_at TEXT NOT NULL, PRIMARY KEY (platform, shop))"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS seller_stories ("
            "seller_id TEXT PRIMARY KEY, story TEXT NOT NULL, created_at TEXT NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS users ("
            "user_id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, "
            "first_name TEXT, last_name TEXT, business_name TEXT, seller_type TEXT, "
            "seller_id TEXT, created_at TEXT NOT NULL)"
        )


_USER_COLS = ["user_id", "email", "password_hash", "first_name", "last_name", "business_name", "seller_type", "seller_id"]


def create_user(user: dict) -> None:
    with _conn() as conn:
        conn.execute(
            f"INSERT INTO users ({', '.join(_USER_COLS)}, created_at) VALUES ({', '.join('?' * len(_USER_COLS))}, ?)",
            [user[c] for c in _USER_COLS] + [datetime.now(timezone.utc).isoformat()],
        )


def _user_row_to_dict(row) -> dict | None:
    return dict(zip(_USER_COLS, row)) if row else None


def get_user_by_email(email: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute(f"SELECT {', '.join(_USER_COLS)} FROM users WHERE email = ?", (email,)).fetchone()
    return _user_row_to_dict(row)


def get_user(user_id: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute(f"SELECT {', '.join(_USER_COLS)} FROM users WHERE user_id = ?", (user_id,)).fetchone()
    return _user_row_to_dict(row)


def set_user_seller(user_id: str, seller_id: str) -> None:
    with _conn() as conn:
        conn.execute("UPDATE users SET seller_id = ? WHERE user_id = ?", (seller_id, user_id))


def save_story(seller_id: str, story: dict) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO seller_stories VALUES (?, ?, ?)",
            (seller_id, json.dumps(story), datetime.now(timezone.utc).isoformat()),
        )


def get_story(seller_id: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT story FROM seller_stories WHERE seller_id = ?", (seller_id,)).fetchone()
    return json.loads(row[0]) if row else None


def save_shop_token(platform: str, shop: str, access_token: str) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO shop_tokens VALUES (?, ?, ?, ?)",
            (platform, shop, access_token, datetime.now(timezone.utc).isoformat()),
        )


def get_shop_token(platform: str, shop: str) -> str | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT access_token FROM shop_tokens WHERE platform = ? AND shop = ?", (platform, shop)
        ).fetchone()
    return row[0] if row else None


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
