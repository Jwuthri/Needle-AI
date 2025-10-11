"""
API Key-related Pydantic models for API serialization.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# Request models
class ApiKeyCreateRequest(BaseModel):
    """API key creation request model."""
    name: str = Field(..., min_length=1, max_length=100, description="API key name/description")
    permissions: Optional[Dict[str, Any]] = Field(None, description="API key permissions")
    expires_at: Optional[datetime] = Field(None, description="Optional expiration date")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Production API Key",
                "permissions": {
                    "chat": True,
                    "completions": True,
                    "admin": False
                },
                "expires_at": "2024-12-31T23:59:59Z"
            }
        }


class ApiKeyUpdateRequest(BaseModel):
    """API key update request model."""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="API key name/description")
    permissions: Optional[Dict[str, Any]] = Field(None, description="API key permissions")
    is_active: Optional[bool] = Field(None, description="Whether API key is active")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Updated API Key Name",
                "permissions": {
                    "chat": True,
                    "completions": False,
                    "admin": False
                },
                "is_active": True
            }
        }


# Response models
class ApiKeyInfo(BaseModel):
    """API key information (without the actual key)."""
    id: int = Field(..., description="API key ID")
    name: str = Field(..., description="API key name/description")
    user_id: int = Field(..., description="Owner user ID")
    is_active: bool = Field(..., description="Whether API key is active")
    permissions: Optional[Dict[str, Any]] = Field(None, description="API key permissions")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    last_used_at: Optional[datetime] = Field(None, description="Last usage timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    usage_count: int = Field(0, description="Number of times key has been used")

    class Config:
        from_attributes = True  # For SQLAlchemy model conversion
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Production API Key",
                "user_id": 1,
                "is_active": True,
                "permissions": {
                    "chat": True,
                    "completions": True,
                    "admin": False
                },
                "created_at": "2024-01-01T12:00:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
                "last_used_at": "2024-01-15T09:00:00Z",
                "expires_at": "2024-12-31T23:59:59Z",
                "usage_count": 250
            }
        }


class ApiKeyCreateResponse(BaseModel):
    """API key creation response (includes the actual key - shown only once)."""
    id: int = Field(..., description="API key ID")
    name: str = Field(..., description="API key name/description")
    api_key: str = Field(..., description="The actual API key (shown only once)")
    permissions: Optional[Dict[str, Any]] = Field(None, description="API key permissions")
    created_at: datetime = Field(..., description="Creation timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Production API Key",
                "api_key": "ak_1234567890abcdef1234567890abcdef",
                "permissions": {
                    "chat": True,
                    "completions": True,
                    "admin": False
                },
                "created_at": "2024-01-01T12:00:00Z",
                "expires_at": "2024-12-31T23:59:59Z"
            }
        }


class ApiKeyUsageStats(BaseModel):
    """API key usage statistics."""
    api_key_id: int = Field(..., description="API key ID")
    usage_count: int = Field(0, description="Total number of requests")
    last_used_at: Optional[datetime] = Field(None, description="Last usage timestamp")
    requests_today: int = Field(0, description="Requests made today")
    requests_this_week: int = Field(0, description="Requests made this week")
    requests_this_month: int = Field(0, description="Requests made this month")
    average_requests_per_day: float = Field(0.0, description="Average requests per day")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "api_key_id": 1,
                "usage_count": 1250,
                "last_used_at": "2024-01-15T09:00:00Z",
                "requests_today": 45,
                "requests_this_week": 320,
                "requests_this_month": 1250,
                "average_requests_per_day": 41.7
            }
        }


# List models
class ApiKeyListItem(BaseModel):
    """API key list item."""
    id: int = Field(..., description="API key ID")
    name: str = Field(..., description="API key name/description")
    is_active: bool = Field(..., description="Whether API key is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    last_used_at: Optional[datetime] = Field(None, description="Last usage timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    usage_count: int = Field(0, description="Number of times key has been used")
    key_preview: str = Field(..., description="Masked preview of the API key")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Production API Key",
                "is_active": True,
                "created_at": "2024-01-01T12:00:00Z",
                "last_used_at": "2024-01-15T09:00:00Z",
                "expires_at": "2024-12-31T23:59:59Z",
                "usage_count": 250,
                "key_preview": "ak_1234...cdef"
            }
        }


class ApiKeyListResponse(BaseModel):
    """Paginated API key list response."""
    api_keys: List[ApiKeyListItem] = Field(..., description="List of API keys")
    total: int = Field(..., description="Total number of API keys")
    limit: int = Field(..., description="Items per page")
    offset: int = Field(..., description="Items skipped")
    has_more: bool = Field(..., description="Whether there are more items")

    class Config:
        json_schema_extra = {
            "example": {
                "api_keys": [
                    {
                        "id": 1,
                        "name": "Production API Key",
                        "is_active": True,
                        "created_at": "2024-01-01T12:00:00Z",
                        "last_used_at": "2024-01-15T09:00:00Z",
                        "expires_at": "2024-12-31T23:59:59Z",
                        "usage_count": 250,
                        "key_preview": "ak_1234...cdef"
                    }
                ],
                "total": 1,
                "limit": 50,
                "offset": 0,
                "has_more": False
            }
        }


# Permission models
class ApiKeyPermissions(BaseModel):
    """Standard API key permissions."""
    chat: bool = Field(False, description="Access to chat endpoints")
    completions: bool = Field(False, description="Access to completion endpoints")
    tasks: bool = Field(False, description="Access to background task endpoints")
    admin: bool = Field(False, description="Administrative access")
    rate_limit_override: Optional[int] = Field(None, description="Custom rate limit")

    class Config:
        json_schema_extra = {
            "example": {
                "chat": True,
                "completions": True,
                "tasks": False,
                "admin": False,
                "rate_limit_override": 1000
            }
        }


class ApiKeyValidationResponse(BaseModel):
    """API key validation response."""
    valid: bool = Field(..., description="Whether the API key is valid")
    api_key_id: Optional[int] = Field(None, description="API key ID if valid")
    user_id: Optional[int] = Field(None, description="Owner user ID if valid")
    permissions: Optional[Dict[str, Any]] = Field(None, description="API key permissions if valid")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp if applicable")
    error: Optional[str] = Field(None, description="Error message if invalid")

    class Config:
        json_schema_extra = {
            "example": {
                "valid": True,
                "api_key_id": 1,
                "user_id": 1,
                "permissions": {
                    "chat": True,
                    "completions": True,
                    "admin": False
                },
                "expires_at": "2024-12-31T23:59:59Z",
                "error": None
            }
        }
