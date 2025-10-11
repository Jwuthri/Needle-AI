"""
Distributed tracing configuration using OpenTelemetry.

This module sets up distributed tracing for NeedleAi using OpenTelemetry
with support for multiple exporters (Jaeger, Zipkin, OTLP) and automatic instrumentation.
"""

import os
from contextlib import contextmanager
from typing import Any, Dict, Optional

from app.core.config.settings import Settings
from app.utils.logging import get_logger
from opentelemetry import baggage, context, trace

# Exporters
# Conditional imports for tracing (optional dependencies)
try:
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.exporter.zipkin.json import ZipkinExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    TRACING_AVAILABLE = True
except ImportError as e:
    # Tracing dependencies not installed
    TRACING_AVAILABLE = False
    JaegerExporter = None
    OTLPSpanExporter = None
    ZipkinExporter = None
    FastAPIInstrumentor = None
    HTTPXClientInstrumentor = None
    RedisInstrumentor = None
    RequestsInstrumentor = None
    SQLAlchemyInstrumentor = None

from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)

logger = get_logger("tracing")

# Global tracer instance
tracer: Optional[trace.Tracer] = None


class TracingConfig:
    """Tracing configuration and setup."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.service_name = settings.app_name.lower().replace(" ", "-")
        self.service_version = settings.app_version
        self.environment = settings.environment

        # Tracing settings from environment
        self.enabled = os.getenv("ENABLE_TRACING", "false").lower() == "true"
        self.exporter_type = os.getenv("TRACING_EXPORTER", "console").lower()
        self.jaeger_endpoint = os.getenv("JAEGER_ENDPOINT", "http://localhost:14268/api/traces")
        self.zipkin_endpoint = os.getenv("ZIPKIN_ENDPOINT", "http://localhost:9411/api/v2/spans")
        self.otlp_endpoint = os.getenv("OTLP_ENDPOINT", "http://localhost:4317")
        self.sample_rate = float(os.getenv("TRACING_SAMPLE_RATE", "1.0"))

        # Custom span attributes
        self.default_attributes = {
            "service.name": self.service_name,
            "service.version": self.service_version,
            "deployment.environment": self.environment,
            "service.instance.id": os.getenv("HOSTNAME", "unknown"),
        }

    def setup_tracing(self) -> bool:
        """
        Set up distributed tracing with OpenTelemetry.

        Returns:
            bool: True if tracing was successfully configured, False otherwise.
        """
        if not self.enabled:
            logger.info("Distributed tracing is disabled")
            return False

        try:
            # Create resource with service information
            resource = Resource.create({
                SERVICE_NAME: self.service_name,
                SERVICE_VERSION: self.service_version,
                "deployment.environment": self.environment,
                "service.instance.id": os.getenv("HOSTNAME", "unknown"),
            })

            # Set up tracer provider
            tracer_provider = TracerProvider(resource=resource)

            # Configure span processor and exporter
            span_processor = self._create_span_processor()
            if span_processor:
                tracer_provider.add_span_processor(span_processor)

            # Set global tracer provider
            trace.set_tracer_provider(tracer_provider)

            # Get global tracer
            global tracer
            tracer = trace.get_tracer(__name__)

            logger.info(
                f"Distributed tracing initialized with {self.exporter_type} exporter, "
                f"service: {self.service_name}, version: {self.service_version}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to initialize distributed tracing: {e}")
            return False

    def _create_span_processor(self) -> Optional[BatchSpanProcessor]:
        """Create appropriate span processor based on exporter type."""
        try:
            if self.exporter_type == "jaeger":
                exporter = JaegerExporter(
                    collector_endpoint=self.jaeger_endpoint,
                    max_tag_value_length=1024,
                )
                return BatchSpanProcessor(exporter)

            elif self.exporter_type == "zipkin":
                exporter = ZipkinExporter(
                    endpoint=self.zipkin_endpoint,
                    timeout=10,
                )
                return BatchSpanProcessor(exporter)

            elif self.exporter_type == "otlp":
                exporter = OTLPSpanExporter(
                    endpoint=self.otlp_endpoint,
                    timeout=10,
                )
                return BatchSpanProcessor(exporter)

            elif self.exporter_type == "console":
                exporter = ConsoleSpanExporter()
                return SimpleSpanProcessor(exporter)

            else:
                logger.warning(f"Unknown exporter type: {self.exporter_type}")
                return None

        except Exception as e:
            logger.error(f"Failed to create span processor: {e}")
            return None

    def instrument_app(self, app):
        """Instrument FastAPI app and other services."""
        if not self.enabled:
            return

        try:
            # Instrument FastAPI
            FastAPIInstrumentor.instrument_app(
                app,
                tracer_provider=trace.get_tracer_provider(),
                excluded_urls="health,metrics,docs,redoc,openapi.json",
            )

            # Instrument SQLAlchemy
            SQLAlchemyInstrumentor().instrument(
                tracer_provider=trace.get_tracer_provider(),
            )

            # Instrument Redis
            RedisInstrumentor().instrument(
                tracer_provider=trace.get_tracer_provider(),
            )

            # Instrument HTTP clients
            RequestsInstrumentor().instrument(
                tracer_provider=trace.get_tracer_provider(),
            )

            HTTPXClientInstrumentor().instrument(
                tracer_provider=trace.get_tracer_provider(),
            )

            logger.info("Auto-instrumentation enabled for FastAPI, SQLAlchemy, Redis, and HTTP clients")

        except Exception as e:
            logger.error(f"Failed to instrument services: {e}")


def get_tracer() -> trace.Tracer:
    """Get the global tracer instance."""
    global tracer
    if tracer is None:
        # Return no-op tracer if tracing is not initialized
        return trace.NoOpTracer()
    return tracer


@contextmanager
def trace_operation(operation_name: str, attributes: Optional[Dict[str, Any]] = None):
    """
    Context manager for tracing operations.

    Args:
        operation_name: Name of the operation being traced
        attributes: Additional attributes to add to the span

    Example:
        with trace_operation("database_query", {"table": "users", "action": "select"}):
            result = await db.query(User).all()
    """
    tracer = get_tracer()

    with tracer.start_as_current_span(operation_name) as span:
        try:
            # Add default attributes
            span.set_attributes({
                "operation.name": operation_name,
                "service.name": os.getenv("SERVICE_NAME", "needleai"),
            })

            # Add custom attributes
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, str(value))

            yield span

        except Exception as e:
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise


def trace_async_function(operation_name: Optional[str] = None, attributes: Optional[Dict[str, Any]] = None):
    """
    Decorator for tracing async functions.

    Args:
        operation_name: Custom operation name (defaults to function name)
        attributes: Additional attributes to add to the span

    Example:
        @trace_async_function("user_creation", {"component": "auth"})
        async def create_user(user_data: dict):
            return await user_repository.create(user_data)
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"

            with trace_operation(op_name, attributes) as span:
                # Add function details
                span.set_attributes({
                    "function.name": func.__name__,
                    "function.module": func.__module__,
                })

                return await func(*args, **kwargs)

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper

    return decorator


def trace_sync_function(operation_name: Optional[str] = None, attributes: Optional[Dict[str, Any]] = None):
    """
    Decorator for tracing sync functions.

    Args:
        operation_name: Custom operation name (defaults to function name)
        attributes: Additional attributes to add to the span

    Example:
        @trace_sync_function("password_validation", {"component": "auth"})
        def validate_password(password: str) -> bool:
            return len(password) >= 8
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"

            with trace_operation(op_name, attributes) as span:
                # Add function details
                span.set_attributes({
                    "function.name": func.__name__,
                    "function.module": func.__module__,
                })

                return func(*args, **kwargs)

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper

    return decorator


def add_span_attributes(attributes: Dict[str, Any]):
    """Add attributes to the current span."""
    current_span = trace.get_current_span()
    if current_span.is_recording():
        for key, value in attributes.items():
            current_span.set_attribute(key, str(value))


def add_span_event(name: str, attributes: Optional[Dict[str, Any]] = None):
    """Add an event to the current span."""
    current_span = trace.get_current_span()
    if current_span.is_recording():
        current_span.add_event(name, attributes or {})


def set_baggage_item(key: str, value: str):
    """Set a baggage item that will be propagated to child spans."""
    ctx = baggage.set_baggage(key, value)
    context.attach(ctx)


def get_baggage_item(key: str) -> Optional[str]:
    """Get a baggage item from the current context."""
    return baggage.get_baggage(key)


def get_trace_id() -> str:
    """Get the current trace ID as a string."""
    current_span = trace.get_current_span()
    if current_span and current_span.get_span_context().is_valid:
        return format(current_span.get_span_context().trace_id, "032x")
    return "0"


def get_span_id() -> str:
    """Get the current span ID as a string."""
    current_span = trace.get_current_span()
    if current_span and current_span.get_span_context().is_valid:
        return format(current_span.get_span_context().span_id, "016x")
    return "0"


# Global tracing configuration instance
tracing_config: Optional[TracingConfig] = None


def initialize_tracing(settings: Settings) -> bool:
    """
    Initialize distributed tracing system.

    Args:
        settings: Application settings

    Returns:
        bool: True if tracing was successfully initialized
    """
    if not TRACING_AVAILABLE:
        logger.warning("Tracing dependencies not available. Skipping tracing initialization.")
        return False

    global tracing_config

    tracing_config = TracingConfig(settings)
    return tracing_config.setup_tracing()


def instrument_fastapi_app(app, settings: Settings):
    """Instrument FastAPI app with distributed tracing."""
    if not TRACING_AVAILABLE:
        logger.warning("Tracing dependencies not available. Skipping FastAPI instrumentation.")
        return

    global tracing_config

    if tracing_config is None:
        tracing_config = TracingConfig(settings)
        tracing_config.setup_tracing()

    tracing_config.instrument_app(app)


def shutdown_tracing():
    """Shutdown tracing and clean up resources."""
    try:
        tracer_provider = trace.get_tracer_provider()
        if hasattr(tracer_provider, 'shutdown'):
            tracer_provider.shutdown()
        logger.info("Distributed tracing shutdown completed")
    except Exception as e:
        logger.error(f"Error during tracing shutdown: {e}")
