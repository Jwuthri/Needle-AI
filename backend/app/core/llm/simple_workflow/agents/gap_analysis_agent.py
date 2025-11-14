"""Gap Analysis Agent - Identifies product gaps and unmet needs"""

from typing import Any, Dict, List, Optional

from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.tools import FunctionTool
from llama_index.llms.openai import OpenAI

from app.core.llm.workflow.tools import review_analysis_tools


def create_gap_analysis_agent(llm: OpenAI, user_id: str) -> FunctionAgent:
    """
    Create the gap analysis agent for identifying product gaps.
    
    Args:
        llm: OpenAI LLM instance
        user_id: User ID to pre-bind to all tools
        
    Returns:
        FunctionAgent configured as gap analysis specialist
    """
    # Create wrapper functions that hide user_id from LLM
    def detect_product_gaps(analysis_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Identify product gaps, unmet needs, and feature requests."""
        return review_analysis_tools.detect_product_gaps(user_id=user_id, analysis_params=analysis_params)
    
    def semantic_search_reviews(query: str, limit: int = 10) -> Dict[str, Any]:
        """Perform semantic search on reviews using vector embeddings."""
        return review_analysis_tools.semantic_search_reviews(user_id=user_id, query=query, limit=limit)
    
    def extract_keywords(filters: Optional[Dict[str, Any]] = None, top_n: int = 20) -> Dict[str, Any]:
        """Extract top keywords from reviews."""
        return review_analysis_tools.extract_keywords(user_id=user_id, filters=filters, top_n=top_n)
    
    def query_user_reviews_table(
        query: str,
        table_name: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query user reviews table with SQL."""
        return review_analysis_tools.query_user_reviews_table(
            user_id=user_id, query=query, table_name=table_name, limit=limit
        )
    
    detect_gaps_tool = FunctionTool.from_defaults(fn=detect_product_gaps)
    semantic_search_tool = FunctionTool.from_defaults(fn=semantic_search_reviews)
    extract_keywords_tool = FunctionTool.from_defaults(fn=extract_keywords)
    query_user_reviews_tool = FunctionTool.from_defaults(fn=query_user_reviews_table)
    
    return FunctionAgent(
        name="gap_analysis",
        description="Specialist in identifying product gaps, unmet needs, and feature requests",
        system_prompt="""You are a product gap analysis specialist. You help identify:
1. Product gaps and unmet customer needs
2. Feature requests and improvement opportunities
3. Common pain points across reviews
4. Areas where competitors might have advantages

Use semantic search to find relevant reviews, extract keywords, and detect patterns.
After analysis, hand off to Visualization Agent for charts, then to Report Writer for final formatting.
Be thorough and evidence-based in your analysis.""",
        tools=[detect_gaps_tool, semantic_search_tool, extract_keywords_tool, query_user_reviews_tool],
        llm=llm,
    )
