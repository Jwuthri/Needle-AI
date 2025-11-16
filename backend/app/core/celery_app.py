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
    # Connection resilience settings
    "broker_connection_retry": True,
    "broker_connection_retry_on_startup": True,
    "broker_connection_max_retries": 10,
    "broker_pool_limit": 10,
    "broker_heartbeat": 30,
    "broker_transport_options": {
        "visibility_timeout": 3600,  # 1 hour
        "max_connections": 50,
        "socket_timeout": 30,
        "socket_connect_timeout": 30,
        "socket_keepalive": True,
        "socket_keepalive_options": {
            1: 1,  # TCP_KEEPIDLE
            2: 1,  # TCP_KEEPINTVL
            3: 3,  # TCP_KEEPCNT
        },
        "health_check_interval": 30,
        "retry_on_timeout": True,
    },
    # Result backend connection settings
    "result_backend_transport_options": {
        "max_connections": 50,
        "socket_timeout": 30,
        "socket_connect_timeout": 30,
        "socket_keepalive": True,
        "health_check_interval": 30,
        "retry_on_timeout": True,
    },
    # Worker settings for long-running tasks
    "worker_cancel_long_running_tasks_on_connection_loss": True,
    "task_acks_late": True,
    "task_reject_on_worker_lost": True,
    "worker_prefetch_multiplier": 1,
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

