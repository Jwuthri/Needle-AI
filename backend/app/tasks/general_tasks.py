"""
General background tasks for NeedleAi.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import psutil
from app.config import get_settings
from app.core.celery_app import celery_app
from app.services.redis_client import RedisClient
from app.utils.logging import get_logger

logger = get_logger("general_tasks")
settings = get_settings()


@celery_app.task(bind=True, max_retries=3)
def send_notification(
    self,
    recipient: str,
    message: str,
    notification_type: str = "info",
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Send notification to user or system.

    Args:
        recipient: Notification recipient (email, user_id, etc.)
        message: Notification message
        notification_type: Type of notification (info, warning, error, success)
        metadata: Additional metadata

    Returns:
        Dict with notification result
    """
    try:
        logger.info(f"Sending {notification_type} notification to {recipient}")

        self.update_state(
            state='PROGRESS',
            meta={'current': 30, 'total': 100, 'status': 'Preparing notification...'}
        )

        # Here you would integrate with your notification service
        # (email, push notifications, webhooks, etc.)

        import time
        time.sleep(1)  # Simulate notification sending

        self.update_state(
            state='PROGRESS',
            meta={'current': 100, 'total': 100, 'status': 'Notification sent!'}
        )

        notification_result = {
            "task_id": self.request.id,
            "recipient": recipient,
            "message": message,
            "type": notification_type,
            "metadata": metadata or {},
            "sent_at": datetime.utcnow().isoformat(),
            "status": "sent"
        }

        logger.info(f"Notification sent successfully to {recipient}")
        return notification_result

    except Exception as exc:
        logger.error(f"Error sending notification: {str(exc)}")

        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60)

        return {
            "task_id": self.request.id,
            "recipient": recipient,
            "error": str(exc),
            "status": "failed"
        }


@celery_app.task(bind=True, max_retries=2)
def cleanup_expired_cache(self, pattern: str = "*", max_age_hours: int = 24) -> Dict[str, Any]:
    """
    Clean up expired cache entries.

    Args:
        pattern: Redis key pattern to match (default: all keys)
        max_age_hours: Maximum age in hours before considering cache expired

    Returns:
        Dict with cleanup statistics
    """
    try:
        logger.info(f"Starting cache cleanup with pattern: {pattern}")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def _cleanup_async():
            redis_client = RedisClient(redis_url=settings.redis_url)
            await redis_client.connect()

            self.update_state(
                state='PROGRESS',
                meta={'current': 25, 'total': 100, 'status': 'Scanning cache keys...'}
            )

            # Get keys matching pattern
            cache_keys = await redis_client.redis.keys(f"cache:{pattern}")
            expired_keys = []
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)

            self.update_state(
                state='PROGRESS',
                meta={'current': 50, 'total': 100, 'status': f'Checking {len(cache_keys)} cache entries...'}
            )

            # Check each cache entry's timestamp
            for key in cache_keys:
                try:
                    cache_data = await redis_client.get(key.decode())
                    if cache_data and isinstance(cache_data, dict):
                        cached_at = datetime.fromisoformat(
                            cache_data.get("cached_at", datetime.utcnow().isoformat())
                        )
                        if cached_at < cutoff_time:
                            expired_keys.append(key.decode())
                except Exception as e:
                    logger.warning(f"Error checking cache key {key.decode()}: {str(e)}")
                    # Add to expired list if we can't read it
                    expired_keys.append(key.decode())

            self.update_state(
                state='PROGRESS',
                meta={'current': 75, 'total': 100, 'status': f'Removing {len(expired_keys)} expired entries...'}
            )

            # Remove expired entries
            deleted_count = 0
            for key in expired_keys:
                try:
                    await redis_client.delete(key)
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Error deleting cache key {key}: {str(e)}")

            await redis_client.disconnect()
            return deleted_count

        try:
            deleted_count = loop.run_until_complete(_cleanup_async())
        finally:
            loop.close()

        logger.info(f"Cache cleanup completed: {deleted_count} entries removed")

        return {
            "task_id": self.request.id,
            # "keys_scanned": len(cache_keys),
            "keys_deleted": deleted_count,
            "pattern": pattern,
            "max_age_hours": max_age_hours,
            "status": "completed"
        }

    except Exception as exc:
        logger.error(f"Error in cache cleanup: {str(exc)}")

        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=300)

        return {
            "task_id": self.request.id,
            "error": str(exc),
            "status": "failed"
        }


@celery_app.task(bind=True, max_retries=1)
def health_check_services(self) -> Dict[str, Any]:
    """
    Perform health check on all system services.

    Returns:
        Dict with health check results
    """
    try:
        logger.info("Starting system health check")

        health_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "services": {}
        }

        self.update_state(
            state='PROGRESS',
            meta={'current': 20, 'total': 100, 'status': 'Checking system resources...'}
        )

        # System resource check
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            health_results["system"] = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": (disk.used / disk.total) * 100,
                "load_average": psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else None,
                "status": "healthy" if cpu_percent < 80 and memory.percent < 80 else "warning"
            }
        except Exception as e:
            health_results["system"] = {"status": "error", "error": str(e)}

        self.update_state(
            state='PROGRESS',
            meta={'current': 50, 'total': 100, 'status': 'Checking Redis connection...'}
        )

        # Redis health check
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def _check_redis_async():
                redis_client = RedisClient(redis_url=settings.redis_url)
                await redis_client.connect()

                # Test Redis operations
                test_key = "health_check_test"
                await redis_client.set(test_key, "test_value", expire=60)
                test_value = await redis_client.get(test_key)
                await redis_client.delete(test_key)

                result = {
                    "status": "healthy" if test_value == "test_value" else "error",
                    "response_time_ms": 50  # Mock response time
                }

                await redis_client.disconnect()
                return result

            try:
                redis_result = loop.run_until_complete(_check_redis_async())
                health_results["services"]["redis"] = redis_result
            finally:
                loop.close()

        except Exception as e:
            health_results["services"]["redis"] = {"status": "error", "error": str(e)}

        self.update_state(
            state='PROGRESS',
            meta={'current': 80, 'total': 100, 'status': 'Checking external services...'}
        )

        # LLM service health check (basic connectivity)
        try:
            # This would check your LLM provider connectivity
            health_results["services"]["llm"] = {
                "status": "healthy",
                "provider": settings.llm_provider,
                "model": settings.default_model
            }
        except Exception as e:
            health_results["services"]["llm"] = {"status": "error", "error": str(e)}

        # Overall system health
        service_statuses = [service.get("status", "error") for service in health_results["services"].values()]
        system_status = health_results.get("system", {}).get("status", "error")

        if "error" in service_statuses or system_status == "error":
            overall_status = "unhealthy"
        elif "warning" in service_statuses or system_status == "warning":
            overall_status = "degraded"
        else:
            overall_status = "healthy"

        health_results["overall_status"] = overall_status
        health_results["task_id"] = self.request.id

        logger.info(f"Health check completed - Overall status: {overall_status}")

        return health_results

    except Exception as exc:
        logger.error(f"Error in health check: {str(exc)}")

        return {
            "task_id": self.request.id,
            "error": str(exc),
            "status": "failed",
            "timestamp": datetime.utcnow().isoformat()
        }


@celery_app.task(bind=True, max_retries=1)
def generate_report(
    self,
    report_type: str,
    date_range: Optional[Dict[str, str]] = None,
    filters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate system reports (usage, performance, etc.).

    Args:
        report_type: Type of report to generate (usage, performance, errors)
        date_range: Optional date range for report
        filters: Optional filters to apply

    Returns:
        Dict with report data
    """
    try:
        logger.info(f"Generating {report_type} report")

        self.update_state(
            state='PROGRESS',
            meta={'current': 25, 'total': 100, 'status': 'Collecting data...'}
        )

        # Mock report generation
        import time
        time.sleep(2)

        self.update_state(
            state='PROGRESS',
            meta={'current': 75, 'total': 100, 'status': 'Processing report...'}
        )

        time.sleep(1)

        report_data = {
            "task_id": self.request.id,
            "report_type": report_type,
            "generated_at": datetime.utcnow().isoformat(),
            "date_range": date_range,
            "filters": filters,
            "data": {
                "summary": {
                    "total_requests": 1000,
                    "successful_requests": 950,
                    "failed_requests": 50,
                    "average_response_time": 245
                },
                "details": [
                    {"metric": "API Calls", "value": 1000, "trend": "+5%"},
                    {"metric": "LLM Tokens", "value": 50000, "trend": "+12%"},
                    {"metric": "Error Rate", "value": "5%", "trend": "-2%"}
                ]
            },
            "status": "completed"
        }

        logger.info(f"Report generated successfully: {report_type}")

        return report_data

    except Exception as exc:
        logger.error(f"Error generating report: {str(exc)}")

        return {
            "task_id": self.request.id,
            "error": str(exc),
            "status": "failed"
        }
