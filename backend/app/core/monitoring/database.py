"""
Database connection pool monitoring and metrics.

This module provides comprehensive monitoring of database connection pools,
including connection usage, health checks, and performance metrics.
"""

import asyncio
import time
from datetime import datetime
from typing import Any, Dict

from app.utils.logging import get_logger
from prometheus_client import Counter, Gauge, Histogram
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.pool import NullPool, QueuePool, StaticPool

logger = get_logger("database_monitoring")

# Prometheus metrics for database monitoring
DB_CONNECTIONS_TOTAL = Gauge(
    'db_connections_total',
    'Total number of database connections',
    ['pool_name', 'status']  # status: active, idle, invalid
)

DB_CONNECTIONS_CREATED = Counter(
    'db_connections_created_total',
    'Total number of connections created',
    ['pool_name']
)

DB_CONNECTIONS_CLOSED = Counter(
    'db_connections_closed_total',
    'Total number of connections closed',
    ['pool_name']
)

DB_CONNECTION_ERRORS = Counter(
    'db_connection_errors_total',
    'Total number of connection errors',
    ['pool_name', 'error_type']
)

DB_QUERY_DURATION = Histogram(
    'db_query_duration_seconds',
    'Time spent executing database queries',
    ['pool_name', 'query_type']
)

DB_POOL_EXHAUSTION = Counter(
    'db_pool_exhaustion_total',
    'Number of times pool was exhausted',
    ['pool_name']
)

DB_CONNECTION_WAIT_TIME = Histogram(
    'db_connection_wait_time_seconds',
    'Time spent waiting for database connections',
    ['pool_name']
)


class DatabasePoolMonitor:
    """Monitor database connection pools for performance and health."""

    def __init__(self, engine: AsyncEngine, pool_name: str = "default"):
        self.engine = engine
        self.pool_name = pool_name
        self.pool = engine.pool if hasattr(engine, 'pool') else None
        self.last_check = datetime.utcnow()
        self.metrics = {
            "pool_size": 0,
            "checked_out": 0,
            "overflow": 0,
            "checked_in": 0,
            "invalid": 0,
            "total_created": 0,
            "total_closed": 0,
            "errors": 0,
            "avg_query_time": 0.0,
            "last_error": None
        }

    async def get_pool_status(self) -> Dict[str, Any]:
        """
        Get current pool status and metrics.

        Returns:
            Dict with pool status information
        """
        if not self.pool:
            return {"error": "No pool available", "pool_type": "unknown"}

        pool_status = {
            "pool_name": self.pool_name,
            "pool_type": type(self.pool).__name__,
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            if isinstance(self.pool, QueuePool):
                # QueuePool specific metrics
                pool_status.update({
                    "size": self.pool.size(),
                    "checked_out": self.pool.checkedout(),
                    "overflow": self.pool.overflow(),
                    "checked_in": self.pool.checkedin(),
                    "invalid": self.pool.invalidated(),
                    "pool_capacity": self.pool.size() + self.pool._max_overflow,
                    "utilization": (self.pool.checkedout() / max(1, self.pool.size() + self.pool._max_overflow)) * 100,
                })

            elif isinstance(self.pool, (NullPool, StaticPool)):
                pool_status.update({
                    "pool_type_info": "Single connection pool",
                    "size": 1,
                    "checked_out": 1 if hasattr(self.pool, '_connection') else 0,
                })

            # Update Prometheus metrics
            self._update_prometheus_metrics(pool_status)

            # Store metrics for tracking
            self.metrics.update(pool_status)
            self.last_check = datetime.utcnow()

        except Exception as e:
            logger.error(f"Error getting pool status: {e}")
            pool_status["error"] = str(e)
            DB_CONNECTION_ERRORS.labels(
                pool_name=self.pool_name,
                error_type="status_check"
            ).inc()

        return pool_status

    def _update_prometheus_metrics(self, pool_status: Dict[str, Any]):
        """Update Prometheus metrics with pool status."""
        try:
            if "checked_out" in pool_status:
                DB_CONNECTIONS_TOTAL.labels(
                    pool_name=self.pool_name,
                    status="active"
                ).set(pool_status["checked_out"])

            if "checked_in" in pool_status:
                DB_CONNECTIONS_TOTAL.labels(
                    pool_name=self.pool_name,
                    status="idle"
                ).set(pool_status["checked_in"])

            if "invalid" in pool_status:
                DB_CONNECTIONS_TOTAL.labels(
                    pool_name=self.pool_name,
                    status="invalid"
                ).set(pool_status["invalid"])

        except Exception as e:
            logger.warning(f"Error updating Prometheus metrics: {e}")

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the database connection.

        Returns:
            Health check results
        """
        start_time = time.time()
        health_result = {
            "healthy": False,
            "pool_name": self.pool_name,
            "timestamp": datetime.utcnow().isoformat(),
            "response_time": 0.0,
            "error": None
        }

        try:
            # Test database connectivity
            async with self.engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                await result.fetchone()

            response_time = time.time() - start_time
            health_result.update({
                "healthy": True,
                "response_time": response_time
            })

            # Record query time
            DB_QUERY_DURATION.labels(
                pool_name=self.pool_name,
                query_type="health_check"
            ).observe(response_time)

        except Exception as e:
            response_time = time.time() - start_time
            error_msg = str(e)

            health_result.update({
                "healthy": False,
                "response_time": response_time,
                "error": error_msg
            })

            logger.error(f"Database health check failed for {self.pool_name}: {error_msg}")

            DB_CONNECTION_ERRORS.labels(
                pool_name=self.pool_name,
                error_type="health_check"
            ).inc()

        return health_result

    async def monitor_query_performance(self, query_type: str = "general"):
        """
        Context manager for monitoring query performance.

        Usage:
            async with monitor.monitor_query_performance("select"):
                result = await session.execute(query)
        """
        class QueryTimer:
            def __init__(self, pool_name: str, query_type: str):
                self.pool_name = pool_name
                self.query_type = query_type
                self.start_time = None

            async def __aenter__(self):
                self.start_time = time.time()
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                if self.start_time:
                    duration = time.time() - self.start_time
                    DB_QUERY_DURATION.labels(
                        pool_name=self.pool_name,
                        query_type=self.query_type
                    ).observe(duration)

                    if exc_type:
                        DB_CONNECTION_ERRORS.labels(
                            pool_name=self.pool_name,
                            error_type="query_error"
                        ).inc()

        return QueryTimer(self.pool_name, query_type)

    async def check_pool_exhaustion(self) -> Dict[str, Any]:
        """
        Check if the pool is approaching exhaustion.

        Returns:
            Pool exhaustion status and recommendations
        """
        pool_status = await self.get_pool_status()

        if "error" in pool_status:
            return {"error": pool_status["error"]}

        exhaustion_info = {
            "pool_name": self.pool_name,
            "is_exhausted": False,
            "utilization": 0.0,
            "available_connections": 0,
            "recommendations": []
        }

        if "utilization" in pool_status:
            utilization = pool_status["utilization"]
            exhaustion_info["utilization"] = utilization

            # Calculate available connections
            if "pool_capacity" in pool_status and "checked_out" in pool_status:
                available = pool_status["pool_capacity"] - pool_status["checked_out"]
                exhaustion_info["available_connections"] = max(0, available)

                # Check exhaustion thresholds
                if utilization > 90:
                    exhaustion_info["is_exhausted"] = True
                    exhaustion_info["recommendations"].append("Pool is critically high - consider increasing pool size")

                    DB_POOL_EXHAUSTION.labels(pool_name=self.pool_name).inc()

                elif utilization > 75:
                    exhaustion_info["recommendations"].append("Pool utilization is high - monitor closely")

                elif utilization > 50:
                    exhaustion_info["recommendations"].append("Pool utilization is moderate - consider monitoring")

        return exhaustion_info

    async def get_slow_queries_analysis(self) -> Dict[str, Any]:
        """
        Analyze slow queries and connection patterns.

        Returns:
            Analysis of query performance
        """
        try:
            # Get recent metrics (this would be more sophisticated in production)
            # For now, return basic analysis based on stored metrics
            analysis = {
                "pool_name": self.pool_name,
                "timestamp": datetime.utcnow().isoformat(),
                "avg_query_time": self.metrics.get("avg_query_time", 0.0),
                "total_queries": 0,  # Would need to track this
                "slow_queries": 0,   # Would need to track this
                "recommendations": []
            }

            avg_time = self.metrics.get("avg_query_time", 0.0)

            if avg_time > 1.0:
                analysis["recommendations"].append("Average query time is high - consider query optimization")
            elif avg_time > 0.5:
                analysis["recommendations"].append("Monitor query performance - some queries may need optimization")

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing slow queries: {e}")
            return {"error": str(e)}

    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get a comprehensive metrics summary.

        Returns:
            Summary of all collected metrics
        """
        return {
            "pool_name": self.pool_name,
            "last_updated": self.last_check.isoformat(),
            "metrics": self.metrics.copy(),
            "health_status": "unknown",  # Would be updated by health checks
            "monitoring_active": True
        }


class DatabaseMonitoringService:
    """Service for managing multiple database pool monitors."""

    def __init__(self):
        self.monitors: Dict[str, DatabasePoolMonitor] = {}
        self.monitoring_active = True

    def register_pool(self, engine: AsyncEngine, pool_name: str = "default"):
        """Register a database pool for monitoring."""
        monitor = DatabasePoolMonitor(engine, pool_name)
        self.monitors[pool_name] = monitor
        logger.info(f"Registered database pool monitor: {pool_name}")

    async def get_all_pool_status(self) -> Dict[str, Any]:
        """Get status for all monitored pools."""
        status = {}

        for pool_name, monitor in self.monitors.items():
            try:
                status[pool_name] = await monitor.get_pool_status()
            except Exception as e:
                status[pool_name] = {"error": str(e)}

        return status

    async def health_check_all(self) -> Dict[str, Any]:
        """Run health checks on all monitored pools."""
        health_results = {}

        for pool_name, monitor in self.monitors.items():
            try:
                health_results[pool_name] = await monitor.health_check()
            except Exception as e:
                health_results[pool_name] = {
                    "healthy": False,
                    "error": str(e)
                }

        return health_results

    async def check_all_exhaustion(self) -> Dict[str, Any]:
        """Check pool exhaustion for all monitors."""
        exhaustion_results = {}

        for pool_name, monitor in self.monitors.items():
            try:
                exhaustion_results[pool_name] = await monitor.check_pool_exhaustion()
            except Exception as e:
                exhaustion_results[pool_name] = {"error": str(e)}

        return exhaustion_results

    async def start_monitoring_loop(self, interval: int = 60):
        """Start continuous monitoring loop."""
        logger.info(f"Starting database monitoring loop (interval: {interval}s)")

        while self.monitoring_active:
            try:
                # Update all pool metrics
                await self.get_all_pool_status()

                # Check for pool exhaustion
                exhaustion_results = await self.check_all_exhaustion()

                # Log warnings for exhausted pools
                for pool_name, result in exhaustion_results.items():
                    if result.get("is_exhausted"):
                        logger.warning(
                            f"Pool {pool_name} is exhausted: {result.get('utilization', 0):.1f}% utilized"
                        )

                await asyncio.sleep(interval)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(interval)

    def stop_monitoring(self):
        """Stop the monitoring loop."""
        self.monitoring_active = False
        logger.info("Database monitoring stopped")


# Global monitoring service instance
db_monitoring_service = DatabaseMonitoringService()
