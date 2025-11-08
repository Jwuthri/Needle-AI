"""
Query analyzer agent for determining workflow execution paths.
"""

from llama_index.core.agent.workflow import FunctionAgent, AgentStreamStructuredOutput
from app.utils.logging import get_logger

from app.optimal_workflow.agents.base import get_llm, QueryAnalysis

logger = get_logger(__name__)


async def analyze_query(query: str, stream_callback=None) -> QueryAnalysis:
    """
    Analyze user query to determine execution path.
    
    Args:
        query: User query string
        stream_callback: Optional callback for streaming structured output events
    """
    llm = get_llm()
    
    prompt = f"""Analyze this user query and determine what workflow steps are needed.

Query: {query}

Determine:
- Does this need data retrieval? (mentions specific company, asks for reviews, needs data)
- Does this need NLP analysis? (asks for gaps, patterns, clustering, sentiment, features)
- What company are they asking about?
- What type of query is this?
- What type of analysis is needed (TFIDF, clustering, sentiment, etc)?"""

    # Use FunctionAgent with structured output
    agent = FunctionAgent(
        tools=[],  # No tools needed for this agent
        llm=llm,
        output_cls=QueryAnalysis,
        system_prompt="You are a query analyzer that determines workflow execution paths."
    )
    
    handler = agent.run(prompt)
    
    # Stream events and collect final result
    final_output = None
    if stream_callback:
        logger.info("Starting to stream events...")
        async for event in handler.stream_events():
            event_name = type(event).__name__
            logger.info(f"Got event: {event_name}")
            
            # Emit ALL AgentStream events for token-by-token streaming
            if event_name == "AgentStream":
                stream_callback({
                    "type": "agent_stream",
                    "data": {
                        "delta": event.delta if hasattr(event, 'delta') else str(event)
                    }
                })
            
            # else:
            #     print(f"Got event: {event}")
            # Emit structured output when available
            if isinstance(event, AgentStreamStructuredOutput):
                # Store the last output as final
                final_output = event.output
                logger.info(f"Streaming structured output: {final_output}")
                # Emit the structured output as it streams
                stream_callback({
                    "type": "agent_stream_structured",
                    "data": {
                        "partial_content": event.output,
                        "is_complete": False
                    }
                })
        logger.info(f"Streaming complete. Final output: {final_output}")
        # If we got output from streaming, convert dict to Pydantic
        if final_output is None:
            agent_output = await handler
            final_output = agent_output.output if hasattr(agent_output, 'output') else agent_output
        
        # Convert dict to Pydantic model
        if isinstance(final_output, dict):
            final_output = QueryAnalysis(**final_output)
    else:
        # Non-streaming path
        agent_output = await handler
        final_output = agent_output.output if hasattr(agent_output, 'output') else agent_output
        # Convert dict to Pydantic model
        if isinstance(final_output, dict):
            final_output = QueryAnalysis(**final_output)
    
    logger.info(f"Query analysis: {final_output}")
    return final_output