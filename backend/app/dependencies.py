"""
FastAPI dependencies for dependency injection.
"""

from functools import lru_cache
from typing import Optional

from app.services.orchestrator_service import OrchestratorService
from app.services.tree_orchestrator_service import TreeOrchestratorService
from app.config import get_settings


# Cache orchestrator instances
_orchestrator_instance: Optional[OrchestratorService] = None
_tree_orchestrator_instance: Optional[TreeOrchestratorService] = None


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


async def cleanup_orchestrator_services():
    """Cleanup orchestrator service instances."""
    global _orchestrator_instance, _tree_orchestrator_instance
    
    if _orchestrator_instance:
        await _orchestrator_instance.cleanup()
        _orchestrator_instance = None
    
    if _tree_orchestrator_instance:
        await _tree_orchestrator_instance.cleanup()
        _tree_orchestrator_instance = None
