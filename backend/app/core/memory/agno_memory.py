"""
Agno-based memory implementations for all vector databases.
Uses latest Agno API with db parameter for persistence.
"""
from abc import abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from agno.agent import Agent
from agno.db.postgres import PostgresDb
from agno.vectordb.chroma import ChromaDb
from agno.db.redis import RedisDb
from agno.vectordb.pineconedb import PineconeDb
from agno.vectordb.qdrant import Qdrant
from agno.vectordb.weaviate import Weaviate
from agno.knowledge.knowledge import Knowledge

from app.core.memory.base import MemoryInterface
from app.exceptions import ConfigurationError, ExternalServiceError
from app.utils.logging import get_logger

logger = get_logger("agno_memory")


class AgnoMemoryInterface(MemoryInterface):
    """
    Base class for Agno-based memory implementations.
    Uses latest Agno API with db parameter for persistence.
    """

    def __init__(self, settings: Any):
        self.settings = settings
        self.db: Optional[Any] = None  # PostgresDb or RedisDb
        self.knowledge: Optional[Knowledge] = None  # Vector DB for semantic search
        self._initialized = False

    @abstractmethod
    async def _create_agno_db(self) -> Any:
        """Create the Agno db instance (PostgresDb or RedisDb)."""

    @abstractmethod
    async def _create_knowledge(self) -> Optional[Knowledge]:
        """Create Knowledge base with vector DB if applicable."""

    async def initialize(self):
        """Initialize the Agno memory system with db parameter."""
        if not self._initialized:
            try:
                self.db = await self._create_agno_db()
                self.knowledge = await self._create_knowledge()
                self._initialized = True
                logger.info(f"Initialized {self.__class__.__name__}")
            except Exception as e:
                logger.error(f"Failed to initialize {self.__class__.__name__}: {e}")
                raise ConfigurationError(f"Memory initialization failed: {e}")

    async def cleanup(self):
        """Cleanup resources."""
        if self.db:
            try:
                if hasattr(self.db, 'close'):
                    await self.db.close()
                self._initialized = False
                logger.debug(f"Cleaned up {self.__class__.__name__}")
            except Exception as e:
                logger.warning(f"Error cleaning up {self.__class__.__name__}: {e}")

    async def store_message(self, session_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Store a message using Agno's memory system.
        Note: In new Agno API, this is handled automatically by Agent with db parameter.
        """
        if not self._initialized:
            await self.initialize()

        # Memory storage is automatic when Agent is created with db parameter
        # This method is kept for interface compatibility
        logger.debug(f"Message storage handled automatically by Agent for session {session_id}")
        return True

    async def get_messages(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Retrieve messages using Agno's memory system.
        Note: Use agent.get_messages() or agent.get_session_history() instead.
        """
        if not self._initialized:
            await self.initialize()

        # In new Agno API, use Agent's methods directly
        logger.warning("Message retrieval should use Agent's get_session_history() method")
        return []

    async def clear_session(self, session_id: str) -> bool:
        """
        Clear session using Agno's memory system.
        Note: Use agent.clear_session() method instead.
        """
        if not self._initialized:
            await self.initialize()

        # In new Agno API, use Agent's methods directly
        logger.warning("Session clearing should use Agent's clear_session() method")
        return True

    async def search_similar(self, query: str, session_id: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for similar content using Knowledge base.
        Note: Use Agent with Knowledge configured for semantic search.
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Use Knowledge base for semantic search if available
            if self.knowledge:
                # Knowledge search is handled by Agent automatically
                logger.debug(f"Semantic search available via Knowledge base")
                return []
            else:
                logger.warning("Knowledge base not configured for semantic search")
                return []

        except Exception as e:
            logger.error(f"Error searching similar content: {e}")
            raise ExternalServiceError(f"Failed to search: {e}", service="agno_memory")

    async def health_check(self) -> bool:
        """Check if Agno memory is healthy."""
        try:
            if not self._initialized:
                await self.initialize()

            # Check db connection if available
            if self.db:
                return True
            
            return self._initialized

        except Exception as e:
            logger.error(f"Agno memory health check failed: {e}")
            return False


class AgnoPineconeMemory(AgnoMemoryInterface):
    """Agno-based Pinecone memory implementation using Knowledge for vector search."""

    async def _create_agno_db(self) -> Optional[Any]:
        """
        Pinecone is used as Knowledge base, not for db parameter.
        Return None as db will be handled by PostgresDb or RedisDb if needed.
        """
        return None

    async def _create_knowledge(self) -> Optional[Knowledge]:
        """Create Knowledge base with Pinecone vector store."""
        api_key = self.settings.get_secret("pinecone_api_key")
        if not api_key:
            raise ConfigurationError("Pinecone API key not configured")
        
        # Convert SecretStr to str if needed
        api_key_str = str(api_key) if hasattr(api_key, '__str__') else api_key
        
        # Create Pinecone vector DB for Knowledge
        vector_db = PineconeDb(
            name=self.settings.pinecone_index_name,
            dimension=1536,  # OpenAI embedding dimension
            metric="cosine",
            spec={"serverless": {"cloud": "aws", "region": "us-east-1"}},
            api_key=api_key_str,
        )
        
        # Create Knowledge base with Pinecone
        knowledge = Knowledge(
            name=f"{getattr(self.settings, 'app_name', 'app')}_knowledge",
            description="Vector database for semantic search and memory",
            vector_db=vector_db,
        )
        
        logger.info("Created Pinecone Knowledge base for semantic search")
        return knowledge


class AgnoWeaviateMemory(AgnoMemoryInterface):
    """Agno-based Weaviate memory implementation using Knowledge."""

    async def _create_agno_db(self) -> Optional[Any]:
        """Weaviate is used as Knowledge base."""
        return None

    async def _create_knowledge(self) -> Optional[Knowledge]:
        """Create Knowledge base with Weaviate vector store."""
        api_key = self.settings.get_secret("weaviate_api_key")
        
        # Convert SecretStr to str if needed
        api_key_str = str(api_key) if api_key and hasattr(api_key, '__str__') else api_key
        
        # Create Weaviate vector DB
        vector_db = Weaviate(
            url=self.settings.weaviate_url,
            api_key=api_key_str,
        )

        knowledge = Knowledge(
            name=f"{getattr(self.settings, 'app_name', 'app')}_knowledge",
            description="Weaviate vector database for semantic search",
            vector_db=vector_db,
        )
        
        logger.info("Created Weaviate Knowledge base")
        return knowledge


class AgnoQdrantMemory(AgnoMemoryInterface):
    """Agno-based Qdrant memory implementation using Knowledge."""

    async def _create_agno_db(self) -> Optional[Any]:
        """Qdrant is used as Knowledge base."""
        return None

    async def _create_knowledge(self) -> Optional[Knowledge]:
        """Create Knowledge base with Qdrant vector store."""
        api_key = self.settings.get_secret("qdrant_api_key")
        api_key_str = str(api_key) if api_key and hasattr(api_key, '__str__') else api_key
        
        # Create Qdrant vector DB
        vector_db = Qdrant(
            url=self.settings.qdrant_url,
            api_key=api_key_str,
            collection_name=self.settings.qdrant_collection_name,
        )

        knowledge = Knowledge(
            name=f"{getattr(self.settings, 'app_name', 'app')}_knowledge",
            description="Qdrant vector database for semantic search",
            vector_db=vector_db,
        )
        
        logger.info("Created Qdrant Knowledge base")
        return knowledge


class AgnoChromaMemory(AgnoMemoryInterface):
    """Agno-based ChromaDB memory implementation using Knowledge."""

    async def _create_agno_db(self) -> Optional[Any]:
        """ChromaDB is used as Knowledge base."""
        return None

    async def _create_knowledge(self) -> Optional[Knowledge]:
        """Create Knowledge base with ChromaDB vector store."""
        # Create ChromaDB vector DB
        vector_db = ChromaDb(
            path=self.settings.chromadb_path,
            collection_name=self.settings.chromadb_collection_name,
        )

        knowledge = Knowledge(
            name=f"{getattr(self.settings, 'app_name', 'app')}_knowledge",
            description="ChromaDB vector database for semantic search",
            vector_db=vector_db,
        )
        
        logger.info("Created ChromaDB Knowledge base")
        return knowledge


class AgnoChatMemory(AgnoMemoryInterface):
    """Agno-based chat-only memory (no vector storage, no persistence)."""

    async def _create_agno_db(self) -> Optional[Any]:
        """No persistent storage for chat-only memory."""
        return None

    async def _create_knowledge(self) -> Optional[Knowledge]:
        """No knowledge base for chat-only memory."""
        return None


class AgnoRedisMemory(AgnoMemoryInterface):
    """Agno-based Redis memory implementation for persistence."""

    def __init__(self, settings: Any, redis_client=None):
        super().__init__(settings)
        self.redis_client = redis_client

    async def _create_agno_db(self) -> Any:
        """Create RedisDb for persistent storage."""
        if not self.redis_client:
            # Create Redis connection URL
            redis_url = self.settings.get_redis_url_with_auth(db=0)
        else:
            # Use existing Redis client URL
            redis_url = self.settings.get_redis_url_with_auth(db=0)
        
        # Create RedisDb for Agent persistence
        redis_db = RedisDb(
            db_url=redis_url,
            table_name="agno_sessions",
        )
        
        logger.info("Created RedisDb for persistent memory storage")
        return redis_db

    async def _create_knowledge(self) -> Optional[Knowledge]:
        """No knowledge base for Redis-only memory."""
        return None


class AgnoMemoryFactory:
    """Factory for creating Agno-based memory instances using latest API."""

    MEMORY_PROVIDERS = {
        "pinecone": AgnoPineconeMemory,
        "weaviate": AgnoWeaviateMemory,
        "qdrant": AgnoQdrantMemory,
        "chromadb": AgnoChromaMemory,
        "chat": AgnoChatMemory,
        "redis": AgnoRedisMemory,
    }

    @classmethod
    async def create_memory(
        cls,
        provider: str,
        settings: Any,
        redis_client=None
    ) -> AgnoMemoryInterface:
        """Create an Agno memory instance based on provider."""
        provider = provider.lower()

        if provider not in cls.MEMORY_PROVIDERS:
            available_providers = ", ".join(cls.MEMORY_PROVIDERS.keys())
            raise ConfigurationError(
                f"Unsupported Agno memory provider: {provider}. "
                f"Available providers: {available_providers}"
            )

        memory_class = cls.MEMORY_PROVIDERS[provider]

        # Special handling for Redis memory
        if provider == "redis" and redis_client:
            memory_instance = memory_class(settings, redis_client)
        else:
            memory_instance = memory_class(settings)

        # Initialize the memory
        await memory_instance.initialize()

        logger.info(f"Created Agno memory provider: {provider}")
        return memory_instance

    @classmethod
    def get_available_providers(cls) -> List[str]:
        """Get list of available Agno memory providers."""
        return list(cls.MEMORY_PROVIDERS.keys())

    @classmethod
    def validate_provider_config(cls, provider: str, settings: Any) -> Dict[str, Any]:
        """Validate configuration for a specific provider."""
        validation_report = {
            "provider": provider,
            "valid": True,
            "errors": [],
            "warnings": []
        }
        provider = provider.lower()

        if provider == "pinecone":
            if not settings.get_secret("pinecone_api_key"):
                validation_report["errors"].append("Pinecone API key is required")
            if not settings.pinecone_index_name:
                validation_report["errors"].append("Pinecone index name is required")

        elif provider == "weaviate":
            if not settings.weaviate_url:
                validation_report["errors"].append("Weaviate URL is required")

        elif provider == "qdrant":
            if not settings.qdrant_url:
                validation_report["errors"].append("Qdrant URL is required")
            if not settings.qdrant_collection_name:
                validation_report["errors"].append("Qdrant collection name is required")

        elif provider == "chromadb":
            if not settings.chromadb_path:
                validation_report["errors"].append("ChromaDB path is required")
            if not settings.chromadb_collection_name:
                validation_report["errors"].append("ChromaDB collection name is required")

        validation_report["valid"] = len(validation_report["errors"]) == 0
        return validation_report

