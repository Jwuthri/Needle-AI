"""
Execution Tree API models for request/response serialization.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field


class ExecutionNodeTypeEnum(str, Enum):
    """Execution node types."""
    QUERY = "query"
    TOOL = "tool"
    AGENT = "agent"
    LLM_CALL = "llm_call"
    SUBTASK = "subtask"


class ExecutionNodeStatusEnum(str, Enum):
    """Execution node status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ExecutionTreeNodeResponse(BaseModel):
    """Execution tree node response."""
    id: int
    node_id: str
    parent_node_id: Optional[str] = None
    node_type: ExecutionNodeTypeEnum
    name: str
    status: ExecutionNodeStatusEnum
    
    # Agent/Tool details
    agent_id: Optional[str] = None
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    tool_result: Optional[Dict[str, Any]] = None
    
    # Input/Output
    input_summary: Optional[str] = None
    output_summary: Optional[str] = None
    
    # Timing
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    
    # Error handling
    error_message: Optional[str] = None
    
    # LLM metrics
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    
    # Metadata
    extra_metadata: Optional[Dict[str, Any]] = None
    
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ExecutionTreeSessionResponse(BaseModel):
    """Execution tree session response."""
    id: int
    session_id: str
    message_id: Optional[str] = None
    user_id: Optional[str] = None
    
    query: str
    status: ExecutionNodeStatusEnum
    
    # Timing
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    
    # Result
    result_summary: Optional[str] = None
    error_message: Optional[str] = None
    
    # Metadata
    extra_metadata: Optional[Dict[str, Any]] = None
    
    # Nodes
    nodes: List[ExecutionTreeNodeResponse] = []
    
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ExecutionTreeListResponse(BaseModel):
    """List of execution tree sessions."""
    trees: List[ExecutionTreeSessionResponse]
    total: int
    limit: int
    offset: int

    class Config:
        json_schema_extra = {
            "example": {
                "trees": [
                    {
                        "id": 1,
                        "session_id": "session-123",
                        "message_id": "msg-456",
                        "user_id": "user-789",
                        "query": "What is Gorgias?",
                        "status": "completed",
                        "started_at": "2025-10-12T00:00:00Z",
                        "completed_at": "2025-10-12T00:00:05Z",
                        "duration_ms": 5000,
                        "result_summary": "Completed successfully",
                        "nodes": [
                            {
                                "id": 1,
                                "node_id": "node-1",
                                "node_type": "tool",
                                "name": "web_search",
                                "status": "completed",
                                "tool_name": "web_search",
                                "started_at": "2025-10-12T00:00:01Z",
                                "completed_at": "2025-10-12T00:00:03Z",
                                "duration_ms": 2000
                            }
                        ]
                    }
                ],
                "total": 1,
                "limit": 50,
                "offset": 0
            }
        }

