"""
Celery application configuration and setup for NeedleAi.
"""

from app.config import get_settings
from celery import Celery

settings = get_settings()

# Create Celery app instance
celery_app = Celery(
    "needleai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.llm_tasks",
        "app.tasks.chat_tasks",
        "app.tasks.general_tasks"
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,

    # Result backend settings
    result_expires=settings.celery_result_expires,
    result_backend_transport_options={
        'master_name': 'mymaster',
        'visibility_timeout': 3600,
        'retry_policy': {
            'timeout': 5.0
        }
    },

    # Task execution settings
    task_always_eager=settings.celery_task_always_eager,
    task_eager_propagates=True,
    task_ignore_result=False,
    task_store_eager_result=True,

    # Worker settings
    worker_prefetch_multiplier=settings.celery_worker_prefetch_multiplier,
    worker_max_tasks_per_child=settings.celery_worker_max_tasks_per_child,
    worker_disable_rate_limits=False,

    # Routing
    task_routes=settings.celery_task_routes,

    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,

    # Error handling
    task_reject_on_worker_lost=True,
    task_acks_late=True,
)

# Additional configuration for production
if settings.environment == "production":
    celery_app.conf.update(
        broker_connection_retry_on_startup=True,
        broker_connection_retry=True,
        broker_connection_max_retries=3,
        broker_pool_limit=10,
        result_backend_max_retries=3,
        result_backend_retry_delay=1,
    )
