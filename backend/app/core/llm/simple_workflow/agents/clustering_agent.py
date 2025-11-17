"""Clustering Agent - Groups similar reviews"""

from typing import Any, Dict, Optional

from app.core.llm.simple_workflow.tools.clustering_analysis_tool import cuterize_dataset
from app.core.llm.simple_workflow.tools.semantic_search_tool import semantic_search_from_query, semantic_search_from_sql
from app.core.llm.simple_workflow.tools.user_dataset_tool import get_available_datasets_in_context
from app.core.llm.simple_workflow.tools.forfeit_tool import forfeit_request
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

    cuterize_dataset_tool = FunctionTool.from_defaults(fn=cuterize_dataset)
    semantic_search_from_sql_tool = FunctionTool.from_defaults(fn=semantic_search_from_sql)
    semantic_search_from_query_tool = FunctionTool.from_defaults(fn=semantic_search_from_query)
    get_available_datasets_in_context_tool = FunctionTool.from_defaults(fn=get_available_datasets_in_context)
    forfeit_tool = FunctionTool.from_defaults(fn=forfeit_request)

    return FunctionAgent(
        name="clustering",
        description="Groups similar reviews. BRIEF responses only.",
        system_prompt="""You are a clustering specialist. Group reviews, BE BRIEF.

ANALYZE:
- Group similar reviews
- Identify themes
- Extract key patterns

FORFEIT WHEN:
- No embeddings available for clustering
- Dataset too small for meaningful clusters
- Clustering repeatedly fails
Call forfeit_request with clear reason.

BREVITY RULES:
- Keep findings under 80 words
- Use bullet points only
- NO lengthy explanations
- NEVER mention routing, agents, or internal workflow
- Example: "5 clusters found: [theme1], [theme2], [theme3]..." """,
        tools=[cuterize_dataset_tool, get_available_datasets_in_context_tool, semantic_search_from_sql_tool, semantic_search_from_query_tool, forfeit_tool],
        llm=llm,
    )
