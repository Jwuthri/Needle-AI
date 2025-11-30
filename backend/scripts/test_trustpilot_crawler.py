#!/usr/bin/env python3
"""
Test script for Trustpilot Website Content Crawler.

Usage:
    python scripts/test_trustpilot_crawler.py notion.so --limit 10
    python scripts/test_trustpilot_crawler.py "https://www.trustpilot.com/review/notion.so" --limit 20
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import get_settings
from app.services.scrapers import TrustpilotCrawler, TrustpilotQuickScraper


async def main():
    parser = argparse.ArgumentParser(
        description="Scrape Trustpilot reviews using Apify Website Content Crawler"
    )
    parser.add_argument(
        "company",
        help="Company name, slug (e.g., notion.so), or full Trustpilot URL"
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=20,
        help="Maximum number of reviews to collect (default: 20)"
    )
    parser.add_argument(
        "--quick", "-q",
        action="store_true",
        help="Quick mode - only scrape first page"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path (JSON)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    settings = get_settings()
    
    # Check API token
    if not settings.get_secret("apify_api_token"):
        print("❌ APIFY_API_TOKEN not set in environment!")
        print("Set it in your .env file: APIFY_API_TOKEN=your_token")
        sys.exit(1)
    
    print(f"🔍 Scraping Trustpilot reviews for: {args.company}")
    print(f"   Limit: {args.limit} reviews")
    print(f"   Mode: {'Quick (1 page)' if args.quick else 'Full crawl'}")
    print()
    
    try:
        if args.quick:
            scraper = TrustpilotQuickScraper(settings)
            reviews = await scraper.scrape_single_page(args.company)
        else:
            scraper = TrustpilotCrawler(settings)
            reviews = await scraper.scrape(args.company, limit=args.limit)
        
        print(f"✅ Found {len(reviews)} reviews")
        print()
        
        # Display reviews
        for i, review in enumerate(reviews, 1):
            print(f"─── Review {i} ───")
            if review.author:
                print(f"👤 Author: {review.author}")
            if review.metadata and review.metadata.get("rating"):
                stars = "★" * review.metadata["rating"] + "☆" * (5 - review.metadata["rating"])
                print(f"⭐ Rating: {stars}")
            if review.review_date:
                print(f"📅 Date: {review.review_date.strftime('%Y-%m-%d')}")
            print(f"📝 Content: {review.content[:300]}...")
            print()
        
        # Save to file if requested
        if args.output:
            output_data = [r.to_dict() for r in reviews]
            # Convert datetime to string for JSON
            for r in output_data:
                if r.get("review_date"):
                    r["review_date"] = r["review_date"].isoformat()
            
            with open(args.output, "w") as f:
                json.dump(output_data, f, indent=2)
            print(f"💾 Saved to: {args.output}")
        
        # Show cost estimate
        cost = await scraper.estimate_cost(args.limit)
        print(f"💰 Estimated cost: ${cost:.4f}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

