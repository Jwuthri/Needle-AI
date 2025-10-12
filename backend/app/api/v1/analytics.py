"""
Analytics API endpoints for dashboard.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.security.clerk_auth import ClerkUser, get_current_user
from app.database.repositories import CompanyRepository, ReviewRepository
from app.database.repositories.llm_call import LLMCallRepository
from app.database.models.llm_call import LLMCallTypeEnum, LLMCallStatusEnum
from app.services.analytics_service import AnalyticsService
from app.utils.logging import get_logger

logger = get_logger("analytics_api")

router = APIRouter()


class OverviewResponse(BaseModel):
    """Analytics overview response."""
    total_reviews: int
    reviews_by_source: dict
    sentiment_distribution: dict
    average_sentiment: float
    date_range: dict


class InsightsResponse(BaseModel):
    """LLM-generated insights response."""
    themes: list[str]
    product_gaps: list[str]
    feature_requests: list[str]
    competitors: list[str]
    summary: str
    total_reviews_analyzed: int


@router.get("/{company_id}/overview", response_model=OverviewResponse)
async def get_analytics_overview(
    company_id: str,
    current_user: ClerkUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None
) -> OverviewResponse:
    """
    Get analytics overview for a company.
    
    Provides:
    - Total reviews count
    - Reviews breakdown by source
    - Sentiment distribution
    - Average sentiment score
    """
    try:
        # Verify company ownership
        company = await CompanyRepository.get_by_id(db, company_id)
        if not company or company.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found"
            )

        # Get analytics
        analytics_service = AnalyticsService()
        overview = await analytics_service.get_overview(
            db,
            company_id=company_id,
            date_from=date_from,
            date_to=date_to
        )

        return OverviewResponse(**overview)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting analytics overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get analytics: {str(e)}"
        )


@router.get("/{company_id}/insights", response_model=InsightsResponse)
async def get_company_insights(
    company_id: str,
    current_user: ClerkUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 50
) -> InsightsResponse:
    """
    Get LLM-generated insights for a company.
    
    Analyzes recent reviews to identify:
    - Common themes
    - Product gaps
    - Top feature requests
    - Competitor mentions
    - Overall summary
    """
    try:
        # Verify company ownership
        company = await CompanyRepository.get_by_id(db, company_id)
        if not company or company.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found"
            )

        # Generate insights
        analytics_service = AnalyticsService()
        await analytics_service.initialize()
        
        insights = await analytics_service.generate_insights(
            db,
            company_id=company_id,
            limit=limit
        )

        return InsightsResponse(**insights)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating insights: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate insights: {str(e)}"
        )


@router.get("/{company_id}/reviews")
async def get_filtered_reviews(
    company_id: str,
    current_user: ClerkUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    source_id: Optional[str] = None,
    min_sentiment: Optional[float] = None,
    max_sentiment: Optional[float] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    Get filtered reviews for a company.
    
    Supports filtering by:
    - Source (Reddit, Twitter, etc.)
    - Sentiment range
    - Pagination
    """
    try:
        # Verify company ownership
        company = await CompanyRepository.get_by_id(db, company_id)
        if not company or company.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found"
            )

        # Get reviews
        reviews = await ReviewRepository.list_company_reviews(
            db,
            company_id=company_id,
            source_id=source_id,
            min_sentiment=min_sentiment,
            max_sentiment=max_sentiment,
            limit=limit,
            offset=offset
        )

        # Format response
        review_data = []
        for review in reviews:
            review_data.append({
                "id": review.id,
                "content": review.content,
                "author": review.author,
                "url": review.url,
                "sentiment_score": review.sentiment_score,
                "source_id": review.source_id,
                "scraped_at": review.scraped_at.isoformat(),
                "review_date": review.review_date.isoformat() if review.review_date else None,
                "metadata": review.metadata
            })

        total = await ReviewRepository.count_company_reviews(db, company_id, source_id)

        return {
            "reviews": review_data,
            "total": total,
            "limit": limit,
            "offset": offset
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting filtered reviews: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get reviews: {str(e)}"
        )


@router.get("/{company_id}/sentiment-trend")
async def get_sentiment_trend(
    company_id: str,
    current_user: ClerkUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    days: int = 30
):
    """
    Get sentiment trend over time.
    
    Returns daily sentiment averages for the specified period.
    """
    try:
        # Verify company ownership
        company = await CompanyRepository.get_by_id(db, company_id)
        if not company or company.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found"
            )

        # Get trend data
        analytics_service = AnalyticsService()
        trend = await analytics_service.get_sentiment_trend(
            db,
            company_id=company_id,
            days=days
        )

        return trend

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting sentiment trend: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sentiment trend: {str(e)}"
        )


@router.get("/llm-calls/cost-stats")
async def get_llm_cost_stats(
    current_user: ClerkUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    days: int = 30
):
    """
    Get LLM call cost statistics for the current user.
    
    Returns:
    - Total calls and success/failure counts
    - Total cost and tokens used
    - Breakdown by call type and model
    """
    try:
        stats = await LLMCallRepository.get_cost_stats(
            db,
            user_id=current_user.id,
            days=days
        )
        return stats

    except Exception as e:
        logger.error(f"Error getting LLM cost stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cost stats: {str(e)}"
        )


@router.get("/llm-calls/list")
async def list_llm_calls(
    current_user: ClerkUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    session_id: Optional[str] = None,
    call_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    List LLM calls for the current user.
    
    Useful for debugging and monitoring LLM usage.
    """
    try:
        # Parse enum values
        call_type_enum = LLMCallTypeEnum(call_type) if call_type else None
        status_enum = LLMCallStatusEnum(status) if status else None
        
        calls = await LLMCallRepository.list_by_filters(
            db,
            user_id=current_user.id,
            session_id=session_id,
            call_type=call_type_enum,
            status=status_enum,
            limit=limit,
            offset=offset
        )
        
        # Convert to dict for JSON response
        calls_data = [call.to_dict() for call in calls]
        
        return {
            "calls": calls_data,
            "total": len(calls_data),
            "limit": limit,
            "offset": offset
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid enum value: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error listing LLM calls: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list LLM calls: {str(e)}"
        )

