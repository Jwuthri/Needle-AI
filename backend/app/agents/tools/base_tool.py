"""
Base tool interface for the orchestration system.
All tools inherit from BaseTool and implement the execute method.
"""

import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """Result from a tool execution."""
    
    success: bool = Field(..., description="Whether the tool executed successfully")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Tool output data")
    summary: str = Field(..., description="Human-readable summary of the result")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    duration_ms: Optional[int] = Field(default=None, description="Execution duration in milliseconds")


class BaseTool(ABC):
    """
    Base class for all orchestrator tools.
    
    Tools are reusable components that perform specific tasks like:
    - Retrieving data from vector databases
    - Searching the web
    - Analyzing data
    - Generating visualizations
    
    Each tool should:
    1. Have a clear name and description
    2. Define required and optional parameters
    3. Return a ToolResult with structured data
    4. Handle errors gracefully
    """
    
    def __init__(self):
        """Initialize the tool."""
        self._validate_tool_definition()
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name (unique identifier)."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for LLM to understand when to use it."""
        pass
    
    @property
    def parameters(self) -> Dict[str, Any]:
        """
        Tool parameters schema.
        
        Returns JSON Schema describing the parameters this tool accepts.
        This is used by the LLM to know how to call the tool.
        
        Example:
            {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "integer", "description": "Max results"}
                },
                "required": ["query"]
            }
        """
        return {
            "type": "object",
            "properties": {},
            "required": []
        }
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with given parameters.
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            ToolResult with success status, data, and summary
        """
        pass
    
    def _validate_tool_definition(self):
        """Validate that tool is properly defined."""
        if not self.name:
            raise ValueError(f"{self.__class__.__name__} must define a name")
        if not self.description:
            raise ValueError(f"{self.__class__.__name__} must define a description")
    
    async def run(self, **kwargs) -> ToolResult:
        """
        Run the tool with timing and error handling.
        
        This wraps execute() to add timing and consistent error handling.
        """
        start_time = time.time()
        
        try:
            result = await self.execute(**kwargs)
            
            # Add timing if not already set
            if result.duration_ms is None:
                result.duration_ms = int((time.time() - start_time) * 1000)
            
            return result
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return ToolResult(
                success=False,
                summary=f"Tool execution failed: {str(e)}",
                error=str(e),
                duration_ms=duration_ms,
                metadata={"tool_name": self.name}
            )
    
    def to_agno_tool(self) -> Dict[str, Any]:
        """
        Convert this tool to Agno tool format.
        
        Agno uses a specific format for tools that includes:
        - function name
        - function description  
        - parameters schema
        - callable function
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
                "callable": self.run
            }
        }

