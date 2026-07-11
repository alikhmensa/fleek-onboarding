from models.schemas import OnboardingData, SellerProfile, SellerItem, SellerOrder


def mock_shopify() -> OnboardingData:
    profile = SellerProfile(
        platform="shopify",
        seller_id="78234561",
        username="StreetWear Vault",
        rating=4.8,
        total_items_sold=342,
        location="London",
        profile_url="https://streetwearvault.myshopify.com",
    )

    items = [
        SellerItem(
            platform="shopify",
            item_id="SKU-SW-001",
            title="Nike Air Max 90 - Triple White",
            description="Worn twice, excellent condition. UK 10. Comes with original box.",
            price=85.00,
            currency="GBP",
            category="Sneakers",
            brand="Nike",
            condition="Very good",
            size="UK 10",
            color="White",
            photos=[
                "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=800",
                "https://images.unsplash.com/photo-1606107557195-0e29a4b5b4aa?w=800",
            ],
            status="active",
            url="https://streetwearvault.myshopify.com/products/nike-air-max-90-white",
        ),
        SellerItem(
            platform="shopify",
            item_id="SKU-SW-002",
            title="Carhartt WIP Michigan Coat - Black",
            description="Classic chore coat. Size L. Light fading adds character.",
            price=120.00,
            currency="GBP",
            category="Jackets",
            brand="Carhartt WIP",
            condition="Good",
            size="L",
            color="Black",
            photos=[
                "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=800",
            ],
            status="active",
            url="https://streetwearvault.myshopify.com/products/carhartt-michigan-coat",
        ),
        SellerItem(
            platform="shopify",
            item_id="SKU-SW-003",
            title="Stussy Logo Hoodie - Navy",
            description="2024 collection. Worn a handful of times. Size M.",
            price=65.00,
            currency="GBP",
            category="Hoodies",
            brand="Stussy",
            condition="Very good",
            size="M",
            color="Navy",
            photos=[
                "https://images.unsplash.com/photo-1556821840-3a63f95609a7?w=800",
                "https://images.unsplash.com/photo-1578768079470-0a4536e7f3a7?w=800",
            ],
            status="active",
            url="https://streetwearvault.myshopify.com/products/stussy-logo-hoodie-navy",
        ),
        SellerItem(
            platform="shopify",
            item_id="SKU-SW-004",
            title="Vintage Levi's 501 - Light Wash",
            description="W32 L32. Classic straight leg. Authentic vintage 90s pair.",
            price=55.00,
            currency="GBP",
            category="Jeans",
            brand="Levi's",
            condition="Good",
            size="W32 L32",
            color="Light Blue",
            photos=[
                "https://images.unsplash.com/photo-1542272454315-4c01d7abdf4a?w=800",
            ],
            status="active",
            url="https://streetwearvault.myshopify.com/products/vintage-levis-501-light-wash",
        ),
        SellerItem(
            platform="shopify",
            item_id="SKU-SW-005",
            title="The North Face Nuptse 700 - Black",
            description="2023 model. Barely worn. Size S. Puffer in perfect condition.",
            price=195.00,
            currency="GBP",
            category="Jackets",
            brand="The North Face",
            condition="New without tags",
            size="S",
            color="Black",
            photos=[
                "https://images.unsplash.com/photo-1544966503-7cc5ac882d5f?w=800",
                "https://images.unsplash.com/photo-1611312449408-fcece27cdbb7?w=800",
            ],
            status="active",
            url="https://streetwearvault.myshopify.com/products/tnf-nuptse-700-black",
        ),
    ]

    orders = [
        SellerOrder(
            platform="shopify",
            order_id="ORD-10421",
            item_id="SKU-SW-009",
            title="Adidas Samba OG - White/Black",
            price=72.00,
            currency="GBP",
            buyer_username="james.t@gmail.com",
            sold_at="2026-06-28T14:20:00+00:00",
            status="fulfilled",
            tracking_number="RM123456789GB",
        ),
        SellerOrder(
            platform="shopify",
            order_id="ORD-10418",
            item_id="SKU-SW-007",
            title="Palace Tri-Ferg Tee - White",
            price=45.00,
            currency="GBP",
            buyer_username="sarah.k@outlook.com",
            sold_at="2026-06-25T09:15:00+00:00",
            status="fulfilled",
            tracking_number="RM987654321GB",
        ),
        SellerOrder(
            platform="shopify",
            order_id="ORD-10415",
            item_id="SKU-SW-006",
            title="New Balance 550 - Green/White",
            price=95.00,
            currency="GBP",
            buyer_username="mike.r@yahoo.com",
            sold_at="2026-06-20T18:45:00+00:00",
            status="fulfilled",
            tracking_number=None,
        ),
        SellerOrder(
            platform="shopify",
            order_id="ORD-10412",
            item_id="SKU-SW-011",
            title="Dickies 874 Original Fit - Khaki",
            price=38.00,
            currency="GBP",
            buyer_username="lucy.w@gmail.com",
            sold_at="2026-06-15T11:30:00+00:00",
            status="fulfilled",
            tracking_number="RM456789123GB",
        ),
    ]

    return OnboardingData(
        profile=profile,
        items=items,
        orders=orders,
        total_items_fetched=len(items),
        total_orders_fetched=len(orders),
    )


def mock_ebay() -> OnboardingData:
    profile = SellerProfile(
        platform="ebay",
        seller_id="vintage_finds_uk",
        username="vintage_finds_uk",
        rating=99.2,
        total_items_sold=1547,
        location="Manchester",
    )

    items = [
        SellerItem(
            platform="ebay",
            item_id="EB-334521",
            title="Burberry Vintage Nova Check Scarf",
            description="Authentic Burberry cashmere scarf. Classic nova check pattern. Excellent condition.",
            price=145.00,
            currency="GBP",
            category="Scarves",
            brand="Burberry",
            condition="Very good",
            photos=[
                "https://images.unsplash.com/photo-1601924638867-3a6de6b7a500?w=800",
            ],
            status="active",
        ),
        SellerItem(
            platform="ebay",
            item_id="EB-334522",
            title="Ralph Lauren Oxford Shirt - Blue Stripe",
            description="Classic fit. Size M. Barely worn.",
            price=35.00,
            currency="GBP",
            category="Shirts",
            brand="Ralph Lauren",
            condition="Very good",
            size="M",
            color="Blue",
            photos=[
                "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=800",
            ],
            status="active",
        ),
        SellerItem(
            platform="ebay",
            item_id="EB-334523",
            title="Dr Martens 1460 Boots - Cherry Red",
            description="UK 8. Broken in perfectly. Minor scuffing.",
            price=89.00,
            currency="GBP",
            category="Boots",
            brand="Dr. Martens",
            condition="Good",
            size="UK 8",
            color="Cherry Red",
            photos=[
                "https://images.unsplash.com/photo-1608256246200-53e635b5b65f?w=800",
            ],
            status="active",
        ),
    ]

    orders = [
        SellerOrder(
            platform="ebay",
            order_id="EB-ORD-88431",
            item_id="EB-334519",
            title="Barbour Beaufort Wax Jacket - Olive",
            price=165.00,
            currency="GBP",
            buyer_username="d***r",
            sold_at="2026-07-01T16:00:00+00:00",
            status="FULFILLED",
            tracking_number="JD0001234567",
        ),
        SellerOrder(
            platform="ebay",
            order_id="EB-ORD-88427",
            item_id="EB-334515",
            title="Fred Perry Twin Tipped Polo - Black",
            price=42.00,
            currency="GBP",
            buyer_username="s***k",
            sold_at="2026-06-27T12:10:00+00:00",
            status="FULFILLED",
            tracking_number="RM555666777GB",
        ),
    ]

    return OnboardingData(
        profile=profile,
        items=items,
        orders=orders,
        total_items_fetched=len(items),
        total_orders_fetched=len(orders),
    )


def mock_vinted() -> OnboardingData:
    profile = SellerProfile(
        platform="vinted",
        seller_id="94521873",
        username="preloved_emma",
        rating=4.9,
        total_items_sold=89,
        location="Bristol",
        profile_url="https://www.vinted.co.uk/member/94521873-preloved-emma",
    )

    items = [
        SellerItem(
            platform="vinted",
            item_id="VT-8823401",
            title="Zara Satin Midi Skirt - Black",
            description="Size S. Worn once for an event.",
            price=18.00,
            currency="GBP",
            brand="Zara",
            condition="New without tags",
            size="S",
            color="Black",
            photos=[
                "https://images.unsplash.com/photo-1583496661160-fb5886a0aaaa?w=800",
            ],
            status="active",
            url="https://www.vinted.co.uk/items/8823401-zara-satin-midi-skirt",
        ),
        SellerItem(
            platform="vinted",
            item_id="VT-8823402",
            title="H&M Oversized Blazer - Beige",
            description="Size M. Perfect for layering.",
            price=25.00,
            currency="GBP",
            brand="H&M",
            condition="Very good",
            size="M",
            color="Beige",
            photos=[
                "https://images.unsplash.com/photo-1591047139829-d91aecb6caea?w=800",
            ],
            status="active",
            url="https://www.vinted.co.uk/items/8823402-hm-oversized-blazer",
        ),
        SellerItem(
            platform="vinted",
            item_id="VT-8823403",
            title="Converse Chuck 70 - Parchment",
            description="UK 6. Barely worn. Classic hi-tops.",
            price=35.00,
            currency="GBP",
            brand="Converse",
            condition="Very good",
            size="UK 6",
            color="Parchment",
            photos=[
                "https://images.unsplash.com/photo-1607522370275-f14206abe190?w=800",
            ],
            status="active",
            url="https://www.vinted.co.uk/items/8823403-converse-chuck-70",
        ),
    ]

    return OnboardingData(
        profile=profile,
        items=items,
        orders=[],
        total_items_fetched=len(items),
        total_orders_fetched=0,
    )
