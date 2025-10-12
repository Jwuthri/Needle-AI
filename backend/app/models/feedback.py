"""
Feedback models for chat responses.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class FeedbackType(str, Enum):
    """Types of feedback."""
    LIKE = "like"
    DISLIKE = "dislike"
    COPY = "copy"


class ChatFeedback(BaseModel):
    """Feedback on a chat response."""
    message_id: str = Field(..., description="Message ID that received feedback")
    feedback_type: FeedbackType = Field(..., description="Type of feedback")
    comment: Optional[str] = Field(None, max_length=1000, description="Optional feedback comment")

    class Config:
        json_schema_extra = {
            "example": {
                "message_id": "msg_123",
                "feedback_type": "like",
                "comment": "Very helpful analysis!"
            }
        }


class FeedbackResponse(BaseModel):
    """Response after submitting feedback."""
    success: bool
    message: str

