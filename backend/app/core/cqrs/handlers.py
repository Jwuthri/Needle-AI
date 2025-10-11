"""
Base handler implementations for CQRS pattern in NeedleAi.

Provides abstract base classes for command and query handlers with common functionality.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, Optional, Type, TypeVar

from app.core.tracing import add_span_attributes, add_span_event, trace_async_function
from app.utils.logging import get_logger

from .exceptions import (
    AuthorizationError,
    CommandValidationError,
    HandlerTimeoutError,
    QueryValidationError,
)
from .interfaces import (
    CommandResult,
    ICommandHandler,
    IQueryHandler,
    OperationStatus,
    QueryResult,
    TCommand,
    TQuery,
    TResult,
)

logger = get_logger("cqrs.handlers")

# Handler type variables
TCommandHandler = TypeVar('TCommandHandler', bound='BaseCommandHandler')
TQueryHandler = TypeVar('TQueryHandler', bound='BaseQueryHandler')


class BaseCommandHandler(ICommandHandler[TCommand, TResult], ABC, Generic[TCommand, TResult]):
    """
    Base implementation for command handlers.

    Provides common functionality like validation, error handling,
    tracing, and transaction management.
    """

    def __init__(self):
        self.logger = get_logger(f"command.{self.__class__.__name__}")
        self._timeout_seconds = 30.0  # Default timeout

    @abstractmethod
    async def _handle(self, command: TCommand) -> TResult:
        """
        Internal method to implement command handling logic.

        This method should contain the actual business logic and will be
        wrapped with common functionality like validation, tracing, etc.

        Args:
            command: The validated command to handle

        Returns:
            The command result data

        Raises:
            Can raise exceptions which will be wrapped in CommandResult
        """

    def get_command_type(self) -> Type[TCommand]:
        """Get the command type this handler processes."""
        # This should be overridden by concrete handlers
        # In practice, this would use type hints or class attributes
        raise NotImplementedError("Concrete handlers must implement get_command_type")

    @trace_async_function()
    async def handle(self, command: TCommand) -> CommandResult[TResult]:
        """
        Handle command execution with full lifecycle management.

        This method provides:
        - Input validation
        - Authorization checks
        - Distributed tracing
        - Error handling and logging
        - Timeout protection
        - Transaction management
        """
        operation_id = command.metadata.operation_id
        command_name = command.get_command_name()

        # Add tracing attributes
        add_span_attributes({
            "cqrs.operation_type": "command",
            "cqrs.command_name": command_name,
            "cqrs.operation_id": operation_id,
            "cqrs.handler": self.__class__.__name__,
        })

        start_time = time.time()

        try:
            # 1. Validate command
            await self._validate_command(command)
            add_span_event("command.validation.completed")

            # 2. Authorize command execution
            await self._authorize_command(command)
            add_span_event("command.authorization.completed")

            # 3. Execute command with timeout
            result_data = await self._execute_with_timeout(command)

            # 4. Create successful result
            execution_time = time.time() - start_time
            add_span_attributes({
                "cqrs.execution_time_ms": round(execution_time * 1000, 2),
                "cqrs.status": "success",
            })
            add_span_event("command.execution.completed", {
                "execution_time_ms": round(execution_time * 1000, 2)
            })

            self.logger.info(
                f"Command executed successfully: {command_name}",
                extra={
                    "operation_id": operation_id,
                    "execution_time_ms": round(execution_time * 1000, 2),
                    "command_name": command_name,
                }
            )

            return CommandResult.success(
                data=result_data,
                metadata=command.metadata,
                affected_entities=await self._get_affected_entities(command, result_data),
            )

        except CommandValidationError as e:
            add_span_attributes({"cqrs.status": "validation_error"})
            add_span_event("command.validation.failed", {"errors": e.validation_errors})

            self.logger.warning(
                f"Command validation failed: {command_name}",
                extra={
                    "operation_id": operation_id,
                    "validation_errors": e.validation_errors,
                    "command_name": command_name,
                }
            )

            return CommandResult.validation_error(
                errors=e.validation_errors,
                metadata=command.metadata,
            )

        except AuthorizationError as e:
            add_span_attributes({"cqrs.status": "unauthorized"})
            add_span_event("command.authorization.failed")

            self.logger.warning(
                f"Command authorization failed: {command_name}",
                extra={
                    "operation_id": operation_id,
                    "user_id": e.user_id,
                    "command_name": command_name,
                }
            )

            return CommandResult.failure(
                status=OperationStatus.UNAUTHORIZED,
                errors={"message": e.message},
                metadata=command.metadata,
            )

        except HandlerTimeoutError as e:
            add_span_attributes({"cqrs.status": "timeout"})
            add_span_event("command.execution.timeout", {"timeout_seconds": e.timeout_seconds})

            self.logger.error(
                f"Command execution timed out: {command_name}",
                extra={
                    "operation_id": operation_id,
                    "timeout_seconds": e.timeout_seconds,
                    "command_name": command_name,
                }
            )

            return CommandResult.failure(
                status=OperationStatus.FAILED,
                errors={"message": f"Execution timed out after {e.timeout_seconds}s"},
                metadata=command.metadata,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            add_span_attributes({
                "cqrs.status": "error",
                "cqrs.execution_time_ms": round(execution_time * 1000, 2),
            })
            add_span_event("command.execution.failed", {
                "error_type": type(e).__name__,
                "error_message": str(e),
            })

            self.logger.error(
                f"Command execution failed: {command_name}",
                extra={
                    "operation_id": operation_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "command_name": command_name,
                },
                exc_info=True
            )

            return CommandResult.failure(
                status=OperationStatus.FAILED,
                errors={
                    "message": "Command execution failed",
                    "error_type": type(e).__name__,
                    "error_details": str(e),
                },
                metadata=command.metadata,
            )

    async def _validate_command(self, command: TCommand) -> None:
        """Validate command and raise CommandValidationError if invalid."""
        validation_errors = command.validate()
        if validation_errors:
            raise CommandValidationError(
                command_name=command.get_command_name(),
                validation_errors=validation_errors,
                operation_id=command.metadata.operation_id,
            )

    async def _authorize_command(self, command: TCommand) -> None:
        """
        Authorize command execution.

        Override this method to implement authorization logic.
        Raise AuthorizationError if user is not authorized.
        """
        # Default: no authorization required
        # Override in concrete handlers for authorization logic

    async def _execute_with_timeout(self, command: TCommand) -> TResult:
        """Execute command with timeout protection."""
        try:
            return await asyncio.wait_for(self._handle(command), timeout=self._timeout_seconds)
        except asyncio.TimeoutError:
            raise HandlerTimeoutError(
                operation_name=command.get_command_name(),
                timeout_seconds=self._timeout_seconds,
                operation_id=command.metadata.operation_id,
            )

    async def _get_affected_entities(
        self,
        command: TCommand,
        result: TResult
    ) -> Optional[Dict[str, Any]]:
        """
        Get information about entities affected by the command.

        Override this method to provide information about which entities
        were created, updated, or deleted by the command execution.
        """
        return None

    def set_timeout(self, timeout_seconds: float) -> None:
        """Set execution timeout for this handler."""
        self._timeout_seconds = timeout_seconds


class BaseQueryHandler(IQueryHandler[TQuery, TResult], ABC, Generic[TQuery, TResult]):
    """
    Base implementation for query handlers.

    Provides common functionality like validation, caching,
    tracing, and pagination.
    """

    def __init__(self):
        self.logger = get_logger(f"query.{self.__class__.__name__}")
        self._timeout_seconds = 15.0  # Default timeout (shorter than commands)
        self._cache_enabled = True

    @abstractmethod
    async def _handle(self, query: TQuery) -> TResult:
        """
        Internal method to implement query handling logic.

        This method should contain the actual data retrieval logic
        and will be wrapped with common functionality.

        Args:
            query: The validated query to handle

        Returns:
            The query result data

        Raises:
            Can raise exceptions which will be wrapped in QueryResult
        """

    def get_query_type(self) -> Type[TQuery]:
        """Get the query type this handler processes."""
        raise NotImplementedError("Concrete handlers must implement get_query_type")

    @trace_async_function()
    async def handle(self, query: TQuery) -> QueryResult[TResult]:
        """
        Handle query execution with full lifecycle management.

        This method provides:
        - Input validation
        - Authorization checks
        - Caching (if enabled)
        - Distributed tracing
        - Error handling and logging
        - Timeout protection
        """
        operation_id = query.metadata.operation_id
        query_name = query.get_query_name()

        # Add tracing attributes
        add_span_attributes({
            "cqrs.operation_type": "query",
            "cqrs.query_name": query_name,
            "cqrs.operation_id": operation_id,
            "cqrs.handler": self.__class__.__name__,
        })

        start_time = time.time()

        try:
            # 1. Validate query
            await self._validate_query(query)
            add_span_event("query.validation.completed")

            # 2. Authorize query execution
            await self._authorize_query(query)
            add_span_event("query.authorization.completed")

            # 3. Check cache if enabled
            cached_result = await self._get_cached_result(query) if self._cache_enabled else None
            if cached_result is not None:
                execution_time = time.time() - start_time
                add_span_attributes({
                    "cqrs.execution_time_ms": round(execution_time * 1000, 2),
                    "cqrs.status": "success",
                    "cqrs.cache_hit": True,
                })
                add_span_event("query.cache.hit")

                return QueryResult.success(
                    data=cached_result,
                    metadata=query.metadata,
                    cache_info={"hit": True, "key": query.get_cache_key()},
                )

            # 4. Execute query with timeout
            result_data = await self._execute_with_timeout(query)

            # 5. Cache result if applicable
            if self._cache_enabled:
                await self._cache_result(query, result_data)
                add_span_event("query.cache.stored")

            # 6. Create successful result
            execution_time = time.time() - start_time
            add_span_attributes({
                "cqrs.execution_time_ms": round(execution_time * 1000, 2),
                "cqrs.status": "success",
                "cqrs.cache_hit": False,
            })
            add_span_event("query.execution.completed", {
                "execution_time_ms": round(execution_time * 1000, 2)
            })

            self.logger.info(
                f"Query executed successfully: {query_name}",
                extra={
                    "operation_id": operation_id,
                    "execution_time_ms": round(execution_time * 1000, 2),
                    "query_name": query_name,
                }
            )

            return QueryResult.success(
                data=result_data,
                metadata=query.metadata,
                pagination=await self._get_pagination_info(query, result_data),
                cache_info={"hit": False, "key": query.get_cache_key()},
            )

        except QueryValidationError as e:
            add_span_attributes({"cqrs.status": "validation_error"})
            add_span_event("query.validation.failed", {"errors": e.validation_errors})

            self.logger.warning(
                f"Query validation failed: {query_name}",
                extra={
                    "operation_id": operation_id,
                    "validation_errors": e.validation_errors,
                    "query_name": query_name,
                }
            )

            return QueryResult.failure(
                status=OperationStatus.VALIDATION_ERROR,
                errors=e.validation_errors,
                metadata=query.metadata,
            )

        except AuthorizationError as e:
            add_span_attributes({"cqrs.status": "unauthorized"})
            add_span_event("query.authorization.failed")

            self.logger.warning(
                f"Query authorization failed: {query_name}",
                extra={
                    "operation_id": operation_id,
                    "user_id": e.user_id,
                    "query_name": query_name,
                }
            )

            return QueryResult.failure(
                status=OperationStatus.UNAUTHORIZED,
                errors={"message": e.message},
                metadata=query.metadata,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            add_span_attributes({
                "cqrs.status": "error",
                "cqrs.execution_time_ms": round(execution_time * 1000, 2),
            })
            add_span_event("query.execution.failed", {
                "error_type": type(e).__name__,
                "error_message": str(e),
            })

            self.logger.error(
                f"Query execution failed: {query_name}",
                extra={
                    "operation_id": operation_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "query_name": query_name,
                },
                exc_info=True
            )

            return QueryResult.failure(
                status=OperationStatus.FAILED,
                errors={
                    "message": "Query execution failed",
                    "error_type": type(e).__name__,
                    "error_details": str(e),
                },
                metadata=query.metadata,
            )

    async def _validate_query(self, query: TQuery) -> None:
        """Validate query and raise QueryValidationError if invalid."""
        validation_errors = query.validate()
        if validation_errors:
            raise QueryValidationError(
                query_name=query.get_query_name(),
                validation_errors=validation_errors,
                operation_id=query.metadata.operation_id,
            )

    async def _authorize_query(self, query: TQuery) -> None:
        """
        Authorize query execution.

        Override this method to implement authorization logic.
        """
        # Default: no authorization required

    async def _execute_with_timeout(self, query: TQuery) -> TResult:
        """Execute query with timeout protection."""
        try:
            return await asyncio.wait_for(self._handle(query), timeout=self._timeout_seconds)
        except asyncio.TimeoutError:
            raise HandlerTimeoutError(
                operation_name=query.get_query_name(),
                timeout_seconds=self._timeout_seconds,
                operation_id=query.metadata.operation_id,
            )

    async def _get_cached_result(self, query: TQuery) -> Optional[TResult]:
        """
        Get cached result for query.

        Override this method to implement caching logic.
        """
        return None

    async def _cache_result(self, query: TQuery, result: TResult) -> None:
        """
        Cache query result.

        Override this method to implement caching logic.
        """

    async def _get_pagination_info(
        self,
        query: TQuery,
        result: TResult
    ) -> Optional[Dict[str, Any]]:
        """
        Get pagination information for query result.

        Override this method to provide pagination details.
        """
        return None

    def set_timeout(self, timeout_seconds: float) -> None:
        """Set execution timeout for this handler."""
        self._timeout_seconds = timeout_seconds

    def disable_cache(self) -> None:
        """Disable caching for this handler."""
        self._cache_enabled = False

    def enable_cache(self) -> None:
        """Enable caching for this handler."""
        self._cache_enabled = True
