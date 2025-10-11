"""
CQRS interfaces and base types for NeedleAi.

Defines the core abstractions for Command Query Responsibility Segregation pattern.
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, Optional, Type, TypeVar

# Type variables for generic command/query handling
TCommand = TypeVar('TCommand', bound='ICommand')
TQuery = TypeVar('TQuery', bound='IQuery')
TResult = TypeVar('TResult')


class OperationStatus(str, Enum):
    """Status enumeration for command/query operations."""
    SUCCESS = "success"
    FAILED = "failed"
    VALIDATION_ERROR = "validation_error"
    NOT_FOUND = "not_found"
    UNAUTHORIZED = "unauthorized"
    CONFLICT = "conflict"


@dataclass
class OperationMetadata:
    """Metadata for command/query operations."""
    operation_id: str
    timestamp: datetime
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
    source: Optional[str] = None
    version: Optional[str] = None

    @classmethod
    def create(
        cls,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        source: Optional[str] = None,
        version: Optional[str] = None
    ) -> "OperationMetadata":
        """Create new operation metadata with generated ID and timestamp."""
        return cls(
            operation_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            user_id=user_id,
            correlation_id=correlation_id,
            source=source,
            version=version,
        )


class ICommand(ABC):
    """
    Base interface for all commands (write operations).

    Commands represent intentions to change system state and should be named
    with verbs in the imperative form (e.g., CreateUser, UpdateProfile).
    """

    def __init__(self):
        self.metadata = OperationMetadata.create()

    @abstractmethod
    def validate(self) -> Dict[str, Any]:
        """
        Validate command data.

        Returns:
            Dict containing validation results. Empty dict means valid.
            Non-empty dict should contain field names as keys and error messages as values.
        """

    def get_command_name(self) -> str:
        """Get the command name (defaults to class name)."""
        return self.__class__.__name__

    def get_aggregate_id(self) -> Optional[str]:
        """Get the ID of the aggregate this command targets (if applicable)."""
        return getattr(self, 'id', None) or getattr(self, 'aggregate_id', None)


class IQuery(ABC):
    """
    Base interface for all queries (read operations).

    Queries represent requests for data and should be named with nouns
    or questions (e.g., GetUser, FindActiveUsers, UserExists).
    """

    def __init__(self):
        self.metadata = OperationMetadata.create()

    @abstractmethod
    def validate(self) -> Dict[str, Any]:
        """
        Validate query parameters.

        Returns:
            Dict containing validation results. Empty dict means valid.
        """

    def get_query_name(self) -> str:
        """Get the query name (defaults to class name)."""
        return self.__class__.__name__

    def get_cache_key(self) -> Optional[str]:
        """Get cache key for this query (if cacheable)."""
        return None

    def get_cache_ttl(self) -> Optional[int]:
        """Get cache TTL in seconds for this query."""
        return None


@dataclass
class CommandResult(Generic[TResult]):
    """Result of a command execution."""

    status: OperationStatus
    data: Optional[TResult] = None
    errors: Optional[Dict[str, Any]] = None
    metadata: Optional[OperationMetadata] = None
    affected_entities: Optional[Dict[str, Any]] = None

    @property
    def is_success(self) -> bool:
        """Check if command was successful."""
        return self.status == OperationStatus.SUCCESS

    @property
    def is_failure(self) -> bool:
        """Check if command failed."""
        return self.status != OperationStatus.SUCCESS

    @classmethod
    def success(
        cls,
        data: Optional[TResult] = None,
        metadata: Optional[OperationMetadata] = None,
        affected_entities: Optional[Dict[str, Any]] = None
    ) -> "CommandResult[TResult]":
        """Create a successful command result."""
        return cls(
            status=OperationStatus.SUCCESS,
            data=data,
            metadata=metadata,
            affected_entities=affected_entities
        )

    @classmethod
    def failure(
        cls,
        status: OperationStatus,
        errors: Optional[Dict[str, Any]] = None,
        metadata: Optional[OperationMetadata] = None
    ) -> "CommandResult[TResult]":
        """Create a failed command result."""
        return cls(
            status=status,
            errors=errors or {},
            metadata=metadata
        )

    @classmethod
    def validation_error(
        cls,
        errors: Dict[str, Any],
        metadata: Optional[OperationMetadata] = None
    ) -> "CommandResult[TResult]":
        """Create a validation error result."""
        return cls.failure(
            status=OperationStatus.VALIDATION_ERROR,
            errors=errors,
            metadata=metadata
        )


@dataclass
class QueryResult(Generic[TResult]):
    """Result of a query execution."""

    status: OperationStatus
    data: Optional[TResult] = None
    errors: Optional[Dict[str, Any]] = None
    metadata: Optional[OperationMetadata] = None
    pagination: Optional[Dict[str, Any]] = None
    cache_info: Optional[Dict[str, Any]] = None

    @property
    def is_success(self) -> bool:
        """Check if query was successful."""
        return self.status == OperationStatus.SUCCESS

    @property
    def is_failure(self) -> bool:
        """Check if query failed."""
        return self.status != OperationStatus.SUCCESS

    @classmethod
    def success(
        cls,
        data: Optional[TResult] = None,
        metadata: Optional[OperationMetadata] = None,
        pagination: Optional[Dict[str, Any]] = None,
        cache_info: Optional[Dict[str, Any]] = None
    ) -> "QueryResult[TResult]":
        """Create a successful query result."""
        return cls(
            status=OperationStatus.SUCCESS,
            data=data,
            metadata=metadata,
            pagination=pagination,
            cache_info=cache_info
        )

    @classmethod
    def failure(
        cls,
        status: OperationStatus,
        errors: Optional[Dict[str, Any]] = None,
        metadata: Optional[OperationMetadata] = None
    ) -> "QueryResult[TResult]":
        """Create a failed query result."""
        return cls(
            status=status,
            errors=errors or {},
            metadata=metadata
        )

    @classmethod
    def not_found(
        cls,
        message: str = "Resource not found",
        metadata: Optional[OperationMetadata] = None
    ) -> "QueryResult[TResult]":
        """Create a not found result."""
        return cls.failure(
            status=OperationStatus.NOT_FOUND,
            errors={"message": message},
            metadata=metadata
        )


class ICommandHandler(ABC, Generic[TCommand, TResult]):
    """
    Base interface for command handlers.

    Command handlers contain the business logic for executing commands
    and should ensure data consistency and business rule enforcement.
    """

    @abstractmethod
    async def handle(self, command: TCommand) -> CommandResult[TResult]:
        """
        Execute the command and return the result.

        Args:
            command: The command to execute

        Returns:
            CommandResult containing the execution result

        Raises:
            Should not raise exceptions - wrap in CommandResult instead
        """

    def get_command_type(self) -> Type[TCommand]:
        """Get the command type this handler processes."""
        # This would be implemented by concrete handlers
        raise NotImplementedError

    def supports_command(self, command: ICommand) -> bool:
        """Check if this handler supports the given command."""
        return isinstance(command, self.get_command_type())


class IQueryHandler(ABC, Generic[TQuery, TResult]):
    """
    Base interface for query handlers.

    Query handlers contain the logic for retrieving and projecting data
    and should focus on read performance and data presentation.
    """

    @abstractmethod
    async def handle(self, query: TQuery) -> QueryResult[TResult]:
        """
        Execute the query and return the result.

        Args:
            query: The query to execute

        Returns:
            QueryResult containing the query result

        Raises:
            Should not raise exceptions - wrap in QueryResult instead
        """

    def get_query_type(self) -> Type[TQuery]:
        """Get the query type this handler processes."""
        raise NotImplementedError

    def supports_query(self, query: IQuery) -> bool:
        """Check if this handler supports the given query."""
        return isinstance(query, self.get_query_type())


class ICommandBus(ABC):
    """
    Interface for command bus - dispatches commands to appropriate handlers.
    """

    @abstractmethod
    async def execute(self, command: ICommand) -> CommandResult[Any]:
        """
        Execute a command through the appropriate handler.

        Args:
            command: The command to execute

        Returns:
            CommandResult from the handler
        """

    @abstractmethod
    def register_handler(
        self,
        command_type: Type[ICommand],
        handler: ICommandHandler[Any, Any]
    ) -> None:
        """Register a command handler for a specific command type."""


class IQueryBus(ABC):
    """
    Interface for query bus - dispatches queries to appropriate handlers.
    """

    @abstractmethod
    async def execute(self, query: IQuery) -> QueryResult[Any]:
        """
        Execute a query through the appropriate handler.

        Args:
            query: The query to execute

        Returns:
            QueryResult from the handler
        """

    @abstractmethod
    def register_handler(
        self,
        query_type: Type[IQuery],
        handler: IQueryHandler[Any, Any]
    ) -> None:
        """Register a query handler for a specific query type."""


# Common result types for convenience
CommandResultVoid = CommandResult[None]
CommandResultStr = CommandResult[str]
CommandResultInt = CommandResult[int]
CommandResultDict = CommandResult[Dict[str, Any]]

QueryResultList = QueryResult[list]
QueryResultDict = QueryResult[Dict[str, Any]]
QueryResultOptional = QueryResult[Optional[Any]]
