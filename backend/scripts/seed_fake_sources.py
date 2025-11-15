"""
Seed script to create fake review sources in the database.

This script creates LLM-based fake review generation sources that users can
select from the data sources page to generate realistic fake reviews.
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


async def seed_fake_sources():
    """Create fake review generation sources in the database."""
    
    fake_sources = [
        {
            "name": "LLM Fake Reviews - Reddit",
            "source_type": SourceTypeEnum.REDDIT,
            "description": "Generate realistic fake Reddit-style reviews using AI. Perfect for testing and demonstration purposes.",
            "cost_per_review": 0.01,  # $0.01 per review
            "is_active": True,
            "config": {
                "type": "fake_generator",
                "platform": "reddit",
                "llm_based": True
            }
        },
        {
            "name": "LLM Fake Reviews - Twitter/X",
            "source_type": SourceTypeEnum.TWITTER,
            "description": "Generate realistic fake Twitter/X-style reviews using AI. Great for demos and testing workflows.",
            "cost_per_review": 0.01,  # $0.01 per review
            "is_active": True,
            "config": {
                "type": "fake_generator",
                "platform": "twitter",
                "llm_based": True
            }
        }
    ]
    
    async with get_async_session() as session:
        created_count = 0
        updated_count = 0
        
        for source_data in fake_sources:
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
        print(f"\n✅ Fake review sources seeded successfully!")
        print(f"   - Created: {created_count}")
        print(f"   - Updated: {updated_count}")
        print(f"\nThese sources are now available in the data sources page.\n")


def main():
    """Main entry point."""
    print("\n🌱 Seeding fake review sources...\n")
    try:
        asyncio.run(seed_fake_sources())
    except Exception as e:
        logger.error(f"Error seeding fake sources: {e}")
        print(f"\n❌ Error: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()

