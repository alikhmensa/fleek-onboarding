from __future__ import annotations
import os
import base64
import hashlib
import secrets
import urllib.parse
import requests


class EbayOAuth:
    SANDBOX_AUTH_URL = "https://auth.sandbox.ebay.com/oauth2/authorize"
    PROD_AUTH_URL = "https://auth.ebay.com/oauth2/authorize"
    SANDBOX_TOKEN_URL = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
    PROD_TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"

    SCOPES = [
        "https://api.ebay.com/oauth/api_scope",
        "https://api.ebay.com/oauth/api_scope/sell.inventory.readonly",
        "https://api.ebay.com/oauth/api_scope/sell.fulfillment.readonly",
        "https://api.ebay.com/oauth/api_scope/sell.analytics.readonly",
        "https://api.ebay.com/oauth/api_scope/commerce.identity.readonly",
    ]

    def __init__(self):
        self.client_id = os.getenv("EBAY_CLIENT_ID", "")
        self.client_secret = os.getenv("EBAY_CLIENT_SECRET", "")
        self.redirect_uri = os.getenv("EBAY_REDIRECT_URI", "")
        self.sandbox = os.getenv("EBAY_SANDBOX", "true").lower() == "true"

    @property
    def auth_url(self):
        return self.SANDBOX_AUTH_URL if self.sandbox else self.PROD_AUTH_URL

    @property
    def token_url(self):
        return self.SANDBOX_TOKEN_URL if self.sandbox else self.PROD_TOKEN_URL

    def get_login_url(self, state: str | None = None) -> str:
        state = state or secrets.token_urlsafe(16)
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.SCOPES),
            "state": state,
        }
        return f"{self.auth_url}?{urllib.parse.urlencode(params)}"

    def exchange_code(self, code: str) -> dict:
        credentials = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()
        resp = requests.post(
            self.token_url,
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri,
            },
        )
        resp.raise_for_status()
        return resp.json()

    def refresh_token(self, refresh_token: str) -> dict:
        credentials = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()
        resp = requests.post(
            self.token_url,
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "scope": " ".join(self.SCOPES),
            },
        )
        resp.raise_for_status()
        return resp.json()


class ShopifyOAuth:
    SCOPES = "read_orders,read_products,read_inventory"

    def __init__(self):
        self.api_key = os.getenv("SHOPIFY_API_KEY", "")
        self.api_secret = os.getenv("SHOPIFY_API_SECRET", "")
        self.redirect_uri = os.getenv("SHOPIFY_REDIRECT_URI", "")
        self.scopes = os.getenv("SHOPIFY_SCOPES", self.SCOPES)

    def get_login_url(self, shop_domain: str, state: str | None = None) -> str:
        state = state or secrets.token_urlsafe(16)
        nonce = state
        params = {
            "client_id": self.api_key,
            "scope": self.scopes,
            "redirect_uri": self.redirect_uri,
            "state": nonce,
        }
        return f"https://{shop_domain}/admin/oauth/authorize?{urllib.parse.urlencode(params)}"

    def verify_hmac(self, params: dict) -> bool:
        hmac_value = params.pop("hmac", None)
        if not hmac_value:
            return False
        sorted_params = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        digest = hashlib.hmac_new(
            self.api_secret.encode(), sorted_params.encode(), hashlib.sha256
        ).hexdigest()
        return secrets.compare_digest(digest, hmac_value)

    def exchange_code(self, shop_domain: str, code: str) -> dict:
        payload = {
            "client_id": self.api_key,
            "client_secret": self.api_secret,
            "code": code,
        }
        resp = requests.post(
            f"https://{shop_domain}/admin/oauth/access_token",
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if not resp.ok:
            print(f"Shopify token exchange failed: {resp.status_code} {resp.text}")
        resp.raise_for_status()
        return resp.json()
