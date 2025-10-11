"""
Agno Context Management - How Agno handles context windows automatically.
"""

from typing import Any, Dict

try:
    from agno import Agent
    from agno.memory import ChatMemory, HybridMemory, VectorMemory
    from agno.models.openrouter import OpenRouter
    AGNO_AVAILABLE = True
except ImportError:
    AGNO_AVAILABLE = False

from app.utils.logging import get_logger

logger = get_logger("agno_context_manager")


class AgnoContextManager:
    """
    Demonstrates how Agno handles context window management automatically.

    Agno provides several built-in strategies for managing context limits:
    1. Automatic memory compression
    2. Sliding window with retrieval
    3. Intelligent summarization
    4. Vector-based context selection
    """

    def __init__(self, model_name: str, api_key: str):
        if not AGNO_AVAILABLE:
            raise ImportError("Agno package required")

        self.model_name = model_name
        self.api_key = api_key

        # Create agent with different memory strategies
        self.agents = self._create_agents_with_different_strategies()

    def _create_agents_with_different_strategies(self) -> Dict[str, Agent]:
        """Create agents with different context management strategies."""

        agents = {}

        # 1. CHAT MEMORY ONLY (automatic compression)
        agents["chat_only"] = Agent(
            model=OpenRouter(id=self.model_name),
            memory=ChatMemory(
                # Agno automatically compresses when approaching context limit
                max_messages=100,           # Keep last 100 messages
                compress_when_full=True,    # Auto-compress older messages
                compression_ratio=0.5       # Compress to 50% of original size
            ),
            instructions="You have chat memory with automatic compression."
        )

        # 2. VECTOR MEMORY ONLY (semantic retrieval)
        agents["vector_only"] = Agent(
            model=OpenRouter(id=self.model_name),
            memory=VectorMemory(
                # Uses vector search to retrieve relevant context
                max_items=1000,             # Store many items in vector DB
                retrieve_count=10,          # Retrieve 10 most relevant items
                relevance_threshold=0.7     # Only retrieve if >70% relevant
            ),
            instructions="You have vector memory for semantic retrieval."
        )

        # 3. HYBRID MEMORY (best of both worlds) - RECOMMENDED
        agents["hybrid"] = Agent(
            model=OpenRouter(id=self.model_name),
            memory=HybridMemory(
                chat_memory=ChatMemory(
                    max_messages=50,        # Recent conversation
                    compress_when_full=True
                ),
                vector_memory=VectorMemory(
                    max_items=10000,        # Long-term memory
                    retrieve_count=15       # Retrieve relevant context
                ),
                # Agno automatically balances both memory types
                balance_ratio=0.7           # 70% chat, 30% vector in context
            ),
            instructions="You have hybrid memory for optimal context management."
        )

        # 4. ADAPTIVE MEMORY (automatic strategy selection)
        agents["adaptive"] = Agent(
            model=OpenRouter(id=self.model_name),
            memory=HybridMemory(
                # Agno automatically adapts based on conversation type
                adaptive_compression=True,   # Smart compression
                context_aware=True,         # Aware of model limits
                auto_summarize=True,        # Auto-summarize long conversations
            ),
            instructions="You have adaptive memory that auto-adjusts to context limits."
        )

        return agents

    async def demonstrate_context_management(self, conversation_length: str = "long"):
        """Demonstrate how Agno handles different conversation lengths."""

        results = {}

        # Simulate conversations of different lengths
        if conversation_length == "short":
            messages = ["Hello", "How are you?", "Tell me about AI"]
        elif conversation_length == "medium":
            messages = [f"Message {i}: " + "This is a medium length conversation. " * 5
                       for i in range(20)]
        else:  # long
            messages = [f"Message {i}: " + "This is a very long conversation with lots of context. " * 10
                       for i in range(100)]

        # Test each agent type
        for agent_type, agent in self.agents.items():
            logger.info(f"Testing {agent_type} with {conversation_length} conversation")

            # Send all messages and see how context is managed
            for i, message in enumerate(messages):
                try:
                    response = await agent.run(f"{message} (Turn {i+1})")

                    # Check context utilization
                    context_info = self._get_context_info(agent)

                    results[f"{agent_type}_turn_{i+1}"] = {
                        "response_length": len(response) if response else 0,
                        "context_tokens_used": context_info.get("tokens_used", 0),
                        "context_percentage": context_info.get("percentage_used", 0),
                        "memory_strategy": context_info.get("strategy_used", "unknown"),
                        "compressed": context_info.get("compression_applied", False)
                    }

                    # Log when Agno applies compression or retrieval
                    if context_info.get("compression_applied"):
                        logger.info(f"Agno compressed context for {agent_type} at turn {i+1}")

                    if context_info.get("retrieval_applied"):
                        logger.info(f"Agno used vector retrieval for {agent_type} at turn {i+1}")

                except Exception as e:
                    logger.error(f"Error with {agent_type} at turn {i+1}: {e}")
                    break

        return results

    def _get_context_info(self, agent: Agent) -> Dict[str, Any]:
        """Get context utilization info from Agno agent."""

        # Agno provides context information (exact API may vary)
        try:
            if hasattr(agent, 'context_info'):
                return agent.context_info
            elif hasattr(agent, 'memory') and hasattr(agent.memory, 'get_context_info'):
                return agent.memory.get_context_info()
            else:
                # Fallback estimation
                return {
                    "tokens_used": 0,
                    "percentage_used": 0,
                    "strategy_used": "automatic",
                    "compression_applied": False,
                    "retrieval_applied": False
                }
        except Exception as e:
            logger.debug(f"Could not get context info: {e}")
            return {}

    def get_context_strategies_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about different context management strategies."""

        return {
            "chat_only": {
                "description": "Automatic compression of older messages",
                "best_for": "Short to medium conversations",
                "pros": ["Simple", "Fast", "Preserves recent context"],
                "cons": ["May lose important older information"],
                "context_limit_handling": "Automatic compression when approaching limit"
            },

            "vector_only": {
                "description": "Semantic retrieval of relevant past content",
                "best_for": "Knowledge-heavy conversations",
                "pros": ["Preserves important information", "Semantic understanding"],
                "cons": ["May miss recent conversational context"],
                "context_limit_handling": "Retrieves most relevant historical content"
            },

            "hybrid": {
                "description": "Combines chat memory + vector retrieval",
                "best_for": "Most production applications",
                "pros": ["Best of both worlds", "Intelligent balance"],
                "cons": ["Slightly more complex"],
                "context_limit_handling": "Smart balance of recent + relevant historical"
            },

            "adaptive": {
                "description": "Automatically adapts strategy based on conversation",
                "best_for": "Diverse conversation types",
                "pros": ["Fully automatic", "Optimal for each situation"],
                "cons": ["Less predictable"],
                "context_limit_handling": "Dynamically selects best strategy"
            }
        }


def get_model_context_limits() -> Dict[str, int]:
    """Context limits for popular models (tokens)."""
    return {
        # Latest Models
        "gpt-4o": 128000,
        "gpt-4o-mini": 128000,
        "claude-3.5-sonnet": 200000,
        "claude-3-haiku": 200000,
        "gemini-1.5-pro": 2000000,  # 2M tokens!
        "gemini-1.5-flash": 1000000,

        # Open Source
        "llama-3.3-70b": 131072,
        "deepseek-chat": 64000,
        "qwen-2.5-72b": 32768,
    }


def estimate_token_count(text: str) -> int:
    """Rough estimation of token count (4 chars ≈ 1 token)."""
    return len(text) // 4


# Example usage and benefits
AGNO_CONTEXT_BENEFITS = {
    "automatic_management": "No manual context window handling needed",
    "intelligent_compression": "Preserves important information while reducing size",
    "semantic_retrieval": "Finds relevant past information automatically",
    "multi_strategy": "Different strategies for different conversation types",
    "transparent": "Works behind the scenes, no code changes needed",
    "scalable": "Handles conversations of any length",
    "memory_efficient": "Only loads relevant context into model",
    "cost_effective": "Reduces token usage through smart management"
}
