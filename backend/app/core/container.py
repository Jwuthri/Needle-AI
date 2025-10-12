"""
Dependency Injection Container for NeedleAi.
"""

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Any, AsyncGenerator, Callable, Dict, Optional, Type, TypeVar

from app.exceptions import ConfigurationError
from app.utils.logging import get_logger

logger = get_logger("container")

T = TypeVar("T")


class ServiceLifetime(str, Enum):
    """Service lifetime scope."""
    SINGLETON = "singleton"
    SCOPED = "scoped"
    TRANSIENT = "transient"


@dataclass
class ServiceDescriptor:
    """Service registration descriptor."""
    service_type: Type
    implementation: Type
    lifetime: ServiceLifetime
    factory: Optional[Callable] = None
    instance: Optional[Any] = None


class DIContainer:
    """Dependency Injection Container with proper lifecycle management."""

    def __init__(self):
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._singletons: Dict[Type, Any] = {}
        self._scoped_services: Dict[Type, Any] = {}
        self._initialized_services: set = set()
        self._is_disposing = False

    def register_singleton(
        self,
        service_type: Type[T],
        implementation: Optional[Type[T]] = None,
        factory: Optional[Callable[[], T]] = None
    ) -> "DIContainer":
        """Register a singleton service."""
        impl = implementation or service_type
        self._services[service_type] = ServiceDescriptor(
            service_type=service_type,
            implementation=impl,
            lifetime=ServiceLifetime.SINGLETON,
            factory=factory
        )
        return self

    def register_scoped(
        self,
        service_type: Type[T],
        implementation: Optional[Type[T]] = None,
        factory: Optional[Callable[[], T]] = None
    ) -> "DIContainer":
        """Register a scoped service (per-request)."""
        impl = implementation or service_type
        self._services[service_type] = ServiceDescriptor(
            service_type=service_type,
            implementation=impl,
            lifetime=ServiceLifetime.SCOPED,
            factory=factory
        )
        return self

    def register_transient(
        self,
        service_type: Type[T],
        implementation: Optional[Type[T]] = None,
        factory: Optional[Callable[[], T]] = None
    ) -> "DIContainer":
        """Register a transient service (new instance every time)."""
        impl = implementation or service_type
        self._services[service_type] = ServiceDescriptor(
            service_type=service_type,
            implementation=impl,
            lifetime=ServiceLifetime.TRANSIENT,
            factory=factory
        )
        return self

    async def get_service(self, service_type: Type[T]) -> T:
        """Get a service instance."""
        if self._is_disposing:
            raise RuntimeError("Container is being disposed")

        descriptor = self._services.get(service_type)
        if not descriptor:
            raise ValueError(f"Service {service_type.__name__} not registered")

        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            return await self._get_singleton(descriptor)
        elif descriptor.lifetime == ServiceLifetime.SCOPED:
            return await self._get_scoped(descriptor)
        else:  # TRANSIENT
            return await self._create_instance(descriptor)

    async def _get_singleton(self, descriptor: ServiceDescriptor) -> Any:
        """Get or create singleton instance."""
        if descriptor.service_type in self._singletons:
            return self._singletons[descriptor.service_type]

        instance = await self._create_instance(descriptor)
        self._singletons[descriptor.service_type] = instance
        self._initialized_services.add(descriptor.service_type)
        return instance

    async def _get_scoped(self, descriptor: ServiceDescriptor) -> Any:
        """Get or create scoped instance."""
        if descriptor.service_type in self._scoped_services:
            return self._scoped_services[descriptor.service_type]

        instance = await self._create_instance(descriptor)
        self._scoped_services[descriptor.service_type] = instance
        return instance

    async def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """Create service instance using factory or constructor."""
        try:
            if descriptor.factory:
                instance = descriptor.factory()
                if asyncio.iscoroutine(instance):
                    instance = await instance
            else:
                instance = descriptor.implementation()

            # Initialize if it has an async init method
            if hasattr(instance, 'initialize') and callable(instance.initialize):
                await instance.initialize()

            return instance

        except Exception as e:
            logger.error(f"Failed to create instance of {descriptor.service_type.__name__}: {e}")
            raise

    @asynccontextmanager
    async def scope(self) -> AsyncGenerator["DIContainer", None]:
        """Create a new scope for scoped services."""
        old_scoped = self._scoped_services.copy()
        self._scoped_services.clear()

        try:
            yield self
        finally:
            # Cleanup scoped services
            for service in self._scoped_services.values():
                if hasattr(service, 'cleanup') and callable(service.cleanup):
                    try:
                        await service.cleanup()
                    except Exception as e:
                        logger.warning(f"Error cleaning up scoped service: {e}")

            self._scoped_services = old_scoped

    async def dispose(self):
        """Dispose all services and cleanup resources."""
        self._is_disposing = True

        # Dispose singletons in reverse order of creation
        for service_type in reversed(list(self._initialized_services)):
            service = self._singletons.get(service_type)
            if service and hasattr(service, 'cleanup') and callable(service.cleanup):
                try:
                    await service.cleanup()
                    logger.debug(f"Cleaned up {service_type.__name__}")
                except Exception as e:
                    logger.error(f"Error disposing {service_type.__name__}: {e}")

        self._singletons.clear()
        self._scoped_services.clear()
        self._initialized_services.clear()
        self._is_disposing = False

        logger.info("All services disposed successfully")


# Global container instance
_container: Optional[DIContainer] = None


def get_container() -> DIContainer:
    """Get the global DI container."""
    global _container
    if _container is None:
        _container = DIContainer()
        _configure_services(_container)
    return _container


def _configure_services(container: DIContainer):
    """
    Configure all services in the DI container.
    
    Architecture:
    - PostgreSQL for persistent data
    - Redis for caching, sessions, and Celery broker
    - Celery for background tasks (scraping, sentiment, indexing)
    - WebSocket for real-time updates
    """
    from app.core.memory.base import MemoryInterface
    from app.database.repositories import (
        ApiKeyRepository,
        ChatMessageRepository,
        ChatSessionRepository,
        TaskResultRepository,
        UserRepository,
    )
    from app.services.conversation_service import ConversationService
    from app.services.redis_client import RedisClient

    # Register infrastructure services as singletons
    container.register_singleton(RedisClient)

    # Register repositories as scoped (per-request)
    container.register_scoped(UserRepository)
    container.register_scoped(ChatSessionRepository)
    container.register_scoped(ChatMessageRepository)
    container.register_scoped(ApiKeyRepository)
    container.register_scoped(TaskResultRepository)

    # Register business services as scoped
    # Note: Using string key for ChatService since we use different implementations
    container._services["ChatService"] = ServiceDescriptor(
        service_type=object,  # Generic type since we use protocol
        implementation=None,
        lifetime=ServiceLifetime.SCOPED,
        factory=_create_chat_service
    )
    container.register_scoped(ConversationService)
    container.register_scoped(MemoryInterface, factory=_create_memory_store)

    logger.info("All services registered in DI container")


async def _create_chat_service():
    """Factory for ChatService using Agno-first approach with fallbacks."""
    from app.config import get_settings
    from app.core.memory.base import MemoryInterface
    from app.services.chat_service_factory import create_chat_service_from_settings

    container = get_container()
    settings = get_settings()

    # Try to get dependencies for custom service fallback
    memory_store = None
    llm_service = None

    try:
        memory_store = await container.get_service(MemoryInterface)
    except Exception as e:
        logger.debug(f"Memory store not available: {e}")

    try:
        from app.core.llm.factory import get_llm_client
        llm_service = get_llm_client(settings.llm_provider, settings)
    except Exception as e:
        logger.debug(f"LLM service not available: {e}")

    # Use the chat service factory with automatic selection
    chat_service = await create_chat_service_from_settings(
        settings=settings,
        memory_store=memory_store,
        llm_service=llm_service
    )

    logger.info(f"Created chat service: {chat_service.__class__.__name__}")
    return chat_service


async def _create_memory_store():
    """Factory for memory store using Agno-first approach with fallbacks."""
    from app.config import get_settings
    from app.core.memory.factory import create_memory_from_settings
    from app.services.redis_client import RedisClient

    container = get_container()
    settings = get_settings()

    # Try to get Redis client for providers that need it
    redis_client = None
    try:
        redis_client = await container.get_service(RedisClient)
        logger.debug("Redis client available for memory store")
    except Exception as e:
        logger.debug(f"Redis client not available: {e}")

    try:
        # Use the new Agno-first memory factory
        memory_store = await create_memory_from_settings(settings, redis_client)
        logger.info(f"Created memory store: {memory_store.__class__.__name__}")
        return memory_store
    except Exception as e:
        logger.error(f"Failed to create configured memory store: {e}")

        # Ultimate fallback to in-memory store
        try:
            from app.core.memory.in_memory import InMemoryStore
            logger.warning("Falling back to in-memory store")
            return InMemoryStore()
        except Exception as fallback_error:
            logger.error(f"Even fallback memory store failed: {fallback_error}")
            raise ConfigurationError(f"No memory store could be created: {e}")
