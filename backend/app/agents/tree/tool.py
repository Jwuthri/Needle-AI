"""
Enhanced tool system with async generators and metadata extraction.

Tools in the tree architecture are async generators that yield Return objects.
"""

import inspect
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Union
from functools import wraps

from app.agents.tree.returns import Return, Error, Status
from app.agents.tree.environment import TreeData


class TreeTool(ABC):
    """
    Base class for tree tools.
    
    Tools are async generators that:
    1. Receive TreeData with full context
    2. Yield Return objects (Status, Result, Text, Error)
    3. Optionally check availability via is_tool_available()
    4. Optionally have conditional execution via run_if_true()
    """
    
    def __init__(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        branch_id: Optional[str] = None,
        end: bool = False
    ):
        """
        Initialize tool.
        
        Args:
            name: Tool name (defaults to class name)
            description: Tool description
            branch_id: Branch this tool belongs to
            end: Whether this tool ends the tree execution
        """
        self.name = name or self.__class__.__name__
        self.description = description or self.__doc__ or "No description provided"
        self.branch_id = branch_id
        self.end = end
        self.metadata = self._extract_metadata()
    
    def _extract_metadata(self) -> Dict[str, Any]:
        """Extract metadata from tool implementation."""
        # Get __call__ signature
        sig = inspect.signature(self.__call__)
        
        parameters = {}
        for param_name, param in sig.parameters.items():
            if param_name in ["self", "tree_data"]:
                continue
            
            parameters[param_name] = {
                "name": param_name,
                "type": param.annotation.__name__ if param.annotation != inspect.Parameter.empty else "Any",
                "required": param.default == inspect.Parameter.empty,
                "default": param.default if param.default != inspect.Parameter.empty else None
            }
        
        return {
            "name": self.name,
            "description": self.description,
            "parameters": parameters,
            "branch_id": self.branch_id,
            "end": self.end
        }
    
    async def is_tool_available(self, tree_data: TreeData) -> tuple[bool, Optional[str]]:
        """
        Check if tool is available for execution.
        
        Args:
            tree_data: Tree data with context
            
        Returns:
            Tuple of (available, reason_if_unavailable)
        """
        return True, None
    
    def run_if_true(self, tree_data: TreeData) -> bool:
        """
        Conditional execution check.
        
        Args:
            tree_data: Tree data with context
            
        Returns:
            Whether to run this tool
        """
        return True
    
    @abstractmethod
    async def __call__(
        self,
        tree_data: TreeData,
        **kwargs
    ) -> AsyncGenerator[Return, None]:
        """
        Execute the tool.
        
        Args:
            tree_data: Tree data with full context
            **kwargs: Tool-specific parameters
            
        Yields:
            Return objects (Status, Result, Text, Error, etc.)
        """
        pass
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get tool metadata."""
        return self.metadata


def tool(
    function: Optional[Callable] = None,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    end: bool = False,
    branch_id: Optional[str] = None
) -> Union[TreeTool, Callable]:
    """
    Decorator to convert a function into a TreeTool.
    
    Usage:
        @tool(name="query_db", description="Query vector database")
        async def query_database(tree_data: TreeData, query: str):
            yield Status(f"Searching for: {query}")
            results = await search(query)
            yield Result(results, "Search complete")
    
    Args:
        function: Function to convert
        name: Tool name (defaults to function name)
        description: Tool description (defaults to docstring)
        status: Status message when tool starts
        end: Whether tool ends execution
        branch_id: Branch ID this tool belongs to
        
    Returns:
        TreeTool instance or decorator
    """
    def decorator(func: Callable) -> TreeTool:
        # Extract metadata from function
        tool_name = name or func.__name__
        tool_description = description or func.__doc__ or "No description"
        
        # Create wrapper class
        class FunctionTool(TreeTool):
            def __init__(self):
                super().__init__(
                    name=tool_name,
                    description=tool_description,
                    branch_id=branch_id,
                    end=end
                )
                self._func = func
                self._status = status
            
            async def __call__(
                self,
                tree_data: TreeData,
                **kwargs
            ) -> AsyncGenerator[Return, None]:
                # Yield initial status if provided
                if self._status:
                    yield Status(self._status)
                
                # Execute function
                try:
                    # Check if function is async generator
                    if inspect.isasyncgenfunction(self._func):
                        async for result in self._func(tree_data, **kwargs):
                            yield result
                    # Check if function is async
                    elif inspect.iscoroutinefunction(self._func):
                        result = await self._func(tree_data, **kwargs)
                        if isinstance(result, Return):
                            yield result
                        else:
                            # Wrap non-Return results
                            from app.agents.tree.returns import Result
                            yield Result(
                                data=result,
                                summary=f"{tool_name} completed",
                                display_type="json"
                            )
                    else:
                        raise ValueError(f"Tool function must be async or async generator")
                
                except Exception as e:
                    yield Error(
                        message=f"Error in {tool_name}: {str(e)}",
                        error_type="execution",
                        recoverable=False,
                        metadata={"tool": tool_name, "error": str(e)}
                    )
        
        return FunctionTool()
    
    # Support both @tool and @tool()
    if function is None:
        return decorator
    else:
        return decorator(function)

