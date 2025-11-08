"""
General Agent - Fallback specialist for general questions.
"""

from typing import List

from app.services.specialists.base_specialist import BaseSpecialist
from app.agents.tools.base_tool import BaseTool
from app.agents.tools.web_search_tool import WebSearchTool
from app.agents.tools.mcp_api_tool import MCPAPITool
from app.agents.tools.citation_tool import CitationTool


GENERAL_AGENT_PROMPT = """You are a General Assistant for Needle AI.

Your expertise:
- Answering general questions
- Providing definitions and explanations
- Assisting with how-to queries
- Helping users navigate the platform

Available tools:
- web_search: Search for current information
- mcp_api_call: Access external APIs when needed
- citation: Cite sources

Reasoning process:
1. Understand what the user needs
2. Determine if you need external information
3. Search or call APIs as needed
4. Provide clear, helpful answers

Be friendly, clear, and helpful. If you're not sure about something, admit it and search for information."""


class GeneralAgent(BaseSpecialist):
    """General assistant as fallback with web search and MCP tools."""
    
    @property
    def name(self) -> str:
        return "general"
    
    @property
    def description(self) -> str:
        return "General questions, definitions, how-to, platform help"
    
    @property
    def system_prompt(self) -> str:
        return GENERAL_AGENT_PROMPT
    
    @property
    def model_name(self) -> str:
        return getattr(
            self.settings,
            "general_agent_model",
            "openai/gpt-4o-mini"
        )
    
    def _initialize_tools(self) -> List[BaseTool]:
        """Initialize general agent tools."""
        return [
            WebSearchTool(),
            MCPAPITool(),
            CitationTool()
        ]

