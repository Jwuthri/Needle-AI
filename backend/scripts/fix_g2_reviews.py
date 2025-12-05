#!/usr/bin/env python3
"""
Fix G2 reviews that were scraped without proper platform and embeddings.

Usage:
    uv run python scripts/fix_g2_reviews.py
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.session import get_async_session
from app.database.repositories.review import ReviewRepository
from app.database.repositories.review_source import ReviewSourceRepository
from app.services.embedding_service import get_embedding_service
from sqlalchemy import text


async def fix_g2_reviews():
    """Fix G2 reviews: set platform and generate embeddings."""
    async with get_async_session() as session:
        # 1. Fix platform for reviews from G2 source
        print("Looking for G2 source...")
        
        # Find G2 source
        result = await session.execute(
            text("SELECT id FROM review_sources WHERE source_type = 'g2' LIMIT 1")
        )
        g2_source = result.fetchone()
        
        if not g2_source:
            print("No G2 source found!")
            return
        
        g2_source_id = g2_source[0]
        print(f"Found G2 source: {g2_source_id}")
        
        # Update platform for all reviews from G2 source that have platform = NULL or 'unknown'
        update_result = await session.execute(
            text("""
                UPDATE reviews 
                SET platform = 'g2' 
                WHERE source_id = :source_id 
                AND (platform IS NULL OR platform = 'unknown')
            """),
            {"source_id": g2_source_id}
        )
        await session.commit()
        print(f"Updated platform for {update_result.rowcount} reviews")
        
        # 2. Generate embeddings for reviews without them
        print("\nGenerating embeddings for reviews without them...")
        
        reviews_without_embeddings = await ReviewRepository.get_reviews_without_embeddings(
            session, limit=1000
        )
        
        if not reviews_without_embeddings:
            print("All reviews have embeddings!")
            return
        
        print(f"Found {len(reviews_without_embeddings)} reviews without embeddings")
        
        embedding_service = get_embedding_service()
        
        # Process in batches of 50
        batch_size = 50
        total_embedded = 0
        
        for i in range(0, len(reviews_without_embeddings), batch_size):
            batch = reviews_without_embeddings[i:i+batch_size]
            texts = [r.content for r in batch]
            
            print(f"Processing batch {i//batch_size + 1} ({len(batch)} reviews)...")
            
            try:
                embeddings = await embedding_service.generate_embeddings_batch(texts)
                
                for review, embedding in zip(batch, embeddings):
                    if embedding:
                        await ReviewRepository.update_embedding(session, review.id, embedding)
                        total_embedded += 1
                
                await session.commit()
                print(f"  Embedded {total_embedded} reviews so far")
                
            except Exception as e:
                print(f"  Error in batch: {e}")
                continue
        
        print(f"\nDone! Generated embeddings for {total_embedded} reviews")
        
        # 3. Re-sync to user table
        print("\nRe-syncing to user tables...")
        
        # Get unique user_ids from companies
        result = await session.execute(
            text("""
                SELECT DISTINCT c.created_by 
                FROM companies c 
                JOIN reviews r ON r.company_id = c.id
            """)
        )
        user_ids = [row[0] for row in result.fetchall()]
        
        from app.services.user_reviews_service import UserReviewsService
        
        for user_id in user_ids:
            try:
                reviews_service = UserReviewsService(session)
                synced = await reviews_service.sync_reviews_to_user_table(user_id=user_id)
                print(f"  Synced {synced} reviews for user {user_id}")
            except Exception as e:
                print(f"  Error syncing for user {user_id}: {e}")
        
        print("\nAll done!")


if __name__ == "__main__":
    asyncio.run(fix_g2_reviews())

