"""
Query analyzer agent for determining workflow execution paths.
"""

from llama_index.core.llms import ChatMessage
from app.utils.logging import get_logger

from app.optimal_workflow.agents.base import get_llm, QueryAnalysis

logger = get_logger(__name__)


async def analyze_query(query: str, stream_callback=None) -> QueryAnalysis:
    """
    Analyze user query to determine execution path.
    
    Args:
        query: User query string
        stream_callback: Optional callback for streaming output
    """
    llm = get_llm()
    sllm = llm.as_structured_llm(output_cls=QueryAnalysis)
    
    prompt = f"""Analyze this user query and determine what workflow steps are needed:

Query: {query}

Determine:
- Does this need data retrieval? (mentions specific company, asks for reviews, needs data)
- Does this need NLP analysis? (asks for gaps, patterns, clustering, sentiment, features)
- What company are they asking about?
- What type of query is this?
- What type of analysis is needed (TFIDF, clustering, sentiment, etc)?"""

    messages = [
        ChatMessage(role="system", content="You are a query analyzer that determines workflow execution paths."),
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
    
    logger.info(f"Query analysis: {result}")
    return result

if __name__ == "__main__":
    import asyncio
    result = asyncio.run(analyze_query("What are the main product gaps for Netflix based on customer reviews?"))
    print(result)