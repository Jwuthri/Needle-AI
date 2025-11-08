"""
FastAPI dependencies for dependency injection.
"""

from functools import lru_cache
from typing import Optional, Any

from app.services.orchestrator_service import OrchestratorService
from app.services.tree_orchestrator_service import TreeOrchestratorService
from app.services.hybrid_orchestrator_service import HybridOrchestratorService
from app.services.conversation_service import ConversationService
from app.services.redis_client import RedisClient
from app.core.container import get_container
from app.config import get_settings


# Cache orchestrator instances
_orchestrator_instance: Optional[OrchestratorService] = None
_tree_orchestrator_instance: Optional[TreeOrchestratorService] = None
_hybrid_orchestrator_instance: Optional[HybridOrchestratorService] = None


@lru_cache()
def get_settings_cached():
    """Get cached settings instance."""
    return get_settings()


async def get_orchestrator_service() -> OrchestratorService:
    """
    Get or create the orchestrator service instance.
    
    Returns:
        OrchestratorService instance
    """
    global _orchestrator_instance
    
    if _orchestrator_instance is None:
        settings = get_settings_cached()
        _orchestrator_instance = OrchestratorService(settings)
        await _orchestrator_instance.initialize()
    
    return _orchestrator_instance


async def get_tree_orchestrator_service() -> TreeOrchestratorService:
    """
    Get or create the tree orchestrator service instance.
    
    Returns:
        TreeOrchestratorService instance
    """
    global _tree_orchestrator_instance
    
    if _tree_orchestrator_instance is None:
        settings = get_settings_cached()
        _tree_orchestrator_instance = TreeOrchestratorService(settings)
        await _tree_orchestrator_instance.initialize()
    
    return _tree_orchestrator_instance


async def get_hybrid_orchestrator_service() -> HybridOrchestratorService:
    """
    Get or create the hybrid orchestrator service instance.
    
    Returns:
        HybridOrchestratorService instance
    """
    global _hybrid_orchestrator_instance
    
    if _hybrid_orchestrator_instance is None:
        settings = get_settings_cached()
        _hybrid_orchestrator_instance = HybridOrchestratorService(settings)
        await _hybrid_orchestrator_instance.initialize()
    
    return _hybrid_orchestrator_instance


async def cleanup_orchestrator_services():
    """Cleanup orchestrator service instances."""
    global _orchestrator_instance, _tree_orchestrator_instance, _hybrid_orchestrator_instance
    
    if _orchestrator_instance:
        await _orchestrator_instance.cleanup()
        _orchestrator_instance = None
    
    if _tree_orchestrator_instance:
        await _tree_orchestrator_instance.cleanup()
        _tree_orchestrator_instance = None
    
    if _hybrid_orchestrator_instance:
        # Hybrid orchestrator doesn't need cleanup (no resources to close)
        _hybrid_orchestrator_instance = None


async def get_conversation_service() -> ConversationService:
    """
    Get conversation service instance from DI container.
    
    Returns:
        ConversationService instance
    """
    container = get_container()
    return await container.get_service(ConversationService)


async def get_chat_service() -> Any:
    """
    Get chat service instance from DI container.
    
    Returns:
        Chat service instance (protocol-based, can be various implementations)
    """
    from app.core.container import ServiceLifetime
    
    container = get_container()
    # ChatService is registered with string key "ChatService"
    descriptor = container._services.get("ChatService")
    if not descriptor:
        raise ValueError("ChatService not registered in container")
    
    if descriptor.lifetime == ServiceLifetime.SCOPED:
        return await container._get_scoped(descriptor)
    elif descriptor.lifetime == ServiceLifetime.SINGLETON:
        return await container._get_singleton(descriptor)
    else:
        return await container._create_instance(descriptor)


async def get_redis_client() -> RedisClient:
    """
    Get Redis client instance from DI container.
    
    Returns:
        RedisClient instance
    """
    container = get_container()
    return await container.get_service(RedisClient)
