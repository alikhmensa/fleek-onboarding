from pydantic import BaseModel, Field


class PriceBand(BaseModel):
    min: float
    median: float
    max: float
    currency: str = "GBP"


class Saturation(BaseModel):
    oversupplied: list[str] = []
    gaps: list[str] = []


class SellerProfile(BaseModel):
    aesthetic: list[str]
    price_band: PriceBand
    saturation: Saturation
    assumed_margin_multiple: float = 3.0
    budget: float


class InventoryItem(BaseModel):
    id: str
    title: str
    description: str
    image_url: str
    brand: str
    category: str
    condition_grade: str
    fleek_cost: float
    predicted_resale: float
    predicted_days_to_clear: int
    supplier_id: str
    moq: int
    rating: float | None = None


class Candidate(InventoryItem):
    fit: float = 0.0  # best cosine similarity across search intents (stage 3)
    est_margin: float = 0.0  # predicted_resale / fleek_cost (stage 4)
    score: float = 0.0  # blended rank score (stage 5)


class Bundle(BaseModel):
    supplier_id: str
    items: list[Candidate]
    total_cost: float
    est_margin: float
    est_clear_days: int
    rationale: str = ""


class OnboardResponse(BaseModel):
    seller_id: str
    profile: SellerProfile


class RecommendationsResponse(BaseModel):
    bundles: list[Bundle]
    relaxations: list[str] = Field(default_factory=list)
