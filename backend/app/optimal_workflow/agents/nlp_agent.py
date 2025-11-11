"""
NLP analysis agent for performing text analytics on retrieved data.

This agent has access to NLP tools and decides which analysis to perform
based on the query and analysis type.
"""

import json
from typing import Dict, Any, List

from llama_index.core.agent.workflow import FunctionAgent

from app.utils.logging import get_logger
from .base import get_llm, QueryAnalysis
from ..tools import (
    compute_tfidf_tool,
    cluster_reviews_tool,
    analyze_sentiment_tool,
    identify_features_tool,
)

logger = get_logger(__name__)


# System prompt for the NLP agent
NLP_AGENT_SYSTEM_PROMPT = """You are an expert NLP analysis agent specialized in text analytics.

Your role is to analyze user queries and call the appropriate NLP tools. 

IMPORTANT: After calling the tools, STOP. Do not provide additional commentary or ask follow-up questions.

Tool Selection Guidelines:
- identify_features: Extract feature requests, pain points, product gaps
  → Use for: "what's missing", "feature requests", "product gaps", "pain points"
  → Requires: text_column, optional: rating_column, min_frequency

- cluster_reviews: Group similar text by themes/topics
  → Use for: "themes", "topics", "patterns", "grouping", "categories"
  → Requires: text_column, optional: num_clusters, include_metadata

- analyze_sentiment: Analyze sentiment and ratings distribution
  → Use for: "sentiment", "ratings", "satisfaction", "positive/negative"
  → Requires: text_column, optional: rating_column, group_by

- compute_tfidf: Extract most important terms and keywords
  → Use for: "key terms", "important words", "keywords", "vocabulary"
  → Requires: text_column, optional: top_n, ngram_range

Column Naming Conventions:
- Text columns: review_text, text, feedback, comment, description, content
- Rating columns: rating, score, stars, sentiment_score
- ID columns: id, review_id, feedback_id, user_id

Always:
- Use exact dataset names provided in the context
- Verify column names match available columns
- Choose the most appropriate tool(s) for the query
- Call the tools and STOP immediately, do not suggest any Next steps
"""


def _build_user_prompt(
    query: str,
    analysis: QueryAnalysis,
    retrieved_data: Dict[str, Any]
) -> str:
    """
    Build the user prompt with query context and available datasets.
    
    Args:
        query: Original user query
        analysis: Query analysis result
        retrieved_data: Retrieved data with datasets
        
    Returns:
        Formatted user prompt string
    """
    prompt_parts = [
        "=== ANALYSIS REQUEST ===",
        f"Query: {query}",
        f"Analysis Type: {analysis.analysis_type}",
        f"Company: {analysis.company or 'Not specified'}",
        f"Reasoning: {analysis.reasoning}",
        "",
        "=== AVAILABLE DATASETS ===",
    ]
    
    # Add dataset information with columns
    if retrieved_data and 'data' in retrieved_data:
        for dataset_name, dataset_value in retrieved_data['data'].items():
            if dataset_name.endswith('_error'):
                continue
                
            row_count = len(dataset_value) if isinstance(dataset_value, list) else 0
            prompt_parts.append(f"\nDataset: '{dataset_name}' ({row_count} rows)")
            
            # Extract column names from first row
            if isinstance(dataset_value, list) and len(dataset_value) > 0:
                if isinstance(dataset_value[0], dict):
                    columns = list(dataset_value[0].keys())
                    prompt_parts.append(f"  Columns: {', '.join(columns)}")
    
    prompt_parts.extend([
        "",
        "=== YOUR TASK ===",
        "Analyze the query and call the appropriate NLP tool(s) with:",
        "- dataset_name: exact name from available datasets",
        "- text_column: the column containing text data",
        "- other required/optional parameters",
        "",
        "Call the tool(s) now. Do NOT provide commentary after calling tools.",
    ])
    
    return "\n".join(prompt_parts)


def _extract_tool_calls(response: Any) -> List[Dict[str, Any]]:
    """
    Extract tool calls from agent response.
    
    Args:
        response: Agent response object (AgentOutput)
        
    Returns:
        List of tool call dictionaries with standardized format
    """
    tool_calls = []
    # Extract from response.tool_calls (new FunctionAgent API)
    if hasattr(response, 'tool_calls') and response.tool_calls:
        for tc in response.tool_calls:
            # tc is a ToolCallResult with tool_output containing the actual result
            if hasattr(tc, 'tool_output') and hasattr(tc.tool_output, 'raw_output'):
                tool_calls.append(tc.tool_output.raw_output)
    
    return tool_calls


async def perform_nlp_analysis(
    query: str,
    analysis: QueryAnalysis,
    retrieved_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Perform NLP analysis using an agent with access to NLP tools.
    
    The agent will:
    1. Understand the query and analysis type
    2. Select appropriate NLP tool(s)
    3. Execute tools and return results
    
    Args:
        query: Original user query
        analysis: Query analysis result
        retrieved_data: Retrieved data from previous step
        
    Returns:
        Dictionary containing tool calls and their parameters
    """
    logger.info(f"Starting NLP analysis for query: {query}")
    logger.info(f"Analysis type: {analysis.analysis_type}")
    
    # Initialize LLM and tools
    llm = get_llm()
    tools = [
        compute_tfidf_tool,
        cluster_reviews_tool,
        analyze_sentiment_tool,
        identify_features_tool,
    ]
    
    # Create agent with system prompt
    # Set max_iterations=1 to stop after calling tools (no follow-up commentary)
    agent = FunctionAgent(
        tools=tools,
        llm=llm,
        verbose=True,
        system_prompt=NLP_AGENT_SYSTEM_PROMPT,
        max_iterations=1
    )
    
    # Build user prompt with context
    user_prompt = _build_user_prompt(query, analysis, retrieved_data)
    
    # Execute agent
    try:
        response = await agent.run(user_prompt)
        logger.info(f"Agent response: {response}")
        
        # Extract tool calls
        tool_calls = _extract_tool_calls(response)
        logger.info(f"Extracted {len(tool_calls)} tool calls")
        
        return {
            "tool_calls": tool_calls,
            "agent_response": str(response),
            "reasoning": analysis.reasoning,
        }
        
    except Exception as e:
        logger.error(f"Error in NLP agent: {e}", exc_info=True)
        return {
            "error": str(e),
            "tool_calls": [],
            "agent_response": "",
        }
