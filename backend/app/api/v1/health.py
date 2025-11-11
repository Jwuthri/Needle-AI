"""
Health check endpoints for NeedleAi.
"""

from datetime import datetime
from typing import Any, Dict

from app.config import Settings, get_settings
from app.models.base import HealthResponse
from fastapi import APIRouter, Depends, status

router = APIRouter()


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
