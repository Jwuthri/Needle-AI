#!/usr/bin/env python3
"""
Test TrustRadius scraper.

Usage:
    python scripts/test_trustradius_scraper.py [PRODUCT] [--limit N] [-o FILE]
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.config import get_settings
from app.services.scrapers import TrustRadiusScraper


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("product", nargs="?", default="slack")
    parser.add_argument("--limit", "-l", type=int, default=5)
    parser.add_argument("-o", "--output", type=str, help="Output JSON file")
    args = parser.parse_args()
    
    print(f"\n🔍 TrustRadius scraper test")
    print(f"   Product: {args.product}")
    print(f"   Limit: {args.limit}")
    
    settings = get_settings()
    
    if not settings.get_secret("apify_api_token"):
        print("\n❌ Set APIFY_API_TOKEN in .env")
        sys.exit(1)
    
    scraper = TrustRadiusScraper(settings)
    
    print(f"\n⏳ Fetching reviews (this may take a minute)...")
    
    try:
        reviews = await scraper.scrape(query=args.product, limit=args.limit)
        
        if not reviews:
            print("\n⚠️  No reviews found")
            sys.exit(1)
        
        print(f"\n✅ Got {len(reviews)} reviews\n")
        
        for i, r in enumerate(reviews):
            print(f"{'='*50}")
            print(f"Review #{i+1}")
            if r.author:
                print(f"Author: {r.author}")
            if r.metadata.get("rating"):
                rating = r.metadata["rating"]
                stars = "★" * int(round(rating)) + "☆" * (5 - int(round(rating)))
                print(f"Rating: {stars} ({rating})")
            if r.metadata.get("job_title"):
                print(f"Title: {r.metadata['job_title']}")
            if r.review_date:
                print(f"Date: {r.review_date.strftime('%Y-%m-%d')}")
            print(f"\n{r.content[:400]}...")
        
        print(f"\n{'='*50}")
        print(f"Total: {len(reviews)} reviews")
        cost = await scraper.estimate_cost(len(reviews))
        print(f"Estimated cost: ${cost:.2f}")
        
        # Write to file if -o specified
        if args.output:
            output_data = [
                {
                    "content": r.content,
                    "author": r.author,
                    "url": r.url,
                    "date": r.review_date.isoformat() if r.review_date else None,
                    **r.metadata
                }
                for r in reviews
            ]
            with open(args.output, "w") as f:
                json.dump(output_data, f, indent=2)
            print(f"\n📁 Saved to {args.output}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

