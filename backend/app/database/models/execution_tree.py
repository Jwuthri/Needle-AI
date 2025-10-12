"""
Execution Tree database models for tracking agent/tool execution steps.
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    Float,
)
from sqlalchemy.orm import relationship

from app.database.base import Base


class ExecutionNodeType(str, PyEnum):
    """Execution node types."""
    QUERY = "query"
    TOOL = "tool"
    AGENT = "agent"
    LLM_CALL = "llm_call"
    SUBTASK = "subtask"


class ExecutionNodeStatus(str, PyEnum):
    """Execution node status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ExecutionTreeSession(Base):
    """
    Stores execution tree for a chat message.
    Tracks the overall execution flow and metadata.
    """
    __tablename__ = "execution_tree_sessions"

    id = Column(Integer, primary_key=True, index=True)
    
    # Link to chat session and message
    session_id = Column(String(255), index=True, nullable=False)
    message_id = Column(String(255), index=True, nullable=True)  # Optional link to specific message
    
    # User context
    user_id = Column(String(255), index=True, nullable=True)
    
    # Query and metadata
    query = Column(Text, nullable=False)
    status = Column(Enum(ExecutionNodeStatus), default=ExecutionNodeStatus.RUNNING, nullable=False)
    
    # Timing
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Float, nullable=True)  # Total duration in milliseconds
    
    # Result
    result_summary = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Additional metadata
    extra_metadata = Column(JSON, nullable=True)
    
    # Relationships
    nodes = relationship("ExecutionTreeNode", back_populates="tree_session", cascade="all, delete-orphan")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ExecutionTreeNode(Base):
    """
    Individual node in the execution tree.
    Represents a tool call, agent action, or LLM call.
    """
    __tablename__ = "execution_tree_nodes"

    id = Column(Integer, primary_key=True, index=True)
    
    # Link to tree session
    tree_session_id = Column(Integer, ForeignKey("execution_tree_sessions.id"), nullable=False, index=True)
    
    # Node identity
    node_id = Column(String(100), nullable=False, index=True)  # UUID for this node
    parent_node_id = Column(String(100), nullable=True, index=True)  # Parent node for hierarchy
    
    # Node details
    node_type = Column(Enum(ExecutionNodeType), nullable=False)
    name = Column(String(255), nullable=False)  # Tool/agent name
    status = Column(Enum(ExecutionNodeStatus), default=ExecutionNodeStatus.RUNNING, nullable=False)
    
    # Agent context (if applicable)
    agent_id = Column(String(255), nullable=True)
    
    # Tool details (if tool call)
    tool_name = Column(String(255), nullable=True)
    tool_args = Column(JSON, nullable=True)
    tool_result = Column(JSON, nullable=True)
    
    # Input/Output
    input_summary = Column(Text, nullable=True)
    output_summary = Column(Text, nullable=True)
    
    # Timing
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Float, nullable=True)  # Duration in milliseconds
    
    # Error handling
    error_message = Column(Text, nullable=True)
    
    # LLM metrics (if LLM call)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    
    # Additional metadata
    extra_metadata = Column(JSON, nullable=True)
    
    # Relationships
    tree_session = relationship("ExecutionTreeSession", back_populates="nodes")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

