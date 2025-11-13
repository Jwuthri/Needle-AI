"""Health check endpoint."""

from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from back_end.app.database.session import get_db
from back_end.app.core.config.settings import get_settings

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    response_model=Dict[str, Any],
    summary="Health check endpoint",
    description="Check application health and database connectivity",
)
async def health_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Health check endpoint to verify application status.
    
    Returns application information and database connectivity status.
    
    Args:
        db: Database session for connectivity check
        
    Returns:
        Dictionary with health status information
    """
    # Check database connectivity
    db_status = "healthy"
    db_error = None
    
    try:
        # Execute a simple query to verify database connection
        result = await db.execute(text("SELECT 1"))
        result.scalar()
    except Exception as e:
        db_status = "unhealthy"
        db_error = str(e)
    
    # Determine overall status
    overall_status = "healthy" if db_status == "healthy" else "degraded"
    
    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "application": {
            "name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
        },
        "database": {
            "status": db_status,
            "name": settings.database_name,
            "error": db_error,
        },
    }


@router.get(
    "/health/ready",
    status_code=status.HTTP_200_OK,
    summary="Readiness check",
    description="Check if application is ready to accept requests",
)
async def readiness_check(db: AsyncSession = Depends(get_db)) -> Dict[str, str]:
    """
    Readiness check for Kubernetes/container orchestration.
    
    Returns 200 if the application is ready to serve traffic.
    
    Args:
        db: Database session for connectivity check
        
    Returns:
        Dictionary with ready status
        
    Raises:
        HTTPException: If application is not ready
    """
    try:
        # Verify database connection
        await db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database not ready: {str(e)}",
        )


@router.get(
    "/health/live",
    status_code=status.HTTP_200_OK,
    summary="Liveness check",
    description="Check if application is alive",
)
async def liveness_check() -> Dict[str, str]:
    """
    Liveness check for Kubernetes/container orchestration.
    
    Returns 200 if the application process is alive.
    This endpoint does not check external dependencies.
    
    Returns:
        Dictionary with alive status
    """
    return {"status": "alive"}
