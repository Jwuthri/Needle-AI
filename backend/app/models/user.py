"""
User-related Pydantic models for API serialization.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, validator


class UserStatusEnum(str, Enum):
    """User status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


# Request models
class UserRegistrationRequest(BaseModel):
    """User registration request model."""
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=8, description="Password")
    full_name: Optional[str] = Field(None, max_length=100, description="Full name")

    @validator("username")
    def validate_username(cls, v):
        """Validate username format."""
        import re
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Username can only contain letters, numbers, hyphens, and underscores")
        return v.lower()

    class Config:
        json_schema_extra = {
            "example": {
                "username": "johndoe",
                "email": "john.doe@example.com",
                "password": "SecurePass123!",
                "full_name": "John Doe"
            }
        }


class UserLoginRequest(BaseModel):
    """User login request model."""
    username_or_email: str = Field(..., description="Username or email address")
    password: str = Field(..., description="Password")

    class Config:
        json_schema_extra = {
            "example": {
                "username_or_email": "johndoe",
                "password": "SecurePass123!"
            }
        }


class UserUpdateRequest(BaseModel):
    """User update request model."""
    full_name: Optional[str] = Field(None, max_length=100, description="Full name")
    bio: Optional[str] = Field(None, max_length=500, description="User biography")
    preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences")

    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "John Smith",
                "bio": "Software developer and AI enthusiast",
                "preferences": {
                    "theme": "dark",
                    "language": "en",
                    "notifications": True
                }
            }
        }


class PasswordChangeRequest(BaseModel):
    """Password change request model."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")

    class Config:
        json_schema_extra = {
            "example": {
                "current_password": "OldPass123!",
                "new_password": "NewSecurePass123!"
            }
        }


# Response models
class UserProfile(BaseModel):
    """User profile response model."""
    id: int = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    full_name: Optional[str] = Field(None, description="Full name")
    bio: Optional[str] = Field(None, description="User biography")
    is_active: bool = Field(..., description="Whether user is active")
    is_superuser: bool = Field(False, description="Whether user has admin privileges")
    status: UserStatusEnum = Field(..., description="User status")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    last_login_at: Optional[datetime] = Field(None, description="Last login timestamp")

    class Config:
        from_attributes = True  # For SQLAlchemy model conversion
        json_schema_extra = {
            "example": {
                "id": 1,
                "username": "johndoe",
                "email": "john.doe@example.com",
                "full_name": "John Doe",
                "bio": "Software developer passionate about AI",
                "is_active": True,
                "is_superuser": False,
                "status": "active",
                "created_at": "2024-01-01T12:00:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
                "last_login_at": "2024-01-15T09:00:00Z"
            }
        }


class UserPublicProfile(BaseModel):
    """Public user profile (limited information)."""
    id: int = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    full_name: Optional[str] = Field(None, description="Full name")
    bio: Optional[str] = Field(None, description="User biography")
    created_at: datetime = Field(..., description="Account creation timestamp")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "username": "johndoe",
                "full_name": "John Doe",
                "bio": "Software developer passionate about AI",
                "created_at": "2024-01-01T12:00:00Z"
            }
        }


class UserStats(BaseModel):
    """User statistics response model."""
    user_id: int = Field(..., description="User ID")
    total_requests: int = Field(0, description="Total API requests made")
    total_tokens: int = Field(0, description="Total tokens consumed")
    total_sessions: int = Field(0, description="Total chat sessions created")
    total_messages: int = Field(0, description="Total messages sent")
    last_active_at: Optional[datetime] = Field(None, description="Last activity timestamp")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "total_requests": 150,
                "total_tokens": 25000,
                "total_sessions": 12,
                "total_messages": 89,
                "last_active_at": "2024-01-15T09:00:00Z"
            }
        }


class LoginResponse(BaseModel):
    """Login response model."""
    user: UserProfile = Field(..., description="User profile information")
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "user": {
                    "id": 1,
                    "username": "johndoe",
                    "email": "john.doe@example.com",
                    "full_name": "John Doe",
                    "is_active": True,
                    "status": "active"
                },
                "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                "token_type": "bearer",
                "expires_in": 1800
            }
        }


# List models
class UserListItem(BaseModel):
    """User list item for admin views."""
    id: int = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    full_name: Optional[str] = Field(None, description="Full name")
    is_active: bool = Field(..., description="Whether user is active")
    status: UserStatusEnum = Field(..., description="User status")
    created_at: datetime = Field(..., description="Account creation timestamp")
    last_login_at: Optional[datetime] = Field(None, description="Last login timestamp")
    total_requests: int = Field(0, description="Total API requests")

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Paginated user list response."""
    users: List[UserListItem] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    limit: int = Field(..., description="Items per page")
    offset: int = Field(..., description="Items skipped")
    has_more: bool = Field(..., description="Whether there are more items")

    class Config:
        json_schema_extra = {
            "example": {
                "users": [
                    {
                        "id": 1,
                        "username": "johndoe",
                        "email": "john.doe@example.com",
                        "full_name": "John Doe",
                        "is_active": True,
                        "status": "active",
                        "created_at": "2024-01-01T12:00:00Z",
                        "last_login_at": "2024-01-15T09:00:00Z",
                        "total_requests": 150
                    }
                ],
                "total": 1,
                "limit": 50,
                "offset": 0,
                "has_more": False
            }
        }
