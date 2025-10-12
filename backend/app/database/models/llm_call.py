"""
LLM Call logging model for debugging and monitoring.

This table logs ALL LLM API calls including:
- User-visible chat messages
- Hidden RAG queries
- Background task calls (sentiment, summarization)
- System prompts and internal queries
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum as SQLEnum, Float, Index, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from ..base import Base


class LLMCallTypeEnum(str, enum.Enum):
    """Type of LLM call for categorization."""
    CHAT = "chat"  # User-facing chat message
    RAG_QUERY = "rag_query"  # Hidden RAG retrieval query
    RAG_SYNTHESIS = "rag_synthesis"  # RAG answer synthesis
    SENTIMENT_ANALYSIS = "sentiment_analysis"  # Sentiment analysis task
    SUMMARIZATION = "summarization"  # Review summarization
    EMBEDDING = "embedding"  # Text embedding generation
    CLASSIFICATION = "classification"  # Text classification
    EXTRACTION = "extraction"  # Information extraction
    SYSTEM = "system"  # System/internal calls
    OTHER = "other"  # Other types


class LLMCallStatusEnum(str, enum.Enum):
    """Status of the LLM call."""
    PENDING = "pending"
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"


class LLMCall(Base):
    """
    Log table for all LLM API calls.
    
    Used for:
    - Debugging RAG pipelines
    - Cost tracking and analysis
    - Performance monitoring
    - Audit trails
    - Finding production issues
    """
    __tablename__ = "llm_calls"

    # Primary identification
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    call_type = Column(SQLEnum(LLMCallTypeEnum), nullable=False, index=True)
    status = Column(SQLEnum(LLMCallStatusEnum), default=LLMCallStatusEnum.PENDING, nullable=False)
    
    # Provider and model info
    provider = Column(String(50), nullable=False, index=True)  # openrouter, openai, anthropic
    model = Column(String(100), nullable=False, index=True)  # gpt-4, claude-3, etc.
    
    # Request details (matches LLM API format)
    system_prompt = Column(Text, nullable=True)  # System prompt if used
    messages = Column(JSON, nullable=False)  # Array of {role, content} messages
    temperature = Column(Float, nullable=True)
    max_tokens = Column(Integer, nullable=True)
    top_p = Column(Float, nullable=True)
    tools = Column(JSON, nullable=True)  # Available tools/functions
    tool_choice = Column(String(50), nullable=True)  # auto, none, or specific tool
    request_params = Column(JSON, nullable=True)  # Other parameters
    
    # Response details (matches LLM API format)
    response_message = Column(JSON, nullable=True)  # Full response message with role, content, tool_calls
    finish_reason = Column(String(50), nullable=True)  # stop, length, tool_calls, etc.
    
    # Token usage and cost
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    estimated_cost = Column(Float, nullable=True)  # In USD
    
    # Performance metrics
    latency_ms = Column(Integer, nullable=True)  # Response time in milliseconds
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    error_code = Column(String(50), nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Context and tracing
    user_id = Column(String, nullable=True, index=True)  # If user-initiated
    session_id = Column(String, nullable=True, index=True)  # Chat session if applicable
    task_id = Column(String, nullable=True, index=True)  # Celery task ID if background
    company_id = Column(String, nullable=True, index=True)  # Related company
    review_id = Column(String, nullable=True, index=True)  # Related review
    trace_id = Column(String, nullable=True, index=True)  # Distributed tracing ID
    parent_call_id = Column(String, nullable=True, index=True)  # Parent call if nested
    
    # Metadata for debugging
    extra_metadata = Column(JSON, nullable=True)  # Additional context
    tags = Column(JSON, nullable=True)  # Tags for filtering (e.g., ["production", "rag"])
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        Index('idx_llm_call_type_status', 'call_type', 'status'),
        Index('idx_llm_call_provider_model', 'provider', 'model'),
        Index('idx_llm_call_user_created', 'user_id', 'created_at'),
        Index('idx_llm_call_created_at', 'created_at'),
        Index('idx_llm_call_trace', 'trace_id'),
    )

    def __repr__(self):
        return f"<LLMCall(id={self.id}, type={self.call_type.value}, model={self.model}, status={self.status.value})>"

    @property
    def duration_ms(self) -> int:
        """Calculate call duration in milliseconds."""
        if self.completed_at and self.started_at:
            return int((self.completed_at - self.started_at).total_seconds() * 1000)
        return self.latency_ms or 0

    def to_dict(self):
        """Convert to dictionary for logging."""
        # Get last user message for preview
        last_user_msg = None
        if self.messages:
            for msg in reversed(self.messages):
                if msg.get('role') == 'user':
                    last_user_msg = msg.get('content', '')
                    break
        
        # Get assistant response for preview
        response_preview = None
        if self.response_message:
            response_preview = self.response_message.get('content', '')
        
        return {
            'id': self.id,
            'call_type': self.call_type.value,
            'status': self.status.value,
            'provider': self.provider,
            'model': self.model,
            'prompt_preview': last_user_msg[:100] if last_user_msg else None,
            'response_preview': response_preview[:100] if response_preview else None,
            'has_tool_calls': bool(self.response_message and self.response_message.get('tool_calls')),
            'total_tokens': self.total_tokens,
            'estimated_cost': self.estimated_cost,
            'latency_ms': self.latency_ms,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

