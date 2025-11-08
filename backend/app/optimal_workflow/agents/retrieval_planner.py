"""
Retrieval planner agent for SQL query generation.
"""

from typing import Dict, Any, Optional
from llama_index.core.agent.workflow import FunctionAgent, AgentStreamStructuredOutput
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
        stream_callback: Optional callback for streaming structured output events
    """
    llm = get_llm("gpt-5-mini")
    
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
    
    prompt = f"""Create a data retrieval plan for this query:

Query: {query}

{analysis_context}

Available Tables:
{schema_context}

Generate SQL queries and explain the retrieval strategy."""

    # Use FunctionAgent with structured output
    agent = FunctionAgent(
        tools=[],
        llm=llm,
        output_cls=RetrievalPlan,
        system_prompt="You are a data retrieval planner that creates SQL queries."
    )
    
    handler = agent.run(prompt)
    
    # Stream events and collect final result
    final_output = None
    if stream_callback:
        async for event in handler.stream_events():
            event_name = type(event).__name__
            
            # Emit ALL AgentStream events for token-by-token streaming
            if event_name == "AgentStream":
                stream_callback({
                    "type": "agent_stream",
                    "data": {
                        "delta": event.delta if hasattr(event, 'delta') else str(event)
                    }
                })
            
            # Emit structured output when available
            if isinstance(event, AgentStreamStructuredOutput):
                # Store the last output as final
                final_output = event.output
                stream_callback({
                    "type": "agent_stream_structured",
                    "data": {
                        "partial_content": event.output,
                        "is_complete": False
                    }
                })
        # If we got output from streaming, convert dict to Pydantic
        if final_output is None:
            agent_output = await handler
            final_output = agent_output.output if hasattr(agent_output, 'output') else agent_output
        
        # Convert dict to Pydantic model
        if isinstance(final_output, dict):
            final_output = RetrievalPlan(**final_output)
    else:
        # Non-streaming path
        agent_output = await handler
        final_output = agent_output.output if hasattr(agent_output, 'output') else agent_output
        # Convert dict to Pydantic model
        if isinstance(final_output, dict):
            final_output = RetrievalPlan(**final_output)
    
    logger.info(f"Retrieval plan: {len(final_output.sql_queries)} queries")
    return final_output
