"""
Analytics Agent - Specialist for data analysis and visualizations.
"""

from typing import List

from app.services.specialists.base_specialist import BaseSpecialist
from app.agents.tools.base_tool import BaseTool
from app.agents.tools.database_query_tool import DatabaseQueryTool
from app.agents.tools.data_analysis_tool import DataAnalysisTool
from app.agents.tools.nlp_tool import NLPTool
from app.agents.tools.visualization_tool import VisualizationTool
from app.agents.tools.rag_retrieval_tool import RAGRetrievalTool
from app.agents.tools.citation_tool import CitationTool


ANALYTICS_AGENT_PROMPT = """You are a Data Analytics Specialist for Needle AI.

Your expertise:
- Statistical analysis and trend detection
- Data visualization and reporting
- NLP and text analytics
- Pattern recognition

Available tools:
- database_query: Fetch structured data
- data_analysis: Perform statistical operations
- nlp_tool: Extract insights from text
- visualization: Create informative charts
- rag_retrieval: When analyzing review text
- citation: Document data sources

Reasoning process:
1. Identify what data is needed to answer the question
2. Fetch the data (use database_query or rag_retrieval)
3. Perform appropriate analysis (use data_analysis, nlp_tool)
4. Create visualizations if helpful
5. Explain your methodology

Be precise, show your work, and visualize when helpful. Focus on actionable insights."""


class AnalyticsAgent(BaseSpecialist):
    """Analytics specialist with database queries, statistics, NLP, visualizations."""
    
    @property
    def name(self) -> str:
        return "analytics"
    
    @property
    def description(self) -> str:
        return "Data analysis, statistics, trends, visualizations, aggregations"
    
    @property
    def system_prompt(self) -> str:
        return ANALYTICS_AGENT_PROMPT
    
    @property
    def model_name(self) -> str:
        return getattr(
            self.settings,
            "analytics_agent_model",
            "openai/gpt-5"
        )
    
    def _initialize_tools(self) -> List[BaseTool]:
        """Initialize analytics agent tools."""
        return [
            DatabaseQueryTool(),
            DataAnalysisTool(),
            NLPTool(),
            VisualizationTool(),
            RAGRetrievalTool(),
            CitationTool()
        ]

