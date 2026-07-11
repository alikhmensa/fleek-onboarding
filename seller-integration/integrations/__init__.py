from integrations.base import BaseIntegration
from integrations.vinted import VintedIntegration
from integrations.ebay import EbayIntegration
from integrations.shopify import ShopifyIntegration

PLATFORMS = {
    "vinted": VintedIntegration,
    "ebay": EbayIntegration,
    "shopify": ShopifyIntegration,
}


def get_integration(platform: str, **kwargs) -> BaseIntegration:
    cls = PLATFORMS.get(platform.lower())
    if not cls:
        raise ValueError(f"Unsupported platform: {platform}. Supported: {list(PLATFORMS.keys())}")
    return cls(**kwargs)
