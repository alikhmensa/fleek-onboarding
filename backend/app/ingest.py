"""Stage 1 — parse a Shopify orders CSV into line items and deterministic price stats.

price_band is computed here in pandas, never by the LLM.
"""

import io

import numpy as np
import pandas as pd

from .config import BUDGET_MAX, BUDGET_MIN, DEFAULT_BUDGET
from .schemas import PriceBand

# Shopify orders-export column names → ours; bare fallbacks let simple CSVs work too
COLUMN_ALIASES = {
    "title": ["Lineitem name", "title", "Title", "product_title"],
    "price": ["Lineitem price", "price", "Price"],
    "quantity": ["Lineitem quantity", "quantity", "Quantity"],
    "created_at": ["Created at", "created_at", "Created At"],
    "vendor": ["Vendor", "vendor"],
    "product_type": ["Product Type", "product_type", "Type"],
}


def parse_orders(file_bytes: bytes, filename: str = "") -> pd.DataFrame:
    if filename.lower().endswith((".xlsx", ".xls")) or file_bytes[:4] == b"PK\x03\x04":
        raw = pd.read_excel(io.BytesIO(file_bytes))
    else:
        raw = pd.read_csv(io.BytesIO(file_bytes))
    df = pd.DataFrame()
    for ours, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in raw.columns:
                df[ours] = raw[alias]
                break
    if "title" not in df.columns or "price" not in df.columns:
        raise ValueError("CSV must contain line-item title and price columns (Shopify orders export)")

    df = df.dropna(subset=["title", "price"])
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df = df.dropna(subset=["price"])
    df = df[df["price"] > 0]
    df["quantity"] = pd.to_numeric(df.get("quantity", 1), errors="coerce").fillna(1).astype(int).clip(lower=1)
    if df.empty:
        raise ValueError("CSV parsed but contained no sellable line items")
    return df


def shopify_orders_to_df(orders, items) -> pd.DataFrame:
    """Convert connector ShopOrder/ShopItem lists into the same line-item frame
    parse_orders produces; brand comes from the item catalogue where the sold
    product is still listed."""
    brand_by_id = {i.item_id: i.brand for i in items if i.brand}
    df = pd.DataFrame(
        {
            "title": o.title,
            "price": o.price,
            "quantity": 1,
            "created_at": o.sold_at.isoformat() if o.sold_at else None,
            "vendor": brand_by_id.get(o.item_id),
        }
        for o in orders
    )
    if df.empty:
        return df
    return df[df["price"] > 0]


def compute_price_band(df: pd.DataFrame, currency: str = "GBP") -> PriceBand:
    prices = np.repeat(df["price"].to_numpy(), df["quantity"].to_numpy())
    return PriceBand(
        min=round(float(np.min(prices)), 2),
        median=round(float(np.median(prices)), 2),
        max=round(float(np.max(prices)), 2),
        currency=currency,
    )


def infer_budget(df: pd.DataFrame, margin_multiple: float) -> float:
    """~4 weeks of restock at their sales pace: 4 × weekly revenue ÷ margin multiple."""
    revenue = float((df["price"] * df["quantity"]).sum())
    weeks = 4.0
    if "created_at" in df.columns:
        dates = pd.to_datetime(df["created_at"], errors="coerce", utc=True, format="mixed").dropna()
        if len(dates) > 1:
            weeks = max((dates.max() - dates.min()).days / 7.0, 1.0)
    budget = 4.0 * (revenue / weeks) / max(margin_multiple, 1.0)
    if not np.isfinite(budget) or budget <= 0:
        return DEFAULT_BUDGET
    return round(min(max(budget, BUDGET_MIN), BUDGET_MAX), 0)


def aggregate_for_llm(df: pd.DataFrame) -> dict:
    """Compact summary for the profile call — never send thousands of raw rows."""
    agg: dict = {
        "total_items_sold": int(df["quantity"].sum()),
        "distinct_products": int(df["title"].nunique()),
        "price_gbp": {
            "min": round(float(df["price"].min()), 2),
            "median": round(float(df["price"].median()), 2),
            "max": round(float(df["price"].max()), 2),
        },
    }
    top = (
        df.groupby("title")
        .agg(units=("quantity", "sum"), price=("price", "median"))
        .sort_values("units", ascending=False)
        .head(40)
    )
    agg["top_products"] = [
        {"title": t, "units": int(r.units), "price": round(float(r.price), 2)} for t, r in top.iterrows()
    ]
    for col in ("vendor", "product_type"):
        if col in df.columns and df[col].notna().any():
            counts = df.groupby(col)["quantity"].sum().sort_values(ascending=False).head(15)
            agg[f"units_by_{col}"] = {str(k): int(v) for k, v in counts.items()}
    return agg
