"""
Scraping API models.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.database.models.scraping_job import JobStatusEnum


class ScrapingJobCreate(BaseModel):
    """Request to create a scraping job."""
    company_id: str = Field(..., description="Company ID to scrape reviews for")
    source_id: str = Field(..., description="Review source ID (Reddit, Twitter, etc.)")
    review_count: int = Field(..., ge=1, le=1000, description="Number of reviews to scrape")

    class Config:
        json_schema_extra = {
            "example": {
                "company_id": "comp_123",
                "source_id": "source_reddit",
                "review_count": 100
            }
        }


class ScrapingJobResponse(BaseModel):
    """Scraping job response."""
    id: str
    company_id: str
    source_id: str
    user_id: str
    status: JobStatusEnum
    progress_percentage: float
    total_reviews_target: int
    reviews_fetched: int
    cost: float
    celery_task_id: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class CostEstimate(BaseModel):
    """Cost estimate for scraping."""
    source_name: str
    review_count: int
    cost: float
    cost_per_review: float

