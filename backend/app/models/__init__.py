"""
Pydantic models for NeedleAi.
"""

from .api_key import *
from .base import *
from .chat import *
from .completion import *
from .task import *
from .user import *

__all__ = [
    # Chat models
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    "ChatSession",
    "MessageHistory",
    # Completion models
    "CompletionRequest",
    "CompletionResponse",
    "StreamingCompletionResponse",
    # User models
    "UserProfile",
    "UserPublicProfile",
    "UserRegistrationRequest",
    "UserLoginRequest",
    "UserUpdateRequest",
    "PasswordChangeRequest",
    "LoginResponse",
    "UserStats",
    "UserListResponse",
    # Note: API Key and advanced Task models available but not currently used in endpoints
    # Base models
    "HealthResponse",
    "ErrorResponse",
    "EnhancedErrorResponse",
    "SuccessResponse",
    "StatusResponse",
    "APIInfo",
    "PaginatedResponse"
]
