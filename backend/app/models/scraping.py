"""
Scraping API models.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.database.models.scraping_job import JobStatusEnum


class ScrapingJobCreate(BaseModel):
    """Request to create a scraping job."""
    company_id: str = Field(..., description="Company ID to scrape reviews for")
    source_id: str = Field(..., description="Review source ID (Reddit, Twitter, etc.)")
    review_count: Optional[int] = Field(None, ge=1, le=1000, description="Number of reviews to scrape/generate")
    max_cost: Optional[float] = Field(None, ge=0.01, le=1000.0, description="Maximum cost in credits")
    generation_mode: Optional[str] = Field(None, description="Mode: 'fake' for LLM generation, 'real' for actual scraping")

    class Config:
        json_schema_extra = {
            "example": {
                "company_id": "comp_123",
                "source_id": "source_reddit",
                "review_count": 100,
                "generation_mode": "fake"
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
    # Human-readable names
    source_name: Optional[str] = None
    company_name: Optional[str] = None

    class Config:
        from_attributes = True


class CostEstimate(BaseModel):
    """Cost estimate for scraping."""
    source_name: str
    review_count: int
    cost: float
    cost_per_review: float

