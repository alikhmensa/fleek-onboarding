from __future__ import annotations
from datetime import datetime
from vinted_scraper import VintedScraper
from integrations.base import BaseIntegration
from models.schemas import SellerProfile, SellerItem, SellerOrder


class VintedIntegration(BaseIntegration):
    platform = "vinted"

    def __init__(self, domain: str = "https://www.vinted.co.uk", **kwargs):
        self.scraper = VintedScraper(domain)

    def get_profile(self, seller_id: str) -> SellerProfile:
        items = self.scraper.search(params={"user_id": seller_id, "per_page": 1})
        if items and items[0].user:
            user = items[0].user
            return SellerProfile(
                platform=self.platform,
                seller_id=seller_id,
                username=user.login or "",
                profile_url=user.profile_url,
            )
        return SellerProfile(
            platform=self.platform,
            seller_id=seller_id,
            username=seller_id,
        )

    def get_items(self, seller_id: str, limit: int = 50) -> list[SellerItem]:
        raw_items = self.scraper.search(
            params={"user_id": seller_id, "per_page": min(limit, 96)}
        )
        items = []
        for item in raw_items[:limit]:
            photos = []
            if item.photos:
                for p in item.photos:
                    if hasattr(p, "url") and p.url:
                        photos.append(p.url)

            items.append(SellerItem(
                platform=self.platform,
                item_id=str(item.id),
                title=item.title or "",
                description=item.description,
                price=float(item.price) if item.price else 0.0,
                currency=item.currency or "EUR",
                brand=item.brand_title or (item.brand.title if item.brand else None),
                condition=item.status,
                size=item.size_title,
                photos=photos,
                status="active" if item.is_visible else "hidden",
                url=item.url,
            ))
        return items

    def get_orders(self, seller_id: str, limit: int = 50) -> list[SellerOrder]:
        return []
