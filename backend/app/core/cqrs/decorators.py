"""
CQRS decorators for NeedleAi.

Provides decorators for handler registration, caching, transactions, and other cross-cutting concerns.
"""

import asyncio
from datetime import timedelta
from typing import Callable, List, Optional, Type

from app.core.tracing import add_span_attributes, add_span_event, trace_async_function
from app.utils.logging import get_logger

from .bus import get_cqrs_bus
from .interfaces import ICommand, ICommandHandler, IQuery, IQueryHandler

logger = get_logger("cqrs.decorators")


def command_handler(
    command_type: Type[ICommand],
    auto_register: bool = True,
    timeout_seconds: Optional[float] = None
):
    """
    Decorator to mark a class as a command handler and optionally register it.

    Args:
        command_type: The command type this handler processes
        auto_register: Whether to automatically register with the global bus
        timeout_seconds: Override default timeout for this handler

    Example:
        @command_handler(CreateUserCommand)
        class CreateUserHandler(BaseCommandHandler[CreateUserCommand, str]):
            async def _handle(self, command: CreateUserCommand) -> str:
                # Implementation here
                return user_id
    """
    def decorator(handler_class: Type[ICommandHandler]):
        # Store command type metadata on the handler class
        handler_class._command_type = command_type
        handler_class._auto_register = auto_register

        # Override get_command_type method
        def get_command_type(self) -> Type[ICommand]:
            return command_type

        handler_class.get_command_type = get_command_type

        # Set timeout if specified
        if timeout_seconds is not None:
            original_init = handler_class.__init__

            def __init__(self, *args, **kwargs):
                original_init(self, *args, **kwargs)
                self.set_timeout(timeout_seconds)

            handler_class.__init__ = __init__

        # Auto-register with global bus if requested
        if auto_register:
            try:
                cqrs_bus = get_cqrs_bus()
                handler_instance = handler_class()
                cqrs_bus.register_command_handler(command_type, handler_instance)
                logger.info(f"Auto-registered command handler: {command_type.__name__} -> {handler_class.__name__}")
            except Exception as e:
                logger.warning(f"Failed to auto-register command handler {handler_class.__name__}: {e}")

        return handler_class

    return decorator


def query_handler(
    query_type: Type[IQuery],
    auto_register: bool = True,
    timeout_seconds: Optional[float] = None,
    cache_enabled: bool = True
):
    """
    Decorator to mark a class as a query handler and optionally register it.

    Args:
        query_type: The query type this handler processes
        auto_register: Whether to automatically register with the global bus
        timeout_seconds: Override default timeout for this handler
        cache_enabled: Whether caching is enabled for this handler

    Example:
        @query_handler(GetUserQuery, cache_enabled=True)
        class GetUserHandler(BaseQueryHandler[GetUserQuery, UserDto]):
            async def _handle(self, query: GetUserQuery) -> UserDto:
                # Implementation here
                return user_dto
    """
    def decorator(handler_class: Type[IQueryHandler]):
        # Store query type metadata on the handler class
        handler_class._query_type = query_type
        handler_class._auto_register = auto_register

        # Override get_query_type method
        def get_query_type(self) -> Type[IQuery]:
            return query_type

        handler_class.get_query_type = get_query_type

        # Configure handler
        original_init = handler_class.__init__

        def __init__(self, *args, **kwargs):
            original_init(self, *args, **kwargs)

            if timeout_seconds is not None:
                self.set_timeout(timeout_seconds)

            if not cache_enabled:
                self.disable_cache()

        handler_class.__init__ = __init__

        # Auto-register with global bus if requested
        if auto_register:
            try:
                cqrs_bus = get_cqrs_bus()
                handler_instance = handler_class()
                cqrs_bus.register_query_handler(query_type, handler_instance)
                logger.info(f"Auto-registered query handler: {query_type.__name__} -> {handler_class.__name__}")
            except Exception as e:
                logger.warning(f"Failed to auto-register query handler {handler_class.__name__}: {e}")

        return handler_class

    return decorator


def transactional(
    isolation_level: Optional[str] = None,
    rollback_on: Optional[List[Type[Exception]]] = None,
    commit_on_success: bool = True
):
    """
    Decorator to wrap command handler execution in a database transaction.

    Args:
        isolation_level: Database isolation level (READ_COMMITTED, REPEATABLE_READ, etc.)
        rollback_on: List of exception types that should trigger rollback
        commit_on_success: Whether to commit transaction on success

    Example:
        @transactional(isolation_level="REPEATABLE_READ")
        class CreateOrderHandler(BaseCommandHandler):
            async def _handle(self, command: CreateOrderCommand) -> str:
                # This will run in a transaction
                return order_id
    """
    def decorator(handler_class: Type[ICommandHandler]):
        original_handle = handler_class._handle
        rollback_exceptions = tuple(rollback_on or [Exception])

        @trace_async_function("transactional_handler")
        async def transactional_handle(self, command):
            add_span_attributes({
                "transaction.isolation_level": isolation_level or "default",
                "transaction.commit_on_success": commit_on_success,
            })

            # This is a simplified transaction wrapper
            # In practice, you'd integrate with your database session/transaction manager
            transaction_started = False

            try:
                # Start transaction (pseudo-code - integrate with your DB layer)
                add_span_event("transaction.started", {
                    "isolation_level": isolation_level
                })
                transaction_started = True

                # Execute original handler
                result = await original_handle(self, command)

                # Commit transaction if successful
                if commit_on_success:
                    add_span_event("transaction.committed")
                    # await self.db_session.commit()  # Your DB integration here

                return result

            except rollback_exceptions as e:
                if transaction_started:
                    add_span_event("transaction.rolled_back", {
                        "reason": str(e),
                        "exception_type": type(e).__name__
                    })
                    # await self.db_session.rollback()  # Your DB integration here
                raise

        handler_class._handle = transactional_handle
        return handler_class

    return decorator


def cached_query(
    cache_key_prefix: Optional[str] = None,
    ttl_seconds: Optional[int] = None,
    ttl_delta: Optional[timedelta] = None,
    cache_null_results: bool = False,
    vary_by: Optional[List[str]] = None
):
    """
    Decorator to add caching to query handlers.

    Args:
        cache_key_prefix: Prefix for cache keys (defaults to query name)
        ttl_seconds: Cache TTL in seconds
        ttl_delta: Cache TTL as timedelta (alternative to ttl_seconds)
        cache_null_results: Whether to cache null/empty results
        vary_by: List of query attributes to include in cache key

    Example:
        @cached_query(ttl_seconds=300, vary_by=["user_id", "status"])
        class GetUserOrdersHandler(BaseQueryHandler):
            async def _handle(self, query: GetUserOrdersQuery) -> List[OrderDto]:
                # Results will be cached for 5 minutes
                return orders
    """
    def decorator(handler_class: Type[IQueryHandler]):
        # Calculate TTL
        cache_ttl = None
        if ttl_seconds is not None:
            cache_ttl = ttl_seconds
        elif ttl_delta is not None:
            cache_ttl = int(ttl_delta.total_seconds())

        # Override cache methods
        handler_class._get_cached_result
        handler_class._cache_result

        async def _get_cached_result(self, query):
            cache_key = _build_cache_key(query, cache_key_prefix, vary_by)

            add_span_attributes({
                "cache.key": cache_key,
                "cache.operation": "get",
            })

            # This is simplified - integrate with your cache implementation
            # cached_value = await self.cache.get(cache_key)
            cached_value = None  # Placeholder

            if cached_value is not None:
                add_span_event("cache.hit", {"key": cache_key})
                return cached_value

            add_span_event("cache.miss", {"key": cache_key})
            return None

        async def _cache_result(self, query, result):
            if result is None and not cache_null_results:
                return

            cache_key = _build_cache_key(query, cache_key_prefix, vary_by)

            add_span_attributes({
                "cache.key": cache_key,
                "cache.operation": "set",
                "cache.ttl_seconds": cache_ttl,
            })

            # This is simplified - integrate with your cache implementation
            # await self.cache.set(cache_key, result, ttl=cache_ttl)

            add_span_event("cache.stored", {
                "key": cache_key,
                "ttl_seconds": cache_ttl
            })

        handler_class._get_cached_result = _get_cached_result
        handler_class._cache_result = _cache_result

        return handler_class

    return decorator


def _build_cache_key(
    query: IQuery,
    prefix: Optional[str] = None,
    vary_by: Optional[List[str]] = None
) -> str:
    """Build cache key for query."""
    key_parts = [prefix or query.get_query_name()]

    if vary_by:
        for attr in vary_by:
            if hasattr(query, attr):
                value = getattr(query, attr)
                key_parts.append(f"{attr}={value}")

    return ":".join(key_parts)


def retry_on_failure(
    max_attempts: int = 3,
    delay_seconds: float = 1.0,
    backoff_multiplier: float = 2.0,
    retry_on: Optional[List[Type[Exception]]] = None
):
    """
    Decorator to add retry logic to command/query handlers.

    Args:
        max_attempts: Maximum number of retry attempts
        delay_seconds: Initial delay between retries
        backoff_multiplier: Multiplier for exponential backoff
        retry_on: List of exception types that should trigger retry

    Example:
        @retry_on_failure(max_attempts=3, delay_seconds=0.5)
        class ProcessPaymentHandler(BaseCommandHandler):
            async def _handle(self, command: ProcessPaymentCommand) -> str:
                # Will retry up to 3 times on failure
                return payment_id
    """
    def decorator(handler_class):
        original_handle = handler_class._handle
        retry_exceptions = tuple(retry_on or [Exception])

        @trace_async_function("retry_handler")
        async def retry_handle(self, operation):
            attempt = 1
            delay = delay_seconds

            add_span_attributes({
                "retry.max_attempts": max_attempts,
                "retry.initial_delay": delay_seconds,
                "retry.backoff_multiplier": backoff_multiplier,
            })

            while attempt <= max_attempts:
                try:
                    add_span_event("retry.attempt", {"attempt": attempt})
                    result = await original_handle(self, operation)

                    if attempt > 1:
                        add_span_event("retry.succeeded", {"attempt": attempt})

                    return result

                except retry_exceptions as e:
                    if attempt == max_attempts:
                        add_span_event("retry.exhausted", {
                            "final_attempt": attempt,
                            "error": str(e)
                        })
                        raise

                    add_span_event("retry.failed_attempt", {
                        "attempt": attempt,
                        "error": str(e),
                        "next_delay": delay
                    })

                    await asyncio.sleep(delay)
                    delay *= backoff_multiplier
                    attempt += 1

            # This should never be reached
            raise RuntimeError("Retry logic error")

        handler_class._handle = retry_handle
        return handler_class

    return decorator


def authorize(
    permissions: List[str],
    resource_id_field: Optional[str] = None,
    allow_admin_override: bool = True
):
    """
    Decorator to add authorization to command/query handlers.

    Args:
        permissions: List of required permissions
        resource_id_field: Field name containing resource ID for resource-based authorization
        allow_admin_override: Whether admin users can override permission checks

    Example:
        @authorize(permissions=["user:update"], resource_id_field="user_id")
        class UpdateUserHandler(BaseCommandHandler):
            async def _handle(self, command: UpdateUserCommand) -> None:
                # User must have 'user:update' permission for this user
                pass
    """
    def decorator(handler_class):
        original_authorize = getattr(handler_class, '_authorize_command', None) or getattr(handler_class, '_authorize_query', None)

        async def authorize_operation(self, operation):
            user_id = operation.metadata.user_id
            if not user_id:
                from .exceptions import AuthorizationError
                raise AuthorizationError(
                    operation_name=operation.get_command_name() if hasattr(operation, 'get_command_name') else operation.get_query_name(),
                    required_permissions=permissions
                )

            # This is simplified - integrate with your authorization system
            # user_permissions = await self.auth_service.get_user_permissions(user_id)
            # if not all(perm in user_permissions for perm in permissions):
            #     raise AuthorizationError(...)

            add_span_attributes({
                "auth.user_id": user_id,
                "auth.required_permissions": permissions,
                "auth.resource_field": resource_id_field,
            })

            # Call original authorization if it exists
            if original_authorize:
                await original_authorize(self, operation)

        if hasattr(handler_class, '_authorize_command'):
            handler_class._authorize_command = authorize_operation
        elif hasattr(handler_class, '_authorize_query'):
            handler_class._authorize_query = authorize_operation
        else:
            # Add the method to the class
            handler_class._authorize_command = authorize_operation
            handler_class._authorize_query = authorize_operation

        return handler_class

    return decorator


def validate_input(
    validator_func: Optional[Callable] = None,
    schema_class: Optional[Type] = None,
    strict: bool = True
):
    """
    Decorator to add custom validation to command/query handlers.

    Args:
        validator_func: Custom validation function
        schema_class: Pydantic model class for validation
        strict: Whether validation should be strict

    Example:
        @validate_input(schema_class=CreateUserSchema)
        class CreateUserHandler(BaseCommandHandler):
            async def _handle(self, command: CreateUserCommand) -> str:
                # Command will be validated against CreateUserSchema
                return user_id
    """
    def decorator(handler_class):
        original_validate = getattr(handler_class, '_validate_command', None) or getattr(handler_class, '_validate_query', None)

        async def validate_operation(self, operation):
            # Call original validation first
            if original_validate:
                await original_validate(self, operation)

            # Apply custom validation
            if validator_func:
                validation_result = validator_func(operation)
                if validation_result:  # Non-empty dict means errors
                    from .exceptions import CommandValidationError, QueryValidationError
                    error_class = CommandValidationError if hasattr(operation, 'get_command_name') else QueryValidationError
                    raise error_class(
                        command_name=operation.get_command_name() if hasattr(operation, 'get_command_name') else operation.get_query_name(),
                        validation_errors=validation_result,
                        operation_id=operation.metadata.operation_id
                    )

            if schema_class:
                try:
                    # This would integrate with Pydantic validation
                    # schema_class.parse_obj(operation.__dict__)
                    pass
                except Exception as e:
                    from .exceptions import CommandValidationError, QueryValidationError
                    error_class = CommandValidationError if hasattr(operation, 'get_command_name') else QueryValidationError
                    raise error_class(
                        command_name=operation.get_command_name() if hasattr(operation, 'get_command_name') else operation.get_query_name(),
                        validation_errors={"schema": str(e)},
                        operation_id=operation.metadata.operation_id
                    )

        if hasattr(handler_class, '_validate_command'):
            handler_class._validate_command = validate_operation
        elif hasattr(handler_class, '_validate_query'):
            handler_class._validate_query = validate_operation
        else:
            handler_class._validate_command = validate_operation
            handler_class._validate_query = validate_operation

        return handler_class

    return decorator
