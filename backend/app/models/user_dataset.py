"""
Pydantic models for user dataset API endpoints.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class FieldMetadataResponse(BaseModel):
    """Field metadata response model."""

    field_name: str = Field(..., description="Name of the field")
    data_type: str = Field(..., description="Data type")
    description: str = Field(..., description="Field description")
    unique_value_count: Optional[int] = Field(default=None, description="Number of unique values")
    top_values: Optional[List[str]] = Field(default=None, description="Top values with counts")


class VectorStoreColumnsResponse(BaseModel):
    """Vector store columns response model."""

    main_column: str = Field(..., description="Primary column for text embedding")
    alternative_columns: List[str] = Field(..., description="Alternative columns for concatenation")
    description: str = Field(..., description="Explanation of column suitability")


class UserDatasetResponse(BaseModel):
    """Response model for user dataset."""

    id: str = Field(..., description="Dataset ID")
    user_id: str = Field(..., description="User ID")
    origin: str = Field(..., description="File origin (filename or URL)")
    table_name: str = Field(..., description="Table name in database (format: __user_{user_id}_{name})")
    description: Optional[str] = Field(default=None, description="LLM-generated summary")
    row_count: int = Field(..., description="Number of rows")
    field_metadata: Optional[List[dict]] = Field(default=None, description="Field metadata")
    column_stats: Optional[dict] = Field(default=None, description="Column statistics")
    sample_data: Optional[List[dict]] = Field(default=None, description="First 5 rows")
    vector_store_columns: Optional[dict] = Field(default=None, description="Vector store columns")
    meta: Optional[dict] = Field(default=None, description="Additional metadata")
    created_at: Optional[str] = Field(default=None, description="Creation timestamp")
    updated_at: Optional[str] = Field(default=None, description="Update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "dataset_123",
                "user_id": "user_456",
                "origin": "products.csv",
                "table_name": "__user_user_456_products",
                "description": "A dataset containing fashion products...",
                "row_count": 450,
                "field_metadata": [
                    {
                        "field_name": "product_id",
                        "data_type": "text",
                        "description": "Unique identifier for products",
                        "unique_value_count": 450,
                        "top_values": None
                    }
                ],
                "column_stats": {},
                "sample_data": [],
                "vector_store_columns": None,
                "meta": {},
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:00:00Z"
            }
        }


class UserDatasetListResponse(BaseModel):
    """Response model for listing user datasets."""

    datasets: List[UserDatasetResponse] = Field(..., description="List of datasets")
    total: int = Field(..., description="Total number of datasets")


class UserDatasetUploadResponse(BaseModel):
    """Response model for CSV upload."""

    success: bool = Field(..., description="Whether upload was successful")
    dataset_id: str = Field(..., description="Created dataset ID")
    table_name: str = Field(..., description="Table name in database (format: __user_{user_id}_{name})")
    row_count: int = Field(..., description="Number of rows imported")
    column_count: int = Field(..., description="Number of columns")
    description: str = Field(..., description="LLM-generated summary")
    field_metadata: List[dict] = Field(..., description="Field metadata")
    column_stats: dict = Field(..., description="Column statistics")
    sample_data: List[dict] = Field(..., description="First 5 rows")
    vector_store_columns: Optional[dict] = Field(default=None, description="Vector store columns")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "dataset_id": "dataset_123",
                "table_name": "__user_user_456_products",
                "row_count": 450,
                "column_count": 14,
                "description": "A dataset containing fashion products...",
                "field_metadata": [],
                "column_stats": {},
                "sample_data": [],
                "vector_store_columns": None
            }
        }

