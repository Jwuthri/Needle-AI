"""
Celery tasks for review scraping.
"""

import asyncio
from typing import List

from celery import Task

from app.config import get_settings
from app.core.celery_app import celery_app
from app.database.models.scraping_job import JobStatusEnum
from app.database.models.review_source import SourceTypeEnum
from app.database.session import get_async_session
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
    
    async with get_async_session() as session:
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

