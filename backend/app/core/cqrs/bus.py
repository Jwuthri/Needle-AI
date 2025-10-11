"""
CQRS bus implementations for NeedleAi.

Provides command and query buses for dispatching operations to appropriate handlers.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Type

from app.core.cqrs.exceptions import (
    BusNotInitializedError,
    CommandHandlerNotFoundError,
    DuplicateHandlerError,
    QueryHandlerNotFoundError,
)
from app.core.cqrs.interfaces import (
    CommandResult,
    ICommand,
    ICommandBus,
    ICommandHandler,
    IQuery,
    IQueryBus,
    IQueryHandler,
    OperationStatus,
    QueryResult,
)
from app.core.tracing import add_span_attributes, add_span_event, trace_async_function
from app.utils.logging import get_logger

logger = get_logger("cqrs.bus")


@dataclass
class HandlerRegistry:
    """Registry entry for a handler."""
    handler: Any
    handler_class_name: str
    registered_at: datetime


class CommandBus(ICommandBus):
    """
    Command bus implementation for dispatching commands to handlers.

    Manages command handler registration and provides dispatch functionality
    with middleware support for cross-cutting concerns.
    """

    def __init__(self, allow_handler_override: bool = False):
        """
        Initialize command bus.

        Args:
            allow_handler_override: Whether to allow overriding existing handlers
        """
        self._handlers: Dict[Type[ICommand], HandlerRegistry] = {}
        self._middleware: list[Callable] = []
        self._allow_override = allow_handler_override
        self._initialized = True
        self.logger = get_logger("cqrs.command_bus")

    def register_handler(
        self,
        command_type: Type[ICommand],
        handler: ICommandHandler[Any, Any]
    ) -> None:
        """
        Register a command handler for a specific command type.

        Args:
            command_type: The command type to handle
            handler: The handler instance

        Raises:
            DuplicateHandlerError: If handler already exists and override not allowed
        """
        if command_type in self._handlers and not self._allow_override:
            existing_handler = self._handlers[command_type].handler_class_name
            new_handler = handler.__class__.__name__
            raise DuplicateHandlerError(
                handler_type="command",
                operation_type=command_type,
                existing_handler=existing_handler,
                new_handler=new_handler
            )

        self._handlers[command_type] = HandlerRegistry(
            handler=handler,
            handler_class_name=handler.__class__.__name__,
            registered_at=datetime.utcnow()
        )

        self.logger.info(
            f"Registered command handler: {command_type.__name__} -> {handler.__class__.__name__}"
        )

    def register_handlers(self, handlers: Dict[Type[ICommand], ICommandHandler[Any, Any]]) -> None:
        """Register multiple command handlers at once."""
        for command_type, handler in handlers.items():
            self.register_handler(command_type, handler)

    def get_registered_handlers(self) -> Dict[str, str]:
        """Get information about registered handlers."""
        return {
            command_type.__name__: registry.handler_class_name
            for command_type, registry in self._handlers.items()
        }

    def add_middleware(self, middleware: Callable) -> None:
        """Add middleware to the command pipeline."""
        self._middleware.append(middleware)
        self.logger.info(f"Added command middleware: {middleware.__name__}")

    @trace_async_function("command_bus_execute")
    async def execute(self, command: ICommand) -> CommandResult[Any]:
        """
        Execute a command through the appropriate handler.

        Args:
            command: The command to execute

        Returns:
            CommandResult from the handler

        Raises:
            CommandHandlerNotFoundError: If no handler is found
            BusNotInitializedError: If bus is not initialized
        """
        if not self._initialized:
            raise BusNotInitializedError("Command")

        command_type = type(command)
        command_name = command.get_command_name()
        operation_id = command.metadata.operation_id

        # Add tracing attributes
        add_span_attributes({
            "cqrs.bus_type": "command",
            "cqrs.command_type": command_type.__name__,
            "cqrs.operation_id": operation_id,
        })

        # Find handler
        if command_type not in self._handlers:
            error = CommandHandlerNotFoundError(
                command_type=command_type,
                operation_id=operation_id
            )
            add_span_event("command_bus.handler_not_found", {
                "command_type": command_type.__name__
            })
            self.logger.error(f"No handler found for command: {command_name}")
            raise error

        handler_registry = self._handlers[command_type]
        handler = handler_registry.handler

        add_span_attributes({
            "cqrs.handler_class": handler.__class__.__name__,
        })
        add_span_event("command_bus.handler_found", {
            "handler_class": handler.__class__.__name__
        })

        self.logger.debug(
            f"Dispatching command to handler: {command_name} -> {handler.__class__.__name__}",
            extra={"operation_id": operation_id}
        )

        try:
            # Apply middleware and execute
            result = await self._execute_with_middleware(command, handler)

            add_span_event("command_bus.execution_completed", {
                "status": result.status.value,
                "success": result.is_success,
            })

            if result.is_success:
                self.logger.info(
                    f"Command executed successfully: {command_name}",
                    extra={"operation_id": operation_id}
                )
            else:
                self.logger.warning(
                    f"Command execution failed: {command_name} - {result.status}",
                    extra={
                        "operation_id": operation_id,
                        "errors": result.errors,
                    }
                )

            return result

        except Exception as e:
            add_span_event("command_bus.execution_error", {
                "error_type": type(e).__name__,
                "error_message": str(e),
            })

            self.logger.error(
                f"Unexpected error during command execution: {command_name}",
                extra={"operation_id": operation_id},
                exc_info=True
            )

            return CommandResult.failure(
                status=OperationStatus.FAILED,
                errors={
                    "message": "Unexpected error during command execution",
                    "error_type": type(e).__name__,
                    "error_details": str(e),
                },
                metadata=command.metadata,
            )

    async def _execute_with_middleware(
        self,
        command: ICommand,
        handler: ICommandHandler[Any, Any]
    ) -> CommandResult[Any]:
        """Execute command with middleware pipeline."""
        if not self._middleware:
            return await handler.handle(command)

        # Build middleware chain
        async def execute_handler():
            return await handler.handle(command)

        # Apply middleware in reverse order
        for middleware in reversed(self._middleware):
            original_executor = execute_handler

            async def execute_with_middleware(cmd=command, executor=original_executor, mw=middleware):
                return await mw(cmd, executor)

            execute_handler = execute_with_middleware

        return await execute_handler()

    def shutdown(self) -> None:
        """Shutdown the command bus."""
        self._handlers.clear()
        self._middleware.clear()
        self._initialized = False
        self.logger.info("Command bus shut down")


class QueryBus(IQueryBus):
    """
    Query bus implementation for dispatching queries to handlers.

    Manages query handler registration and provides dispatch functionality
    with caching and middleware support.
    """

    def __init__(self, allow_handler_override: bool = False):
        """
        Initialize query bus.

        Args:
            allow_handler_override: Whether to allow overriding existing handlers
        """
        self._handlers: Dict[Type[IQuery], HandlerRegistry] = {}
        self._middleware: list[Callable] = []
        self._allow_override = allow_handler_override
        self._initialized = True
        self.logger = get_logger("cqrs.query_bus")

    def register_handler(
        self,
        query_type: Type[IQuery],
        handler: IQueryHandler[Any, Any]
    ) -> None:
        """
        Register a query handler for a specific query type.

        Args:
            query_type: The query type to handle
            handler: The handler instance

        Raises:
            DuplicateHandlerError: If handler already exists and override not allowed
        """
        if query_type in self._handlers and not self._allow_override:
            existing_handler = self._handlers[query_type].handler_class_name
            new_handler = handler.__class__.__name__
            raise DuplicateHandlerError(
                handler_type="query",
                operation_type=query_type,
                existing_handler=existing_handler,
                new_handler=new_handler
            )

        self._handlers[query_type] = HandlerRegistry(
            handler=handler,
            handler_class_name=handler.__class__.__name__,
            registered_at=datetime.utcnow()
        )

        self.logger.info(
            f"Registered query handler: {query_type.__name__} -> {handler.__class__.__name__}"
        )

    def register_handlers(self, handlers: Dict[Type[IQuery], IQueryHandler[Any, Any]]) -> None:
        """Register multiple query handlers at once."""
        for query_type, handler in handlers.items():
            self.register_handler(query_type, handler)

    def get_registered_handlers(self) -> Dict[str, str]:
        """Get information about registered handlers."""
        return {
            query_type.__name__: registry.handler_class_name
            for query_type, registry in self._handlers.items()
        }

    def add_middleware(self, middleware: Callable) -> None:
        """Add middleware to the query pipeline."""
        self._middleware.append(middleware)
        self.logger.info(f"Added query middleware: {middleware.__name__}")

    @trace_async_function("query_bus_execute")
    async def execute(self, query: IQuery) -> QueryResult[Any]:
        """
        Execute a query through the appropriate handler.

        Args:
            query: The query to execute

        Returns:
            QueryResult from the handler

        Raises:
            QueryHandlerNotFoundError: If no handler is found
            BusNotInitializedError: If bus is not initialized
        """
        if not self._initialized:
            raise BusNotInitializedError("Query")

        query_type = type(query)
        query_name = query.get_query_name()
        operation_id = query.metadata.operation_id

        # Add tracing attributes
        add_span_attributes({
            "cqrs.bus_type": "query",
            "cqrs.query_type": query_type.__name__,
            "cqrs.operation_id": operation_id,
        })

        # Find handler
        if query_type not in self._handlers:
            error = QueryHandlerNotFoundError(
                query_type=query_type,
                operation_id=operation_id
            )
            add_span_event("query_bus.handler_not_found", {
                "query_type": query_type.__name__
            })
            self.logger.error(f"No handler found for query: {query_name}")
            raise error

        handler_registry = self._handlers[query_type]
        handler = handler_registry.handler

        add_span_attributes({
            "cqrs.handler_class": handler.__class__.__name__,
        })
        add_span_event("query_bus.handler_found", {
            "handler_class": handler.__class__.__name__
        })

        self.logger.debug(
            f"Dispatching query to handler: {query_name} -> {handler.__class__.__name__}",
            extra={"operation_id": operation_id}
        )

        try:
            # Apply middleware and execute
            result = await self._execute_with_middleware(query, handler)

            add_span_event("query_bus.execution_completed", {
                "status": result.status.value,
                "success": result.is_success,
            })

            if result.is_success:
                self.logger.info(
                    f"Query executed successfully: {query_name}",
                    extra={"operation_id": operation_id}
                )
            else:
                self.logger.warning(
                    f"Query execution failed: {query_name} - {result.status}",
                    extra={
                        "operation_id": operation_id,
                        "errors": result.errors,
                    }
                )

            return result

        except Exception as e:
            add_span_event("query_bus.execution_error", {
                "error_type": type(e).__name__,
                "error_message": str(e),
            })

            self.logger.error(
                f"Unexpected error during query execution: {query_name}",
                extra={"operation_id": operation_id},
                exc_info=True
            )

            return QueryResult.failure(
                status=OperationStatus.FAILED,
                errors={
                    "message": "Unexpected error during query execution",
                    "error_type": type(e).__name__,
                    "error_details": str(e),
                },
                metadata=query.metadata,
            )

    async def _execute_with_middleware(
        self,
        query: IQuery,
        handler: IQueryHandler[Any, Any]
    ) -> QueryResult[Any]:
        """Execute query with middleware pipeline."""
        if not self._middleware:
            return await handler.handle(query)

        # Build middleware chain
        async def execute_handler():
            return await handler.handle(query)

        # Apply middleware in reverse order
        for middleware in reversed(self._middleware):
            original_executor = execute_handler

            async def execute_with_middleware(qry=query, executor=original_executor, mw=middleware):
                return await mw(qry, executor)

            execute_handler = execute_with_middleware

        return await execute_handler()

    def shutdown(self) -> None:
        """Shutdown the query bus."""
        self._handlers.clear()
        self._middleware.clear()
        self._initialized = False
        self.logger.info("Query bus shut down")


class CQRSBus:
    """
    Combined CQRS bus that provides both command and query dispatch functionality.

    This is a convenience class that wraps both CommandBus and QueryBus
    and provides a unified interface for CQRS operations.
    """

    def __init__(self, allow_handler_override: bool = False):
        """Initialize combined CQRS bus."""
        self.command_bus = CommandBus(allow_handler_override)
        self.query_bus = QueryBus(allow_handler_override)
        self.logger = get_logger("cqrs.bus")

    # Command operations
    def register_command_handler(
        self,
        command_type: Type[ICommand],
        handler: ICommandHandler[Any, Any]
    ) -> None:
        """Register a command handler."""
        self.command_bus.register_handler(command_type, handler)

    def register_command_handlers(
        self,
        handlers: Dict[Type[ICommand], ICommandHandler[Any, Any]]
    ) -> None:
        """Register multiple command handlers."""
        self.command_bus.register_handlers(handlers)

    async def execute_command(self, command: ICommand) -> CommandResult[Any]:
        """Execute a command."""
        return await self.command_bus.execute(command)

    def add_command_middleware(self, middleware: Callable) -> None:
        """Add middleware to the command pipeline."""
        self.command_bus.add_middleware(middleware)

    # Query operations
    def register_query_handler(
        self,
        query_type: Type[IQuery],
        handler: IQueryHandler[Any, Any]
    ) -> None:
        """Register a query handler."""
        self.query_bus.register_handler(query_type, handler)

    def register_query_handlers(
        self,
        handlers: Dict[Type[IQuery], IQueryHandler[Any, Any]]
    ) -> None:
        """Register multiple query handlers."""
        self.query_bus.register_handlers(handlers)

    async def execute_query(self, query: IQuery) -> QueryResult[Any]:
        """Execute a query."""
        return await self.query_bus.execute(query)

    def add_query_middleware(self, middleware: Callable) -> None:
        """Add middleware to the query pipeline."""
        self.query_bus.add_middleware(middleware)

    # Combined operations
    def get_registered_handlers(self) -> Dict[str, Dict[str, str]]:
        """Get information about all registered handlers."""
        return {
            "commands": self.command_bus.get_registered_handlers(),
            "queries": self.query_bus.get_registered_handlers(),
        }

    def get_handler_count(self) -> Dict[str, int]:
        """Get count of registered handlers."""
        command_handlers = self.command_bus.get_registered_handlers()
        query_handlers = self.query_bus.get_registered_handlers()

        return {
            "commands": len(command_handlers),
            "queries": len(query_handlers),
            "total": len(command_handlers) + len(query_handlers),
        }

    def shutdown(self) -> None:
        """Shutdown both command and query buses."""
        self.command_bus.shutdown()
        self.query_bus.shutdown()
        self.logger.info("CQRS bus shut down")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.shutdown()


# Global CQRS bus instance (can be configured via dependency injection)
_global_cqrs_bus: Optional[CQRSBus] = None


def get_cqrs_bus() -> CQRSBus:
    """Get the global CQRS bus instance."""
    global _global_cqrs_bus
    if _global_cqrs_bus is None:
        _global_cqrs_bus = CQRSBus()
    return _global_cqrs_bus


def initialize_cqrs_bus(allow_handler_override: bool = False) -> CQRSBus:
    """Initialize and return the global CQRS bus."""
    global _global_cqrs_bus
    _global_cqrs_bus = CQRSBus(allow_handler_override)
    return _global_cqrs_bus


def shutdown_cqrs_bus() -> None:
    """Shutdown the global CQRS bus."""
    global _global_cqrs_bus
    if _global_cqrs_bus:
        _global_cqrs_bus.shutdown()
        _global_cqrs_bus = None
