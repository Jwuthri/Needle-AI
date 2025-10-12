"""
Celery tasks for vector indexing to Pinecone.
"""

import asyncio
from typing import List

from celery import Task

from app.core.celery_app import celery_app
from app.database.session import get_async_session
from app.database.repositories import ReviewRepository
from app.services.vector_service import VectorService
from app.utils.logging import get_logger

logger = get_logger("indexing_tasks")


@celery_app.task(bind=True)
def index_reviews_to_vector_db(self: Task, review_ids: List[str]) -> dict:
    """Celery wrapper for async vector indexing."""
    try:
        return asyncio.run(index_reviews_async(self, review_ids))
    except Exception as e:
        logger.error(f"Indexing task failed: {e}")
        raise


async def index_reviews_async(task: Task, review_ids: List[str]) -> dict:
    """
    Index reviews to Pinecone vector database.
    
    Args:
        task: Celery task instance
        review_ids: List of review IDs to index
        
    Returns:
        Result dictionary with indexed count
    """
    vector_service = VectorService()
    await vector_service.initialize()

    async with get_async_session() as session:
        indexed_count = 0
        failed_count = 0

        try:
            # Fetch all reviews
            reviews_to_index = []
            for review_id in review_ids:
                review = await ReviewRepository.get_by_id(session, review_id)
                if review:
                    reviews_to_index.append({
                        "review_id": review.id,
                        "content": review.content,
                        "company_id": review.company_id,
                        "source": review.source_id,
                        "sentiment_score": review.sentiment_score,
                        "author": review.author,
                        "url": review.url,
                        "review_date": review.review_date
                    })

            # Update progress
            task.update_state(
                state='PROGRESS',
                meta={'current': 10, 'total': 100, 'status': 'Generating embeddings...'}
            )

            # Batch index to Pinecone
            vector_ids = await vector_service.index_reviews_batch(
                reviews_to_index,
                batch_size=100
            )

            # Update progress
            task.update_state(
                state='PROGRESS',
                meta={'current': 80, 'total': 100, 'status': 'Updating database...'}
            )

            # Update reviews with vector IDs
            for i, (review, vector_id) in enumerate(zip(reviews_to_index, vector_ids)):
                try:
                    await ReviewRepository.set_vector_id(
                        session,
                        review["review_id"],
                        vector_id
                    )
                    indexed_count += 1
                except Exception as e:
                    logger.warning(f"Failed to update vector ID for review {review['review_id']}: {e}")
                    failed_count += 1

            # Commit changes
            await session.commit()

            task.update_state(
                state='PROGRESS',
                meta={'current': 100, 'total': 100, 'status': 'Completed'}
            )

            logger.info(f"Indexed {indexed_count} reviews to Pinecone")

            return {
                "indexed": indexed_count,
                "failed": failed_count,
                "total": len(review_ids)
            }

        except Exception as e:
            logger.error(f"Error indexing reviews: {e}")
            raise

        finally:
            await vector_service.cleanup()


@celery_app.task
def index_single_review(review_id: str) -> dict:
    """Index a single review (for real-time indexing)."""
    try:
        return asyncio.run(index_single_review_async(review_id))
    except Exception as e:
        logger.error(f"Single review indexing failed: {e}")
        raise


async def index_single_review_async(review_id: str) -> dict:
    """Async implementation for single review indexing."""
    vector_service = VectorService()
    await vector_service.initialize()

    async with get_async_session() as session:
        try:
            # Get review
            review = await ReviewRepository.get_by_id(session, review_id)
            if not review:
                return {"success": False, "error": "Review not found"}

            # Index to Pinecone
            vector_id = await vector_service.index_review(
                review_id=review.id,
                content=review.content,
                company_id=review.company_id,
                source=review.source_id,
                sentiment_score=review.sentiment_score,
                author=review.author,
                url=review.url,
                review_date=review.review_date,
                metadata=review.metadata
            )

            # Update review with vector ID
            await ReviewRepository.set_vector_id(session, review_id, vector_id)
            await session.commit()

            logger.info(f"Indexed single review {review_id}")

            return {"success": True, "vector_id": vector_id}

        except Exception as e:
            logger.error(f"Error indexing single review {review_id}: {e}")
            raise

        finally:
            await vector_service.cleanup()

