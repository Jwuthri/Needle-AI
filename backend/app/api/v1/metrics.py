"""
Metrics and monitoring endpoints for NeedleAi.
"""

from typing import Any, Dict

from app.config import Settings, get_settings
from app.core.monitoring import app_metrics, get_system_info, health_checker
from app.models.base import StatusResponse
from app.utils.logging import get_logger
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

logger = get_logger("metrics_api")

router = APIRouter()


@router.get("/", response_model=Dict[str, Any])
async def get_application_metrics(
    settings: Settings = Depends(get_settings)
) -> Dict[str, Any]:
    """
    Get comprehensive application metrics.

    Returns detailed metrics about application performance,
    including request counts, response times, resource usage, etc.
    """
    try:
        # Get application metrics
        app_summary = app_metrics.get_summary()

        # Get endpoint statistics
        endpoint_stats = app_metrics.get_endpoint_stats()

        # Get system information
        system_info = get_system_info()

        return {
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "metrics": {
                "application": app_summary,
                "endpoints": endpoint_stats,
                "system": system_info
            }
        }

    except Exception as e:
        logger.error(f"Failed to get application metrics: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "MetricsError",
                "message": "Failed to retrieve application metrics",
                "details": str(e)
            }
        )


@router.get("/summary")
async def get_metrics_summary(
    settings: Settings = Depends(get_settings)
) -> Dict[str, Any]:
    """
    Get a summary of key application metrics.

    Returns a simplified view of the most important metrics
    for quick health assessment.
    """
    try:
        summary = app_metrics.get_summary()

        return {
            "service": settings.app_name,
            "status": "healthy" if summary["error_rate_percent"] < 5.0 else "degraded",
            "uptime": summary["uptime_human"],
            "requests": {
                "total": summary["total_requests"],
                "errors": summary["total_errors"],
                "error_rate": f"{summary['error_rate_percent']}%",
                "active": summary["active_requests"],
                "per_minute": summary["requests_per_minute"]
            },
            "performance": {
                "avg_response_time_ms": summary["average_response_time_ms"],
                "memory_usage_mb": summary["memory_usage"].get("rss_mb", 0),
                "cpu_usage_percent": summary["cpu_usage"].get("percent", 0)
            }
        }

    except Exception as e:
        logger.error(f"Failed to get metrics summary: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "MetricsError",
                "message": "Failed to retrieve metrics summary"
            }
        )


@router.get("/endpoints")
async def get_endpoint_metrics() -> Dict[str, Any]:
    """
    Get detailed metrics for individual API endpoints.

    Returns performance statistics for each endpoint,
    including request counts, response times, and error rates.
    """
    try:
        endpoint_stats = app_metrics.get_endpoint_stats()

        # Calculate derived metrics for each endpoint
        enhanced_stats = {}
        for endpoint, stats in endpoint_stats.items():
            error_rate = 0.0
            if stats["count"] > 0:
                error_rate = (stats["errors"] / stats["count"]) * 100

            enhanced_stats[endpoint] = {
                **stats,
                "error_rate_percent": round(error_rate, 2),
                "requests_per_minute": 0,  # Would need time tracking for accurate calculation
                "p95_response_time": stats["max_time"],  # Simplified, would need percentile calculation
                "throughput": stats["count"] / max(stats["avg_time"], 0.001)  # requests per second
            }

        return {
            "endpoints": enhanced_stats,
            "total_endpoints": len(enhanced_stats)
        }

    except Exception as e:
        logger.error(f"Failed to get endpoint metrics: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "MetricsError",
                "message": "Failed to retrieve endpoint metrics"
            }
        )


@router.get("/system")
async def get_system_metrics() -> Dict[str, Any]:
    """
    Get system resource metrics.

    Returns information about CPU, memory, disk usage,
    and other system-level metrics.
    """
    try:
        system_info = get_system_info()
        app_summary = app_metrics.get_summary()

        return {
            "system": system_info,
            "application_resources": {
                "memory": app_summary["memory_usage"],
                "cpu": app_summary["cpu_usage"]
            }
        }

    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "MetricsError",
                "message": "Failed to retrieve system metrics"
            }
        )


@router.get("/health-checks")
async def get_health_checks() -> Dict[str, Any]:
    """
    Get results of all registered health checks.

    Returns detailed health check results for all
    registered services and dependencies.
    """
    try:
        health_results = await health_checker.check_all()

        return {
            "overall_healthy": health_results["healthy"],
            "checks": health_results["checks"],
            "timestamp": health_results["timestamp"],
            "total_checks": len(health_results["checks"]),
            "failed_checks": sum(1 for check in health_results["checks"].values() if not check.get("healthy", False))
        }

    except Exception as e:
        logger.error(f"Failed to get health checks: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "HealthCheckError",
                "message": "Failed to retrieve health check results"
            }
        )


@router.get("/health-checks/{check_name}")
async def get_single_health_check(check_name: str) -> Dict[str, Any]:
    """
    Get results of a specific health check.

    Args:
        check_name: Name of the health check to run

    Returns:
        Health check result for the specified check.
    """
    try:
        result = await health_checker.check_single(check_name)

        return {
            "check_name": check_name,
            "result": result
        }

    except Exception as e:
        logger.error(f"Failed to get health check for {check_name}: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "HealthCheckError",
                "message": f"Failed to retrieve health check for {check_name}"
            }
        )


@router.post("/reset", response_model=StatusResponse)
async def reset_metrics(
    settings: Settings = Depends(get_settings)
) -> StatusResponse:
    """
    Reset all application metrics.

    WARNING: This will clear all collected metrics data.
    Should only be used in development/testing environments.
    """
    if settings.environment == "production":
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "error": "PermissionError",
                "message": "Metrics reset is not allowed in production environment"
            }
        )

    try:
        app_metrics.reset_metrics()
        logger.info("Application metrics reset successfully")

        return StatusResponse(
            status="success",
            message="Application metrics reset successfully"
        )

    except Exception as e:
        logger.error(f"Failed to reset metrics: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "MetricsError",
                "message": "Failed to reset metrics"
            }
        )


# Prometheus-style metrics endpoint (if needed for external monitoring)
@router.get("/prometheus")
async def get_prometheus_metrics() -> str:
    """
    Get metrics in Prometheus format.

    Returns metrics in a format that can be scraped by Prometheus
    or other monitoring systems that understand this format.
    """
    try:
        summary = app_metrics.get_summary()
        app_metrics.get_endpoint_stats()

        # Basic Prometheus format metrics
        metrics_lines = []

        # Application metrics
        metrics_lines.append(f"# HELP app_requests_total Total number of requests")
        metrics_lines.append(f"# TYPE app_requests_total counter")
        metrics_lines.append(f"app_requests_total {summary['total_requests']}")

        metrics_lines.append(f"# HELP app_errors_total Total number of errors")
        metrics_lines.append(f"# TYPE app_errors_total counter")
        metrics_lines.append(f"app_errors_total {summary['total_errors']}")

        metrics_lines.append(f"# HELP app_response_time_seconds Average response time")
        metrics_lines.append(f"# TYPE app_response_time_seconds gauge")
        metrics_lines.append(f"app_response_time_seconds {summary['average_response_time_ms'] / 1000}")

        metrics_lines.append(f"# HELP app_active_requests Currently active requests")
        metrics_lines.append(f"# TYPE app_active_requests gauge")
        metrics_lines.append(f"app_active_requests {summary['active_requests']}")

        # Memory metrics
        memory_usage = summary.get("memory_usage", {})
        if "rss_mb" in memory_usage:
            metrics_lines.append(f"# HELP app_memory_usage_bytes Memory usage in bytes")
            metrics_lines.append(f"# TYPE app_memory_usage_bytes gauge")
            metrics_lines.append(f"app_memory_usage_bytes {memory_usage['rss_mb'] * 1024 * 1024}")

        # CPU metrics
        cpu_usage = summary.get("cpu_usage", {})
        if "percent" in cpu_usage:
            metrics_lines.append(f"# HELP app_cpu_usage_percent CPU usage percentage")
            metrics_lines.append(f"# TYPE app_cpu_usage_percent gauge")
            metrics_lines.append(f"app_cpu_usage_percent {cpu_usage['percent']}")

        return "\n".join(metrics_lines)

    except Exception as e:
        logger.error(f"Failed to generate Prometheus metrics: {e}")
        return f"# Error generating metrics: {str(e)}"
