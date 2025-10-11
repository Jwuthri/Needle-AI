"""
Chat Service Factory - Choose between Agno and custom implementations.
"""

from enum import Enum
from typing import Any, Optional, Protocol

from app.exceptions import ConfigurationError
from app.utils.logging import get_logger

logger = get_logger("chat_service_factory")


class ChatServiceType(str, Enum):
    """Available chat service types."""
    AGNO = "agno"
    CUSTOM = "custom"
    AUTO = "auto"  # Automatically choose best available


class ChatServiceProtocol(Protocol):
    """Protocol that all chat services must implement."""

    async def initialize(self) -> None:
        """Initialize the chat service."""
        ...

    async def cleanup(self) -> None:
        """Cleanup chat service resources."""
        ...

    async def process_message(self, request: Any, user_id: Optional[str] = None) -> Any:
        """Process a chat message."""
        ...

    async def health_check(self) -> bool:
        """Check if the chat service is healthy."""
        ...


class ChatServiceFactory:
    """
    Factory for creating chat services with automatic fallback logic.

    Priority:
    1. Agno-based service (if available and configured)
    2. Custom service (fallback)
    """

    @classmethod
    async def create_chat_service(
        cls,
        settings: Any,
        service_type: ChatServiceType = ChatServiceType.AUTO,
        memory_store: Optional[Any] = None,
        llm_service: Optional[Any] = None
    ) -> ChatServiceProtocol:
        """
        Create a chat service instance.

        Args:
            settings: Application settings
            service_type: Preferred service type (auto, agno, custom)
            memory_store: Memory store instance (for custom service)
            llm_service: LLM service instance (for custom service)

        Returns:
            Chat service instance
        """
        # Determine which service to create
        use_agno = await cls._should_use_agno(settings, service_type)

        if use_agno:
            try:
                service = await cls._create_agno_service(settings)
                logger.info("Created Agno-based chat service")
                return service
            except Exception as e:
                if service_type == ChatServiceType.AGNO:
                    # User specifically requested Agno, don't fallback
                    raise ConfigurationError(f"Failed to create Agno chat service: {e}")

                logger.warning(f"Agno service creation failed, falling back to custom: {e}")

        # Create custom service
        service = await cls._create_custom_service(settings, memory_store, llm_service)
        logger.info("Created custom chat service")
        return service

    @classmethod
    async def _should_use_agno(cls, settings: Any, service_type: ChatServiceType) -> bool:
        """Determine if Agno service should be used."""
        # Check explicit service type preference
        if service_type == ChatServiceType.AGNO:
            return True
        elif service_type == ChatServiceType.CUSTOM:
            return False

        # AUTO mode - check if Agno is available and properly configured

        # 1. Check if Agno agents are enabled in settings
        if not getattr(settings, "use_agno_agents", False):
            logger.debug("Agno agents disabled in settings")
            return False

        # 2. Check if Agno package is available
        try:
            logger.debug("Agno package is available")
        except ImportError:
            logger.debug("Agno package not available")
            return False

        # 3. Check if required API keys are configured
        if settings.llm_provider == "openrouter":
            if not settings.get_secret("openrouter_api_key"):
                logger.debug("OpenRouter API key not configured")
                return False
        else:
            if not settings.get_secret("openai_api_key"):
                logger.debug("OpenAI API key not configured")
                return False

        # 4. Check vector database configuration if memory is enabled
        if getattr(settings, "use_agno_memory", False):
            vector_db = getattr(settings, "vector_database", "").lower()
            if vector_db and vector_db != "none":
                if not cls._validate_vector_db_config(settings, vector_db):
                    logger.debug(f"Vector database {vector_db} not properly configured")
                    return False

        logger.debug("All conditions met for Agno service")
        return True

    @classmethod
    def _validate_vector_db_config(cls, settings: Any, vector_db: str) -> bool:
        """Validate vector database configuration."""
        if vector_db == "pinecone":
            return bool(
                settings.get_secret("pinecone_api_key") and
                getattr(settings, "pinecone_index_name", None)
            )
        elif vector_db == "weaviate":
            return bool(getattr(settings, "weaviate_url", None))
        elif vector_db == "qdrant":
            return bool(
                getattr(settings, "qdrant_url", None) and
                getattr(settings, "qdrant_collection_name", None)
            )
        elif vector_db == "chromadb":
            return bool(
                getattr(settings, "chromadb_path", None) and
                getattr(settings, "chromadb_collection_name", None)
            )

        return False

    @classmethod
    async def _create_agno_service(cls, settings: Any) -> ChatServiceProtocol:
        """Create Agno-based chat service."""
        from app.services.agno_chat_service import AgnoChatService

        service = AgnoChatService(settings)
        await service.initialize()
        return service

    @classmethod
    async def _create_custom_service(
        cls,
        settings: Any,
        memory_store: Optional[Any] = None,
        llm_service: Optional[Any] = None
    ) -> ChatServiceProtocol:
        """Create custom chat service."""
        from app.services.chat_service import ChatService

        # If dependencies not provided, we need to create them
        if not memory_store or not llm_service:
            # This is a fallback - in production, these should be provided by DI
            logger.warning("Creating chat service without proper dependencies")

            if not memory_store:
                from app.core.memory import create_memory_from_settings
                memory_store = await create_memory_from_settings(settings)

            if not llm_service:
                from app.core.llm.factory import get_llm_client
                llm_service = get_llm_client(settings.llm_provider, settings)

        service = ChatService(
            memory_store=memory_store,
            llm_service=llm_service,
            settings=settings
        )

        # Initialize if the service has an initialize method
        if hasattr(service, 'initialize'):
            await service.initialize()

        return service

    @classmethod
    def get_recommended_service_type(cls, settings: Any) -> ChatServiceType:
        """Get recommended service type based on configuration."""
        # Check if user has explicitly configured Agno
        if getattr(settings, "use_agno_agents", False):
            try:
                return ChatServiceType.AGNO
            except ImportError:
                pass

        # Check if vector database is configured (Agno handles these better)
        vector_db = getattr(settings, "vector_database", "").lower()
        if vector_db and vector_db not in ["none", "redis", "in-memory"]:
            try:
                return ChatServiceType.AGNO
            except ImportError:
                pass

        # Default to custom service
        return ChatServiceType.CUSTOM

    @classmethod
    def get_service_capabilities(cls, service_type: ChatServiceType, settings: Any) -> dict:
        """Get capabilities for a service type."""
        if service_type == ChatServiceType.AGNO:
            return {
                "provider": "agno",
                "memory_management": "automatic",
                "vector_search": True,
                "multi_agent": True,
                "structured_outputs": True,
                "conversation_persistence": True,
                "semantic_search": True,
                "supported_models": "all_openai_compatible",
                "supported_vector_dbs": ["pinecone", "weaviate", "qdrant", "chromadb"],
            }
        else:
            return {
                "provider": "custom",
                "memory_management": "manual",
                "vector_search": bool(getattr(settings, "vector_database", "") != "none"),
                "multi_agent": False,
                "structured_outputs": False,
                "conversation_persistence": True,
                "semantic_search": bool(getattr(settings, "vector_database", "") != "none"),
                "supported_models": ["openrouter", "custom"],
                "supported_vector_dbs": ["pinecone", "weaviate", "redis", "in-memory"],
            }

    @classmethod
    async def validate_service_config(
        cls,
        service_type: ChatServiceType,
        settings: Any
    ) -> dict:
        """Validate configuration for a service type."""
        validation = {
            "service_type": service_type,
            "valid": True,
            "errors": [],
            "warnings": [],
            "recommendations": []
        }

        if service_type == ChatServiceType.AGNO:
            # Validate Agno-specific requirements
            try:
                pass
            except ImportError:
                validation["errors"].append("Agno package not installed")
                validation["valid"] = False

            if not getattr(settings, "use_agno_agents", False):
                validation["warnings"].append("use_agno_agents is disabled")

            # Validate API keys
            if settings.llm_provider == "openrouter":
                if not settings.get_secret("openrouter_api_key"):
                    validation["errors"].append("OpenRouter API key required")
            else:
                if not settings.get_secret("openai_api_key"):
                    validation["errors"].append("OpenAI API key required")

        elif service_type == ChatServiceType.CUSTOM:
            # Validate custom service requirements
            if settings.llm_provider not in ["openrouter", "custom"]:
                validation["warnings"].append(f"LLM provider {settings.llm_provider} may not be supported")

        # Common validations
        if not getattr(settings, "default_model", None):
            validation["errors"].append("default_model not configured")

        validation["valid"] = len(validation["errors"]) == 0

        # Add recommendations
        if service_type == ChatServiceType.AUTO:
            recommended = cls.get_recommended_service_type(settings)
            validation["recommendations"].append(f"Recommended service type: {recommended}")

        return validation


# Convenience functions

async def create_chat_service_from_settings(
    settings: Any,
    memory_store: Optional[Any] = None,
    llm_service: Optional[Any] = None
) -> ChatServiceProtocol:
    """Create chat service based on settings (convenience function)."""
    return await ChatServiceFactory.create_chat_service(
        settings=settings,
        service_type=ChatServiceType.AUTO,
        memory_store=memory_store,
        llm_service=llm_service
    )


async def create_agno_chat_service(settings: Any) -> ChatServiceProtocol:
    """Create Agno chat service only (no fallback)."""
    return await ChatServiceFactory.create_chat_service(
        settings=settings,
        service_type=ChatServiceType.AGNO
    )


async def create_custom_chat_service(
    settings: Any,
    memory_store: Any,
    llm_service: Any
) -> ChatServiceProtocol:
    """Create custom chat service only."""
    return await ChatServiceFactory.create_chat_service(
        settings=settings,
        service_type=ChatServiceType.CUSTOM,
        memory_store=memory_store,
        llm_service=llm_service
    )
