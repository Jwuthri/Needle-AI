#!/usr/bin/env python3
"""
Test script for G2 Product Scraper (omkar-cloud/g2-product-scraper).

Usage:
    python scripts/test_g2_scraper.py notion --limit 10
    python scripts/test_g2_scraper.py "https://www.g2.com/products/slack/reviews" --limit 20
    python scripts/test_g2_scraper.py gorgias -o g2_reviews.json
    python scripts/test_g2_scraper.py notion --intel  # Show product intelligence only
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import get_settings
from app.services.scrapers import G2Scraper


def display_intelligence(intel):
    """Display product intelligence data."""
    if not intel:
        print("❌ No intelligence data available")
        return
    
    print("\n" + "=" * 60)
    print("📊 PRODUCT INTELLIGENCE")
    print("=" * 60)
    
    if intel.product_name:
        print(f"\n🏷️  Product: {intel.product_name}")
    if intel.average_rating:
        stars = "★" * int(intel.average_rating) + "☆" * (5 - int(intel.average_rating))
        print(f"⭐ Rating: {stars} ({intel.average_rating}/5)")
    if intel.total_reviews:
        print(f"📝 Total Reviews: {intel.total_reviews:,}")
    
    if intel.what_is:
        print(f"\n📋 What is it:\n   {intel.what_is[:300]}...")
    
    if intel.positioning:
        print(f"\n🎯 Positioning:\n   {intel.positioning[:300]}...")
    
    # Company Info
    print("\n--- Company Info ---")
    if intel.vendor_name:
        print(f"🏢 Vendor: {intel.vendor_name}")
    if intel.company_location:
        print(f"📍 Location: {intel.company_location}")
    if intel.company_founded_year:
        print(f"📅 Founded: {intel.company_founded_year}")
    if intel.company_website:
        print(f"🌐 Website: {intel.company_website}")
    
    # Social
    if intel.twitter_followers or intel.linkedin_employees:
        print("\n--- Social ---")
        if intel.twitter_followers:
            print(f"🐦 Twitter: {intel.twitter_followers:,} followers")
        if intel.linkedin_employees:
            print(f"💼 LinkedIn: {intel.linkedin_employees:,} employees")
    
    # Categories
    if intel.categories:
        print("\n--- Categories ---")
        for cat in intel.categories[:5]:
            print(f"   • {cat.get('name', cat)}")
    
    # Alternatives
    if intel.alternatives:
        print(f"\n--- Top Alternatives ({len(intel.alternatives)} total) ---")
        sorted_alts = sorted(intel.alternatives, key=lambda x: x.get("reviews", 0), reverse=True)
        for alt in sorted_alts[:5]:
            rating = alt.get("rating", "?")
            reviews = alt.get("reviews", 0)
            print(f"   • {alt.get('name')}: {rating}⭐ ({reviews:,} reviews)")
    
    # Pricing
    if intel.pricing_plans:
        print(f"\n--- Pricing Plans ({len(intel.pricing_plans)} tiers) ---")
        for plan in intel.pricing_plans:
            name = plan.get("plan_name", "Unknown")
            price = plan.get("plan_price", "N/A")
            print(f"   • {name}: {price}")
    
    # Features
    if intel.feature_summary:
        print(f"\n--- Key Features ({len(intel.feature_summary)} total) ---")
        for feat in intel.feature_summary[:10]:
            print(f"   • {feat.get('name')} ({feat.get('category', '')})")
    
    print()


async def main():
    parser = argparse.ArgumentParser(
        description="Scrape G2 reviews using omkar-cloud/g2-product-scraper"
    )
    parser.add_argument(
        "product",
        help="Product name/slug (e.g., notion, slack, gorgias) or full G2 URL"
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=50,
        help="Maximum number of reviews to collect (default: 50)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path for reviews (JSON)"
    )
    parser.add_argument(
        "--intel", "-i",
        action="store_true",
        help="Show product intelligence (alternatives, pricing, features)"
    )
    parser.add_argument(
        "--intel-output",
        help="Output file path for intelligence data (JSON)"
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
    
    scraper = G2Scraper(settings)
    g2_url = scraper.build_g2_url(args.product)
    
    print(f"🔍 Scraping G2 for: {args.product}")
    print(f"   URL: {g2_url}")
    print(f"   Limit: {args.limit} reviews")
    print(f"   Actor: omkar-cloud/g2-product-scraper")
    print()
    print("⏳ This may take a few minutes...")
    print()
    
    try:
        # Use scrape_with_intelligence to get both
        result = await scraper.scrape_with_intelligence(args.product, limit=args.limit)
        reviews = result.reviews
        intel = result.intelligence
        
        print(f"✅ Found {len(reviews)} reviews")
        
        # Display product intelligence
        if args.intel or args.intel_output:
            display_intelligence(intel)
        
        # Display reviews (skip if only intel requested)
        if not args.intel or args.output:
            print()
            for i, review in enumerate(reviews[:20], 1):  # Show max 20
                print(f"─── Review {i} ───")
                if review.author:
                    print(f"👤 Author: {review.author}")
                if review.metadata:
                    if review.metadata.get("job_title"):
                        print(f"💼 Role: {review.metadata['job_title']}")
                    if review.metadata.get("rating"):
                        rating = review.metadata["rating"]
                        rating_int = int(rating) if rating else 0
                        stars = "★" * rating_int + "☆" * (5 - rating_int)
                        print(f"⭐ Rating: {stars} ({rating}/5)")
                    if review.metadata.get("company_size"):
                        print(f"🏢 Company: {review.metadata['company_size']}")
                if review.review_date:
                    print(f"📅 Date: {review.review_date.strftime('%Y-%m-%d')}")
                
                # Show likes/dislikes if available
                if review.metadata:
                    if review.metadata.get("likes"):
                        likes_preview = review.metadata['likes'][:200]
                        print(f"👍 Likes: {likes_preview}{'...' if len(review.metadata['likes']) > 200 else ''}")
                    if review.metadata.get("dislikes"):
                        dislikes_preview = review.metadata['dislikes'][:200]
                        print(f"👎 Dislikes: {dislikes_preview}{'...' if len(review.metadata['dislikes']) > 200 else ''}")
                
                print(f"📝 Content: {review.content[:300]}...")
                print()
            
            if len(reviews) > 20:
                print(f"... and {len(reviews) - 20} more reviews")
                print()
        
        # Save reviews to file
        if args.output:
            output_data = [r.to_dict() for r in reviews]
            # Convert datetime to string for JSON
            for r in output_data:
                if r.get("review_date"):
                    r["review_date"] = r["review_date"].isoformat()
            
            with open(args.output, "w") as f:
                json.dump(output_data, f, indent=2)
            print(f"💾 Reviews saved to: {args.output}")
        
        # Save intelligence to file
        if args.intel_output and intel:
            intel_data = intel.to_dict()
            with open(args.intel_output, "w") as f:
                json.dump(intel_data, f, indent=2)
            print(f"💾 Intelligence saved to: {args.intel_output}")
        
        # Show cost estimate
        cost = await scraper.estimate_cost(len(reviews))
        print(f"💰 Estimated cost: ${cost:.4f}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

