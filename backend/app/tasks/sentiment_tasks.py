"""
Celery tasks for sentiment analysis.
"""

import asyncio
from typing import List

from celery import Task

from app.config import get_settings
from app.core.celery_app import celery_app
from app.database.session import get_async_session
from app.database.repositories import ReviewRepository
from app.utils.logging import get_logger

logger = get_logger("sentiment_tasks")


@celery_app.task(bind=True)
def analyze_sentiment_batch(self: Task, review_ids: List[str]) -> dict:
    """Celery wrapper for async sentiment analysis."""
    try:
        return asyncio.run(analyze_sentiment_batch_async(self, review_ids))
    except Exception as e:
        logger.error(f"Sentiment analysis task failed: {e}")
        raise


async def analyze_sentiment_batch_async(task: Task, review_ids: List[str]) -> dict:
    """
    Analyze sentiment for a batch of reviews using LLM.
    
    Uses a simple prompt-based approach with the configured LLM.
    """
    settings = get_settings()
    
    try:
        from agno.agent import Agent
        from agno.models.openrouter import OpenRouter
        
        # Create sentiment analysis agent with latest API
        api_key = settings.get_secret("openrouter_api_key")
        api_key_str = str(api_key) if hasattr(api_key, '__str__') else api_key
        
        agent = Agent(
            model=OpenRouter(
                id=settings.default_model,
                api_key=api_key_str,
            ),
            instructions="""
            You are a sentiment analysis expert. Analyze the sentiment of customer reviews and provide a score.
            
            Score scale:
            - 1.0: Very positive
            - 0.5: Positive
            - 0.0: Neutral
            - -0.5: Negative
            - -1.0: Very negative
            
            Respond with ONLY a number between -1.0 and 1.0.
            """,
        )
        
    except ImportError:
        logger.error("Agno not available for sentiment analysis")
        return {"success": False, "error": "Agno not installed"}

    async with get_async_session() as session:
        analyzed_count = 0
        failed_count = 0

        for i, review_id in enumerate(review_ids):
            try:
                # Get review
                review = await ReviewRepository.get_by_id(session, review_id)
                if not review or review.sentiment_score is not None:
                    continue  # Skip if already analyzed

                # Analyze sentiment with LLM using async arun()
                prompt = f"Review: {review.content[:500]}"  # Truncate long reviews
                response = await agent.arun(prompt)
                
                # Parse sentiment score
                try:
                    if isinstance(response, str):
                        score_text = response
                    elif hasattr(response, 'content'):
                        score_text = response.content
                    else:
                        score_text = str(response)
                    
                    sentiment_score = float(score_text.strip())
                    
                    # Clamp to valid range
                    sentiment_score = max(-1.0, min(1.0, sentiment_score))
                    
                except (ValueError, AttributeError):
                    logger.warning(f"Could not parse sentiment score from: {response}")
                    sentiment_score = 0.0  # Default to neutral

                # Update review with sentiment
                await ReviewRepository.update_sentiment(
                    session,
                    review_id,
                    sentiment_score
                )
                analyzed_count += 1

                # Update progress
                progress = int(((i + 1) / len(review_ids)) * 100)
                task.update_state(
                    state='PROGRESS',
                    meta={'current': progress, 'total': 100, 'analyzed': analyzed_count}
                )

            except Exception as e:
                logger.warning(f"Failed to analyze sentiment for review {review_id}: {e}")
                failed_count += 1
                continue

        # Commit all changes
        await session.commit()

        logger.info(f"Sentiment analysis completed: {analyzed_count} analyzed, {failed_count} failed")

        return {
            "analyzed": analyzed_count,
            "failed": failed_count,
            "total": len(review_ids)
        }

