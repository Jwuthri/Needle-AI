"""
Structured return types for tree tools.

These objects communicate results, status, and errors to the frontend
in a standardized format.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class Return:
    """
    Base class for all return objects.
    
    Return objects are yielded by tools to communicate:
    - Results (data objects)
    - Text responses
    - Status updates
    - Errors
    - Completion signals
    """
    
    def __init__(self, frontend_type: str, payload_type: str):
        """
        Initialize return object.
        
        Args:
            frontend_type: Type identifier for frontend (e.g., "text", "result", "status")
            payload_type: Specific payload type (e.g., "response", "error", "retrieval")
        """
        self.frontend_type = frontend_type
        self.payload_type = payload_type
        self.timestamp = datetime.utcnow().isoformat()
    
    async def to_frontend(
        self,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        query_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Convert to frontend-friendly format.
        
        Args:
            user_id: User ID
            conversation_id: Conversation ID
            query_id: Query ID
            
        Returns:
            Dictionary for frontend consumption
        """
        return {
            "type": self.frontend_type,
            "payload_type": self.payload_type,
            "timestamp": self.timestamp,
            "user_id": user_id,
            "conversation_id": conversation_id,
            "query_id": query_id
        }


class Text(Return):
    """Text response to user."""
    
    def __init__(self, content: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize text return.
        
        Args:
            content: Text content
            metadata: Optional metadata
        """
        super().__init__("text", "text")
        self.content = content
        self.metadata = metadata or {}
    
    async def to_frontend(
        self,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        query_id: Optional[str] = None
    ) -> Dict[str, Any]:
        base = await super().to_frontend(user_id, conversation_id, query_id)
        base.update({
            "content": self.content,
            "metadata": self.metadata
        })
        return base


class Response(Text):
    """Special text response (alias for clarity)."""
    
    def __init__(self, content: str, metadata: Optional[Dict[str, Any]] = None):
        super().__init__(content, metadata)
        self.payload_type = "response"


class Update(Return):
    """Status or progress update."""
    
    def __init__(
        self,
        message: str,
        level: str = "info",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize update return.
        
        Args:
            message: Update message
            level: Level (info, warning, error)
            metadata: Optional metadata
        """
        super().__init__("update", "update")
        self.message = message
        self.level = level
        self.metadata = metadata or {}
    
    async def to_frontend(
        self,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        query_id: Optional[str] = None
    ) -> Dict[str, Any]:
        base = await super().to_frontend(user_id, conversation_id, query_id)
        base.update({
            "message": self.message,
            "level": self.level,
            "metadata": self.metadata
        })
        return base


class Status(Update):
    """Status update (non-error)."""
    
    def __init__(self, message: str, metadata: Optional[Dict[str, Any]] = None):
        super().__init__(message, level="info", metadata=metadata)
        self.payload_type = "status"


class Warning(Update):
    """Warning message."""
    
    def __init__(self, message: str, metadata: Optional[Dict[str, Any]] = None):
        super().__init__(message, level="warning", metadata=metadata)
        self.payload_type = "warning"


class Completed(Update):
    """Task completion signal."""
    
    def __init__(self, message: str, metadata: Optional[Dict[str, Any]] = None):
        super().__init__(message, level="info", metadata=metadata)
        self.payload_type = "completed"


class Result(Return):
    """Data result from a tool."""
    
    def __init__(
        self,
        data: Any,
        summary: str,
        display_type: str = "json",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize result return.
        
        Args:
            data: Result data
            summary: Human-readable summary
            display_type: How to display (json, table, chart)
            metadata: Optional metadata
        """
        super().__init__("result", "result")
        self.data = data
        self.summary = summary
        self.display_type = display_type
        self.metadata = metadata or {}
    
    async def to_frontend(
        self,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        query_id: Optional[str] = None
    ) -> Dict[str, Any]:
        base = await super().to_frontend(user_id, conversation_id, query_id)
        base.update({
            "data": self.data,
            "summary": self.summary,
            "display_type": self.display_type,
            "metadata": self.metadata
        })
        return base


class Retrieval(Result):
    """Retrieved objects from database/search."""
    
    def __init__(
        self,
        objects: List[Dict[str, Any]],
        summary: str,
        source: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize retrieval return.
        
        Args:
            objects: Retrieved objects
            summary: Summary of retrieval
            source: Source name (e.g., "vector_db", "web_search")
            metadata: Optional metadata
        """
        super().__init__(
            data={"objects": objects, "source": source},
            summary=summary,
            display_type="table",
            metadata=metadata
        )
        self.payload_type = "retrieval"
        self.objects = objects
        self.source = source


class Error(Update):
    """Error message."""
    
    def __init__(
        self,
        message: str,
        error_type: str = "general",
        recoverable: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize error return.
        
        Args:
            message: Error message
            error_type: Error type (general, validation, execution)
            recoverable: Whether error is recoverable
            metadata: Optional metadata
        """
        super().__init__(message, level="error", metadata=metadata)
        self.payload_type = "error"
        self.error_type = error_type
        self.recoverable = recoverable
    
    async def to_frontend(
        self,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        query_id: Optional[str] = None
    ) -> Dict[str, Any]:
        base = await super().to_frontend(user_id, conversation_id, query_id)
        base.update({
            "error_type": self.error_type,
            "recoverable": self.recoverable
        })
        return base

