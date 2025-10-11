"""
Completion models for NeedleAi.
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class CompletionRequest(BaseModel):
    """Request model for completion endpoint."""

    prompt: str = Field(..., description="The prompt to complete", min_length=1)
    max_tokens: Optional[int] = Field(default=100, description="Maximum tokens to generate", ge=1, le=4000)
    temperature: Optional[float] = Field(default=0.7, description="Sampling temperature", ge=0, le=2)
    top_p: Optional[float] = Field(default=1.0, description="Top-p sampling parameter", gt=0, le=1)
    stop: Optional[List[str]] = Field(default=None, description="Stop sequences")
    system_message: Optional[str] = Field(default=None, description="Optional system message")

    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "Write a short story about a robot discovering emotions.",
                "max_tokens": 200,
                "temperature": 0.8,
                "top_p": 0.9,
                "stop": ["\n\n", "THE END"],
                "system_message": "You are a creative writer specializing in science fiction."
            }
        }


class CompletionResponse(BaseModel):
    """Response model for completion endpoint."""

    text: str = Field(..., description="The generated completion text")
    model: str = Field(..., description="The model used for generation")
    usage: Optional[Dict[str, int]] = Field(default=None, description="Token usage information")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "text": "In a world where circuits hummed with life, a small robot named Zara began to feel something strange...",
                "model": "gpt-4",
                "usage": {
                    "prompt_tokens": 12,
                    "completion_tokens": 150,
                    "total_tokens": 162
                },
                "timestamp": "2024-01-01T12:00:00.000Z"
            }
        }


class StreamingCompletionResponse(BaseModel):
    """Response model for streaming completion endpoint."""

    text: str = Field(..., description="The completion text chunk")
    model: str = Field(..., description="The model used for generation")
    done: bool = Field(..., description="Whether the stream is complete")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "text": "In a world where",
                "model": "gpt-4",
                "done": False,
                "timestamp": "2024-01-01T12:00:00.000Z"
            }
        }
