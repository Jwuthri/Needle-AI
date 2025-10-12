"""
Scraping API endpoints.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_rate_limit, get_db
from app.core.security.clerk_auth import ClerkUser, get_current_user
from app.database.repositories import (
    CompanyRepository,
    ReviewRepository,
    ReviewSourceRepository,
    ScrapingJobRepository,
    UserCreditRepository,
)
from app.exceptions import NotFoundError
from app.models.scraping import CostEstimate, ScrapingJobCreate, ScrapingJobResponse
from app.services.scraper_factory import get_scraper_factory
from app.tasks.scraping_tasks import scrape_reviews_task
from app.utils.logging import get_logger

logger = get_logger("scraping_api")

router = APIRouter()


@router.post("/jobs", response_model=ScrapingJobResponse, status_code=status.HTTP_201_CREATED)
async def create_scraping_job(
    data: ScrapingJobCreate,
    current_user: ClerkUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rate_limit = Depends(check_rate_limit)
) -> ScrapingJobResponse:
    """
    Start a new scraping job.
    
    This will:
    1. Check if user has sufficient credits
    2. Create a scraping job
    3. Start background task
    4. Return job details
    """
    try:
        # Verify company exists and user owns it
        company = await CompanyRepository.get_by_id(db, data.company_id)
        if not company or company.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found"
            )

        # Get source
        source = await ReviewSourceRepository.get_by_id(db, data.source_id)
        if not source or not source.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source not found or inactive"
            )

        # Calculate cost
        factory = get_scraper_factory()
        cost = await factory.estimate_total_cost(source.source_type, data.review_count)

        # Check credits
        has_credits = await UserCreditRepository.has_sufficient_credits(
            db, current_user.id, cost
        )
        if not has_credits:
            credit_account = await UserCreditRepository.get_by_user_id(db, current_user.id)
            available = credit_account.credits_available if credit_account else 0
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Insufficient credits. Required: {cost}, Available: {available}"
            )

        # Create job
        job = await ScrapingJobRepository.create(
            db,
            company_id=data.company_id,
            source_id=data.source_id,
            user_id=current_user.id,
            total_reviews_target=data.review_count,
            cost=cost
        )
        await db.commit()

        # Start background task
        task = scrape_reviews_task.delay(
            job_id=job.id,
            company_id=data.company_id,
            source_id=data.source_id,
            user_id=current_user.id,
            review_count=data.review_count
        )

        # Update job with Celery task ID
        await ScrapingJobRepository.set_celery_task_id(db, job.id, task.id)
        await db.commit()

        logger.info(f"Started scraping job {job.id} for user {current_user.id}")

        # Refresh job to get updated data
        job = await ScrapingJobRepository.get_by_id(db, job.id)
        return ScrapingJobResponse.model_validate(job)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating scraping job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create scraping job: {str(e)}"
        )


@router.get("/jobs/{job_id}", response_model=ScrapingJobResponse)
async def get_scraping_job(
    job_id: str,
    current_user: ClerkUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ScrapingJobResponse:
    """Get scraping job status and details."""
    try:
        job = await ScrapingJobRepository.get_by_id(db, job_id)
        
        if not job:
            raise NotFoundError(f"Job {job_id} not found")
        
        if job.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        return ScrapingJobResponse.model_validate(job)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job: {str(e)}"
        )


@router.get("/jobs", response_model=List[ScrapingJobResponse])
async def list_scraping_jobs(
    current_user: ClerkUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    company_id: str = None,
    limit: int = 50,
    offset: int = 0
) -> List[ScrapingJobResponse]:
    """List scraping jobs for current user."""
    try:
        if company_id:
            # Verify company ownership
            company = await CompanyRepository.get_by_id(db, company_id)
            if not company or company.created_by != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Company not found"
                )
            jobs = await ScrapingJobRepository.list_company_jobs(
                db, company_id, limit, offset
            )
        else:
            jobs = await ScrapingJobRepository.list_user_jobs(
                db, current_user.id, limit=limit, offset=offset
            )
        
        return [ScrapingJobResponse.model_validate(job) for job in jobs]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list jobs: {str(e)}"
        )


@router.get("/sources")
async def list_sources(
    db: AsyncSession = Depends(get_db)
):
    """List available review sources."""
    try:
        factory = get_scraper_factory()
        sources = factory.list_available_sources()
        
        return {"sources": sources}
        
    except Exception as e:
        logger.error(f"Error listing sources: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list sources: {str(e)}"
        )


@router.post("/estimate", response_model=CostEstimate)
async def estimate_cost(
    source_id: str,
    review_count: int,
    db: AsyncSession = Depends(get_db)
) -> CostEstimate:
    """Estimate cost for scraping."""
    try:
        source = await ReviewSourceRepository.get_by_id(db, source_id)
        if not source:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source not found"
            )
        
        factory = get_scraper_factory()
        cost = await factory.estimate_total_cost(source.source_type, review_count)
        
        return CostEstimate(
            source_name=source.name,
            review_count=review_count,
            cost=cost,
            cost_per_review=source.cost_per_review
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error estimating cost: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to estimate cost: {str(e)}"
        )

