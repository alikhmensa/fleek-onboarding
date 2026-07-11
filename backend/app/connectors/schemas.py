"""Normalised platform schemas — ported from Shiv's seller-integration module
(models/schemas.py) so both halves speak the same shapes."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class ShopProfile(BaseModel):
    platform: str
    seller_id: str
    username: str
    rating: float | None = None
    total_items_sold: int | None = None
    member_since: datetime | None = None
    location: str | None = None
    profile_url: str | None = None


class ShopItem(BaseModel):
    platform: str
    item_id: str
    title: str
    description: str | None = None
    price: float
    currency: str = "GBP"
    category: str | None = None
    brand: str | None = None
    condition: str | None = None
    size: str | None = None
    color: str | None = None
    photos: list[str] = []
    status: str = "active"
    listed_at: datetime | None = None
    url: str | None = None


class ShopOrder(BaseModel):
    platform: str
    order_id: str
    item_id: str
    title: str
    price: float
    currency: str = "GBP"
    buyer_username: str | None = None
    sold_at: datetime | None = None
    status: str | None = None
    tracking_number: str | None = None


class ShopData(BaseModel):
    profile: ShopProfile | None = None
    items: list[ShopItem] = []
    orders: list[ShopOrder] = []
    total_items_fetched: int = 0
    total_orders_fetched: int = 0
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
