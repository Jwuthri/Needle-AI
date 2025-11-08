"""
Query analyzer agent for determining workflow execution paths.
"""

from llama_index.core.llms import ChatMessage
from app import get_logger

from app.workflow.agents.base import get_llm, QueryAnalysis

logger = get_logger(__name__)


async def analyze_query(query: str) -> QueryAnalysis:
    """
    Analyze user query to determine execution path.
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
    
    response = await sllm.achat(messages)
    result = response.raw
    
    logger.info(f"Query analysis: {result}")
    return result