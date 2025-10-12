"""
Persistent Agno Memory Configurations - Survives server restarts.
Updated to use latest Agno API with db parameter for persistence.
"""

from typing import Any

from agno.agent import Agent
from agno.db.postgres import PostgresDb
from agno.db.redis import RedisDb
from agno.models.openrouter import OpenRouter
from agno.models.openai import OpenAIChat
from app.utils.logging import get_logger

logger = get_logger("persistent_agno_memory")


class PersistentAgnoMemory:
    """
    Production-ready Agno memory configurations that survive server restarts.
    
    Uses latest Agno API:
    - db parameter (PostgresDb/RedisDb) for persistence
    - enable_user_memories=True for cross-session memory
    - read_chat_history=True for automatic context loading
    """

    def __init__(self, settings: Any):
        self.settings = settings

    async def create_persistent_memory(self) -> Agent:
        """
        PostgreSQL-backed memory that persists across restarts (default).
        
        Benefits:
        - Reliable ACID-compliant storage
        - Full conversation history
        - Enterprise-grade persistence
        """

        # Create PostgreSQL database for Agent persistence
        postgres_db = PostgresDb(
            db_url=self._get_postgres_url(),
            table_name="agno_sessions",
        )

        agent = Agent(
            model=self._get_model(),
            db=postgres_db,                   # PostgreSQL persistence
            enable_user_memories=True,        # Enable persistent memories
            read_chat_history=True,           # Auto-load history
            instructions=self._get_instructions(),
        )

        logger.info("Created PostgreSQL-persistent Agno agent")
        return agent

    async def create_persistent_postgres_memory(self) -> Agent:
        """
        PostgreSQL-backed memory for enterprise environments.
        
        Benefits:
        - ACID compliance
        - SQL queries on conversation data
        - Enterprise backup/recovery
        - Compliance ready
        """

        # Create PostgreSQL database for Agent persistence
        postgres_db = PostgresDb(
            db_url=self._get_postgres_url(),
            table_name="agno_sessions",
        )

        agent = Agent(
            model=self._get_model(),
            db=postgres_db,                   # PostgreSQL persistence
            enable_user_memories=True,        # Enable persistent memories
            read_chat_history=True,           # Auto-load history
            instructions=self._get_instructions(),
        )

        logger.info("Created PostgreSQL-persistent Agno agent")
        return agent

    async def create_ephemeral_memory(self) -> Agent:
        """
        Ephemeral memory for development/testing.
        
        Benefits:
        - Simple setup
        - Fast
        - Good for development/testing
        
        Note: Memory is lost on restart
        """

        agent = Agent(
            model=self._get_model(),
            # No db parameter = ephemeral memory
            read_chat_history=True,           # Still load history within session
            instructions=self._get_instructions(),
        )

        logger.info("Created ephemeral Agno agent")
        return agent

    def _get_model(self):
        """Get configured model for agents."""
        if self.settings.llm_provider == "openrouter":
            api_key = self.settings.get_secret("openrouter_api_key")
            return OpenRouter(
                id=self.settings.default_model,
                api_key=str(api_key) if hasattr(api_key, '__str__') else api_key
            )
        else:
            api_key = self.settings.get_secret("openai_api_key")
            return OpenAIChat(
                id=self.settings.default_model,
                api_key=str(api_key) if hasattr(api_key, '__str__') else api_key
            )

    def _get_postgres_url(self) -> str:
        """Get PostgreSQL connection URL."""
        db_config = self.settings.parse_database_url()
        return (
            f"postgresql://{db_config['user']}:{db_config['password']}"
            f"@{db_config['host']}:{db_config['port']}"
            f"/{db_config['database']}"
        )

    def _get_instructions(self) -> str:
        """Get agent instructions."""
        return self.settings.agent_instructions or f"""
        You are an AI assistant for {self.settings.app_name}.
        
        Your memory persists across server restarts, so you can:
        - Remember previous conversations
        - Build on past interactions
        - Maintain long-term context
        - Provide personalized responses
        
        Be helpful, accurate, and leverage your persistent memory wisely.
        """


class PersistenceStrategy:
    """Recommended persistence strategies by use case."""

    STRATEGIES = {
        "development": {
            "recommended": "ephemeral",
            "description": "In-memory only for easy development",
            "backup_frequency": "none",
            "retention": "session only"
        },

        "staging": {
            "recommended": "postgres",
            "description": "PostgreSQL with persistence for testing",
            "backup_frequency": "every 4 hours",
            "retention": "14 days"
        },

        "production_small": {
            "recommended": "postgres",
            "description": "PostgreSQL for production",
            "backup_frequency": "hourly",
            "retention": "30 days"
        },

        "production_enterprise": {
            "recommended": "postgres",
            "description": "PostgreSQL for enterprise compliance",
            "backup_frequency": "every 15 minutes",
            "retention": "1 year"
        },
    }

    @classmethod
    def get_recommendation(cls, environment: str, requirements: list = None) -> dict:
        """Get persistence strategy recommendation."""

        base_strategy = cls.STRATEGIES.get(environment, cls.STRATEGIES["development"])

        # Modify based on requirements
        if requirements:
            if "compliance" in requirements:
                base_strategy["recommended"] = "postgres"
                base_strategy["backup_frequency"] = "every 15 minutes"

            if "high_volume" in requirements:
                base_strategy["recommended"] = "postgres"
                base_strategy["retention"] = "6 months"

            if "cost_sensitive" in requirements:
                base_strategy["recommended"] = "ephemeral"
                base_strategy["retention"] = "none"

        return base_strategy


# Production configuration examples
def get_production_memory_config(settings: Any) -> dict:
    """Get production-ready memory configuration."""
    
    db_config = settings.parse_database_url()

    return {
        # PostgreSQL configuration for persistence (primary)
        "postgres": {
            "host": db_config['host'],
            "port": db_config['port'],
            "database": db_config['database'],
            "user": db_config['user'],
            "password": db_config['password'],
            
            # Backup settings
            "backup_enabled": True,
            "backup_frequency": "1h",
            "retention_policy": "1y"
        },

        # Backup strategy
        "backups": {
            "frequency": "1h",
            "retention": "30d",
            "compression": True,
            "encryption": True,
            "offsite_storage": "s3"            # S3 for offsite backups
        }
    }
