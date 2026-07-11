from abc import ABC, abstractmethod
from models.schemas import SellerProfile, SellerItem, SellerOrder, OnboardingData


class BaseIntegration(ABC):
    platform: str

    @abstractmethod
    def get_profile(self, seller_id: str) -> SellerProfile:
        ...

    @abstractmethod
    def get_items(self, seller_id: str, limit: int = 50) -> list[SellerItem]:
        ...

    @abstractmethod
    def get_orders(self, seller_id: str, limit: int = 50) -> list[SellerOrder]:
        ...

    def get_all(self, seller_id: str, items_limit: int = 50, orders_limit: int = 50) -> OnboardingData:
        profile = self.get_profile(seller_id)
        items = self.get_items(seller_id, limit=items_limit)
        orders = self.get_orders(seller_id, limit=orders_limit)
        return OnboardingData(
            profile=profile,
            items=items,
            orders=orders,
            total_items_fetched=len(items),
            total_orders_fetched=len(orders),
        )
