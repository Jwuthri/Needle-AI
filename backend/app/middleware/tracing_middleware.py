"""
Tracing middleware for adding distributed tracing context to requests.

This middleware enhances request tracing with custom attributes and correlation IDs.
"""

import time
import uuid
from typing import Optional

from app.core.tracing import (
    add_span_attributes,
    add_span_event,
    get_span_id,
    get_trace_id,
    get_tracer,
    set_baggage_item,
)
from app.utils.logging import get_logger
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = get_logger("tracing_middleware")


class TracingMiddleware(BaseHTTPMiddleware):
    """Middleware for enhanced request tracing."""

    def __init__(self, app, service_name: str = "needleai"):
        super().__init__(app)
        self.service_name = service_name
        self.tracer = get_tracer()

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with distributed tracing context."""
        start_time = time.time()

        # Skip tracing for certain endpoints
        if self._should_skip_tracing(request.url.path):
            return await call_next(request)

        # Generate correlation ID if not present
        correlation_id = request.headers.get("x-correlation-id", str(uuid.uuid4()))

        # Set up tracing context
        with self.tracer.start_as_current_span(
            f"{request.method} {request.url.path}",
            kind=trace.SpanKind.SERVER  # type: ignore
        ) as span:

            # Add request attributes
            span.set_attributes({
                "http.method": request.method,
                "http.url": str(request.url),
                "http.scheme": request.url.scheme,
                "http.host": request.url.hostname or "unknown",
                "http.target": request.url.path,
                "http.user_agent": request.headers.get("user-agent", ""),
                "http.route": getattr(request, "route", {}).get("path", ""),
                "correlation.id": correlation_id,
                "service.name": self.service_name,
            })

            # Add query parameters if present
            if request.url.query:
                span.set_attribute("http.query_string", request.url.query)

            # Set baggage for correlation ID propagation
            set_baggage_item("correlation.id", correlation_id)

            # Add request start event
            add_span_event("request.start", {
                "method": request.method,
                "path": request.url.path,
                "correlation_id": correlation_id,
            })

            # Add user context if available
            self._add_user_context(request, span)

            try:
                # Process request
                response = await call_next(request)

                # Add response attributes
                span.set_attributes({
                    "http.status_code": response.status_code,
                    "http.status_text": self._get_status_text(response.status_code),
                    "response.size": len(response.body) if hasattr(response, 'body') else 0,
                })

                # Add response headers
                self._add_response_headers(response, correlation_id)

                # Set span status based on HTTP status
                if response.status_code >= 400:
                    span.set_status(
                        trace.Status(
                            trace.StatusCode.ERROR,
                            f"HTTP {response.status_code}"
                        )
                    )

                # Add request completion event
                duration = time.time() - start_time
                add_span_event("request.complete", {
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                })

                span.set_attribute("http.duration_ms", round(duration * 1000, 2))

                return response

            except Exception as e:
                # Record exception in span
                span.record_exception(e)
                span.set_status(
                    trace.Status(trace.StatusCode.ERROR, str(e))
                )

                # Add error event
                add_span_event("request.error", {
                    "error.type": type(e).__name__,
                    "error.message": str(e),
                })

                raise

    def _should_skip_tracing(self, path: str) -> bool:
        """Check if path should be excluded from tracing."""
        skip_paths = {
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico",
        }

        return path in skip_paths or path.startswith("/static/")

    def _add_user_context(self, request: Request, span):
        """Add user context to span if available."""
        try:
            # Try to extract user information from request
            user_id = request.headers.get("x-user-id")
            if user_id:
                span.set_attribute("user.id", user_id)

            # Check for JWT token
            auth_header = request.headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                span.set_attribute("auth.type", "bearer")
                # Note: Don't log the actual token for security reasons

            # Add client IP
            client_ip = self._get_client_ip(request)
            if client_ip:
                span.set_attribute("client.ip", client_ip)

        except Exception as e:
            logger.debug(f"Failed to add user context: {e}")

    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Extract client IP from request headers."""
        # Check common headers for client IP
        for header in ["x-forwarded-for", "x-real-ip", "x-client-ip"]:
            if header in request.headers:
                # Take first IP if multiple are present
                return request.headers[header].split(",")[0].strip()

        # Fallback to client host
        if hasattr(request.client, 'host'):
            return request.client.host

        return None

    def _add_response_headers(self, response: Response, correlation_id: str):
        """Add tracing headers to response."""
        response.headers["x-correlation-id"] = correlation_id
        response.headers["x-trace-id"] = get_trace_id()
        response.headers["x-span-id"] = get_span_id()

    def _get_status_text(self, status_code: int) -> str:
        """Get HTTP status text for status code."""
        status_texts = {
            200: "OK",
            201: "Created",
            204: "No Content",
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            422: "Unprocessable Entity",
            500: "Internal Server Error",
            502: "Bad Gateway",
            503: "Service Unavailable",
        }

        return status_texts.get(status_code, "Unknown")


class DatabaseTracingMixin:
    """Mixin for adding database tracing to repositories."""

    @staticmethod
    def trace_database_operation(operation: str, table: str, **attributes):
        """Add database operation tracing."""
        span_attributes = {
            "db.operation": operation,
            "db.table": table,
            "db.type": "postgresql",  # or get from settings
            **attributes
        }

        add_span_attributes(span_attributes)
        add_span_event(f"db.{operation}", span_attributes)


class ExternalServiceTracingMixin:
    """Mixin for adding external service call tracing."""

    @staticmethod
    def trace_external_call(service: str, endpoint: str, method: str = "GET", **attributes):
        """Add external service call tracing."""
        span_attributes = {
            "external.service": service,
            "external.endpoint": endpoint,
            "http.method": method,
            **attributes
        }

        add_span_attributes(span_attributes)
        add_span_event(f"external.{service}.call", span_attributes)


# Add missing imports
from opentelemetry import trace
