"""
Celery application stub for task decorators.
"""

import ssl
from celery import Celery
from app.core.config.settings import get_settings

settings = get_settings()

# Prepare broker and backend URLs
redis_url = settings.redis_url if hasattr(settings, 'redis_url') else "redis://localhost:6379/0"

# Create celery app
celery_app = Celery(
    "needleai",
    broker=redis_url,
    backend=redis_url
)

# Configure celery
celery_config = {
    "task_serializer": "json",
    "accept_content": ["json"],
    "result_serializer": "json",
    "timezone": "UTC",
    "enable_utc": True,
    "imports": [
        "app.tasks.scraping_tasks",
        "app.tasks.chat_tasks",
        "app.tasks.embedding_tasks",
        "app.tasks.sentiment_tasks",
    ],
}

# Add SSL configuration if using rediss://
if redis_url.startswith("rediss://"):
    celery_config.update({
        "broker_use_ssl": {
            "ssl_cert_reqs": ssl.CERT_NONE,  # Skip SSL verification (or use CERT_REQUIRED with proper certs)
        },
        "redis_backend_use_ssl": {
            "ssl_cert_reqs": ssl.CERT_NONE,
        }
    })

celery_app.conf.update(celery_config)

