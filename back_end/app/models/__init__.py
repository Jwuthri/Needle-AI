"""Pydantic models for API contracts."""

from .base import BaseSchema, TimestampMixin
from .user import UserBase, UserCreate, UserUpdate, UserResponse
from .company import CompanyBase, CompanyCreate, CompanyUpdate, CompanyResponse
from .chat import (
    ChatMessageBase,
    ChatMessageCreate,
    ChatMessageResponse,
    ChatMessageStepBase,
    ChatMessageStepCreate,
    ChatMessageStepResponse,
    ChatSessionBase,
    ChatSessionCreate,
    ChatSessionResponse,
    ChatRequest,
    ChatResponse,
)
from .user_dataset import (
    UserDatasetBase,
    UserDatasetCreate,
    UserDatasetUpdate,
    UserDatasetResponse,
)

__all__ = [
    # Base
    "BaseSchema",
    "TimestampMixin",
    # User
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    # Company
    "CompanyBase",
    "CompanyCreate",
    "CompanyUpdate",
    "CompanyResponse",
    # Chat
    "ChatMessageBase",
    "ChatMessageCreate",
    "ChatMessageResponse",
    "ChatMessageStepBase",
    "ChatMessageStepCreate",
    "ChatMessageStepResponse",
    "ChatSessionBase",
    "ChatSessionCreate",
    "ChatSessionResponse",
    "ChatRequest",
    "ChatResponse",
    # User Dataset
    "UserDatasetBase",
    "UserDatasetCreate",
    "UserDatasetUpdate",
    "UserDatasetResponse",
]
