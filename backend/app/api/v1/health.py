"""
Health check endpoints for NeedleAi.
"""

from datetime import datetime
from typing import Any, Dict

from app.config import Settings, get_settings
from app.dependencies import (
    check_database_health,
    check_kafka_health,
    check_rabbitmq_health,
    check_redis_health,
)
from app.models.base import HealthResponse
from fastapi import APIRouter, Depends, status

router = APIRouter()


@router.get("/", response_model=HealthResponse)
async def health_check(
    settings: Settings = Depends(get_settings),
    database_health: bool = Depends(check_database_health),
    redis_health: bool = Depends(check_redis_health),
    kafka_health: bool = Depends(check_kafka_health),
    rabbitmq_health: bool = Depends(check_rabbitmq_health)
) -> HealthResponse:
    """
    Comprehensive health check for all services.
    """
    services_status = {
        "database": "healthy" if database_health else "unhealthy",
        "redis": "healthy" if redis_health else "unhealthy",
        "kafka": "healthy" if kafka_health else "unhealthy",
        "rabbitmq": "healthy" if rabbitmq_health else "unhealthy"
    }

    # Overall status - healthy only if all services are healthy
    overall_healthy = all([database_health, redis_health, kafka_health, rabbitmq_health])

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


@router.get("/kafka")
async def kafka_health_check(
    kafka_health: bool = Depends(check_kafka_health)
) -> Dict[str, Any]:
    """Check Kafka service health."""
    return {
        "service": "kafka",
        "status": "healthy" if kafka_health else "unhealthy",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/rabbitmq")
async def rabbitmq_health_check(
    rabbitmq_health: bool = Depends(check_rabbitmq_health)
) -> Dict[str, Any]:
    """Check RabbitMQ service health."""
    return {
        "service": "rabbitmq",
        "status": "healthy" if rabbitmq_health else "unhealthy",
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
    redis_health: bool = Depends(check_redis_health),
    kafka_health: bool = Depends(check_kafka_health),
    rabbitmq_health: bool = Depends(check_rabbitmq_health)
) -> Dict[str, Any]:
    """
    Readiness check - returns 200 only if all critical services are available.
    Used by Kubernetes readiness probes.
    """
    ready = all([database_health, redis_health, kafka_health, rabbitmq_health])

    response = {
        "ready": ready,
        "timestamp": datetime.now().isoformat(),
        "services": {
            "database": database_health,
            "redis": redis_health,
            "kafka": kafka_health,
            "rabbitmq": rabbitmq_health
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


@router.get("/database/pools")
async def database_pool_status():
    """
    Get detailed database connection pool status.
    """
    try:
        from app.core.monitoring.database import db_monitoring_service
        pool_status = await db_monitoring_service.get_all_pool_status()
        return {
            "status": "success",
            "pools": pool_status,
            "timestamp": datetime.now().isoformat()
        }
    except ImportError:
        return {
            "status": "unavailable",
            "message": "Database monitoring not available",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.get("/database/health")
async def database_health_detailed():
    """
    Get detailed database health information.
    """
    try:
        from app.core.monitoring.database import db_monitoring_service
        health_results = await db_monitoring_service.health_check_all()
        return {
            "status": "success",
            "health_checks": health_results,
            "timestamp": datetime.now().isoformat()
        }
    except ImportError:
        return {
            "status": "unavailable",
            "message": "Database monitoring not available",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.get("/database/exhaustion")
async def database_pool_exhaustion():
    """
    Check database pool exhaustion status.
    """
    try:
        from app.core.monitoring.database import db_monitoring_service
        exhaustion_results = await db_monitoring_service.check_all_exhaustion()
        return {
            "status": "success",
            "exhaustion_check": exhaustion_results,
            "timestamp": datetime.now().isoformat()
        }
    except ImportError:
        return {
            "status": "unavailable",
            "message": "Database monitoring not available",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }
