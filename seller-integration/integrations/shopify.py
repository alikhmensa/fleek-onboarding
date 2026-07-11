from __future__ import annotations
from datetime import datetime
import requests
from integrations.base import BaseIntegration
from models.schemas import SellerProfile, SellerItem, SellerOrder


class ShopifyIntegration(BaseIntegration):
    platform = "shopify"

    def __init__(self, shop_domain: str = "", access_token: str = "", **kwargs):
        self.shop_domain = shop_domain
        self.access_token = access_token
        self.api_version = "2024-10"

    def _url(self, endpoint: str) -> str:
        return f"https://{self.shop_domain}/admin/api/{self.api_version}/{endpoint}.json"

    def _headers(self) -> dict:
        return {"X-Shopify-Access-Token": self.access_token}

    def get_profile(self, seller_id: str) -> SellerProfile:
        resp = requests.get(self._url("shop"), headers=self._headers())
        resp.raise_for_status()
        shop = resp.json()["shop"]
        return SellerProfile(
            platform=self.platform,
            seller_id=str(shop["id"]),
            username=shop.get("name", ""),
            location=shop.get("city"),
            member_since=_parse_dt(shop.get("created_at")),
            profile_url=f"https://{self.shop_domain}",
        )

    def get_items(self, seller_id: str, limit: int = 50) -> list[SellerItem]:
        items = []
        params = {"limit": min(limit, 250), "status": "active"}
        resp = requests.get(self._url("products"), headers=self._headers(), params=params)
        resp.raise_for_status()
        products = resp.json().get("products", [])

        for product in products[:limit]:
            variant = product["variants"][0] if product.get("variants") else {}
            photos = [img["src"] for img in product.get("images", []) if img.get("src")]

            items.append(SellerItem(
                platform=self.platform,
                item_id=str(product["id"]),
                title=product.get("title", ""),
                description=product.get("body_html"),
                price=float(variant.get("price", 0)),
                currency="GBP",
                category=product.get("product_type"),
                brand=product.get("vendor"),
                condition=_extract_tag(product.get("tags", ""), "condition"),
                size=variant.get("option1") if variant.get("option1") else None,
                color=variant.get("option2") if variant.get("option2") else None,
                photos=photos,
                status=product.get("status", "active"),
                listed_at=_parse_dt(product.get("created_at")),
                url=f"https://{self.shop_domain}/products/{product.get('handle', '')}",
            ))
        return items

    def get_orders(self, seller_id: str, limit: int = 50) -> list[SellerOrder]:
        orders = []
        params = {"limit": min(limit, 250), "status": "any"}
        resp = requests.get(self._url("orders"), headers=self._headers(), params=params)
        resp.raise_for_status()
        raw_orders = resp.json().get("orders", [])

        for order in raw_orders[:limit]:
            for line in order.get("line_items", []):
                tracking = None
                fulfillments = order.get("fulfillments", [])
                if fulfillments:
                    tracking = fulfillments[0].get("tracking_number")

                orders.append(SellerOrder(
                    platform=self.platform,
                    order_id=str(order["id"]),
                    item_id=str(line.get("product_id", "")),
                    title=line.get("title", ""),
                    price=float(line.get("price", 0)),
                    currency=order.get("currency", "GBP"),
                    buyer_username=order.get("customer", {}).get("email"),
                    sold_at=_parse_dt(order.get("created_at")),
                    status=order.get("fulfillment_status") or "unfulfilled",
                    tracking_number=tracking,
                ))
        return orders


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _extract_tag(tags: str, prefix: str) -> str | None:
    for tag in tags.split(","):
        tag = tag.strip().lower()
        if tag.startswith(f"{prefix}:"):
            return tag.split(":", 1)[1].strip()
    return None
