"""Chat Pydantic schemas for API contracts."""

from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from typing import Optional, Dict, Any, Literal
from datetime import datetime

from .base import BaseSchema, TimestampMixin


class ChatMessageBase(BaseSchema):
    """Base chat message schema with common fields."""
    
    role: Literal["user", "assistant", "system"] = Field(..., description="Message role")
    content: str = Field(..., description="Message content", min_length=1)
    metadata_: Optional[Dict[str, Any]] = Field(None, description="Additional message metadata", serialization_alias="metadata")


class ChatMessageCreate(ChatMessageBase):
    """Schema for creating a new chat message."""
    
    session_id: UUID = Field(..., description="Chat session identifier")


class ChatMessageResponse(ChatMessageBase):
    """Schema for chat message response.
    
    Maps to database table: chat_messages
    """
    
    id: UUID = Field(..., description="Message unique identifier")
    session_id: UUID = Field(..., description="Chat session identifier")
    created_at: datetime = Field(..., description="Message creation timestamp")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "session_id": "987e6543-e21b-12d3-a456-426614174000",
                "role": "user",
                "content": "What are the main product gaps?",
                "metadata": {"source": "web"},
                "created_at": "2024-01-01T00:00:00Z"
            }
        }
    )


class ChatMessageStepBase(BaseSchema):
    """Base chat message step schema with common fields."""
    
    step_type: str = Field(..., description="Type of step (thinking, tool_call, retrieval, etc.)")
    content: Optional[str] = Field(None, description="Step content")
    metadata_: Optional[Dict[str, Any]] = Field(None, description="Additional step metadata", serialization_alias="metadata")


class ChatMessageStepCreate(ChatMessageStepBase):
    """Schema for creating a new chat message step."""
    
    message_id: UUID = Field(..., description="Parent message identifier")


class ChatMessageStepResponse(ChatMessageStepBase):
    """Schema for chat message step response.
    
    Maps to database table: chat_message_steps
    """
    
    id: UUID = Field(..., description="Step unique identifier")
    message_id: UUID = Field(..., description="Parent message identifier")
    created_at: datetime = Field(..., description="Step creation timestamp")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "message_id": "987e6543-e21b-12d3-a456-426614174000",
                "step_type": "thinking",
                "content": "Analyzing user query...",
                "metadata": {"duration_ms": 150},
                "created_at": "2024-01-01T00:00:00Z"
            }
        }
    )


class ChatSessionBase(BaseSchema):
    """Base chat session schema with common fields."""
    
    title: Optional[str] = Field(None, description="Session title", max_length=255)
    company_id: Optional[UUID] = Field(None, description="Associated company identifier")


class ChatSessionCreate(ChatSessionBase):
    """Schema for creating a new chat session."""
    
    user_id: UUID = Field(..., description="User identifier")


class ChatSessionResponse(ChatSessionBase, TimestampMixin):
    """Schema for chat session response.
    
    Maps to database table: chat_sessions
    """
    
    id: UUID = Field(..., description="Session unique identifier")
    user_id: UUID = Field(..., description="User identifier")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "987e6543-e21b-12d3-a456-426614174000",
                "company_id": "456e7890-e12b-34d5-a678-901234567890",
                "title": "Product Analysis Discussion",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }
    )


class ChatRequest(BaseSchema):
    """Schema for chat request."""
    
    message: str = Field(..., description="User's message", min_length=1)
    session_id: Optional[UUID] = Field(None, description="Existing session identifier (creates new if not provided)")
    company_id: Optional[UUID] = Field(None, description="Company context for the chat")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "What are the main product gaps?",
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "company_id": "456e7890-e12b-34d5-a678-901234567890"
            }
        }
    )


class ChatResponse(BaseSchema):
    """Schema for chat response."""
    
    message: str = Field(..., description="AI assistant's response")
    session_id: UUID = Field(..., description="Chat session identifier")
    message_id: UUID = Field(..., description="Message identifier")
    metadata_: Optional[Dict[str, Any]] = Field(None, description="Additional response metadata", serialization_alias="metadata")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Based on the analysis, the main product gaps are...",
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "message_id": "987e6543-e21b-12d3-a456-426614174000",
                "metadata": {
                    "model": "gpt-4",
                    "tokens_used": 150,
                    "processing_time_ms": 1200
                }
            }
        }
    )
