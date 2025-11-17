"""Forfeit tool - Allows agents to gracefully admit when they cannot answer a question."""

from typing import Dict, Any
from llama_index.core.workflow import Context
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ForfeitException(Exception):
    """Exception raised when an agent forfeits."""
    def __init__(self, reason: str, attempted_actions: list[str] = None):
        self.reason = reason
        self.attempted_actions = attempted_actions or []
        super().__init__(reason)


async def forfeit_request(
    ctx: Context,
    reason: str,
    attempted_actions: list[str]
) -> Dict[str, Any]:
    """
    Forfeit the current request and return a helpful explanation to the user.
    
    Use this tool when:
    - You've tried multiple approaches and still can't answer the question
    - The user's data doesn't contain the information needed
    - The question is outside your capabilities
    - You've hit an error multiple times and can't proceed
    
    REQUIRED PARAMETERS:
        reason (str): Clear explanation of why you cannot answer - REQUIRED
            Example: "The dataset doesn't contain pricing information needed to analyze cost trends"
        attempted_actions (list[str]): List of what you tried before forfeiting - REQUIRED
            Example: ["Searched for price data", "Checked all available columns", "Looked for related metrics"]
    
    Returns:
        Dict with forfeit information that will be shown to the user
    """
    logger.warning(f"Agent forfeiting request: {reason}")
    logger.info(f"Attempted actions: {attempted_actions}")
    
    # Store forfeit info in context
    await ctx.store.set("forfeited", True)
    await ctx.store.set("forfeit_reason", reason)
    await ctx.store.set("forfeit_attempted_actions", attempted_actions)
    
    # Raise exception to stop workflow
    raise ForfeitException(reason=reason, attempted_actions=attempted_actions)

