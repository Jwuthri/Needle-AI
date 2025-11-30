"""
Seed script to create real review sources in the database.

This script creates real review scraping sources (G2, Trustpilot, TrustRadius)
that users can select from the data sources page to scrape actual reviews.

Working scrapers:
- G2: Uses omkar-cloud/g2-product-scraper Apify actor
- Trustpilot: Uses apify/website-content-crawler
- TrustRadius: Uses scraped/trustradius-review-scraper Apify actor
"""

import asyncio
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.database.session import get_async_session
from app.database.models.review_source import ReviewSource, SourceTypeEnum
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def seed_real_sources():
    """Create real review scraping sources in the database."""
    
    real_sources = [
        {
            "name": "G2",
            "source_type": SourceTypeEnum.G2,
            "description": "Scrape verified product reviews from G2.com. Get detailed B2B software reviews with ratings, pros, and cons.",
            "cost_per_review": 0.02,
            "is_active": True,
            "config": {
                "type": "real_scraper",
                "platform": "g2",
                "apify_based": True
            }
        },
        {
            "name": "Trustpilot",
            "source_type": SourceTypeEnum.TRUSTPILOT,
            "description": "Scrape verified customer reviews from Trustpilot. Access authentic reviews with star ratings and detailed feedback.",
            "cost_per_review": 0.015,
            "is_active": True,
            "config": {
                "type": "real_scraper",
                "platform": "trustpilot",
                "apify_based": True
            }
        },
        {
            "name": "TrustRadius",
            "source_type": SourceTypeEnum.TRUSTRADIUS,
            "description": "Scrape verified B2B software reviews from TrustRadius. Get detailed reviews with ratings, pros, cons, and buyer insights.",
            "cost_per_review": 0.02,
            "is_active": True,
            "config": {
                "type": "real_scraper",
                "platform": "trustradius",
                "apify_based": True
            }
        }
    ]
    
    async with get_async_session() as session:
        created_count = 0
        updated_count = 0
        
        for source_data in real_sources:
            # Check if source already exists
            from sqlalchemy.future import select
            result = await session.execute(
                select(ReviewSource).filter(ReviewSource.name == source_data["name"])
            )
            existing_source = result.scalar_one_or_none()
            
            if existing_source:
                # Update existing source
                existing_source.description = source_data["description"]
                existing_source.cost_per_review = source_data["cost_per_review"]
                existing_source.is_active = source_data["is_active"]
                existing_source.config = source_data["config"]
                existing_source.source_type = source_data["source_type"]
                updated_count += 1
                logger.info(f"Updated existing source: {source_data['name']}")
            else:
                # Create new source
                new_source = ReviewSource(**source_data)
                session.add(new_source)
                created_count += 1
                logger.info(f"Created new source: {source_data['name']}")
        
        await session.commit()
        
        logger.info(f"Seed complete: Created {created_count}, Updated {updated_count}")
        print(f"\n✅ Real review sources seeded successfully!")
        print(f"   - Created: {created_count}")
        print(f"   - Updated: {updated_count}")
        print(f"\nThese sources are now available in the data sources page.")
        print(f"\n⚠️  Make sure to configure your APIFY_API_TOKEN in .env file!\n")


def main():
    """Main entry point."""
    print("\n🌱 Seeding real review sources...\n")
    try:
        asyncio.run(seed_real_sources())
    except Exception as e:
        logger.error(f"Error seeding real sources: {e}")
        print(f"\n❌ Error: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()

