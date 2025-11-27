"""
Data models for the NeedleAi API.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Message roles in a conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    """A chat message in a conversation."""
    id: str = Field(..., description="Unique message identifier")
    content: str = Field(..., description="The message content")
    role: MessageRole = Field(..., description="The role of the message sender")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the message was created")
    completed_at: Optional[datetime] = Field(default=None, description="When the assistant finished generating the response")
    metadata: Optional[dict] = Field(default=None, description="Additional message metadata")


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str = Field(..., description="The user's message", min_length=1)
    session_id: Optional[str] = Field(default=None, description="Session identifier for conversation continuity")
    company_id: Optional[str] = Field(default=None, description="Company ID to query reviews from (enables RAG mode)")
    dataset_id: Optional[str] = Field(default=None, description="User dataset ID to query from")
    dataset_table_name: Optional[str] = Field(default=None, description="User dataset table name for querying")
    context: Optional[dict] = Field(default=None, description="Additional context for the request")
    conversation_history: Optional[List[dict]] = Field(
        default=None, 
        description="Recent conversation history (last N messages) for context awareness"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "message": "What are the main product gaps?",
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "company_id": "comp_123",
                "dataset_id": "dataset_123",
                "dataset_table_name": "my_reviews_table",
                "context": {}
            }
        }


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    message: str = Field(..., description="The AI assistant's response")
    session_id: str = Field(..., description="Session identifier")
    message_id: str = Field(..., description="Unique identifier for this response message")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the response was generated")
    completed_at: Optional[datetime] = Field(default=None, description="When the response was completed")
    output_format: Optional[str] = Field(default="text", description="Output format (text, visualization, cited_summary)")
    visualization: Optional[dict] = Field(default=None, description="Visualization configuration if applicable")
    sources: Optional[List[dict]] = Field(default=None, description="Source citations")
    metadata: Optional[dict] = Field(default=None, description="Additional response metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Hello! I'm doing well, thank you for asking. How can I help you today?",
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "message_id": "987fcdeb-51a2-43d7-8f29-123456789abc",
                "timestamp": "2024-01-01T12:00:00.000Z",
                "output_format": "text"
            }
        }


class ChatSession(BaseModel):
    """A complete chat session."""
    session_id: str = Field(..., description="Unique session identifier")
    messages: List[ChatMessage] = Field(default=[], description="All messages in the session")
    created_at: datetime = Field(default_factory=datetime.now, description="When the session was created")
    updated_at: datetime = Field(default_factory=datetime.now, description="When the session was last updated")
    metadata: Optional[dict] = Field(default=None, description="Session metadata")


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str = Field(..., description="Error type or code")
    detail: str = Field(..., description="Detailed error message")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the error occurred")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "ValidationError",
                "detail": "The message field is required",
                "timestamp": "2024-01-01T12:00:00.000Z"
            }
        }


class MessageHistory(BaseModel):
    """Message history response model."""
    session_id: str = Field(..., description="Session identifier")
    messages: List[ChatMessage] = Field(..., description="List of messages in the session")
    total: int = Field(..., description="Total number of messages")
    limit: int = Field(..., description="Number of messages per page")
    offset: int = Field(..., description="Number of messages skipped")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "messages": [],
                "total": 25,
                "limit": 100,
                "offset": 0
            }
        }
