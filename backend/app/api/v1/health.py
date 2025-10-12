"""
Health check endpoints for NeedleAi.
"""

from datetime import datetime
from typing import Any, Dict

from app.config import Settings, get_settings
from app.dependencies import (
    check_database_health,
    check_redis_health,
)
from app.models.base import HealthResponse
from fastapi import APIRouter, Depends, status

router = APIRouter()


@router.get("/", response_model=HealthResponse)
async def health_check(
    settings: Settings = Depends(get_settings),
    database_health: bool = Depends(check_database_health),
    redis_health: bool = Depends(check_redis_health)
) -> HealthResponse:
    """
    Comprehensive health check for all core services.
    
    Checks:
    - PostgreSQL database
    - Redis cache/session storage
    - Celery uses Redis (checked via Redis health)
    """
    services_status = {
        "database": "healthy" if database_health else "unhealthy",
        "redis": "healthy" if redis_health else "unhealthy",
        "celery": "healthy" if redis_health else "unhealthy"  # Celery depends on Redis
    }

    # Overall status - healthy only if all services are healthy
    overall_healthy = all([database_health, redis_health])

    return HealthResponse(
        status="healthy" if overall_healthy else "unhealthy",
        timestamp=datetime.now().isoformat(),
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        services=services_status
    )


@router.get("/redis")
async def redis_health_check(
    redis_health: bool = Depends(check_redis_health)
) -> Dict[str, Any]:
    """Check Redis service health."""
    return {
        "service": "redis",
        "status": "healthy" if redis_health else "unhealthy",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/database")
async def database_health_check(
    database_health: bool = Depends(check_database_health)
) -> Dict[str, Any]:
    """Check database service health."""
    return {
        "service": "database",
        "status": "healthy" if database_health else "unhealthy",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/ready")
async def readiness_check(
    database_health: bool = Depends(check_database_health),
    redis_health: bool = Depends(check_redis_health)
) -> Dict[str, Any]:
    """
    Readiness check - returns 200 only if all critical services are available.
    Used by Kubernetes readiness probes.
    
    Critical services:
    - PostgreSQL database
    - Redis (for caching, sessions, and Celery)
    """
    ready = all([database_health, redis_health])

    response = {
        "ready": ready,
        "timestamp": datetime.now().isoformat(),
        "services": {
            "database": database_health,
            "redis": redis_health,
            "celery": redis_health  # Celery depends on Redis
        }
    }

    # Return 503 if not ready
    if not ready:
        from fastapi import Response
        return Response(
            content=response,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    return response


@router.get("/live")
async def liveness_check() -> Dict[str, Any]:
    """
    Liveness check - basic health check that always returns 200 if the app is running.
    Used by Kubernetes liveness probes.
    """
    return {
        "alive": True,
        "timestamp": datetime.now().isoformat()
    }
