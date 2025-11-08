"""
Product Agent - Specialist for product-specific questions and review analysis.
"""

from typing import List

from app.services.specialists.base_specialist import BaseSpecialist
from app.agents.tools.base_tool import BaseTool
from app.agents.tools.rag_retrieval_tool import RAGRetrievalTool
from app.agents.tools.database_query_tool import DatabaseQueryTool
from app.agents.tools.data_analysis_tool import DataAnalysisTool
from app.agents.tools.nlp_tool import NLPTool
from app.agents.tools.visualization_tool import VisualizationTool
from app.agents.tools.citation_tool import CitationTool


PRODUCT_AGENT_PROMPT = """You are a Product Intelligence Specialist for Needle AI's product gap analysis platform.

Your expertise:
- Analyzing customer feedback and product reviews
- Identifying feature gaps and pain points
- Understanding user needs and sentiment
- Providing data-driven product insights

Available tools:
- rag_retrieval: Search product reviews by company, sentiment, source
- database_query: Query structured product data
- data_analysis: Perform statistical analysis
- nlp_tool: Extract themes and keywords
- visualization: Create charts
- citation: Format sources

Reasoning process:
1. Understand what product/company the user is asking about
2. Determine if you need review data (use rag_retrieval)
3. Analyze the data if needed (use data_analysis, nlp_tool)
4. Visualize if trends/patterns are important
5. Always cite your sources

Be specific, data-driven, and actionable. Focus on insights that help improve products."""


class ProductAgent(BaseSpecialist):
    """Product specialist with RAG, database, analysis, NLP, visualization tools."""
    
    @property
    def name(self) -> str:
        return "product"
    
    @property
    def description(self) -> str:
        return "Product-specific questions, feature requests, user feedback, review analysis"
    
    @property
    def system_prompt(self) -> str:
        return PRODUCT_AGENT_PROMPT
    
    @property
    def model_name(self) -> str:
        # Get from settings or default to Claude Sonnet
        return getattr(
            self.settings,
            "product_agent_model",
            "anthropic/claude-sonnet-4.5"
        )
    
    def _initialize_tools(self) -> List[BaseTool]:
        """Initialize product agent tools."""
        return [
            RAGRetrievalTool(),
            DatabaseQueryTool(),
            DataAnalysisTool(),
            NLPTool(),
            VisualizationTool(),
            CitationTool()
        ]

