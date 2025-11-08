"""
Format detector agent for determining output format requirements.
"""

from llama_index.core.agent.workflow import FunctionAgent, AgentStreamStructuredOutput
from app.utils.logging import get_logger

from .base import get_llm, FormatDetection

logger = get_logger(__name__)


async def detect_format(query: str, stream_callback=None) -> FormatDetection:
    """
    Detect desired output format from query using structured LLM.
    
    Args:
        query: User query string
        stream_callback: Optional callback for streaming structured output events
    """
    llm = get_llm()
    
    prompt = f"""Analyze this query and determine the best output format:

Query: {query}

Determine:
- What format would be best? (markdown report, JSON, table, chart)
- What specific formatting details are needed?"""

    # Use FunctionAgent with structured output
    agent = FunctionAgent(
        tools=[],
        llm=llm,
        output_cls=FormatDetection,
        system_prompt="You are a format detection specialist."
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
            final_output = FormatDetection(**final_output)
    else:
        # Non-streaming path
        agent_output = await handler
        final_output = agent_output.output if hasattr(agent_output, 'output') else agent_output
        # Convert dict to Pydantic model
        if isinstance(final_output, dict):
            final_output = FormatDetection(**final_output)
    
    logger.info(f"Format detection: {final_output}")
    return final_output
