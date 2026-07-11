"""Real authentication: users in SQLite, PBKDF2 password hashes, JWT sessions.

POST /auth/register  {email, password, first_name, ...} -> {token, user}
POST /auth/login     {email, password}                  -> {token, user}
GET  /auth/me        Authorization: Bearer <jwt>        -> {user}

The JWT carries only the user_id (sub) and expiry; onboarding links the
resulting seller_id onto the user row so sessions survive page refreshes.
"""

import hashlib
import os
import secrets
import time
import uuid

import jwt
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from . import storage

JWT_SECRET = os.getenv("JWT_SECRET", "fleek-dev-secret-change-in-prod")
JWT_TTL_SECONDS = 7 * 24 * 3600
_PBKDF2_ITERATIONS = 200_000

router = APIRouter(prefix="/auth", tags=["auth"])


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), _PBKDF2_ITERATIONS)
    return f"{salt}${digest.hex()}"

def verify_password(password: str, stored: str) -> bool:
    salt, expected = stored.split("$", 1)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), _PBKDF2_ITERATIONS)
    return secrets.compare_digest(digest.hex(), expected)


def create_token(user_id: str) -> str:
    now = int(time.time())
    return jwt.encode({"sub": user_id, "iat": now, "exp": now + JWT_TTL_SECONDS}, JWT_SECRET, algorithm="HS256")


def user_id_from_header(authorization: str | None) -> str | None:
    """Optional auth: returns the user_id for a valid Bearer token, else None."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        return jwt.decode(authorization[7:], JWT_SECRET, algorithms=["HS256"])["sub"]
    except jwt.InvalidTokenError:
        return None


def require_user(authorization: str | None) -> dict:
    user_id = user_id_from_header(authorization)
    user = storage.get_user(user_id) if user_id else None
    if user is None:
        raise HTTPException(status_code=401, detail="invalid or expired token — log in again")
    return user


class RegisterBody(BaseModel):
    email: str
    password: str
    first_name: str = ""
    last_name: str = ""
    business_name: str = ""
    seller_type: str = ""


class LoginBody(BaseModel):
    email: str
    password: str


def _public(user: dict) -> dict:
    return {k: v for k, v in user.items() if k != "password_hash"}


@router.post("/register")
def register(body: RegisterBody) -> dict:
    email = body.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=422, detail="enter a valid email address")
    if len(body.password) < 8:
        raise HTTPException(status_code=422, detail="password must be at least 8 characters")
    if storage.get_user_by_email(email):
        raise HTTPException(status_code=409, detail="an account with this email already exists — log in instead")
    user = {
        "user_id": "u_" + uuid.uuid4().hex[:8],
        "email": email,
        "password_hash": hash_password(body.password),
        "first_name": body.first_name.strip(),
        "last_name": body.last_name.strip(),
        "business_name": body.business_name.strip(),
        "seller_type": body.seller_type,
        "seller_id": None,
    }
    storage.create_user(user)
    return {"token": create_token(user["user_id"]), "user": _public(user)}


@router.post("/login")
def login(body: LoginBody) -> dict:
    user = storage.get_user_by_email(body.email.strip().lower())
    if user is None or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="wrong email or password")
    return {"token": create_token(user["user_id"]), "user": _public(user)}


@router.get("/me")
def me(authorization: str | None = Header(default=None)) -> dict:
    return {"user": _public(require_user(authorization))}
