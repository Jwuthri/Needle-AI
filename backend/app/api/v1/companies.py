"""
Companies API endpoints for product review analysis.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_rate_limit, get_db
from app.core.security.clerk_auth import ClerkUser, get_current_user
from app.database.repositories import CompanyRepository, ReviewRepository
from app.database.repositories.scraping_job import ScrapingJobRepository
from app.exceptions import NotFoundError
from app.models.company import (
    CompanyCreate,
    CompanyListResponse,
    CompanyResponse,
    CompanyUpdate,
)
from app.tasks.company_tasks import discover_review_urls_task
from app.utils.logging import get_logger

logger = get_logger("companies_api")

router = APIRouter()


@router.post("/", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    data: CompanyCreate,
    current_user: ClerkUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rate_limit = Depends(check_rate_limit)
) -> CompanyResponse:
    """
    Create a new company for review analysis.
    
    The company will be associated with the current user.
    Automatically discovers review URLs in the background.
    """
    try:
        company = await CompanyRepository.create(
            db,
            name=data.name,
            domain=data.domain,
            industry=data.industry,
            description=data.description,
            created_by=current_user.id
        )
        await db.commit()
        
        logger.info(f"Created company {company.id} for user {current_user.id}")
        
        # Trigger background task to discover review URLs
        discover_review_urls_task.delay(company.id)
        logger.info(f"Triggered URL discovery for company {company.id}")
        
        return CompanyResponse.model_validate(company)
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating company: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create company: {str(e)}"
        )


@router.get("/", response_model=CompanyListResponse)
async def list_companies(
    current_user: ClerkUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0
) -> CompanyListResponse:
    """List all companies for the current user."""
    try:
        companies = await CompanyRepository.list_user_companies(
            db,
            user_id=current_user.id,
            limit=limit,
            offset=offset
        )
        
        total = await CompanyRepository.count_user_companies(db, current_user.id)
        
        # Enrich with review counts and last scrape dates
        company_responses = []
        for company in companies:
            review_count = await ReviewRepository.count_company_reviews(db, company.id)
            last_scrape = await ScrapingJobRepository.get_last_scrape_date(db, company.id)
            company_dict = company.__dict__.copy()
            company_dict['total_reviews'] = review_count
            company_dict['last_scrape'] = last_scrape
            company_responses.append(CompanyResponse.model_validate(company_dict))
        
        return CompanyListResponse(
            companies=company_responses,
            total=total,
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        logger.error(f"Error listing companies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list companies: {str(e)}"
        )


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: str,
    current_user: ClerkUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> CompanyResponse:
    """Get a specific company by ID."""
    try:
        company = await CompanyRepository.get_by_id(db, company_id)
        
        if not company:
            raise NotFoundError(f"Company {company_id} not found")
        
        # Check ownership
        if company.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this company"
            )
        
        # Get review count and last scrape date
        review_count = await ReviewRepository.count_company_reviews(db, company.id)
        last_scrape = await ScrapingJobRepository.get_last_scrape_date(db, company.id)
        company_dict = company.__dict__.copy()
        company_dict['total_reviews'] = review_count
        company_dict['last_scrape'] = last_scrape
        
        return CompanyResponse.model_validate(company_dict)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting company: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get company: {str(e)}"
        )


@router.patch("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: str,
    data: CompanyUpdate,
    current_user: ClerkUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> CompanyResponse:
    """Update a company."""
    try:
        company = await CompanyRepository.get_by_id(db, company_id)
        
        if not company:
            raise NotFoundError(f"Company {company_id} not found")
        
        if company.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this company"
            )
        
        # Update fields
        update_data = data.model_dump(exclude_unset=True)
        updated_company = await CompanyRepository.update(db, company_id, **update_data)
        await db.commit()
        
        logger.info(f"Updated company {company_id}")
        
        return CompanyResponse.model_validate(updated_company)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating company: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update company: {str(e)}"
        )


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(
    company_id: str,
    current_user: ClerkUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a company and all associated data."""
    try:
        company = await CompanyRepository.get_by_id(db, company_id)
        
        if not company:
            raise NotFoundError(f"Company {company_id} not found")
        
        if company.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this company"
            )
        
        # Delete company (cascades to reviews, jobs, imports)
        await CompanyRepository.delete(db, company_id)
        await db.commit()
        
        logger.info(f"Deleted company {company_id}")
        
        return None
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting company: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete company: {str(e)}"
        )

