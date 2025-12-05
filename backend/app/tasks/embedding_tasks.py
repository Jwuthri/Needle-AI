"""
Celery tasks for generating and updating review embeddings.
"""

import logging
from typing import List, Optional

from celery import group

from app.core.celery_app import celery_app
from app.database.session import get_async_session
from app.database.repositories.review import ReviewRepository
from app.services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.embedding_tasks.generate_review_embedding",
    bind=True,
    max_retries=3,
    default_retry_delay=60
)
def generate_review_embedding(self, review_id: str) -> dict:
    """
    Generate and update embedding for a single review.
    
    Args:
        review_id: ID of the review to process
        
    Returns:
        Dictionary with status and review_id
    """
    try:
        import asyncio
        
        async def _generate():
            async with get_async_session() as db:
                # Get review
                review = await ReviewRepository.get_by_id(db, review_id)
                if not review:
                    logger.error(f"Review {review_id} not found")
                    return {"status": "error", "review_id": review_id, "error": "Review not found"}
                
                # Skip if already has embedding
                if review.embedding:
                    logger.info(f"Review {review_id} already has embedding")
                    return {"status": "skipped", "review_id": review_id}
                
                # Generate embedding
                embedding_service = get_embedding_service()
                embedding = await embedding_service.generate_embedding(review.content)
                
                if not embedding:
                    logger.error(f"Failed to generate embedding for review {review_id}")
                    return {"status": "error", "review_id": review_id, "error": "Embedding generation failed"}
                
                # Update review
                await ReviewRepository.update_embedding(db, review_id, embedding)
                await db.commit()
                
                logger.info(f"Successfully generated embedding for review {review_id}")
                return {"status": "success", "review_id": review_id}
        
        return asyncio.run(_generate())
        
    except Exception as e:
        logger.error(f"Error generating embedding for review {review_id}: {e}")
        self.retry(exc=e)


@celery_app.task(
    name="app.tasks.embedding_tasks.generate_embeddings_batch",
    bind=True
)
def generate_embeddings_batch(self, company_id: Optional[str] = None, batch_size: int = 100) -> dict:
    """
    Generate embeddings for reviews that don't have them yet.
    
    Args:
        company_id: Optional company ID to filter reviews
        batch_size: Number of reviews to process in this batch
        
    Returns:
        Dictionary with processing statistics
    """
    try:
        import asyncio
        
        async def _generate_batch():
            async with get_async_session() as db:
                # Get reviews without embeddings
                reviews = await ReviewRepository.get_reviews_without_embeddings(
                    db, 
                    limit=batch_size,
                    company_id=company_id
                )
                
                if not reviews:
                    logger.info("No reviews found without embeddings")
                    return {
                        "status": "completed",
                        "processed": 0,
                        "total_found": 0
                    }
                
                logger.info(f"Found {len(reviews)} reviews without embeddings")
                
                # Extract texts
                texts = [review.content for review in reviews]
                
                # Generate embeddings in batch
                embedding_service = get_embedding_service()
                embeddings = await embedding_service.generate_embeddings_batch(texts)
                
                # Update reviews
                successful = 0
                failed = 0
                
                for review, embedding in zip(reviews, embeddings):
                    if embedding:
                        await ReviewRepository.update_embedding(db, review.id, embedding)
                        successful += 1
                    else:
                        failed += 1
                        logger.warning(f"Failed to generate embedding for review {review.id}")
                
                await db.commit()
                
                logger.info(
                    f"Batch processing completed. "
                    f"Successful: {successful}, Failed: {failed}"
                )
                
                return {
                    "status": "completed",
                    "processed": successful,
                    "failed": failed,
                    "total_found": len(reviews)
                }
        
        return asyncio.run(_generate_batch())
        
    except Exception as e:
        logger.error(f"Error in batch embedding generation: {e}")
        raise


@celery_app.task(
    name="app.tasks.embedding_tasks.generate_all_embeddings",
    bind=True
)
def generate_all_embeddings(
    self, 
    company_id: Optional[str] = None,
    batch_size: int = 100
) -> dict:
    """
    Generate embeddings for all reviews without them, processing in batches.
    
    This task orchestrates multiple batch tasks.
    
    Args:
        company_id: Optional company ID to filter reviews
        batch_size: Number of reviews per batch
        
    Returns:
        Dictionary with overall statistics
    """
    try:
        import asyncio
        
        async def _count_reviews():
            async with get_async_session() as db:
                reviews = await ReviewRepository.get_reviews_without_embeddings(
                    db, 
                    limit=10000,  # Get count up to 10k
                    company_id=company_id
                )
                return len(reviews)
        
        total_reviews = asyncio.run(_count_reviews())
        
        if total_reviews == 0:
            logger.info("No reviews need embeddings")
            return {
                "status": "completed",
                "total_reviews": 0,
                "batches_created": 0
            }
        
        # Calculate number of batches needed
        num_batches = (total_reviews + batch_size - 1) // batch_size
        
        logger.info(
            f"Starting embedding generation for {total_reviews} reviews "
            f"in {num_batches} batches"
        )
        
        # Create batch tasks
        batch_tasks = []
        for i in range(num_batches):
            batch_tasks.append(
                generate_embeddings_batch.s(
                    company_id=company_id,
                    batch_size=batch_size
                )
            )
        
        # Execute batches in parallel (with Celery's concurrency control)
        job = group(batch_tasks)
        result = job.apply_async()
        
        return {
            "status": "processing",
            "total_reviews": total_reviews,
            "batches_created": num_batches,
            "task_group_id": result.id
        }
        
    except Exception as e:
        logger.error(f"Error orchestrating embedding generation: {e}")
        raise


@celery_app.task(
    name="app.tasks.embedding_tasks.regenerate_review_embedding",
    bind=True,
    max_retries=3
)
def regenerate_review_embedding(self, review_id: str) -> dict:
    """
    Regenerate embedding for a review (even if it already has one).
    
    Args:
        review_id: ID of the review to process
        
    Returns:
        Dictionary with status and review_id
    """
    try:
        import asyncio
        
        async def _regenerate():
            async with get_async_session() as db:
                # Get review
                review = await ReviewRepository.get_by_id(db, review_id)
                if not review:
                    logger.error(f"Review {review_id} not found")
                    return {"status": "error", "review_id": review_id, "error": "Review not found"}
                
                # Generate embedding
                embedding_service = get_embedding_service()
                embedding = await embedding_service.generate_embedding(review.content)
                
                if not embedding:
                    logger.error(f"Failed to generate embedding for review {review_id}")
                    return {"status": "error", "review_id": review_id, "error": "Embedding generation failed"}
                
                # Update review
                await ReviewRepository.update_embedding(db, review_id, embedding)
                await db.commit()
                
                logger.info(f"Successfully regenerated embedding for review {review_id}")
                return {"status": "success", "review_id": review_id}
        
        return asyncio.run(_regenerate())
        
    except Exception as e:
        logger.error(f"Error regenerating embedding for review {review_id}: {e}")
        self.retry(exc=e)

