"""
FastAPI dependencies for dependency injection.
"""

from functools import lru_cache
from typing import Optional, Any

from app.services.workflow_orchestrator_service import WorkflowOrchestratorService
from app.services.conversation_service import ConversationService
from app.services.redis_client import RedisClient
from app.core.container import get_container
from app.core.config.settings import get_settings


# Cache orchestrator instance
_workflow_orchestrator_instance: Optional[WorkflowOrchestratorService] = None


@lru_cache()
def get_settings_cached():
    """Get cached settings instance."""
    return get_settings()


async def get_orchestrator_service() -> WorkflowOrchestratorService:
    """
    Get or create the workflow orchestrator service instance.
    
    Returns:
        WorkflowOrchestratorService instance
    """
    global _workflow_orchestrator_instance
    
    if _workflow_orchestrator_instance is None:
        settings = get_settings_cached()
        _workflow_orchestrator_instance = WorkflowOrchestratorService(settings)
        await _workflow_orchestrator_instance.initialize()
    
    return _workflow_orchestrator_instance


async def cleanup_orchestrator_services():
    """Cleanup orchestrator service instance."""
    global _workflow_orchestrator_instance
    
    if _workflow_orchestrator_instance:
        await _workflow_orchestrator_instance.cleanup()
        _workflow_orchestrator_instance = None


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
