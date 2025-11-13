"""Company Pydantic schemas for API contracts."""

from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from uuid import UUID
from typing import Optional

from .base import BaseSchema, TimestampMixin


class CompanyBase(BaseSchema):
    """Base company schema with common fields."""
    
    name: str = Field(..., description="Company name", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="Company description")
    website: Optional[str] = Field(None, description="Company website URL")


class CompanyCreate(CompanyBase):
    """Schema for creating a new company."""
    
    pass


class CompanyUpdate(BaseSchema):
    """Schema for updating an existing company."""
    
    name: Optional[str] = Field(None, description="Company name", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="Company description")
    website: Optional[str] = Field(None, description="Company website URL")


class CompanyResponse(CompanyBase, TimestampMixin):
    """Schema for company response.
    
    Maps to database table: companies
    """
    
    id: UUID = Field(..., description="Company's unique identifier")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Acme Corporation",
                "description": "Leading provider of innovative solutions",
                "website": "https://acme.com",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }
    )
