"""
Agno Context Management - How Agno handles context windows automatically.
Updated to use latest Agno API with db parameter and enable_user_memories.
"""

from typing import Any, Dict

try:
    from agno.agent import Agent
    from agno.db.postgres import PostgresDb
    from agno.models.openrouter import OpenRouter
    from agno.models.openai import OpenAIChat
    AGNO_AVAILABLE = True
except ImportError:
    AGNO_AVAILABLE = False

from app.utils.logging import get_logger

logger = get_logger("agno_context_manager")


class AgnoContextManager:
    """
    Demonstrates how Agno handles context window management automatically.
    
    With the latest Agno API:
    1. Memory is handled by db parameter (PostgresDb/RedisDb)
    2. enable_user_memories=True for persistent memory
    3. read_chat_history=True for automatic context loading
    4. No manual memory management needed
    """

    def __init__(self, model_name: str, api_key: str, postgres_url: str = None):
        if not AGNO_AVAILABLE:
            raise ImportError("Agno package required")

        self.model_name = model_name
        self.api_key = api_key
        self.postgres_url = postgres_url

        # Create agents with different strategies
        self.agents = self._create_agents_with_different_strategies()

    def _create_agents_with_different_strategies(self) -> Dict[str, Agent]:
        """Create agents with different context management strategies."""

        agents = {}

        # 1. EPHEMERAL MEMORY (no persistence)
        agents["ephemeral"] = Agent(
            model=OpenRouter(id=self.model_name, api_key=self.api_key),
            instructions="You have ephemeral memory. Context is lost between sessions.",
            read_chat_history=True,  # Read within session only
        )

        # 2. PERSISTENT MEMORY WITH POSTGRES (recommended)
        if self.postgres_url:
            postgres_db = PostgresDb(
                db_url=self.postgres_url,
                table_name="agno_context_demo",
            )
            
            agents["persistent_postgres"] = Agent(
                model=OpenRouter(id=self.model_name, api_key=self.api_key),
                db=postgres_db,
                enable_user_memories=True,  # Enable persistent user memories
                read_chat_history=True,      # Read chat history automatically
                instructions="You have persistent memory via PostgreSQL. Remember user context across sessions.",
            )

        # 3. MINIMAL CONTEXT (for testing/debugging)
        agents["minimal"] = Agent(
            model=OpenRouter(id=self.model_name, api_key=self.api_key),
            read_chat_history=False,  # Don't load chat history
            instructions="You have minimal context. Respond based on current message only.",
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
                    # Use async arun() method from latest API
                    run_response = await agent.arun(
                        message,
                        stream=False,
                        session_id=f"demo_{agent_type}"
                    )

                    # Extract response
                    response_text = run_response.content if hasattr(run_response, 'content') else str(run_response)

                    results[f"{agent_type}_turn_{i+1}"] = {
                        "response_length": len(response_text),
                        "agent_type": agent_type,
                        "turn": i + 1,
                    }

                    # Log progress
                    if i % 10 == 0:
                        logger.info(f"{agent_type}: Processed turn {i+1}/{len(messages)}")

                except Exception as e:
                    logger.error(f"Error with {agent_type} at turn {i+1}: {e}")
                    break

        return results

    def get_context_strategies_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about different context management strategies."""

        return {
            "ephemeral": {
                "description": "In-memory only, no persistence",
                "best_for": "Testing, development, stateless interactions",
                "pros": ["Simple", "Fast", "No external dependencies"],
                "cons": ["Context lost between sessions", "Not suitable for production"],
                "context_limit_handling": "Automatic within session, reset on restart"
            },

            "persistent_postgres": {
                "description": "PostgreSQL-backed persistent memory",
                "best_for": "Production applications with user sessions",
                "pros": ["Persistent across restarts", "ACID compliance", "Reliable"],
                "cons": ["Requires PostgreSQL database"],
                "context_limit_handling": "Automatic with persistent storage"
            },

            "minimal": {
                "description": "No context loading, current message only",
                "best_for": "Debugging, stateless APIs",
                "pros": ["Minimal overhead", "Predictable"],
                "cons": ["No context awareness"],
                "context_limit_handling": "No history loaded"
            },
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


# Example usage and benefits with latest Agno API
AGNO_CONTEXT_BENEFITS = {
    "automatic_management": "No manual context window handling needed",
    "persistent_memory": "Use db parameter for persistent storage",
    "user_memories": "enable_user_memories=True for cross-session memory",
    "automatic_history": "read_chat_history=True loads context automatically",
    "transparent": "Works behind the scenes, no code changes needed",
    "scalable": "Handles conversations of any length",
    "memory_efficient": "Only loads relevant context into model",
    "cost_effective": "Reduces token usage through smart management"
}
