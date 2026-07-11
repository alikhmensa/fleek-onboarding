"""Mock Shopify shop (condensed from Shiv's mock_data.py) — lets the connect->onboard
flow run before the real dev store is populated. Used when shop == "mock"."""

from datetime import datetime, timedelta, timezone

from .schemas import ShopData, ShopItem, ShopOrder, ShopProfile

_ITEMS = [
    # (id, title, price, category, brand, condition)
    ("SKU-SW-001", "Nike Air Max 90 - Triple White", 85.0, "Sneakers", "Nike", "Very good"),
    ("SKU-SW-002", "Carhartt WIP Michigan Coat - Black", 120.0, "Jackets", "Carhartt WIP", "Good"),
    ("SKU-SW-003", "Stussy Logo Hoodie - Navy", 65.0, "Hoodies", "Stussy", "Very good"),
    ("SKU-SW-004", "Vintage Levi's 501 - Light Wash", 55.0, "Jeans", "Levi's", "Good"),
    ("SKU-SW-005", "The North Face Nuptse 700 - Black", 195.0, "Jackets", "The North Face", "New without tags"),
]

_ORDERS = [
    # (title, price, category-ish brand, days_ago)
    ("Adidas Samba OG - White/Black", 72.0, "Adidas", 3),
    ("Palace Tri-Ferg Tee - White", 45.0, "Palace", 6),
    ("New Balance 550 - Green/White", 88.0, "New Balance", 9),
    ("Carhartt WIP Detroit Jacket - Hamilton Brown", 110.0, "Carhartt WIP", 12),
    ("Nike Tech Fleece Joggers - Grey", 48.0, "Nike", 15),
    ("Stussy 8-Ball Tee - Black", 38.0, "Stussy", 18),
    ("Vintage Nike Windbreaker - Multicolour", 52.0, "Nike", 22),
    ("Supreme Box Logo Beanie - Red", 42.0, "Supreme", 26),
    ("Carhartt WIP Double Knee Pants - Black", 75.0, "Carhartt WIP", 30),
    ("Adidas Firebird Track Top - Navy", 44.0, "Adidas", 34),
    ("Nike Dunk Low - Panda", 95.0, "Nike", 38),
    ("Dickies 874 Work Pants - Charcoal", 40.0, "Dickies", 42),
]


def mock_shop_data() -> ShopData:
    now = datetime.now(timezone.utc)
    items = [
        ShopItem(
            platform="shopify", item_id=iid, title=title, price=price, category=cat,
            brand=brand, condition=cond, status="active",
            photos=[f"https://picsum.photos/seed/{iid}/400/500"],
            url=f"https://streetwearvault.myshopify.com/products/{iid.lower()}",
        )
        for iid, title, price, cat, brand, cond in _ITEMS
    ]
    orders = [
        ShopOrder(
            platform="shopify", order_id=f"ORD-{10400 + n}", item_id=f"SKU-SOLD-{n:03d}",
            title=title, price=price, sold_at=now - timedelta(days=days), status="fulfilled",
        )
        for n, (title, price, _brand, days) in enumerate(_ORDERS)
    ]
    return ShopData(
        profile=ShopProfile(
            platform="shopify", seller_id="78234561", username="StreetWear Vault",
            rating=4.8, total_items_sold=342, location="London",
            profile_url="https://streetwearvault.myshopify.com",
        ),
        items=items,
        orders=orders,
        total_items_fetched=len(items),
        total_orders_fetched=len(orders),
    )
