"""
Background tasks for company operations.
"""

import asyncio

from celery import Task

from app.core.celery_app import celery_app
from app.database.session import get_fresh_async_session
from app.database.repositories import CompanyRepository
from app.services.review_url_discovery import discover_review_urls
from app.utils.logging import get_logger

logger = get_logger("company_tasks")


@celery_app.task(bind=True, max_retries=2)
def discover_review_urls_task(self: Task, company_id: str) -> dict:
    """
    Celery task to discover review URLs for a company.
    
    Searches DuckDuckGo for G2, Trustpilot, and TrustRadius review pages.
    """
    try:
        return asyncio.run(_discover_review_urls_async(company_id))
    except Exception as e:
        logger.error(f"URL discovery task failed for company {company_id}: {e}")
        raise


async def _discover_review_urls_async(company_id: str) -> dict:
    """
    Async implementation of URL discovery.
    """
    async with get_fresh_async_session() as session:
        try:
            # Get company
            company = await CompanyRepository.get_by_id(session, company_id)
            if not company:
                logger.warning(f"Company not found: {company_id}")
                return {"status": "error", "message": "Company not found"}
            
            logger.info(f"Discovering review URLs for company: {company.name}")
            
            # Discover URLs
            urls = await discover_review_urls(company.name)
            
            # Filter out None values
            found_urls = {k: v for k, v in urls.items() if v}
            
            if found_urls:
                # Update company with found URLs
                await CompanyRepository.update(session, company_id, review_urls=found_urls)
                await session.commit()
                
                logger.info(f"Updated company {company.name} with review URLs: {found_urls}")
                return {
                    "status": "success",
                    "company_id": company_id,
                    "urls_found": found_urls
                }
            else:
                logger.info(f"No review URLs found for company: {company.name}")
                return {
                    "status": "success",
                    "company_id": company_id,
                    "urls_found": {}
                }
                
        except Exception as e:
            logger.error(f"Error discovering URLs for company {company_id}: {e}")
            await session.rollback()
            raise

