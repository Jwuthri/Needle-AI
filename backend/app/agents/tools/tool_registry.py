"""
Tool registry for managing available tools in the orchestration system.
"""

from typing import Dict, List, Optional

from app.agents.tools.base_tool import BaseTool
from app.utils.logging import get_logger

logger = get_logger("tool_registry")


class ToolRegistry:
    """
    Central registry for all available tools.
    
    Usage:
        registry = ToolRegistry()
        registry.register(QueryPlannerTool())
        registry.register(RAGRetrievalTool())
        
        # Get tool by name
        tool = registry.get("query_planner")
        
        # Get all tools for agent
        all_tools = registry.get_all_tools()
    """
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
    
    def register(self, tool: BaseTool):
        """Register a tool."""
        if tool.name in self._tools:
            logger.warning(f"Tool {tool.name} already registered, overwriting")
        
        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")
    
    def unregister(self, tool_name: str):
        """Unregister a tool by name."""
        if tool_name in self._tools:
            del self._tools[tool_name]
            logger.debug(f"Unregistered tool: {tool_name}")
    
    def get(self, tool_name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self._tools.get(tool_name)
    
    def get_all_tools(self) -> List[BaseTool]:
        """Get all registered tools."""
        return list(self._tools.values())
    
    def get_tool_names(self) -> List[str]:
        """Get names of all registered tools."""
        return list(self._tools.keys())
    
    def get_tools_for_agno(self) -> List[Dict]:
        """
        Get all tools in Agno-compatible format.
        
        Returns list of tool definitions that can be passed to Agno Agent.
        """
        return [tool.to_agno_tool() for tool in self._tools.values()]
    
    def clear(self):
        """Clear all registered tools."""
        self._tools.clear()
        logger.debug("Cleared all tools from registry")
    
    def __len__(self) -> int:
        """Number of registered tools."""
        return len(self._tools)
    
    def __contains__(self, tool_name: str) -> bool:
        """Check if a tool is registered."""
        return tool_name in self._tools

