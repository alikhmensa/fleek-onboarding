import json
import csv
import os
from datetime import datetime
from models.schemas import OnboardingData


def export_json(data: OnboardingData, output_dir: str = "output") -> str:
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"{data.profile.platform}_{data.profile.seller_id}.json")
    with open(path, "w") as f:
        json.dump(data.model_dump(mode="json"), f, indent=2, default=str)
    return path


def export_items_csv(data: OnboardingData, output_dir: str = "output") -> str:
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"{data.profile.platform}_{data.profile.seller_id}_items.csv")
    if not data.items:
        return path

    fields = list(data.items[0].model_dump().keys())
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for item in data.items:
            row = item.model_dump()
            row["photos"] = "; ".join(row.get("photos", []))
            writer.writerow(row)
    return path
