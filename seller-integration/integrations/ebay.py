from __future__ import annotations
import os
from datetime import datetime
import requests
from integrations.base import BaseIntegration
from models.schemas import SellerProfile, SellerItem, SellerOrder


EBAY_API_BASE = "https://api.ebay.com"
EBAY_SANDBOX_BASE = "https://api.sandbox.ebay.com"


class EbayIntegration(BaseIntegration):
    platform = "ebay"

    def __init__(self, access_token: str = "", **kwargs):
        self.access_token = access_token
        sandbox = kwargs.get("sandbox", os.getenv("EBAY_SANDBOX", "true").lower() == "true")
        self.base_url = EBAY_SANDBOX_BASE if sandbox else EBAY_API_BASE

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def get_profile(self, seller_id: str) -> SellerProfile:
        url = f"{self.base_url}/commerce/identity/v1/user/"
        resp = requests.get(url, headers=self._headers())
        resp.raise_for_status()
        data = resp.json()
        return SellerProfile(
            platform=self.platform,
            seller_id=data.get("userId", seller_id),
            username=data.get("username", seller_id),
            rating=data.get("feedbackScore"),
            member_since=_parse_ebay_date(data.get("registrationDate")),
            location=data.get("businessAddress", {}).get("city"),
        )

    def get_items(self, seller_id: str, limit: int = 50) -> list[SellerItem]:
        url = f"{self.base_url}/sell/inventory/v1/inventory_item"
        params = {"limit": min(limit, 200), "offset": 0}
        resp = requests.get(url, headers=self._headers(), params=params)
        resp.raise_for_status()
        data = resp.json()

        items = []
        for entry in data.get("inventoryItems", [])[:limit]:
            product = entry.get("product", {})
            aspects = product.get("aspects", {})
            image_urls = product.get("imageUrls", [])
            if image_urls and isinstance(image_urls[0], str):
                photos = image_urls
            else:
                photos = [img.get("imageUrl", "") for img in image_urls if isinstance(img, dict)]

            availability = entry.get("availability", {})
            ship_avail = availability.get("shipToLocationAvailability", {})

            items.append(SellerItem(
                platform=self.platform,
                item_id=entry.get("sku", ""),
                title=product.get("title", ""),
                description=product.get("description"),
                price=0.0,
                currency="GBP",
                category=product.get("epid"),
                brand=_first(aspects.get("Brand")),
                condition=entry.get("condition"),
                size=_first(aspects.get("Size")),
                color=_first(aspects.get("Color")),
                photos=photos,
                status="active" if ship_avail.get("quantity", 0) > 0 else "out_of_stock",
            ))
        return items

    def get_orders(self, seller_id: str, limit: int = 50) -> list[SellerOrder]:
        url = f"{self.base_url}/sell/fulfillment/v1/order"
        params = {"limit": min(limit, 200)}
        resp = requests.get(url, headers=self._headers(), params=params)
        resp.raise_for_status()
        data = resp.json()

        orders = []
        for order in data.get("orders", [])[:limit]:
            for line in order.get("lineItems", []):
                orders.append(SellerOrder(
                    platform=self.platform,
                    order_id=order.get("orderId", ""),
                    item_id=line.get("lineItemId", ""),
                    title=line.get("title", ""),
                    price=float(line.get("total", {}).get("value", 0)),
                    currency=line.get("total", {}).get("currency", "GBP"),
                    buyer_username=order.get("buyer", {}).get("username"),
                    sold_at=_parse_ebay_date(order.get("creationDate")),
                    status=order.get("orderFulfillmentStatus"),
                    tracking_number=_get_tracking(order),
                ))
        return orders


def _parse_ebay_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _first(lst: list | None) -> str | None:
    if lst and len(lst) > 0:
        return lst[0]
    return None


def _get_tracking(order: dict) -> str | None:
    for f in order.get("fulfillmentStartInstructions", []):
        shipping = f.get("shippingStep", {})
        info = shipping.get("shipmentTracking", [])
        if info:
            return info[0].get("trackingNumber")
    return None
