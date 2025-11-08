"""
Format detector agent for determining output format requirements.
"""

from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.llms import ChatMessage
from app import get_logger

from .base import get_llm, FormatDetection

logger = get_logger(__name__)


async def detect_format(query: str) -> FormatDetection:
    """
    Detect desired output format from query using FunctionAgent.
    """
    llm = get_llm()
    sllm = llm.as_structured_llm(output_cls=FormatDetection)
    
    prompt = f"""Analyze this query and determine the best output format:

Query: {query}

Determine:
- What format would be best? (markdown report, JSON, table, bullet points, etc)
- Any specific formatting requirements mentioned?"""

    messages = [
        ChatMessage(role="system", content="You are a format detection specialist."),
        ChatMessage(role="user", content=prompt)
    ]
    
    response = await sllm.achat(messages)
    result = response.raw
    
    logger.info(f"Format detection: {result}")
    
    return result
