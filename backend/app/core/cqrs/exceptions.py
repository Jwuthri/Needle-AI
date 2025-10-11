"""
CQRS-specific exceptions for NeedleAi.

Custom exceptions for command and query handling errors.
"""

from typing import Any, Dict, Optional, Type, Union


class CQRSError(Exception):
    """Base exception for all CQRS-related errors."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        operation_id: Optional[str] = None
    ):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.operation_id = operation_id

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for serialization."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
            "operation_id": self.operation_id,
        }


class CommandHandlerNotFoundError(CQRSError):
    """Raised when no handler is found for a command."""

    def __init__(
        self,
        command_type: Union[Type, str],
        operation_id: Optional[str] = None
    ):
        command_name = command_type.__name__ if hasattr(command_type, '__name__') else str(command_type)
        message = f"No handler found for command: {command_name}"
        super().__init__(
            message=message,
            details={"command_type": command_name},
            operation_id=operation_id
        )
        self.command_type = command_type


class QueryHandlerNotFoundError(CQRSError):
    """Raised when no handler is found for a query."""

    def __init__(
        self,
        query_type: Union[Type, str],
        operation_id: Optional[str] = None
    ):
        query_name = query_type.__name__ if hasattr(query_type, '__name__') else str(query_type)
        message = f"No handler found for query: {query_name}"
        super().__init__(
            message=message,
            details={"query_type": query_name},
            operation_id=operation_id
        )
        self.query_type = query_type


class CommandValidationError(CQRSError):
    """Raised when command validation fails."""

    def __init__(
        self,
        command_name: str,
        validation_errors: Dict[str, Any],
        operation_id: Optional[str] = None
    ):
        message = f"Command validation failed: {command_name}"
        super().__init__(
            message=message,
            details={"validation_errors": validation_errors, "command_name": command_name},
            operation_id=operation_id
        )
        self.command_name = command_name
        self.validation_errors = validation_errors


class QueryValidationError(CQRSError):
    """Raised when query validation fails."""

    def __init__(
        self,
        query_name: str,
        validation_errors: Dict[str, Any],
        operation_id: Optional[str] = None
    ):
        message = f"Query validation failed: {query_name}"
        super().__init__(
            message=message,
            details={"validation_errors": validation_errors, "query_name": query_name},
            operation_id=operation_id
        )
        self.query_name = query_name
        self.validation_errors = validation_errors


class CommandExecutionError(CQRSError):
    """Raised when command execution fails."""

    def __init__(
        self,
        command_name: str,
        execution_error: str,
        operation_id: Optional[str] = None,
        original_exception: Optional[Exception] = None
    ):
        message = f"Command execution failed: {command_name} - {execution_error}"
        details = {
            "command_name": command_name,
            "execution_error": execution_error
        }

        if original_exception:
            details["original_exception"] = {
                "type": type(original_exception).__name__,
                "message": str(original_exception)
            }

        super().__init__(
            message=message,
            details=details,
            operation_id=operation_id
        )
        self.command_name = command_name
        self.execution_error = execution_error
        self.original_exception = original_exception


class QueryExecutionError(CQRSError):
    """Raised when query execution fails."""

    def __init__(
        self,
        query_name: str,
        execution_error: str,
        operation_id: Optional[str] = None,
        original_exception: Optional[Exception] = None
    ):
        message = f"Query execution failed: {query_name} - {execution_error}"
        details = {
            "query_name": query_name,
            "execution_error": execution_error
        }

        if original_exception:
            details["original_exception"] = {
                "type": type(original_exception).__name__,
                "message": str(original_exception)
            }

        super().__init__(
            message=message,
            details=details,
            operation_id=operation_id
        )
        self.query_name = query_name
        self.execution_error = execution_error
        self.original_exception = original_exception


class DuplicateHandlerError(CQRSError):
    """Raised when trying to register multiple handlers for the same command/query type."""

    def __init__(
        self,
        handler_type: str,  # "command" or "query"
        operation_type: Union[Type, str],
        existing_handler: str,
        new_handler: str
    ):
        operation_name = operation_type.__name__ if hasattr(operation_type, '__name__') else str(operation_type)
        message = (
            f"Duplicate {handler_type} handler registration for {operation_name}. "
            f"Existing: {existing_handler}, New: {new_handler}"
        )
        super().__init__(
            message=message,
            details={
                "handler_type": handler_type,
                "operation_type": operation_name,
                "existing_handler": existing_handler,
                "new_handler": new_handler
            }
        )


class BusNotInitializedError(CQRSError):
    """Raised when trying to use a bus that hasn't been properly initialized."""

    def __init__(self, bus_type: str):
        message = f"{bus_type} bus is not initialized"
        super().__init__(
            message=message,
            details={"bus_type": bus_type}
        )


class HandlerTimeoutError(CQRSError):
    """Raised when a handler execution times out."""

    def __init__(
        self,
        operation_name: str,
        timeout_seconds: float,
        operation_id: Optional[str] = None
    ):
        message = f"Handler execution timed out after {timeout_seconds}s: {operation_name}"
        super().__init__(
            message=message,
            details={
                "operation_name": operation_name,
                "timeout_seconds": timeout_seconds
            },
            operation_id=operation_id
        )
        self.timeout_seconds = timeout_seconds


class ConcurrencyError(CQRSError):
    """Raised when a concurrency conflict is detected."""

    def __init__(
        self,
        resource_id: str,
        expected_version: Optional[str] = None,
        actual_version: Optional[str] = None,
        operation_id: Optional[str] = None
    ):
        message = f"Concurrency conflict detected for resource: {resource_id}"
        details = {"resource_id": resource_id}

        if expected_version and actual_version:
            message += f" (expected version: {expected_version}, actual: {actual_version})"
            details.update({
                "expected_version": expected_version,
                "actual_version": actual_version
            })

        super().__init__(
            message=message,
            details=details,
            operation_id=operation_id
        )
        self.resource_id = resource_id
        self.expected_version = expected_version
        self.actual_version = actual_version


class AuthorizationError(CQRSError):
    """Raised when user is not authorized to execute a command or query."""

    def __init__(
        self,
        operation_name: str,
        user_id: Optional[str] = None,
        required_permissions: Optional[list] = None,
        operation_id: Optional[str] = None
    ):
        message = f"User not authorized to execute: {operation_name}"
        details = {
            "operation_name": operation_name,
            "user_id": user_id,
            "required_permissions": required_permissions or []
        }

        super().__init__(
            message=message,
            details=details,
            operation_id=operation_id
        )
        self.operation_name = operation_name
        self.user_id = user_id
        self.required_permissions = required_permissions or []


class ResourceNotFoundError(CQRSError):
    """Raised when a requested resource is not found."""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        operation_id: Optional[str] = None
    ):
        message = f"{resource_type} not found: {resource_id}"
        super().__init__(
            message=message,
            details={
                "resource_type": resource_type,
                "resource_id": resource_id
            },
            operation_id=operation_id
        )
        self.resource_type = resource_type
        self.resource_id = resource_id


class BusinessRuleViolationError(CQRSError):
    """Raised when a business rule is violated during command execution."""

    def __init__(
        self,
        rule_name: str,
        violation_message: str,
        operation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        message = f"Business rule violation: {rule_name} - {violation_message}"
        super().__init__(
            message=message,
            details={
                "rule_name": rule_name,
                "violation_message": violation_message,
                "context": context or {}
            },
            operation_id=operation_id
        )
        self.rule_name = rule_name
        self.violation_message = violation_message
        self.context = context or {}
