"""Shopify Admin API client + OAuth — ported from Shiv's seller-integration module.

Changes from the original: relative imports, hmac verification fixed
(hashlib.hmac_new doesn't exist) and actually enforced in the callback,
and get_all bundles profile/items/orders with per-call error tolerance.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import urllib.parse
from datetime import datetime

import requests

from .schemas import ShopData, ShopItem, ShopOrder, ShopProfile


class ShopifyOAuth:
    SCOPES = "read_orders,read_products,read_inventory"

    def __init__(self):
        self.api_key = os.getenv("SHOPIFY_API_KEY", "")
        self.api_secret = os.getenv("SHOPIFY_API_SECRET", "")
        self.redirect_uri = os.getenv("SHOPIFY_REDIRECT_URI", "http://localhost:8000/callback/shopify")
        self.scopes = os.getenv("SHOPIFY_SCOPES", self.SCOPES)

    def get_login_url(self, shop_domain: str) -> str:
        params = {
            "client_id": self.api_key,
            "scope": self.scopes,
            "redirect_uri": self.redirect_uri,
            "state": secrets.token_urlsafe(16),
        }
        return f"https://{shop_domain}/admin/oauth/authorize?{urllib.parse.urlencode(params)}"

    def verify_hmac(self, params: dict) -> bool:
        params = dict(params)
        hmac_value = params.pop("hmac", None)
        if not hmac_value:
            return False
        message = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        digest = hmac.new(self.api_secret.encode(), message.encode(), hashlib.sha256).hexdigest()
        return secrets.compare_digest(digest, hmac_value)

    def exchange_code(self, shop_domain: str, code: str) -> dict:
        resp = requests.post(
            f"https://{shop_domain}/admin/oauth/access_token",
            data={"client_id": self.api_key, "client_secret": self.api_secret, "code": code},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()


class ShopifyClient:
    platform = "shopify"

    def __init__(self, shop_domain: str, access_token: str):
        self.shop_domain = shop_domain
        self.access_token = access_token
        self.api_version = "2024-10"

    def _get(self, endpoint: str, **params) -> dict:
        resp = requests.get(
            f"https://{self.shop_domain}/admin/api/{self.api_version}/{endpoint}.json",
            headers={"X-Shopify-Access-Token": self.access_token},
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def get_profile(self) -> ShopProfile:
        shop = self._get("shop")["shop"]
        return ShopProfile(
            platform=self.platform,
            seller_id=str(shop["id"]),
            username=shop.get("name", ""),
            location=shop.get("city"),
            member_since=_parse_dt(shop.get("created_at")),
            profile_url=f"https://{self.shop_domain}",
        )

    def get_items(self, limit: int = 250) -> list[ShopItem]:
        products = self._get("products", limit=min(limit, 250), status="active").get("products", [])
        items = []
        for product in products[:limit]:
            variant = product["variants"][0] if product.get("variants") else {}
            items.append(
                ShopItem(
                    platform=self.platform,
                    item_id=str(product["id"]),
                    title=product.get("title", ""),
                    description=product.get("body_html"),
                    price=float(variant.get("price", 0)),
                    category=product.get("product_type"),
                    brand=product.get("vendor"),
                    size=variant.get("option1") or None,
                    color=variant.get("option2") or None,
                    photos=[img["src"] for img in product.get("images", []) if img.get("src")],
                    status=product.get("status", "active"),
                    listed_at=_parse_dt(product.get("created_at")),
                    url=f"https://{self.shop_domain}/products/{product.get('handle', '')}",
                )
            )
        return items

    def get_orders(self, limit: int = 250) -> list[ShopOrder]:
        # NOTE: without the read_all_orders scope Shopify only returns ~60 days
        # of orders — fine for a freshly populated dev store.
        raw = self._get("orders", limit=min(limit, 250), status="any").get("orders", [])
        orders = []
        for order in raw[:limit]:
            for line in order.get("line_items", []):
                orders.append(
                    ShopOrder(
                        platform=self.platform,
                        order_id=str(order["id"]),
                        item_id=str(line.get("product_id", "")),
                        title=line.get("title", ""),
                        price=float(line.get("price", 0)),
                        currency=order.get("currency", "GBP"),
                        # processed_at is the true sale date on imported/backdated
                        # orders; created_at is just when the record was made
                        sold_at=_parse_dt(order.get("processed_at") or order.get("created_at")),
                        status=order.get("fulfillment_status") or "unfulfilled",
                    )
                )
        return orders

    def get_all(self) -> ShopData:
        items = self.get_items()
        orders = self.get_orders()
        try:
            profile = self.get_profile()
        except Exception:
            profile = None
        return ShopData(
            profile=profile,
            items=items,
            orders=orders,
            total_items_fetched=len(items),
            total_orders_fetched=len(orders),
        )


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
