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
from app.tasks.scraping_tasks import scrape_reviews_task, generate_fake_reviews_task
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
    Start a new scraping or fake review generation job.
    
    This will:
    1. Check if user has sufficient credits
    2. Calculate review count from max_cost if needed
    3. Create a scraping/generation job
    4. Start background task (real scraping or fake generation)
    5. Return job details
    """
    try:
        logger.info(f"Received scraping job request: company_id={data.company_id}, source_id={data.source_id}, review_count={data.review_count}, max_cost={data.max_cost}, generation_mode={data.generation_mode}")
        
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

        # Determine review count and cost
        review_count = data.review_count
        max_cost = data.max_cost
        
        # If max_cost is provided but not review_count, calculate review_count
        if max_cost is not None and review_count is None:
            review_count = int(max_cost / source.cost_per_review)
            review_count = max(1, min(1000, review_count))  # Clamp between 1 and 1000
        
        # If review_count is not set by now, raise error
        if review_count is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either review_count or max_cost must be provided"
            )

        # Calculate cost
        factory = get_scraper_factory()
        cost = await factory.estimate_total_cost(source.source_type, review_count)

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
            total_reviews_target=review_count,
            cost=cost
        )
        await db.commit()

        # Determine if this is fake generation or real scraping
        # Check config first, then fallback to name-based detection
        source_config = source.config or {}
        is_fake_generation = (
            data.generation_mode == "fake" or
            source_config.get("type") == "fake_generator" or
            "fake" in source.name.lower() or
            "llm" in source.name.lower()
        )

        # Start appropriate background task
        if is_fake_generation:
            task = generate_fake_reviews_task.delay(
                job_id=job.id,
                company_id=data.company_id,
                source_id=data.source_id,
                user_id=current_user.id,
                review_count=review_count
            )
            logger.info(f"Started fake review generation job {job.id} for user {current_user.id}")
        else:
            task = scrape_reviews_task.delay(
                job_id=job.id,
                company_id=data.company_id,
                source_id=data.source_id,
                user_id=current_user.id,
                review_count=review_count
            )
            logger.info(f"Started scraping job {job.id} for user {current_user.id}")

        # Update job with Celery task ID
        await ScrapingJobRepository.set_celery_task_id(db, job.id, task.id)
        await db.commit()

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
        
        # Enrich jobs with source and company names
        result = []
        # Cache lookups to avoid repeated queries
        sources_cache = {}
        companies_cache = {}
        
        for job in jobs:
            job_data = ScrapingJobResponse.model_validate(job)
            
            # Get source name
            if job.source_id not in sources_cache:
                source = await ReviewSourceRepository.get_by_id(db, job.source_id)
                sources_cache[job.source_id] = source.name if source else None
            job_data.source_name = sources_cache[job.source_id]
            
            # Get company name
            if job.company_id not in companies_cache:
                company = await CompanyRepository.get_by_id(db, job.company_id)
                companies_cache[job.company_id] = company.name if company else None
            job_data.company_name = companies_cache[job.company_id]
            
            result.append(job_data)
        
        return result
        
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
    """List available review sources from the database."""
    try:
        # Get all active sources from database
        sources = await ReviewSourceRepository.list_active_sources(db)
        
        # Group sources by type (real vs fake)
        real_sources = []
        fake_sources = []
        
        for source in sources:
            source_dict = {
                "id": source.id,
                "name": source.name,
                "source_type": source.source_type if isinstance(source.source_type, str) else source.source_type.value,
                "description": source.description,
                "cost_per_review": source.cost_per_review,
                "is_active": source.is_active,
                "config": source.config
            }
            
            # Determine if fake or real based on config
            source_config = source.config or {}
            is_fake = (
                source_config.get("type") == "fake_generator" or
                "fake" in source.name.lower() or
                "llm" in source.name.lower()
            )
            
            if is_fake:
                fake_sources.append(source_dict)
            else:
                real_sources.append(source_dict)
        
        return {
            "sources": sources,  # All sources for backward compatibility
            "real_sources": real_sources,
            "fake_sources": fake_sources
        }
        
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

