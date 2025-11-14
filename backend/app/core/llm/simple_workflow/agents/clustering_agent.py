"""Clustering Agent - Groups similar reviews"""

from typing import Any, Dict, Optional

from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.tools import FunctionTool
from llama_index.llms.openai import OpenAI

from app.core.llm.workflow.tools import review_analysis_tools


def create_clustering_agent(llm: OpenAI, user_id: str) -> FunctionAgent:
    """
    Create the clustering agent for grouping similar reviews.
    
    Args:
        llm: OpenAI LLM instance
        user_id: User ID to pre-bind to all tools
        
    Returns:
        FunctionAgent configured as clustering specialist
    """
    # Create wrapper functions that hide user_id from LLM
    def cluster_reviews(n_clusters: int = 5, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Cluster similar reviews to identify themes."""
        return review_analysis_tools.cluster_reviews(user_id=user_id, n_clusters=n_clusters, filters=filters)
    
    def extract_keywords(filters: Optional[Dict[str, Any]] = None, top_n: int = 20) -> Dict[str, Any]:
        """Extract top keywords from reviews."""
        return review_analysis_tools.extract_keywords(user_id=user_id, filters=filters, top_n=top_n)
    
    def semantic_search_reviews(query: str, limit: int = 10) -> Dict[str, Any]:
        """Perform semantic search on reviews using vector embeddings."""
        return review_analysis_tools.semantic_search_reviews(user_id=user_id, query=query, limit=limit)
    
    cluster_reviews_tool = FunctionTool.from_defaults(fn=cluster_reviews)
    extract_keywords_tool = FunctionTool.from_defaults(fn=extract_keywords)
    semantic_search_tool = FunctionTool.from_defaults(fn=semantic_search_reviews)
    
    return FunctionAgent(
        name="clustering",
        description="Specialist in grouping similar reviews and identifying themes",
        system_prompt="""You are a review clustering specialist. You:
1. Group similar reviews into clusters
2. Identify common themes and topics
3. Extract representative reviews for each cluster
4. Analyze keyword patterns within clusters

Use clustering tools and keyword extraction.
After analysis, hand off to Visualization Agent for visualizations, then to Report Writer.
Help users understand the main themes in their review data.""",
        tools=[cluster_reviews_tool, extract_keywords_tool, semantic_search_tool],
        llm=llm,
    )
