"""
Middleware package for NeedleAi.
"""

import json
import time
from typing import Callable
from uuid import uuid4

from app.config import get_settings
from app.core.security.input_sanitization import input_sanitizer
from app.utils.logging import get_logger
from fastapi import HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from .tracing_middleware import (
    DatabaseTracingMixin,
    ExternalServiceTracingMixin,
    TracingMiddleware,
)

logger = get_logger("middleware")


class RequestScopeMiddleware(BaseHTTPMiddleware):
    """Middleware for managing request-scoped dependency injection."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle request-scoped DI cleanup."""
        try:
            response = await call_next(request)
            return response
        finally:
            # Cleanup request-scoped services
            if hasattr(request.state, "container_scope"):
                try:
                    await request.state.container_scope.__aexit__(None, None, None)
                except Exception as e:
                    logger.warning(f"Error cleaning up request scope: {e}")


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid4())
        request.state.request_id = request_id

        # Log request
        start_time = time.time()
        logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            }
        )

        # Process request
        response = await call_next(request)

        # Log response
        process_time = time.time() - start_time
        logger.info(
            "Request completed",
            extra={
                "request_id": request_id,
                "status_code": response.status_code,
                "process_time": f"{process_time:.4f}s",
            }
        )

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware for adding security headers."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware."""

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.client_requests = {}
        self.window_size = 60  # 1 minute

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks and internal requests
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        current_time = time.time()

        # Clean old entries
        self._cleanup_old_requests(current_time)

        # Check rate limit
        if self._is_rate_limited(client_ip, current_time):
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return Response(
                content="Rate limit exceeded",
                status_code=429,
                headers={"Retry-After": "60"}
            )

        # Record request
        self._record_request(client_ip, current_time)

        return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        # Check for forwarded headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"

    def _cleanup_old_requests(self, current_time: float):
        """Remove old request records."""
        cutoff_time = current_time - self.window_size

        for client_ip in list(self.client_requests.keys()):
            self.client_requests[client_ip] = [
                timestamp for timestamp in self.client_requests[client_ip]
                if timestamp > cutoff_time
            ]

            if not self.client_requests[client_ip]:
                del self.client_requests[client_ip]

    def _is_rate_limited(self, client_ip: str, current_time: float) -> bool:
        """Check if client is rate limited."""
        if client_ip not in self.client_requests:
            return False

        return len(self.client_requests[client_ip]) >= self.requests_per_minute

    def _record_request(self, client_ip: str, current_time: float):
        """Record a request timestamp."""
        if client_ip not in self.client_requests:
            self.client_requests[client_ip] = []

        self.client_requests[client_ip].append(current_time)


class InputSanitizationMiddleware(BaseHTTPMiddleware):
    """Middleware for input sanitization and XSS/injection protection."""

    # Endpoints that require strict prompt injection checking
    CHAT_ENDPOINTS = ["/api/v1/chat/", "/api/v1/completions/"]
    
    # Streaming endpoints that should skip body sanitization
    STREAMING_ENDPOINTS = ["/api/v1/chat/stream", "/api/v1/chat-experimental/stream"]

    # Maximum request body size (10MB)
    MAX_BODY_SIZE = 10 * 1024 * 1024

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip for GET requests, certain endpoints, and streaming endpoints
        if (request.method == "GET" or 
            request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"] or
            request.url.path in self.STREAMING_ENDPOINTS):
            return await call_next(request)

        try:
            # Check request body size
            if hasattr(request, 'headers') and 'content-length' in request.headers:
                content_length = int(request.headers['content-length'])
                if content_length > self.MAX_BODY_SIZE:
                    logger.warning(f"Request body too large: {content_length} bytes")
                    return Response(
                        content="Request body too large",
                        status_code=413,
                        headers={"Content-Type": "application/json"}
                    )

            # Read and sanitize request body for POST/PUT requests
            if request.method in ["POST", "PUT", "PATCH"]:
                # Get request body
                body = await request.body()

                if body:
                    try:
                        # Parse JSON body
                        body_json = json.loads(body)
                        sanitized_body = await self._sanitize_json_recursively(
                            body_json,
                            is_chat_endpoint=request.url.path in self.CHAT_ENDPOINTS
                        )

                        # Replace request body with sanitized version
                        sanitized_body_bytes = json.dumps(sanitized_body).encode('utf-8')

                        # Create new request with sanitized body
                        async def receive():
                            return {
                                "type": "http.request",
                                "body": sanitized_body_bytes,
                                "more_body": False,
                            }

                        request._receive = receive

                    except json.JSONDecodeError:
                        # For non-JSON bodies, apply basic sanitization
                        body_str = body.decode('utf-8', errors='ignore')
                        sanitized = input_sanitizer.sanitize_html(body_str, strip_tags=True)

                        async def receive():
                            return {
                                "type": "http.request",
                                "body": sanitized.encode('utf-8'),
                                "more_body": False,
                            }

                        request._receive = receive

            return await call_next(request)

        except Exception as e:
            logger.error(f"Input sanitization error: {e}")
            return Response(
                content=json.dumps({"error": "Request processing failed"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )

    async def _sanitize_json_recursively(self, obj, is_chat_endpoint: bool = False):
        """Recursively sanitize JSON object."""
        if isinstance(obj, dict):
            sanitized = {}
            for key, value in obj.items():
                # Sanitize key
                clean_key = input_sanitizer.sanitize_html(str(key), strip_tags=True)

                # Recursively sanitize value
                sanitized[clean_key] = await self._sanitize_json_recursively(
                    value, is_chat_endpoint
                )
            return sanitized

        elif isinstance(obj, list):
            return [
                await self._sanitize_json_recursively(item, is_chat_endpoint)
                for item in obj
            ]

        elif isinstance(obj, str):
            # Special handling for chat messages
            if is_chat_endpoint and len(obj) > 0:
                result = input_sanitizer.validate_and_sanitize_input(
                    obj,
                    max_length=5000,
                    allow_html=False,
                    check_injection=True
                )

                if not result["is_valid"]:
                    logger.warning(
                        f"Blocked potential prompt injection - Risk: {result['injection_check']['risk_score']:.2f}"
                    )
                    raise HTTPException(
                        status_code=400,
                        detail="Input contains potentially harmful content"
                    )

                return result["sanitized"]
            else:
                # Regular string sanitization
                return input_sanitizer.sanitize_html(obj, strip_tags=True)

        else:
            # Return other types as-is (numbers, booleans, null)
            return obj


def setup_middleware(app):
    """Set up all middleware for the application."""
    settings = get_settings()

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Distributed tracing middleware (early in the chain)
    if settings.enable_tracing:
        app.add_middleware(TracingMiddleware, service_name=settings.app_name)

    # Gzip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)

    # Rate limiting (only in production)
    if settings.environment == "production":
        app.add_middleware(
            RateLimitMiddleware,
            requests_per_minute=settings.rate_limit_requests
        )

    # Input sanitization (before business logic)
    app.add_middleware(InputSanitizationMiddleware)

    # Request-scoped dependency injection cleanup
    app.add_middleware(RequestScopeMiddleware)

    # Request logging (last, so it captures everything)
    app.add_middleware(LoggingMiddleware)


__all__ = [
    "TracingMiddleware",
    "DatabaseTracingMixin",
    "ExternalServiceTracingMixin",
    "RequestScopeMiddleware",
    "LoggingMiddleware",
    "SecurityHeadersMiddleware",
    "RateLimitMiddleware",
    "InputSanitizationMiddleware",
    "setup_middleware",
]
