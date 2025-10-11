"""
Monitoring and observability utilities for NeedleAi.
"""

import asyncio
import time
from contextlib import asynccontextmanager
from datetime import datetime
from functools import wraps
from typing import Any, Dict, List

import psutil
from app.config import Settings
from app.utils.logging import get_logger
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = get_logger("monitoring")


class ApplicationMetrics:
    """Application metrics collector."""

    def __init__(self):
        self.start_time = datetime.utcnow()
        self.request_count = 0
        self.error_count = 0
        self.response_times: List[float] = []
        self.endpoint_stats: Dict[str, Dict[str, Any]] = {}
        self.active_requests = 0
        self.peak_active_requests = 0

    def record_request(self, method: str, path: str, status_code: int, response_time: float):
        """Record request metrics."""
        self.request_count += 1
        self.response_times.append(response_time)

        if status_code >= 400:
            self.error_count += 1

        # Keep only last 1000 response times
        if len(self.response_times) > 1000:
            self.response_times = self.response_times[-1000:]

        # Endpoint-specific stats
        endpoint_key = f"{method} {path}"
        if endpoint_key not in self.endpoint_stats:
            self.endpoint_stats[endpoint_key] = {
                "count": 0,
                "errors": 0,
                "total_time": 0.0,
                "avg_time": 0.0,
                "min_time": float('inf'),
                "max_time": 0.0
            }

        stats = self.endpoint_stats[endpoint_key]
        stats["count"] += 1
        stats["total_time"] += response_time
        stats["avg_time"] = stats["total_time"] / stats["count"]
        stats["min_time"] = min(stats["min_time"], response_time)
        stats["max_time"] = max(stats["max_time"], response_time)

        if status_code >= 400:
            stats["errors"] += 1

    def increment_active_requests(self):
        """Increment active request counter."""
        self.active_requests += 1
        self.peak_active_requests = max(self.peak_active_requests, self.active_requests)

    def decrement_active_requests(self):
        """Decrement active request counter."""
        self.active_requests = max(0, self.active_requests - 1)

    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        uptime = datetime.utcnow() - self.start_time

        avg_response_time = 0.0
        if self.response_times:
            avg_response_time = sum(self.response_times) / len(self.response_times)

        error_rate = 0.0
        if self.request_count > 0:
            error_rate = (self.error_count / self.request_count) * 100

        return {
            "uptime_seconds": uptime.total_seconds(),
            "uptime_human": str(uptime),
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "error_rate_percent": round(error_rate, 2),
            "average_response_time_ms": round(avg_response_time * 1000, 2),
            "active_requests": self.active_requests,
            "peak_active_requests": self.peak_active_requests,
            "requests_per_minute": self.get_requests_per_minute(),
            "memory_usage": self.get_memory_usage(),
            "cpu_usage": self.get_cpu_usage()
        }

    def get_requests_per_minute(self) -> float:
        """Calculate requests per minute."""
        uptime = datetime.utcnow() - self.start_time
        if uptime.total_seconds() < 60:
            return 0.0
        return (self.request_count / uptime.total_seconds()) * 60

    def get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage statistics."""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            return {
                "rss_mb": round(memory_info.rss / 1024 / 1024, 2),
                "vms_mb": round(memory_info.vms / 1024 / 1024, 2),
                "percent": round(process.memory_percent(), 2)
            }
        except Exception as e:
            logger.warning(f"Failed to get memory usage: {e}")
            return {"error": str(e)}

    def get_cpu_usage(self) -> Dict[str, Any]:
        """Get CPU usage statistics."""
        try:
            process = psutil.Process()
            return {
                "percent": round(process.cpu_percent(), 2),
                "system_percent": round(psutil.cpu_percent(), 2),
                "cpu_count": psutil.cpu_count()
            }
        except Exception as e:
            logger.warning(f"Failed to get CPU usage: {e}")
            return {"error": str(e)}

    def get_endpoint_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get endpoint-specific statistics."""
        return self.endpoint_stats

    def reset_metrics(self):
        """Reset all metrics (useful for testing)."""
        self.__init__()


# Global metrics instance
app_metrics = ApplicationMetrics()


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect request metrics."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip metrics collection for health checks and metrics endpoints
        if request.url.path in ["/health", "/metrics", "/api/v1/health"]:
            return await call_next(request)

        start_time = time.time()
        app_metrics.increment_active_requests()

        try:
            response = await call_next(request)

            # Calculate response time
            response_time = time.time() - start_time

            # Record metrics
            app_metrics.record_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                response_time=response_time
            )

            # Add response time header
            response.headers["X-Response-Time"] = f"{response_time:.3f}s"

            return response

        except Exception:
            # Record error
            response_time = time.time() - start_time
            app_metrics.record_request(
                method=request.method,
                path=request.url.path,
                status_code=500,
                response_time=response_time
            )
            raise

        finally:
            app_metrics.decrement_active_requests()


def performance_monitor(operation_name: str):
    """
    Decorator to monitor performance of functions.

    Usage:
        @performance_monitor("database_query")
        async def get_user(user_id: int):
            # ... database query
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.info(f"{operation_name} completed in {execution_time:.3f}s")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"{operation_name} failed after {execution_time:.3f}s: {e}")
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.info(f"{operation_name} completed in {execution_time:.3f}s")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"{operation_name} failed after {execution_time:.3f}s: {e}")
                raise

        # Return appropriate wrapper based on whether function is async
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


@asynccontextmanager
async def request_context(operation_name: str):
    """
    Async context manager for monitoring operations.

    Usage:
        async with request_context("complex_operation"):
            # ... complex operation
    """
    start_time = time.time()
    try:
        logger.info(f"Starting {operation_name}")
        yield
        execution_time = time.time() - start_time
        logger.info(f"{operation_name} completed in {execution_time:.3f}s")
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"{operation_name} failed after {execution_time:.3f}s: {e}")
        raise


class HealthChecker:
    """Application health checker."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.checks: Dict[str, callable] = {}

    def register_check(self, name: str, check_func: callable):
        """Register a health check function."""
        self.checks[name] = check_func

    async def check_all(self) -> Dict[str, Any]:
        """Run all health checks."""
        results = {}
        overall_healthy = True

        for name, check_func in self.checks.items():
            try:
                start_time = time.time()
                is_healthy = await check_func() if asyncio.iscoroutinefunction(check_func) else check_func()
                check_time = time.time() - start_time

                results[name] = {
                    "healthy": is_healthy,
                    "response_time_ms": round(check_time * 1000, 2),
                    "timestamp": datetime.utcnow().isoformat()
                }

                if not is_healthy:
                    overall_healthy = False

            except Exception as e:
                results[name] = {
                    "healthy": False,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
                overall_healthy = False

        return {
            "healthy": overall_healthy,
            "checks": results,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def check_single(self, check_name: str) -> Dict[str, Any]:
        """Run a single health check."""
        if check_name not in self.checks:
            return {
                "healthy": False,
                "error": f"Health check '{check_name}' not found"
            }

        check_func = self.checks[check_name]
        try:
            start_time = time.time()
            is_healthy = await check_func() if asyncio.iscoroutinefunction(check_func) else check_func()
            check_time = time.time() - start_time

            return {
                "healthy": is_healthy,
                "response_time_ms": round(check_time * 1000, 2),
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


# Global health checker instance
health_checker = HealthChecker(None)  # Will be initialized with settings


def setup_monitoring(app, settings: Settings):
    """Set up monitoring for the application."""
    global health_checker
    health_checker = HealthChecker(settings)

    # Add metrics middleware
    app.add_middleware(MetricsMiddleware)

    logger.info("Monitoring and metrics collection enabled")


def get_system_info() -> Dict[str, Any]:
    """Get system information."""
    try:
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        system_uptime = datetime.utcnow() - boot_time

        return {
            "python_version": psutil.sys.version.split()[0],
            "platform": psutil.os.name,
            "cpu_count": psutil.cpu_count(),
            "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "disk_usage": {
                "total_gb": round(psutil.disk_usage('/').total / (1024**3), 2),
                "used_gb": round(psutil.disk_usage('/').used / (1024**3), 2),
                "free_gb": round(psutil.disk_usage('/').free / (1024**3), 2)
            },
            "system_uptime_hours": round(system_uptime.total_seconds() / 3600, 2),
            "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
        }
    except Exception as e:
        logger.warning(f"Failed to get system info: {e}")
        return {"error": str(e)}


# Export the global metrics instance
__all__ = ["app_metrics", "health_checker", "setup_monitoring", "MetricsMiddleware", "performance_monitor", "request_context"]
