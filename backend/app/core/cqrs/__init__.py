"""
CQRS (Command Query Responsibility Segregation) implementation for NeedleAi.

This package provides the infrastructure for separating command (write) operations
from query (read) operations, improving performance, scalability, and maintainability.
"""

from .bus import CommandBus, CQRSBus, QueryBus
from .decorators import cached_query, command_handler, query_handler, transactional
from .exceptions import (
    CommandHandlerNotFoundError,
    CommandValidationError,
    CQRSError,
    QueryHandlerNotFoundError,
    QueryValidationError,
)
from .handlers import BaseCommandHandler, BaseQueryHandler
from .interfaces import (
    CommandResult,
    ICommand,
    ICommandBus,
    ICommandHandler,
    IQuery,
    IQueryBus,
    IQueryHandler,
    QueryResult,
)

__all__ = [
    # Interfaces
    "ICommand",
    "IQuery",
    "ICommandHandler",
    "IQueryHandler",
    "ICommandBus",
    "IQueryBus",
    "CommandResult",
    "QueryResult",

    # Base classes
    "BaseCommandHandler",
    "BaseQueryHandler",

    # Bus implementations
    "CommandBus",
    "QueryBus",
    "CQRSBus",

    # Decorators
    "command_handler",
    "query_handler",
    "transactional",
    "cached_query",

    # Exceptions
    "CQRSError",
    "CommandHandlerNotFoundError",
    "QueryHandlerNotFoundError",
    "CommandValidationError",
    "QueryValidationError",
]
