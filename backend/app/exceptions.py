"""
Custom exceptions for NeedleAi.

This module provides enhanced exception handling with context, tracing, and structured error details.
For backward compatibility, it re-exports the enhanced exception system from core.exceptions.
"""

# Import enhanced exception system
from app.core.exceptions import (  # Base classes; Specific exceptions; Legacy aliases; Utilities; Exception handlers
    BaseAppException,
    BusinessLogicError,
    CacheError,
    ConfigurationError,
    ConflictError,
    DatabaseError,
    ErrorCategory,
    ErrorContext,
    ErrorDetail,
    ErrorSeverity,
    ErrorTracker,
    ExternalServiceError,
    ForbiddenError,
    LLMError,
    MessageQueueError,
    NotFoundError,
    RateLimitError,
    ServiceUnavailableError,
    UnauthorizedError,
    ValidationError,
    base_app_exception_handler,
    general_exception_handler,
    get_error_tracker,
    http_exception_handler,
    setup_enhanced_exception_handlers,
    validation_exception_handler,
)

from .utils.logging import get_logger

logger = get_logger("exceptions")

# Legacy compatibility function
def setup_exception_handlers(app):
    """Set up exception handlers for the application (legacy compatibility)."""
    setup_enhanced_exception_handlers(app)
