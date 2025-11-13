"""Main API router combining all v1 endpoints."""

from fastapi import APIRouter

from app.api.v1 import health, users, companies, chat, user_datasets

# Create main v1 router
api_router = APIRouter()

# Include health check endpoints (no prefix, at root level)
api_router.include_router(health.router)

# Include all feature routers with their prefixes
api_router.include_router(users.router)
api_router.include_router(companies.router)
api_router.include_router(chat.router)
api_router.include_router(user_datasets.router)
