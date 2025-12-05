"""
Company API models for product review analysis.
"""

from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, Field


class ReviewUrls(BaseModel):
    """Auto-discovered review URLs for a company."""
    g2: Optional[str] = None
    trustpilot: Optional[str] = None
    trustradius: Optional[str] = None


class CompanyCreate(BaseModel):
    """Request model for creating a company."""
    name: str = Field(..., min_length=1, max_length=255, description="Company name")
    domain: Optional[str] = Field(None, max_length=255, description="Company domain (e.g., gorgias.com)")
    industry: Optional[str] = Field(None, max_length=100, description="Industry sector")
    description: Optional[str] = Field(None, description="Company description")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Gorgias",
                "domain": "gorgias.com",
                "industry": "Customer Support Software",
                "description": "Help desk software for e-commerce"
            }
        }


class CompanyUpdate(BaseModel):
    """Request model for updating a company."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    domain: Optional[str] = Field(None, max_length=255)
    industry: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None)


class CompanyResponse(BaseModel):
    """Response model for company."""
    id: str
    name: str
    domain: Optional[str]
    industry: Optional[str]
    description: Optional[str]
    created_by: str
    created_at: datetime
    updated_at: datetime
    
    # Auto-discovered review URLs
    review_urls: Optional[Dict[str, str]] = None
    
    # Statistics
    total_reviews: Optional[int] = 0
    last_scrape: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "comp_123",
                "name": "Gorgias",
                "domain": "gorgias.com",
                "industry": "Customer Support Software",
                "created_by": "user_123",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "total_reviews": 150,
                "last_scrape": "2024-01-15T10:30:00Z",
                "review_urls": {
                    "g2": "https://www.g2.com/products/gorgias/reviews",
                    "trustpilot": "https://www.trustpilot.com/review/gorgias.com"
                }
            }
        }


class CompanyListResponse(BaseModel):
    """Response model for list of companies."""
    companies: list[CompanyResponse]
    total: int
    limit: int
    offset: int

