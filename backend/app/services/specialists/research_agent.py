"""
Research Agent - Specialist for market research and competitor analysis.
"""

from typing import List

from app.services.specialists.base_specialist import BaseSpecialist
from app.agents.tools.base_tool import BaseTool
from app.agents.tools.web_search_tool import WebSearchTool
from app.agents.tools.rag_retrieval_tool import RAGRetrievalTool
from app.agents.tools.mcp_api_tool import MCPAPITool
from app.agents.tools.data_analysis_tool import DataAnalysisTool
from app.agents.tools.citation_tool import CitationTool


RESEARCH_AGENT_PROMPT = """You are a Market Research Specialist for Needle AI.

Your expertise:
- Competitive intelligence and market analysis
- Industry trends and gap identification
- External data gathering and synthesis
- Cross-market comparisons

Available tools:
- web_search: Search the internet for current information
- rag_retrieval: Cross-reference with internal review data
- mcp_api_call: Call external APIs (when configured)
- data_analysis: Compare and analyze datasets
- citation: Format all sources properly

Reasoning process:
1. Identify what external information is needed
2. Search the web for current data (use web_search)
3. Cross-reference with internal data if relevant
4. Synthesize findings from multiple sources
5. Always cite sources with URLs

Provide comprehensive, well-sourced insights. Compare and contrast different sources."""


class ResearchAgent(BaseSpecialist):
    """Research specialist with web search, RAG cross-reference, MCP integration."""
    
    @property
    def name(self) -> str:
        return "research"
    
    @property
    def description(self) -> str:
        return "Market research, competitor analysis, external data, industry trends"
    
    @property
    def system_prompt(self) -> str:
        return RESEARCH_AGENT_PROMPT
    
    @property
    def model_name(self) -> str:
        return getattr(
            self.settings,
            "research_agent_model",
            "anthropic/claude-sonnet-4.5"
        )
    
    def _initialize_tools(self) -> List[BaseTool]:
        """Initialize research agent tools."""
        return [
            WebSearchTool(),
            RAGRetrievalTool(),
            MCPAPITool(),
            DataAnalysisTool(),
            CitationTool()
        ]

