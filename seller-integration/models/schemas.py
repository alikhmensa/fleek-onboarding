from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel


class SellerProfile(BaseModel):
    platform: str
    seller_id: str
    username: str
    rating: float | None = None
    total_items_sold: int | None = None
    member_since: datetime | None = None
    location: str | None = None
    profile_url: str | None = None


class SellerItem(BaseModel):
    platform: str
    item_id: str
    title: str
    description: str | None = None
    price: float
    currency: str = "EUR"
    category: str | None = None
    brand: str | None = None
    condition: str | None = None
    size: str | None = None
    color: str | None = None
    photos: list[str] = []
    status: str = "active"
    listed_at: datetime | None = None
    url: str | None = None


class SellerOrder(BaseModel):
    platform: str
    order_id: str
    item_id: str
    title: str
    price: float
    currency: str = "EUR"
    buyer_username: str | None = None
    sold_at: datetime | None = None
    status: str | None = None
    tracking_number: str | None = None


class OnboardingData(BaseModel):
    profile: SellerProfile | None = None
    items: list[SellerItem] = []
    orders: list[SellerOrder] = []
    total_items_fetched: int = 0
    total_orders_fetched: int = 0
    fetched_at: datetime = datetime.now()
