"""
Query classifier to route queries to appropriate workflow based on complexity.
"""

from enum import Enum
import time
from typing import Optional
from pydantic import BaseModel, Field
from llama_index.llms.openai import OpenAI

from app.core.config.settings import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class QueryComplexity(str, Enum):
    """Query complexity levels."""
    SIMPLE = "simple"  # General queries, greetings, non-data questions
    MEDIUM = "medium"  # Follow-up questions, queries answerable with history
    COMPLEX = "complex"  # Queries requiring full data retrieval and analysis


class QueryClassification(BaseModel):
    """Query classification result."""
    complexity: QueryComplexity = Field(..., description="Complexity level of the query")
    reasoning: str = Field(..., description="Brief explanation")
    requires_data: bool = Field(..., description="Whether query requires data retrieval")
    requires_history: bool = Field(..., description="Whether query requires conversation history")


async def classify_query(
    query: str,
    conversation_history: Optional[list] = None,
    user_id: Optional[str] = None
) -> QueryClassification:
    """
    Classify a query to determine which workflow should handle it.
    
    Args:
        query: User's query
        conversation_history: Recent conversation messages for context
        user_id: User ID for potential personalization
        
    Returns:
        QueryClassification with complexity level and reasoning
    """
    settings = get_settings()
    api_key = str(settings.get_secret("openai_api_key"))
    
    # Use gpt-5-nano for fast classification
    llm = OpenAI(
        model="gpt-5-mini",
        api_key=api_key,
        temperature=0.1
    )
    
    # Build context for classification
    history_context = ""
    t0 = time.time()
    if conversation_history and len(conversation_history) > 0:
        recent_messages = conversation_history[-2:]  # Last 1 exchange only for speed
        history_context = "\nRecent: "
        for msg in recent_messages:
            history_context += f"{msg.get('role')}: {msg.get('content', '')[:100]} "
    
    # Ultra-simple prompt - just ask for one word
    prompt = f"""Classify in ONE WORD: simple, medium, or complex

- simple: greetings, general knowledge, no data needed, question not related to products, companies, reviews, analytics, etc.
- medium: follow-up questions needing prior conversation, clarifications, references to previous conversation, etc.
- complex: data analysis, company info, trends, product gaps, customer sentiment, etc.

Query: "{query}"{history_context}

Word:"""

    try:
        from llama_index.core.llms import ChatMessage
        
        messages = [ChatMessage(role="user", content=prompt)]
        
        # Get simple text response (no structured output!)
        response = await llm.achat(messages)
        result_text = response.message.content.strip().lower()
        
        # Parse the one-word response
        if "simple" in result_text:
            complexity = QueryComplexity.SIMPLE
        elif "medium" in result_text:
            complexity = QueryComplexity.MEDIUM
        else:
            complexity = QueryComplexity.COMPLEX
        
        classification = QueryClassification(
            complexity=complexity,
            reasoning="Quick classification",
            requires_data=complexity == QueryComplexity.COMPLEX,
            requires_history=complexity == QueryComplexity.MEDIUM
        )
        
        t1 = time.time()
        logger.info(f"Query classified as {classification.complexity} in {t1 - t0} seconds")
        return classification
        
    except Exception as e:
        logger.error(f"Error classifying query: {e}", exc_info=True)
        # Default to complex on error to ensure proper handling
        return QueryClassification(
            complexity=QueryComplexity.COMPLEX,
            reasoning=f"Classification failed, defaulting to complex: {str(e)}",
            requires_data=True,
            requires_history=False
        )

