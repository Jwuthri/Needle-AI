"""
Celery application stub for task decorators.
"""

import ssl
import logging
from celery import Celery
from celery.signals import setup_logging
from rich.console import Console
from rich.logging import RichHandler
from app.core.config.settings import get_settings


@setup_logging.connect
def setup_celery_logging(**kwargs):
    """Configure Rich logging for Celery workers."""
    console = Console(force_terminal=True)
    
    # Configure root logger with Rich
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                console=console,
                rich_tracebacks=True,
                tracebacks_show_locals=True,
                show_path=False,
                markup=True,
            )
        ],
        force=True,
    )
    
    # Set levels for noisy loggers
    logging.getLogger("celery").setLevel(logging.INFO)
    logging.getLogger("kombu").setLevel(logging.WARNING)
    logging.getLogger("amqp").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

settings = get_settings()

# Use Celery-specific settings if available, otherwise fall back to redis_url
broker_url = getattr(settings, 'celery_broker_url', None) or settings.redis_url
backend_url = getattr(settings, 'celery_result_backend', None) or settings.redis_url

# Convert valkeys:// to rediss:// (Celery understands rediss://)
if broker_url.startswith("valkeys://"):
    broker_url = broker_url.replace("valkeys://", "rediss://", 1)
elif broker_url.startswith("valkey://"):
    broker_url = broker_url.replace("valkey://", "redis://", 1)

if backend_url.startswith("valkeys://"):
    backend_url = backend_url.replace("valkeys://", "rediss://", 1)
elif backend_url.startswith("valkey://"):
    backend_url = backend_url.replace("valkey://", "redis://", 1)

# Check if SSL is needed
use_ssl = broker_url.startswith("rediss://") or backend_url.startswith("rediss://")

# Ensure proper database selection
for url_var in ['broker_url', 'backend_url']:
    url = locals()[url_var]
    if not any(url.endswith(f"/{i}") for i in range(16)):
        locals()[url_var] = url.rstrip("/") + "/0"

# Debug
safe_broker = broker_url.split("@")[-1] if "@" in broker_url else broker_url
print(f"DEBUG: Using Celery with {broker_url.split('://')[0]}://***@{safe_broker}")

# Create celery app
celery_app = Celery(
    "needleai",
    broker=broker_url,
    backend=backend_url
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
        "visibility_timeout": 3600,
        "max_connections": 50,
        "socket_timeout": 30,
        "socket_connect_timeout": 30,
        "socket_keepalive": True,
        # Remove socket_keepalive_options - causes "Error 22" on macOS
        "health_check_interval": 30,
        "retry_on_timeout": True,
        "ssl_cert_reqs": ssl.CERT_NONE if use_ssl else None,
        "ssl_check_hostname": False if use_ssl else None,
    },
    # Result backend connection settings
    "result_backend_transport_options": {
        "max_connections": 50,
        "socket_timeout": 30,
        "socket_connect_timeout": 30,
        "socket_keepalive": True,
        "health_check_interval": 30,
        "retry_on_timeout": True,
        "ssl_cert_reqs": ssl.CERT_NONE if use_ssl else None,
        "ssl_check_hostname": False if use_ssl else None,
    },
    # Worker settings for long-running tasks
    "worker_cancel_long_running_tasks_on_connection_loss": True,
    "task_acks_late": True,
    "task_reject_on_worker_lost": True,
    "worker_prefetch_multiplier": 1,
}

# Add SSL configuration for rediss:// URLs
if use_ssl:
    print("DEBUG: Configuring SSL (CERT_NONE) for rediss:// connections")
    celery_config["broker_use_ssl"] = {
        "ssl_cert_reqs": ssl.CERT_NONE,
        "ssl_check_hostname": False,
    }
    celery_config["redis_backend_use_ssl"] = {
        "ssl_cert_reqs": ssl.CERT_NONE,
        "ssl_check_hostname": False,
    }

celery_app.conf.update(celery_config)

print(f"DEBUG: Celery configured - SSL in transport_options: {use_ssl}")

