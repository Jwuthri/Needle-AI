"""User Pydantic schemas for API contracts."""

from pydantic import BaseModel, ConfigDict, Field, EmailStr
from uuid import UUID
from typing import Optional

from .base import BaseSchema, TimestampMixin


class UserBase(BaseSchema):
    """Base user schema with common fields."""
    
    email: EmailStr = Field(..., description="User's email address")
    full_name: Optional[str] = Field(None, description="User's full name")


class UserCreate(UserBase):
    """Schema for creating a new user."""
    
    clerk_user_id: str = Field(..., description="Clerk user identifier", min_length=1)


class UserUpdate(BaseSchema):
    """Schema for updating an existing user."""
    
    full_name: Optional[str] = Field(None, description="User's full name")
    is_active: Optional[bool] = Field(None, description="Whether the user is active")


class UserResponse(UserBase, TimestampMixin):
    """Schema for user response.
    
    Maps to database table: users
    """
    
    id: UUID = Field(..., description="User's unique identifier")
    clerk_user_id: str = Field(..., description="Clerk user identifier")
    is_active: bool = Field(..., description="Whether the user is active")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "clerk_user_id": "user_2abc123",
                "email": "user@example.com",
                "full_name": "John Doe",
                "is_active": True,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }
    )
