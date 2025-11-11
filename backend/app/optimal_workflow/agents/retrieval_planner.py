"""
Retrieval planner agent for SQL query generation.
"""

from typing import Dict, Any, Optional
from llama_index.core.llms import ChatMessage
from app.utils.logging import get_logger

from .base import get_llm, RetrievalPlan, QueryAnalysis

logger = get_logger(__name__)


async def plan_retrieval(query: str, table_schemas: Dict[str, Any], query_analysis: Optional[QueryAnalysis] = None, stream_callback=None) -> RetrievalPlan:
    """
    Plan data retrieval strategy.
    
    Args:
        query: User query string
        table_schemas: Available table schemas
        query_analysis: Optional query analysis result
        stream_callback: Optional callback for streaming output
    """
    llm = get_llm("gpt-5-mini")
    sllm = llm.as_structured_llm(output_cls=RetrievalPlan)
    
    # Build context about available tables
    schema_context = "\n\n".join([
        f"Table: {name}\nColumns: {', '.join(schema.get('columns', []))}"
        for name, schema in table_schemas.items()
    ])
    
    analysis_context = ""
    if query_analysis:
        analysis_context = f"""
Query Analysis Context:
- Company: {query_analysis.company}
- Query Type: {query_analysis.query_type}
- Analysis Needed: {query_analysis.analysis_type}
"""
    
    prompt = f"""Generate ONLY the minimal SQL queries needed to retrieve data for this query:

Query: {query}
{analysis_context}

Available Tables:
{schema_context}

IMPORTANT RULES:
1. Generate ONLY 1-3 queries maximum - focus on the absolute essentials
2. Keep queries GENERAL - retrieve broader datasets that NLP can filter/analyze later
3. NO DUPLICATES - if one query can cover multiple needs, use just that one
4. Avoid over-filtering - let NLP handle complex filtering in the next step
5. Each query should have a DISTINCT purpose - if similar, merge them

Example: Instead of separate queries for "positive reviews" and "negative reviews", 
create ONE general query for "all reviews" and let NLP analyze sentiment.

Focus on retrieving the RAW DATA needed, not pre-analyzed subsets."""

    messages = [
        ChatMessage(role="system", content="You are a data retrieval planner. Generate MINIMAL, GENERAL SQL queries (1-3 max). Focus on retrieving raw data that NLP will filter/analyze. Avoid duplicates and over-filtering."),
        ChatMessage(role="user", content=prompt)
    ]
    
    if stream_callback:
        # Stream structured updates - send parsed object when it changes
        import json
        previous_obj = None
        async for chunk in await sllm.astream_chat(messages):
            # Extract text from message blocks
            if chunk.message and chunk.message.blocks:
                text = chunk.message.blocks[0].text if chunk.message.blocks else ""
                if text:
                    try:
                        # Try to parse the current JSON
                        current_obj = json.loads(text)
                        # Only emit if the object changed
                        if current_obj != previous_obj:
                            stream_callback({
                                "type": "agent_stream_structured",
                                "data": {
                                    "partial_content": current_obj,
                                    "is_complete": False
                                }
                            })
                            previous_obj = current_obj
                    except json.JSONDecodeError:
                        # Partial JSON, skip
                        pass
        # Get final result
        response = await sllm.achat(messages)
        result = response.raw
    else:
        # Non-streaming mode
        response = await sllm.achat(messages)
        result = response.raw
    
    logger.info(f"Retrieval plan: {len(result.sql_queries)} queries")
    return result
