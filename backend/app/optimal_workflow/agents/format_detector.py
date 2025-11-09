"""
Format detector agent for determining output format requirements.
"""

from llama_index.core.llms import ChatMessage
from app.utils.logging import get_logger

from .base import get_llm, FormatDetection

logger = get_logger(__name__)


async def detect_format(query: str, stream_callback=None) -> FormatDetection:
    """
    Detect desired output format from query using structured LLM.
    
    Args:
        query: User query string
        stream_callback: Optional callback for streaming output
    """
    llm = get_llm()
    sllm = llm.as_structured_llm(output_cls=FormatDetection)
    
    prompt = f"""Analyze this query and determine the desired output format:

Query: {query}

Determine:
- What format type is expected? (markdown, json, table, etc)
- What specific formatting requirements are there?"""

    messages = [
        ChatMessage(role="system", content="You are a format detection specialist that determines output formatting requirements."),
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
    
    logger.info(f"Format detection: {result}")
    return result
