import os
import re
from flask import Flask, request, jsonify, redirect
from dotenv import load_dotenv
from integrations import get_integration
from integrations.oauth import EbayOAuth, ShopifyOAuth

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")

token_store = {}

ebay_oauth = EbayOAuth()
shopify_oauth = ShopifyOAuth()


# ---------------------
# OAuth: eBay
# ---------------------

@app.route("/connect/ebay")
def connect_ebay():
    url = ebay_oauth.get_login_url()
    return redirect(url)


@app.route("/callback/ebay")
def callback_ebay():
    code = request.args.get("code")
    if not code:
        return jsonify({"error": "No authorization code received"}), 400

    tokens = ebay_oauth.exchange_code(code)
    user_id = "ebay_user"

    token_store[f"ebay:{user_id}"] = {
        "access_token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token"),
        "expires_in": tokens.get("expires_in"),
    }
    return jsonify({"status": "connected", "platform": "ebay"})


# ---------------------
# OAuth: Shopify
# ---------------------

@app.route("/connect/shopify")
def connect_shopify():
    shop = request.args.get("shop")
    if not shop:
        return jsonify({"error": "Missing 'shop' parameter (e.g. mystore.myshopify.com)"}), 400
    url = shopify_oauth.get_login_url(shop)
    return redirect(url)


@app.route("/callback/shopify")
def callback_shopify():
    code = request.args.get("code")
    shop = request.args.get("shop")
    if not code or not shop:
        return jsonify({"error": "Missing code or shop parameter"}), 400

    tokens = shopify_oauth.exchange_code(shop, code)
    token_store[f"shopify:{shop}"] = {
        "access_token": tokens["access_token"],
        "shop_domain": shop,
    }
    return jsonify({"status": "connected", "platform": "shopify", "shop": shop})


# ---------------------
# Vinted: No OAuth needed
# ---------------------

@app.route("/connect/vinted", methods=["POST"])
def connect_vinted():
    data = request.get_json()
    profile_url = data.get("profile_url", "")
    seller_id = data.get("seller_id", "")

    if profile_url and not seller_id:
        match = re.search(r"/member/(\d+)", profile_url)
        if match:
            seller_id = match.group(1)

    if not seller_id:
        return jsonify({"error": "Provide profile_url or seller_id"}), 400

    token_store[f"vinted:{seller_id}"] = {"seller_id": seller_id}
    return jsonify({"status": "connected", "platform": "vinted", "seller_id": seller_id})


# ---------------------
# Unified data fetch
# ---------------------

@app.route("/api/seller/<platform>/<seller_id>")
def get_seller_data(platform, seller_id):
    items_limit = request.args.get("items_limit", 50, type=int)
    orders_limit = request.args.get("orders_limit", 50, type=int)

    try:
        if platform == "vinted":
            domain = request.args.get("domain", "https://www.vinted.co.uk")
            integration = get_integration("vinted", domain=domain)

        elif platform == "ebay":
            stored = token_store.get(f"ebay:{seller_id}")
            if not stored:
                return jsonify({"error": "eBay not connected. Visit /connect/ebay first."}), 401
            integration = get_integration("ebay", access_token=stored["access_token"])

        elif platform == "shopify":
            stored = token_store.get(f"shopify:{seller_id}")
            if not stored:
                return jsonify({"error": "Shopify not connected. Visit /connect/shopify?shop=yourstore.myshopify.com first."}), 401
            integration = get_integration("shopify", shop_domain=stored["shop_domain"], access_token=stored["access_token"])

        else:
            return jsonify({"error": f"Unsupported platform: {platform}"}), 400

        data = integration.get_all(seller_id, items_limit=items_limit, orders_limit=orders_limit)
        return jsonify(data.model_dump(mode="json"))

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------
# Multi-platform onboarding
# ---------------------

@app.route("/api/onboard", methods=["POST"])
def onboard_seller():
    """
    Pull data from all connected platforms for a seller.

    POST body:
    {
        "vinted_url": "https://www.vinted.co.uk/member/12345-username",
        "ebay_user_id": "ebay_user",
        "shopify_shop": "mystore.myshopify.com"
    }
    """
    data = request.get_json()
    results = {}

    if data.get("vinted_url"):
        match = re.search(r"/member/(\d+)", data["vinted_url"])
        if match:
            seller_id = match.group(1)
            try:
                integration = get_integration("vinted")
                results["vinted"] = integration.get_all(seller_id).model_dump(mode="json")
            except Exception as e:
                results["vinted"] = {"error": str(e)}

    if data.get("ebay_user_id"):
        uid = data["ebay_user_id"]
        stored = token_store.get(f"ebay:{uid}")
        if stored:
            try:
                integration = get_integration("ebay", access_token=stored["access_token"])
                results["ebay"] = integration.get_all(uid).model_dump(mode="json")
            except Exception as e:
                results["ebay"] = {"error": str(e)}
        else:
            results["ebay"] = {"error": "Not connected"}

    if data.get("shopify_shop"):
        shop = data["shopify_shop"]
        stored = token_store.get(f"shopify:{shop}")
        if stored:
            try:
                integration = get_integration("shopify", shop_domain=shop, access_token=stored["access_token"])
                results["shopify"] = integration.get_all(shop).model_dump(mode="json")
            except Exception as e:
                results["shopify"] = {"error": str(e)}
        else:
            results["shopify"] = {"error": "Not connected"}

    return jsonify(results)


@app.route("/api/platforms")
def list_platforms():
    return jsonify({
        "platforms": [
            {
                "id": "vinted",
                "name": "Vinted",
                "auth": "none",
                "data": ["items", "profile"],
                "connect_url": "/connect/vinted",
            },
            {
                "id": "ebay",
                "name": "eBay",
                "auth": "oauth",
                "data": ["items", "orders", "profile"],
                "connect_url": "/connect/ebay",
            },
            {
                "id": "shopify",
                "name": "Shopify",
                "auth": "oauth",
                "data": ["items", "orders", "profile"],
                "connect_url": "/connect/shopify?shop={shop_domain}",
            },
        ]
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
