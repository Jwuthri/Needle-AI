"""
Celery tasks for review scraping and fake review generation.
"""

import asyncio
from typing import List

from celery import Task

from app.config import get_settings
from app.core.celery_app import celery_app
from app.database.models.scraping_job import JobStatusEnum
from app.database.models.review_source import SourceTypeEnum
from app.database.session import get_fresh_async_session
from app.database.repositories import (
    CompanyRepository,
    ReviewRepository,
    ReviewSourceRepository,
    ScrapingJobRepository,
    UserCreditRepository,
    CreditTransactionRepository
)
from app.database.models.credit_transaction import TransactionTypeEnum
from app.services.scraper_factory import get_scraper_factory
from app.services.fake_review_generator import get_fake_review_generator
from app.services.embedding_service import get_embedding_service
from app.utils.logging import get_logger

logger = get_logger("scraping_tasks")


@celery_app.task(bind=True, max_retries=3)
def scrape_reviews_task(
    self: Task,
    job_id: str,
    company_id: str,
    source_id: str,
    user_id: str,
    review_count: int
) -> dict:
    """
    Celery wrapper for async scraping task.
    
    This wraps the async scraping function to run in Celery.
    """
    try:
        return asyncio.run(
            scrape_reviews_async(self, job_id, company_id, source_id, user_id, review_count)
        )
    except Exception as e:
        logger.error(f"Scraping task failed: {e}")
        raise


async def scrape_reviews_async(
    task: Task,
    job_id: str,
    company_id: str,
    source_id: str,
    user_id: str,
    review_count: int
) -> dict:
    """
    Async scraping implementation.
    
    Steps:
    1. Get company and source details
    2. Initialize scraper
    3. Scrape reviews with progress updates
    4. Save reviews to database
    5. Deduct credits from user
    6. Update job status
    """
    settings = get_settings()
    
    async with get_fresh_async_session() as session:
        try:
            # Get job
            job = await ScrapingJobRepository.get_by_id(session, job_id)
            if not job:
                raise ValueError(f"Job not found: {job_id}")

            # Update job status to running
            await ScrapingJobRepository.update_status(
                session,
                job_id,
                JobStatusEnum.RUNNING
            )
            await session.commit()

            # Get company
            company = await CompanyRepository.get_by_id(session, company_id)
            if not company:
                raise ValueError(f"Company not found: {company_id}")

            # Get source
            source = await ReviewSourceRepository.get_by_id(session, source_id)
            if not source:
                raise ValueError(f"Source not found: {source_id}")

            # Update progress: 10%
            task.update_state(
                state='PROGRESS',
                meta={'current': 10, 'total': 100, 'status': 'Initializing scraper...'}
            )
            await ScrapingJobRepository.update_progress(session, job_id, 10.0, 0)
            await session.commit()

            # Get scraper
            factory = get_scraper_factory()
            scraper = factory.get_scraper(source.source_type)

            # Update progress: 20%
            task.update_state(
                state='PROGRESS',
                meta={'current': 20, 'total': 100, 'status': f'Scraping {source.name}...'}
            )
            await ScrapingJobRepository.update_progress(session, job_id, 20.0, 0)
            await session.commit()

            # Scrape reviews
            query = company.domain or company.name
            scraped_reviews = await scraper.scrape(query=query, limit=review_count)

            logger.info(f"Scraped {len(scraped_reviews)} reviews for job {job_id}")

            # Update progress: 60%
            task.update_state(
                state='PROGRESS',
                meta={'current': 60, 'total': 100, 'status': 'Saving reviews...'}
            )
            await ScrapingJobRepository.update_progress(session, job_id, 60.0, len(scraped_reviews))
            await session.commit()

            # Save reviews to database
            saved_count = 0
            for scraped in scraped_reviews:
                try:
                    await ReviewRepository.create(
                        session,
                        company_id=company_id,
                        source_id=source_id,
                        scraping_job_id=job_id,
                        content=scraped.content,
                        author=scraped.author,
                        url=scraped.url,
                        review_date=scraped.review_date,
                        metadata=scraped.metadata
                    )
                    saved_count += 1
                except Exception as e:
                    logger.warning(f"Failed to save review: {e}")
                    continue

            await session.commit()

            # Update progress: 80%
            task.update_state(
                state='PROGRESS',
                meta={'current': 80, 'total': 100, 'status': 'Deducting credits...'}
            )

            # Deduct credits
            credit_account = await UserCreditRepository.get_by_user_id(session, user_id)
            if credit_account:
                balance_before = credit_account.credits_available
                await UserCreditRepository.deduct_credits(session, user_id, job.cost)
                
                # Record transaction
                await CreditTransactionRepository.create(
                    session,
                    user_credit_id=credit_account.id,
                    transaction_type=TransactionTypeEnum.DEDUCTION,
                    amount=-job.cost,
                    balance_before=balance_before,
                    balance_after=credit_account.credits_available,
                    description=f"Scraping {saved_count} reviews from {source.name}",
                    scraping_job_id=job_id
                )
                await session.commit()

            # Update job to completed
            await ScrapingJobRepository.update_status(
                session,
                job_id,
                JobStatusEnum.COMPLETED
            )
            await ScrapingJobRepository.update_progress(session, job_id, 100.0, saved_count)
            await session.commit()

            # Sync reviews to user's aggregated table
            try:
                from app.services.user_reviews_service import UserReviewsService
                reviews_service = UserReviewsService(session)
                synced_count = await reviews_service.sync_reviews_to_user_table(
                    user_id=user_id,
                    scraping_job_id=job_id
                )
                logger.info(f"Synced {synced_count} reviews to user table for job {job_id}")
            except Exception as e:
                logger.warning(f"Failed to sync reviews to user table for job {job_id}: {e}")
                # Don't fail job completion if sync fails

            logger.info(f"Scraping job {job_id} completed successfully")

            return {
                "job_id": job_id,
                "status": "completed",
                "reviews_saved": saved_count,
                "cost": job.cost
            }

        except Exception as e:
            logger.error(f"Error in scraping job {job_id}: {e}")
            
            # Update job to failed
            try:
                await ScrapingJobRepository.update_status(
                    session,
                    job_id,
                    JobStatusEnum.FAILED,
                    error_message=str(e)
                )
                await session.commit()
            except:
                pass

            raise


@celery_app.task(bind=True, max_retries=3)
def generate_fake_reviews_task(
    self: Task,
    job_id: str,
    company_id: str,
    source_id: str,
    user_id: str,
    review_count: int
) -> dict:
    """
    Celery wrapper for async fake review generation task.
    
    This generates fake reviews using LLM one at a time with embeddings.
    """
    try:
        return asyncio.run(
            generate_fake_reviews_async(self, job_id, company_id, source_id, user_id, review_count)
        )
    except Exception as e:
        logger.error(f"Fake review generation task failed: {e}")
        raise


async def generate_fake_reviews_async(
    task: Task,
    job_id: str,
    company_id: str,
    source_id: str,
    user_id: str,
    review_count: int
) -> dict:
    """
    Async implementation for generating fake reviews.
    
    Steps:
    1. Get company and source details
    2. Initialize fake review generator
    3. Generate reviews one at a time with progress updates
    4. For each review: generate, save, embed, sync to user table
    5. Deduct credits from user
    6. Update job status
    """
    settings = get_settings()
    
    async with get_fresh_async_session() as session:
        try:
            # Get job
            job = await ScrapingJobRepository.get_by_id(session, job_id)
            if not job:
                raise ValueError(f"Job not found: {job_id}")

            # Update job status to running
            await ScrapingJobRepository.update_status(
                session,
                job_id,
                JobStatusEnum.RUNNING
            )
            await session.commit()

            # Get company
            company = await CompanyRepository.get_by_id(session, company_id)
            if not company:
                raise ValueError(f"Company not found: {company_id}")

            # Get source
            source = await ReviewSourceRepository.get_by_id(session, source_id)
            if not source:
                raise ValueError(f"Source not found: {source_id}")

            # Update progress: 5%
            task.update_state(
                state='PROGRESS',
                meta={'current': 5, 'total': 100, 'status': 'Initializing fake review generator...'}
            )
            await ScrapingJobRepository.update_progress(session, job_id, 5.0, 0)
            await session.commit()

            # Get fake review generator and embedding service
            generator = get_fake_review_generator()
            embedding_service = get_embedding_service()

            # Update progress: 10%
            task.update_state(
                state='PROGRESS',
                meta={'current': 10, 'total': 100, 'status': f'Generating {review_count} fake reviews...'}
            )
            await ScrapingJobRepository.update_progress(session, job_id, 10.0, 0)
            await session.commit()

            # Generate reviews one at a time
            saved_count = 0
            for i in range(review_count):
                try:
                    import time
                    start_time = time.time()
                    
                    # Generate fake review using LLM
                    logger.info(f"Starting review {i+1}/{review_count} generation...")
                    fake_review = await generator.generate_review(
                        company_name=company.name,
                        platform=source.name.lower().replace("llm fake reviews - ", ""),
                        industry=company.industry if hasattr(company, 'industry') else None
                    )
                    llm_time = time.time() - start_time
                    logger.info(f"LLM generation took {llm_time:.2f}s")

                    # Save review to database
                    save_start = time.time()
                    review = await ReviewRepository.create(
                        session,
                        company_id=company_id,
                        source_id=source_id,
                        scraping_job_id=job_id,
                        content=fake_review["content"],
                        author=fake_review["author"],
                        url=fake_review["url"],
                        sentiment_score=fake_review["sentiment_score"],
                        metadata=fake_review.get("extra_metadata", {}),
                        review_date=fake_review["review_date"],
                        platform=fake_review["platform"]
                    )
                    await session.flush()
                    save_time = time.time() - save_start
                    logger.info(f"Database save took {save_time:.2f}s")

                    # Generate and save embedding immediately
                    embed_start = time.time()
                    embedding = await embedding_service.generate_embedding(review.content)
                    if embedding:
                        await ReviewRepository.update_embedding(session, review.id, embedding)
                        await session.flush()
                    embed_time = time.time() - embed_start
                    logger.info(f"Embedding generation took {embed_time:.2f}s")

                    saved_count += 1
                    
                    total_time = time.time() - start_time
                    logger.info(f"Review {i+1}/{review_count} completed in {total_time:.2f}s (LLM: {llm_time:.2f}s, DB: {save_time:.2f}s, Embed: {embed_time:.2f}s)")

                    # Update progress after each review
                    # Progress from 10% to 90% based on reviews generated
                    progress = 10.0 + (80.0 * (i + 1) / review_count)
                    task.update_state(
                        state='PROGRESS',
                        meta={
                            'current': int(progress),
                            'total': 100,
                            'status': f'Generated {saved_count}/{review_count} reviews...'
                        }
                    )
                    await ScrapingJobRepository.update_progress(session, job_id, progress, saved_count)
                    await session.commit()

                    logger.info(f"Generated and saved fake review {i + 1}/{review_count} for job {job_id}")

                except Exception as e:
                    logger.warning(f"Failed to generate fake review {i + 1}: {e}")
                    # Continue with next review
                    continue

            # Update progress: 90%
            task.update_state(
                state='PROGRESS',
                meta={'current': 90, 'total': 100, 'status': 'Syncing reviews to user table...'}
            )

            # Sync all reviews to user table ONCE at the end
            from app.services.user_reviews_service import UserReviewsService
            reviews_service = UserReviewsService(session)
            await reviews_service.sync_reviews_to_user_table(
                user_id=user_id,
                scraping_job_id=job_id
            )
            await session.commit()

            # Update progress: 95%
            task.update_state(
                state='PROGRESS',
                meta={'current': 95, 'total': 100, 'status': 'Deducting credits...'}
            )

            # Deduct credits
            credit_account = await UserCreditRepository.get_by_user_id(session, user_id)
            if credit_account:
                balance_before = credit_account.credits_available
                await UserCreditRepository.deduct_credits(session, user_id, job.cost)
                
                # Record transaction
                await CreditTransactionRepository.create(
                    session,
                    user_credit_id=credit_account.id,
                    transaction_type=TransactionTypeEnum.DEDUCTION,
                    amount=-job.cost,
                    balance_before=balance_before,
                    balance_after=credit_account.credits_available,
                    description=f"Generated {saved_count} fake reviews from {source.name}",
                    scraping_job_id=job_id
                )
                await session.commit()

            # Update job to completed
            await ScrapingJobRepository.update_status(
                session,
                job_id,
                JobStatusEnum.COMPLETED
            )
            await ScrapingJobRepository.update_progress(session, job_id, 100.0, saved_count)
            await session.commit()

            logger.info(f"Fake review generation job {job_id} completed successfully with {saved_count} reviews")

            return {
                "job_id": job_id,
                "status": "completed",
                "reviews_generated": saved_count,
                "cost": job.cost
            }

        except Exception as e:
            logger.error(f"Error in fake review generation job {job_id}: {e}")
            
            # Update job to failed
            try:
                await ScrapingJobRepository.update_status(
                    session,
                    job_id,
                    JobStatusEnum.FAILED,
                    error_message=str(e)
                )
                await session.commit()
            except:
                pass

            raise

