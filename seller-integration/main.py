import argparse
import sys
from dotenv import load_dotenv
from integrations import get_integration
from utils.export import export_json, export_items_csv

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Fleek Seller Onboarding - Pull seller data from external platforms")
    parser.add_argument("platform", choices=["vinted", "ebay"], help="Seller platform to pull from")
    parser.add_argument("seller_id", help="Seller ID or username on the platform")
    parser.add_argument("--items-limit", type=int, default=50, help="Max items to fetch")
    parser.add_argument("--orders-limit", type=int, default=50, help="Max orders to fetch")
    parser.add_argument("--output", default="output", help="Output directory")
    parser.add_argument("--format", choices=["json", "csv", "both"], default="both", help="Export format")
    parser.add_argument("--domain", default="https://www.vinted.co.uk", help="Vinted domain (e.g. vinted.fr, vinted.de)")
    args = parser.parse_args()

    print(f"Connecting to {args.platform}...")
    integration = get_integration(args.platform, domain=args.domain)

    print(f"Fetching data for seller: {args.seller_id}")
    data = integration.get_all(
        seller_id=args.seller_id,
        items_limit=args.items_limit,
        orders_limit=args.orders_limit,
    )

    print(f"  Profile: {data.profile.username}")
    print(f"  Items fetched: {data.total_items_fetched}")
    print(f"  Orders fetched: {data.total_orders_fetched}")

    if args.format in ("json", "both"):
        path = export_json(data, args.output)
        print(f"  Exported JSON: {path}")

    if args.format in ("csv", "both"):
        path = export_items_csv(data, args.output)
        print(f"  Exported CSV: {path}")

    print("Done.")


if __name__ == "__main__":
    main()
