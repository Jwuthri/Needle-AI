"""
Celery application stub for task decorators.
"""

from celery import Celery
from app.core.config.settings import get_settings

settings = get_settings()

# Create celery app
celery_app = Celery(
    "needleai",
    broker=settings.redis_url if hasattr(settings, 'redis_url') else "redis://localhost:6379/0",
    backend=settings.redis_url if hasattr(settings, 'redis_url') else "redis://localhost:6379/0"
)

# Configure celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

