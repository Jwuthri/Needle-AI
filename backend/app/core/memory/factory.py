"""
Memory factory with Agno-first approach and custom fallbacks.
"""

from enum import Enum
from typing import Any, Dict, Optional

from app.core.memory.base import MemoryInterface
from app.exceptions import ConfigurationError, ExternalServiceError
from app.utils.logging import get_logger

logger = get_logger("memory_factory")


class MemoryProvider(str, Enum):
    """Available memory providers."""
    AGNO_PINECONE = "agno_pinecone"
    AGNO_WEAVIATE = "agno_weaviate"
    AGNO_QDRANT = "agno_qdrant"
    AGNO_CHROMADB = "agno_chromadb"
    AGNO_CHAT = "agno_chat"
    AGNO_REDIS = "agno_redis"

    # Fallback custom implementations (simple ones only)
    CUSTOM_REDIS = "custom_redis"
    CUSTOM_IN_MEMORY = "custom_in_memory"


class MemoryFactory:
    """
    Smart memory factory that prioritizes Agno implementations
    with fallback to custom implementations.
    """

    # Provider mapping - only custom implementations
    # Vector DBs are configured directly via agno Agent.knowledge, not via memory store
    PROVIDER_MAPPING = {
        "pinecone": [MemoryProvider.CUSTOM_IN_MEMORY],     # Pinecone via agno Agent.knowledge
        "weaviate": [MemoryProvider.CUSTOM_IN_MEMORY],     # Weaviate via agno Agent.knowledge
        "qdrant": [MemoryProvider.CUSTOM_IN_MEMORY],       # Qdrant via agno Agent.knowledge
        "chromadb": [MemoryProvider.CUSTOM_IN_MEMORY],     # ChromaDB via agno Agent.knowledge
        "redis": [MemoryProvider.CUSTOM_REDIS],            # Custom Redis
        "in-memory": [MemoryProvider.CUSTOM_IN_MEMORY],    # In-memory fallback
        "chat": [MemoryProvider.CUSTOM_IN_MEMORY],         # Chat via agno Agent
    }

    @classmethod
    async def create_memory(
        self,
        provider: str,
        settings: Any,
        redis_client: Optional[Any] = None,
        force_custom: bool = False
    ) -> MemoryInterface:
        """
        Create memory instance with Agno-first approach.

        Args:
            provider: Memory provider name (pinecone, weaviate, etc.)
            settings: Application settings
            redis_client: Redis client instance (if available)
            force_custom: Force use of custom implementations

        Returns:
            MemoryInterface instance
        """
        provider = provider.lower().replace("_", "-")

        if provider not in self.PROVIDER_MAPPING:
            available = ", ".join(self.PROVIDER_MAPPING.keys())
            raise ConfigurationError(f"Unsupported memory provider: {provider}. Available: {available}")

        # Get provider priority list
        provider_options = self.PROVIDER_MAPPING[provider]

        # If force_custom is True, skip Agno providers
        if force_custom:
            provider_options = [p for p in provider_options if not p.value.startswith("agno_")]

        # Try each provider in order
        last_error = None
        for provider_option in provider_options:
            try:
                memory_instance = await self._create_provider_instance(
                    provider_option, settings, redis_client
                )

                # Test the instance
                if await memory_instance.health_check():
                    logger.info(f"Successfully created memory provider: {provider_option.value}")
                    return memory_instance
                else:
                    logger.warning(f"Memory provider {provider_option.value} failed health check")

            except Exception as e:
                logger.warning(f"Failed to create {provider_option.value}: {e}")
                last_error = e
                continue

        # If all providers failed
        raise ExternalServiceError(
            f"All memory providers failed for '{provider}'. Last error: {last_error}",
            service="memory_factory"
        )

    @classmethod
    async def _create_provider_instance(
        cls,
        provider_option: MemoryProvider,
        settings: Any,
        redis_client: Optional[Any] = None
    ) -> MemoryInterface:
        """Create a specific memory provider instance."""

        # Only custom implementations (agno memory wrappers deprecated)
        if provider_option == MemoryProvider.CUSTOM_REDIS:
            from app.core.memory.redis_memory import RedisMemory
            if not redis_client:
                raise ConfigurationError("Redis client required for Redis memory")
            return RedisMemory(redis_client)

        elif provider_option == MemoryProvider.CUSTOM_IN_MEMORY:
            from app.core.memory.in_memory import InMemoryStore
            return InMemoryStore()

        else:
            raise ConfigurationError(f"Unknown memory provider: {provider_option}")

    @classmethod
    def get_available_providers(cls) -> Dict[str, Dict[str, Any]]:
        """Get information about available memory providers."""
        providers_info = {}

        for provider_name, provider_options in cls.PROVIDER_MAPPING.items():
            agno_providers = [p for p in provider_options if p.value.startswith("agno_")]
            custom_providers = [p for p in provider_options if p.value.startswith("custom_")]

            providers_info[provider_name] = {
                "agno_available": len(agno_providers) > 0,
                "custom_fallback": len(custom_providers) > 0,
                "agno_providers": [p.value for p in agno_providers],
                "custom_providers": [p.value for p in custom_providers],
                "recommended": agno_providers[0].value if agno_providers else custom_providers[0].value
            }

        return providers_info

    @classmethod
    async def validate_provider_config(cls, provider: str, settings: Any) -> Dict[str, Any]:
        """Validate configuration for a memory provider."""
        provider = provider.lower().replace("_", "-")

        validation_report = {
            "provider": provider,
            "valid": True,
            "errors": [],
            "warnings": [],
            "agno_available": False,
            "custom_available": False
        }

        if provider not in cls.PROVIDER_MAPPING:
            validation_report["errors"].append(f"Unknown provider: {provider}")
            validation_report["valid"] = False
            return validation_report

        # Agno memory wrappers deprecated - vector DBs handled directly by agno Agent
        if provider not in ["redis", "in-memory"]:
            validation_report["warnings"].append(
                f"{provider} should be configured via agno Agent.knowledge, using in-memory for ConversationService"
            )

        # Check custom implementation availability
        custom_errors = cls._validate_custom_config(provider, settings)
        validation_report["custom_available"] = len(custom_errors) == 0

        if custom_errors:
            validation_report["warnings"].extend([
                f"Custom {provider}: {error}" for error in custom_errors
            ])

        # Overall validation
        if not validation_report["agno_available"] and not validation_report["custom_available"]:
            validation_report["valid"] = False
            validation_report["errors"].append(f"No valid implementation available for {provider}")

        return validation_report

    @classmethod
    def _validate_custom_config(cls, provider: str, settings: Any) -> list[str]:
        """Validate custom implementation configuration."""
        errors = []

        if provider == "redis":
            if not getattr(settings, "redis_url", None):
                errors.append("Redis URL missing")
        elif provider not in ["in-memory"]:
            # Vector DBs should be configured via agno Agent, not memory store
            pass

        return errors


# Convenience factory functions

async def create_memory_from_settings(settings: Any, redis_client: Optional[Any] = None) -> MemoryInterface:
    """Create memory instance based on settings configuration."""
    # Determine provider from settings
    memory_type = getattr(settings, "memory_type", "redis").lower()
    vector_database = getattr(settings, "vector_database", "").lower()

    # Priority: vector database > memory type > fallback
    if vector_database and vector_database != "none":
        provider = vector_database
    elif memory_type and memory_type != "vector":
        provider = memory_type
    else:
        provider = "redis"  # Safe fallback

    logger.info(f"Creating memory provider: {provider} (from memory_type={memory_type}, vector_database={vector_database})")

    return await MemoryFactory.create_memory(provider, settings, redis_client)


async def create_agno_memory_only(provider: str, settings: Any) -> MemoryInterface:
    """Deprecated - agno memory wrappers removed."""
    raise ConfigurationError(
        "Agno memory wrappers deprecated. Vector DBs should be configured via agno Agent.knowledge parameter"
    )


async def create_custom_memory_only(provider: str, settings: Any, redis_client: Optional[Any] = None) -> MemoryInterface:
    """Create custom memory only (no Agno)."""
    return await MemoryFactory.create_memory(provider, settings, redis_client, force_custom=True)


# Export main factory function
get_memory_store = create_memory_from_settings
