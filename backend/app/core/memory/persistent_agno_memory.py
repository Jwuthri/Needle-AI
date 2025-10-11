"""
Persistent Agno Memory Configurations - Survives server restarts.
"""

from typing import Any

from agno import Agent
from agno.db.redis import RedisDb
from agno.memory import ChatMemory, HybridMemory, VectorMemory
from agno.vectordb import ChromaDB, Pinecone, Qdrant, Weaviate
from app.utils.logging import get_logger

logger = get_logger("persistent_agno_memory")


class PersistentAgnoMemory:
    """
    Production-ready Agno memory configurations that survive server restarts.

    All configurations use persistent backends to ensure conversation history
    and memory are preserved across server restarts, deployments, and scaling.
    """

    def __init__(self, settings: Any):
        self.settings = settings

    async def create_persistent_redis_memory(self) -> Agent:
        """
        Redis-backed memory that persists across restarts.

        Benefits:
        - Fast access to recent conversations
        - Configurable persistence (RDB + AOF)
        - Scales horizontally
        """

        # Create Redis database for Agent (current Agno API)
        redis_db = RedisDb(
            db_url=self.settings.get_redis_url_with_auth(db=0),
            db_prefix="agno_memory",
            expire=60 * 60 * 24 * 30  # 30 days retention
        )

        # Create chat memory (persistence handled by Agent's RedisDb)
        chat_memory = ChatMemory()

        agent = Agent(
            model=self._get_model(),
            memory=chat_memory,
            instructions=self._get_instructions(),
            db=redis_db,  # Redis persistence handled here
        )

        logger.info("Created Redis-persistent Agno agent")
        return agent

    async def create_persistent_vector_memory(self, vector_db_type: str = "pinecone") -> Agent:
        """
        Vector database memory that persists across restarts.

        Benefits:
        - Long-term semantic memory
        - Inherently persistent (external service)
        - Semantic search capabilities
        """

        # Configure vector database
        if vector_db_type.lower() == "pinecone":
            vector_db = Pinecone(
                api_key=self.settings.get_secret("pinecone_api_key"),
                environment=self.settings.pinecone_environment,
                index_name=self.settings.pinecone_index_name,

                # Persistence is automatic with Pinecone
                namespace=f"{self.settings.app_name}_memory",
                metadata_config={
                    "indexed": ["session_id", "user_id", "timestamp"],
                    "filtering": True
                }
            )

        elif vector_db_type.lower() == "weaviate":
            vector_db = Weaviate(
                url=self.settings.weaviate_url,
                api_key=self.settings.get_secret("weaviate_api_key"),

                # Weaviate persistence configuration
                class_name=f"{self.settings.app_name}Memory",
                persistence_data_path="/data/weaviate",  # Persistent volume
                enable_backup=True,
                backup_schedule="0 2 * * *"  # Daily backups at 2 AM
            )

        elif vector_db_type.lower() == "qdrant":
            vector_db = Qdrant(
                url=self.settings.qdrant_url,
                api_key=self.settings.get_secret("qdrant_api_key"),
                collection_name=self.settings.qdrant_collection_name,

                # Qdrant persistence configuration
                storage_config={
                    "storage_path": "/data/qdrant",  # Persistent volume
                    "wal_config": {
                        "wal_capacity_mb": 1024,
                        "wal_segments_ahead": 2
                    }
                }
            )

        else:  # ChromaDB
            vector_db = ChromaDB(
                path=self.settings.chromadb_path or "/data/chromadb",  # Persistent path
                collection_name=self.settings.chromadb_collection_name,

                # ChromaDB persistence settings
                settings={
                    "persist_directory": "/data/chromadb",
                    "anonymized_telemetry": False,
                    "allow_reset": False  # Prevent accidental data loss
                }
            )

        # Create vector memory
        vector_memory = VectorMemory(
            vector_db=vector_db,
            max_items=100000,            # Large capacity for long-term memory
            retrieve_count=20,           # Retrieve more context
            relevance_threshold=0.6,     # Lower threshold for broader context

            # Persistence settings
            auto_save_interval=60,       # Save every minute
            batch_size=100,              # Batch operations for efficiency
        )

        agent = Agent(
            model=self._get_model(),
            memory=vector_memory,
            instructions=self._get_instructions(),
            persist_sessions=True
        )

        logger.info(f"Created {vector_db_type}-persistent Agno agent")
        return agent

    async def create_persistent_hybrid_memory(self) -> Agent:
        """
        Hybrid memory with both Redis and vector database persistence.

        Benefits:
        - Fast recent conversations (Redis)
        - Long-term semantic memory (Vector DB)
        - Best of both worlds
        - Production-grade reliability
        """

        # Create Redis database for Agent (current Agno API)
        redis_db = RedisDb(
            db_url=self.settings.get_redis_url_with_auth(db=1),
            db_prefix="agno_chat",
            expire=60 * 60 * 24 * 7  # 7 days for chat
        )

        # Chat memory (persistence handled by Agent's RedisDb)
        chat_memory = ChatMemory()

        # Vector database for long-term memory
        vector_db = Pinecone(
            api_key=self.settings.get_secret("pinecone_api_key"),
            environment=self.settings.pinecone_environment,
            index_name=self.settings.pinecone_index_name,
            namespace=f"{self.settings.app_name}_longterm"
        )

        vector_memory = VectorMemory(
            vector_db=vector_db,
            max_items=1000000,           # Very large long-term capacity
            retrieve_count=15,
            relevance_threshold=0.7,
            auto_save_interval=30        # Save every 30 seconds
        )

        # Hybrid memory combining both
        hybrid_memory = HybridMemory(
            chat_memory=chat_memory,
            vector_memory=vector_memory,

            # Balance configuration
            balance_ratio=0.6,           # 60% chat, 40% vector
            auto_promote_threshold=0.8,  # Promote important chat to vector
            cross_reference=True,        # Cross-reference between memories

            # Persistence settings
            sync_interval=120,           # Sync memories every 2 minutes
            backup_enabled=True,
            backup_interval=3600         # Hourly backups
        )

        agent = Agent(
            model=self._get_model(),
            memory=hybrid_memory,
            instructions=self._get_instructions(),
            db=redis_db,  # Redis persistence handled here
        )

        logger.info("Created hybrid-persistent Agno agent")
        return agent

    async def create_persistent_database_memory(self) -> Agent:
        """
        PostgreSQL-backed memory for enterprise environments.

        Benefits:
        - ACID compliance
        - SQL queries on conversation data
        - Enterprise backup/recovery
        - Compliance ready
        """

        # PostgreSQL storage for Agno
        postgres_storage = PostgreSQLStorage(
            host=self.settings.database_host,
            port=self.settings.database_port,
            database=self.settings.database_name,
            username=self.settings.database_user,
            password=self.settings.get_secret("database_password"),

            # Table configuration
            memory_table="agno_memory",
            sessions_table="agno_sessions",
            metadata_table="agno_metadata",

            # Performance settings
            connection_pool_size=20,
            max_overflow=30,
            pool_timeout=30,

            # Persistence settings
            auto_commit=True,
            transaction_isolation="READ_COMMITTED",
            enable_wal=True               # Write-ahead logging
        )

        # Database-backed memory
        db_memory = ChatMemory(
            storage=postgres_storage,
            max_messages=10000,           # Large capacity with DB storage
            compress_when_full=False,     # Keep full data in DB

            # Database-specific settings
            index_messages=True,          # Index for fast queries
            full_text_search=True,        # Enable FTS
            retention_policy="30 days",   # Automatic cleanup
        )

        agent = Agent(
            model=self._get_model(),
            memory=db_memory,
            instructions=self._get_instructions(),

            # Database persistence settings
            persist_sessions=True,
            transaction_mode="auto",      # Automatic transactions
            backup_to_s3=True,            # S3 backups if configured
            compliance_mode=True          # GDPR/SOC2 compliance features
        )

        logger.info("Created database-persistent Agno agent")
        return agent

    async def create_persistent_file_memory(self) -> Agent:
        """
        File-based memory for simple deployments.

        Benefits:
        - Simple setup
        - Version control friendly
        - Good for development/testing
        """

        # File storage configuration
        file_storage = FileStorage(
            base_path=self.settings.data_directory or "/data/agno",

            # File organization
            sessions_dir="sessions",
            memory_dir="memory",
            backups_dir="backups",

            # File settings
            file_format="jsonl",          # JSON Lines for streaming
            compression="gzip",           # Compress old files
            rotation_size="100MB",        # Rotate files at 100MB
            retention_days=30,            # Keep files for 30 days

            # Backup settings
            auto_backup=True,
            backup_interval=3600,         # Hourly backups
            backup_copies=7               # Keep 7 backup copies
        )

        file_memory = ChatMemory(
            storage=file_storage,
            max_messages=5000,
            compress_when_full=True,

            # File-specific settings
            flush_interval=60,            # Write to disk every minute
            sync_writes=True,             # Sync writes to disk
            file_locking=True             # Prevent concurrent writes
        )

        agent = Agent(
            model=self._get_model(),
            memory=file_memory,
            instructions=self._get_instructions(),
            persist_sessions=True
        )

        logger.info("Created file-persistent Agno agent")
        return agent

    def _get_model(self):
        """Get configured model for agents."""
        from agno.models.openrouter import OpenRouter
        return OpenRouter(id=self.settings.default_model)

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
            "recommended": "file",
            "description": "File-based storage for easy development",
            "backup_frequency": "hourly",
            "retention": "7 days"
        },

        "staging": {
            "recommended": "redis",
            "description": "Redis with persistence for testing",
            "backup_frequency": "every 4 hours",
            "retention": "14 days"
        },

        "production_small": {
            "recommended": "hybrid_redis_vector",
            "description": "Redis + vector DB for production",
            "backup_frequency": "hourly",
            "retention": "30 days"
        },

        "production_enterprise": {
            "recommended": "database",
            "description": "PostgreSQL for enterprise compliance",
            "backup_frequency": "every 15 minutes",
            "retention": "1 year"
        },

        "production_scale": {
            "recommended": "hybrid_multi_vector",
            "description": "Multiple vector DBs with Redis cache",
            "backup_frequency": "continuous",
            "retention": "unlimited"
        }
    }

    @classmethod
    def get_recommendation(cls, environment: str, requirements: list = None) -> dict:
        """Get persistence strategy recommendation."""

        base_strategy = cls.STRATEGIES.get(environment, cls.STRATEGIES["development"])

        # Modify based on requirements
        if requirements:
            if "compliance" in requirements:
                base_strategy["recommended"] = "database"
                base_strategy["backup_frequency"] = "every 15 minutes"

            if "high_volume" in requirements:
                base_strategy["recommended"] = "hybrid_multi_vector"
                base_strategy["retention"] = "6 months"

            if "cost_sensitive" in requirements:
                base_strategy["recommended"] = "file"
                base_strategy["retention"] = "14 days"

        return base_strategy


# Production configuration examples
def get_production_memory_config(settings: Any) -> dict:
    """Get production-ready memory configuration."""

    return {
        # Redis configuration for chat memory
        "redis": {
            "host": settings.redis_host,
            "port": settings.redis_port,
            "password": settings.get_secret("redis_password"),
            "db": 0,

            # Redis persistence settings
            "save": "900 1 300 10 60 10000",  # Save snapshots
            "appendonly": "yes",               # Enable AOF
            "appendfsync": "everysec",         # Sync every second
            "auto-aof-rewrite-percentage": 100,
            "auto-aof-rewrite-min-size": "64mb"
        },

        # Vector database for long-term memory
        "vector_db": {
            "provider": settings.vector_database,
            "backup_enabled": True,
            "replication_factor": 3,           # For high availability
            "snapshot_frequency": "4h",
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
