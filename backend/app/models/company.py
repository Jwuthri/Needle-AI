"""
Company API models for product review analysis.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


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
    
    # Statistics
    total_reviews: Optional[int] = 0
    
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
                "total_reviews": 150
            }
        }


class CompanyListResponse(BaseModel):
    """Response model for list of companies."""
    companies: list[CompanyResponse]
    total: int
    limit: int
    offset: int

