"""
Main API v1 router for NeedleAi.
"""

from app.api.v1 import analytics, auth, chat, companies, health, metrics, payments, scraping, tasks
from fastapi import APIRouter

api_router = APIRouter(prefix="/v1")

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(metrics.router, prefix="/metrics", tags=["metrics", "monitoring"])

# Product review platform endpoints
api_router.include_router(companies.router, prefix="/companies", tags=["companies"])
api_router.include_router(scraping.router, prefix="/scraping", tags=["scraping"])
api_router.include_router(payments.router, prefix="/payments", tags=["payments"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
