"""UserDataset Pydantic schemas for API contracts."""

from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from typing import Optional, Dict, Any

from .base import BaseSchema, TimestampMixin


class UserDatasetBase(BaseSchema):
    """Base user dataset schema with common fields."""
    
    name: str = Field(..., description="Dataset name", min_length=1, max_length=255)
    table_name: Optional[str] = Field(None, description="Database table name for the dataset")
    description: Optional[str] = Field(None, description="Dataset description")
    file_path: Optional[str] = Field(None, description="Path to the dataset file")
    file_size: Optional[int] = Field(None, description="File size in bytes", ge=0)
    row_count: Optional[int] = Field(None, description="Number of rows in the dataset", ge=0)
    metadata_: Optional[Dict[str, Any]] = Field(None, description="Additional dataset metadata", serialization_alias="metadata")


class UserDatasetCreate(UserDatasetBase):
    """Schema for creating a new user dataset."""
    
    user_id: UUID = Field(..., description="User identifier")


class UserDatasetUpdate(BaseSchema):
    """Schema for updating an existing user dataset."""
    
    name: Optional[str] = Field(None, description="Dataset name", min_length=1, max_length=255)
    table_name: Optional[str] = Field(None, description="Database table name for the dataset")
    description: Optional[str] = Field(None, description="Dataset description")
    file_path: Optional[str] = Field(None, description="Path to the dataset file")
    file_size: Optional[int] = Field(None, description="File size in bytes", ge=0)
    row_count: Optional[int] = Field(None, description="Number of rows in the dataset", ge=0)
    metadata_: Optional[Dict[str, Any]] = Field(None, description="Additional dataset metadata", serialization_alias="metadata")


class UserDatasetResponse(UserDatasetBase, TimestampMixin):
    """Schema for user dataset response.
    
    Maps to database table: user_datasets
    """
    
    id: UUID = Field(..., description="Dataset unique identifier")
    user_id: UUID = Field(..., description="User identifier")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "987e6543-e21b-12d3-a456-426614174000",
                "name": "Customer Reviews Q1 2024",
                "table_name": "customer_reviews_q1_2024",
                "description": "Product reviews collected in Q1 2024",
                "file_path": "/data/uploads/user_123/reviews_q1_2024.csv",
                "file_size": 2048576,
                "row_count": 15000,
                "metadata": {
                    "columns": ["review_id", "product_id", "rating", "comment"],
                    "format": "csv",
                    "encoding": "utf-8"
                },
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }
    )
