# 🏗️ CQRS Pattern Guide for NeedleAi

> **Command Query Responsibility Segregation** - Enterprise-grade separation of read and write operations

## 🎯 **What You Just Got**

A **complete CQRS implementation** featuring:
- **Command/Query separation** with dedicated handlers
- **Type-safe interfaces** with full async support
- **Automatic handler registration** via decorators
- **Built-in validation** and authorization
- **Distributed tracing** integration
- **Caching support** for queries
- **Transaction management** for commands
- **Retry mechanisms** and error handling
- **Production-ready bus system**

---

## 🚀 **Quick Start**

### **1. Define a Command**

```python
from dataclasses import dataclass
from app.core.cqrs import ICommand
from typing import Dict, Any

@dataclass
class CreateUserCommand(ICommand):
    email: str
    username: str
    password: str
    full_name: str

    def validate(self) -> Dict[str, Any]:
        errors = {}
        if not self.email or "@" not in self.email:
            errors["email"] = "Valid email is required"
        if len(self.password) < 8:
            errors["password"] = "Password must be at least 8 characters"
        return errors
```

### **2. Create a Command Handler**

```python
from app.core.cqrs import BaseCommandHandler, command_handler, transactional

@command_handler(CreateUserCommand)
@transactional()
class CreateUserHandler(BaseCommandHandler[CreateUserCommand, str]):

    async def _handle(self, command: CreateUserCommand) -> str:
        # Your business logic here
        user_id = await self.user_repository.create_user(command)
        return user_id
```

### **3. Define a Query**

```python
@dataclass
class GetUserQuery(IQuery):
    user_id: str

    def validate(self) -> Dict[str, Any]:
        return {"user_id": "Required"} if not self.user_id else {}

    def get_cache_key(self) -> str:
        return f"user:{self.user_id}"

    def get_cache_ttl(self) -> int:
        return 300  # 5 minutes
```

### **4. Create a Query Handler**

```python
from app.core.cqrs import BaseQueryHandler, query_handler, cached_query

@query_handler(GetUserQuery)
@cached_query(ttl_seconds=300)
class GetUserHandler(BaseQueryHandler[GetUserQuery, UserDto]):

    async def _handle(self, query: GetUserQuery) -> UserDto:
        # Your data retrieval logic here
        return await self.user_repository.get_by_id(query.user_id)
```

### **5. Execute Commands and Queries**

```python
from app.core.cqrs import get_cqrs_bus

# Initialize bus (handlers auto-register via decorators)
bus = get_cqrs_bus()

# Execute command
create_command = CreateUserCommand(
    email="user@example.com",
    username="newuser",
    password="securepass123",
    full_name="New User"
)

result = await bus.execute_command(create_command)
if result.is_success:
    user_id = result.data
    print(f"User created: {user_id}")

# Execute query
get_query = GetUserQuery(user_id=user_id)
result = await bus.execute_query(get_query)
if result.is_success:
    user = result.data
    print(f"User retrieved: {user.email}")
```

---

## 🏗️ **Architecture Overview**

```
┌─────────────────────────────────────────────────────────────────┐
│                           CQRS Architecture                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─── Commands (Write) ────┐    ┌─── Queries (Read) ────┐      │
│  │                         │    │                       │      │
│  │  CreateUserCommand      │    │  GetUserQuery         │      │
│  │  UpdateUserCommand      │    │  FindUsersQuery       │      │
│  │  DeleteUserCommand      │    │  GetUserStatsQuery    │      │
│  │                         │    │                       │      │
│  └─────────────────────────┘    └───────────────────────┘      │
│              │                              │                   │
│              ▼                              ▼                   │
│  ┌─────── Command Bus ────────┐  ┌───── Query Bus ──────────┐   │
│  │                           │  │                          │   │
│  │ • Handler Registration    │  │ • Handler Registration   │   │
│  │ • Middleware Pipeline     │  │ • Caching Integration    │   │
│  │ • Transaction Management  │  │ • Result Transformation │   │
│  │ • Error Handling          │  │ • Pagination Support    │   │
│  │                           │  │                          │   │
│  └───────────────────────────┘  └──────────────────────────┘   │
│              │                              │                   │
│              ▼                              ▼                   │
│  ┌─── Command Handlers ────┐    ┌─── Query Handlers ────┐      │
│  │                         │    │                       │      │
│  │ • Business Logic        │    │ • Data Retrieval      │      │
│  │ • Validation            │    │ • Data Projection     │      │
│  │ • Authorization         │    │ • Performance Focus   │      │
│  │ • State Changes         │    │ • Read Models         │      │
│  │                         │    │                       │      │
│  └─────────────────────────┘    └───────────────────────┘      │
│              │                              │                   │
│              ▼                              ▼                   │
│  ┌──── Write Database ────┐    ┌─── Read Database/Cache ───┐   │
│  │                         │    │                           │   │
│  │ • ACID Transactions     │    │ • Optimized for Queries  │   │
│  │ • Consistency Focus     │    │ • Denormalized Views     │   │
│  │ • Data Integrity        │    │ • Caching Layers        │   │
│  │                         │    │                           │   │
│  └─────────────────────────┘    └───────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 **Core Components**

### **Commands (Write Operations)**

Commands represent **intentions to change state**:

```python
@dataclass
class UpdateUserCommand(ICommand):
    user_id: str
    email: Optional[str] = None
    full_name: Optional[str] = None

    def validate(self) -> Dict[str, Any]:
        errors = {}
        if not self.user_id:
            errors["user_id"] = "User ID is required"
        if self.email and "@" not in self.email:
            errors["email"] = "Invalid email format"
        return errors

    def get_aggregate_id(self) -> str:
        return self.user_id  # For event sourcing/aggregates
```

### **Queries (Read Operations)**

Queries represent **requests for data**:

```python
@dataclass
class FindUsersQuery(IQuery):
    email_contains: Optional[str] = None
    role: Optional[UserRole] = None
    page: int = 1
    page_size: int = 20

    def validate(self) -> Dict[str, Any]:
        errors = {}
        if self.page < 1:
            errors["page"] = "Page must be >= 1"
        if not 1 <= self.page_size <= 100:
            errors["page_size"] = "Page size must be 1-100"
        return errors

    def get_cache_key(self) -> str:
        return f"users:find:role={self.role}:page={self.page}"

    def get_cache_ttl(self) -> int:
        return 120  # 2 minutes
```

### **Command Handlers**

Handle **write operations** with business logic:

```python
@command_handler(UpdateUserCommand)
@transactional(isolation_level="REPEATABLE_READ")
@authorize(permissions=["user:update"], resource_id_field="user_id")
@retry_on_failure(max_attempts=3)
class UpdateUserHandler(BaseCommandHandler[UpdateUserCommand, None]):

    async def _handle(self, command: UpdateUserCommand) -> None:
        # 1. Load aggregate/entity
        user = await self.user_repository.get_by_id(command.user_id)
        if not user:
            raise ValueError("User not found")

        # 2. Apply business logic
        if command.email:
            await self._ensure_unique_email(command.email, command.user_id)
            user.email = command.email

        if command.full_name:
            user.full_name = command.full_name

        user.updated_at = datetime.utcnow()

        # 3. Save changes
        await self.user_repository.update(user)

        # 4. Publish domain events (if needed)
        await self.event_publisher.publish(UserUpdatedEvent(user.id, ...))

    async def _ensure_unique_email(self, email: str, exclude_user_id: str):
        existing_user = await self.user_repository.get_by_email(email)
        if existing_user and existing_user.id != exclude_user_id:
            raise ValueError("Email already in use")

    async def _get_affected_entities(
        self,
        command: UpdateUserCommand,
        result: None
    ) -> Dict[str, Any]:
        return {
            "updated": {
                "user": {
                    "id": command.user_id,
                    "fields": ["email", "full_name"] if command.email else ["full_name"]
                }
            }
        }
```

### **Query Handlers**

Handle **read operations** with focus on performance:

```python
@query_handler(FindUsersQuery)
@cached_query(ttl_seconds=120, vary_by=["role", "page", "page_size"])
class FindUsersHandler(BaseQueryHandler[FindUsersQuery, List[UserDto]]):

    async def _handle(self, query: FindUsersQuery) -> List[UserDto]:
        # Use optimized read model or view
        users = await self.user_read_repository.find_users(
            email_contains=query.email_contains,
            role=query.role,
            offset=(query.page - 1) * query.page_size,
            limit=query.page_size
        )

        # Transform to DTOs
        return [UserDto.from_entity(user) for user in users]

    async def _get_pagination_info(
        self,
        query: FindUsersQuery,
        result: List[UserDto]
    ) -> Dict[str, Any]:
        total_count = await self.user_read_repository.count_users(
            email_contains=query.email_contains,
            role=query.role
        )

        total_pages = (total_count + query.page_size - 1) // query.page_size

        return {
            "page": query.page,
            "page_size": query.page_size,
            "total_count": total_count,
            "total_pages": total_pages,
            "has_next": query.page < total_pages,
            "has_previous": query.page > 1
        }
```

---

## 🎨 **Advanced Features**

### **1. Decorators for Cross-Cutting Concerns**

#### **Handler Registration**
```python
@command_handler(CreateUserCommand, timeout_seconds=15.0)
@query_handler(GetUserQuery, cache_enabled=True)
```

#### **Transactions**
```python
@transactional(isolation_level="SERIALIZABLE", rollback_on=[BusinessRuleViolationError])
class CreateOrderHandler(BaseCommandHandler):
    # Handler will run in a transaction
    pass
```

#### **Authorization**
```python
@authorize(permissions=["user:create"], allow_admin_override=True)
class CreateUserHandler(BaseCommandHandler):
    # Handler requires specific permissions
    pass
```

#### **Caching**
```python
@cached_query(
    ttl_seconds=300,
    cache_null_results=False,
    vary_by=["user_id", "include_details"]
)
class GetUserDetailsHandler(BaseQueryHandler):
    # Results cached for 5 minutes
    pass
```

#### **Retry Logic**
```python
@retry_on_failure(
    max_attempts=3,
    delay_seconds=1.0,
    backoff_multiplier=2.0,
    retry_on=[ConnectionError, TimeoutError]
)
class ProcessPaymentHandler(BaseCommandHandler):
    # Retries on specific failures
    pass
```

### **2. Middleware Support**

```python
from app.core.cqrs import get_cqrs_bus

async def audit_middleware(operation, next_handler):
    """Audit all commands and queries."""
    start_time = time.time()

    try:
        result = await next_handler()

        # Log successful operation
        await audit_log.record_operation(
            operation=operation,
            result="success",
            duration=time.time() - start_time
        )

        return result
    except Exception as e:
        # Log failed operation
        await audit_log.record_operation(
            operation=operation,
            result="failed",
            error=str(e),
            duration=time.time() - start_time
        )
        raise

# Register middleware
cqrs_bus = get_cqrs_bus()
cqrs_bus.add_command_middleware(audit_middleware)
cqrs_bus.add_query_middleware(audit_middleware)
```

### **3. Result Handling**

```python
# Command results
result = await bus.execute_command(create_command)

if result.is_success:
    user_id = result.data
    affected = result.affected_entities
    print(f"Created user {user_id}")
else:
    match result.status:
        case OperationStatus.VALIDATION_ERROR:
            print(f"Validation errors: {result.errors}")
        case OperationStatus.UNAUTHORIZED:
            print("Access denied")
        case OperationStatus.FAILED:
            print(f"Execution failed: {result.errors}")

# Query results
result = await bus.execute_query(find_query)

if result.is_success:
    users = result.data
    pagination = result.pagination
    cache_info = result.cache_info

    print(f"Found {len(users)} users")
    print(f"Page {pagination['page']} of {pagination['total_pages']}")
    print(f"Cache hit: {cache_info['hit']}")
```

---

## 🛠️ **Integration with FastAPI**

### **API Endpoints**

```python
from fastapi import APIRouter, Depends, HTTPException
from app.core.cqrs import get_cqrs_bus, CQRSBus

router = APIRouter()

@router.post("/users", response_model=CreateUserResponse)
async def create_user(
    request: CreateUserRequest,
    cqrs_bus: CQRSBus = Depends(get_cqrs_bus)
):
    # Convert request to command
    command = CreateUserCommand(
        email=request.email,
        username=request.username,
        password=request.password,
        full_name=request.full_name
    )

    # Set user context
    command.metadata.user_id = current_user.id  # From auth dependency

    # Execute command
    result = await cqrs_bus.execute_command(command)

    if result.is_failure:
        if result.status == OperationStatus.VALIDATION_ERROR:
            raise HTTPException(status_code=422, detail=result.errors)
        elif result.status == OperationStatus.UNAUTHORIZED:
            raise HTTPException(status_code=403, detail="Access denied")
        else:
            raise HTTPException(status_code=500, detail="Internal server error")

    return CreateUserResponse(
        user_id=result.data,
        message="User created successfully"
    )

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    include_inactive: bool = False,
    cqrs_bus: CQRSBus = Depends(get_cqrs_bus)
):
    query = GetUserQuery(
        user_id=user_id,
        include_inactive=include_inactive
    )

    result = await cqrs_bus.execute_query(query)

    if result.is_failure:
        if result.status == OperationStatus.NOT_FOUND:
            raise HTTPException(status_code=404, detail="User not found")
        else:
            raise HTTPException(status_code=500, detail="Internal server error")

    return UserResponse.from_dto(result.data)

@router.get("/users", response_model=FindUsersResponse)
async def find_users(
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    page: int = 1,
    page_size: int = 20,
    cqrs_bus: CQRSBus = Depends(get_cqrs_bus)
):
    query = FindUsersQuery(
        role=role,
        is_active=is_active,
        page=page,
        page_size=page_size
    )

    result = await cqrs_bus.execute_query(query)

    if result.is_failure:
        raise HTTPException(status_code=500, detail="Internal server error")

    return FindUsersResponse(
        users=[UserResponse.from_dto(user) for user in result.data],
        pagination=result.pagination
    )
```

### **Dependency Injection Integration**

```python
# In app/dependencies.py
from app.core.cqrs import CQRSBus, get_cqrs_bus

async def get_cqrs_bus_dependency() -> CQRSBus:
    """Get CQRS bus for dependency injection."""
    return get_cqrs_bus()

# In app/core/container.py
def _configure_services(container: DIContainer):
    # ... other services ...

    # Register CQRS bus as singleton
    container.register_singleton(CQRSBus, factory=get_cqrs_bus_dependency)
```

---

## 📊 **Performance Considerations**

### **1. Query Optimization**

```python
@query_handler(GetUserDashboardQuery)
@cached_query(ttl_seconds=300)
class GetUserDashboardHandler(BaseQueryHandler):

    async def _handle(self, query: GetUserDashboardQuery) -> UserDashboardDto:
        # Use specialized read model for dashboard
        dashboard_data = await self.dashboard_read_repository.get_user_dashboard(
            user_id=query.user_id
        )

        # Parallel data fetching
        recent_orders, notifications, stats = await asyncio.gather(
            self.order_repository.get_recent_orders(query.user_id, limit=5),
            self.notification_repository.get_unread(query.user_id, limit=10),
            self.analytics_repository.get_user_stats(query.user_id)
        )

        return UserDashboardDto(
            user=dashboard_data.user,
            recent_orders=recent_orders,
            notifications=notifications,
            stats=stats
        )
```

### **2. Command Batching**

```python
@dataclass
class BatchCreateUsersCommand(ICommand):
    users: List[CreateUserRequest]

    def validate(self) -> Dict[str, Any]:
        errors = {}
        if not self.users:
            errors["users"] = "At least one user required"
        if len(self.users) > 100:
            errors["users"] = "Maximum 100 users per batch"
        return errors

@command_handler(BatchCreateUsersCommand)
@transactional()
class BatchCreateUsersHandler(BaseCommandHandler[BatchCreateUsersCommand, List[str]]):

    async def _handle(self, command: BatchCreateUsersCommand) -> List[str]:
        # Process in smaller chunks to avoid long transactions
        user_ids = []
        chunk_size = 10

        for i in range(0, len(command.users), chunk_size):
            chunk = command.users[i:i + chunk_size]
            chunk_ids = await self._create_user_chunk(chunk)
            user_ids.extend(chunk_ids)

        return user_ids

    async def _create_user_chunk(self, users: List[CreateUserRequest]) -> List[str]:
        # Bulk operations for better performance
        return await self.user_repository.bulk_create(users)
```

### **3. Caching Strategies**

```python
@query_handler(GetUserOrdersQuery)
class GetUserOrdersHandler(BaseQueryHandler):

    async def _get_cached_result(self, query: GetUserOrdersQuery):
        # Multi-level caching

        # 1. Check memory cache first
        cache_key = query.get_cache_key()
        result = await self.memory_cache.get(cache_key)
        if result:
            return result

        # 2. Check Redis cache
        result = await self.redis_cache.get(cache_key)
        if result:
            # Store in memory cache for faster access
            await self.memory_cache.set(cache_key, result, ttl=60)
            return result

        return None

    async def _cache_result(self, query: GetUserOrdersQuery, result):
        cache_key = query.get_cache_key()

        # Store in both caches
        await asyncio.gather(
            self.memory_cache.set(cache_key, result, ttl=60),
            self.redis_cache.set(cache_key, result, ttl=300)
        )
```

---

## 🧪 **Testing CQRS Components**

### **1. Command Handler Testing**

```python
import pytest
from app.core.cqrs import CreateUserCommand
from app.handlers.user.create_user_handler import CreateUserHandler

class TestCreateUserHandler:

    @pytest.fixture
    def handler(self):
        return CreateUserHandler()

    @pytest.mark.asyncio
    async def test_create_user_success(self, handler):
        # Arrange
        command = CreateUserCommand(
            email="test@example.com",
            username="testuser",
            password="securepass123",
            full_name="Test User"
        )

        # Act
        result = await handler.handle(command)

        # Assert
        assert result.is_success
        assert result.data is not None
        assert result.affected_entities["created"]["user"]["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_create_user_validation_error(self, handler):
        # Arrange
        command = CreateUserCommand(
            email="invalid-email",
            username="",
            password="short",
            full_name=""
        )

        # Act
        result = await handler.handle(command)

        # Assert
        assert result.is_failure
        assert result.status == OperationStatus.VALIDATION_ERROR
        assert "email" in result.errors
        assert "username" in result.errors
        assert "password" in result.errors
```

### **2. Query Handler Testing**

```python
class TestGetUserHandler:

    @pytest.fixture
    def handler(self):
        return GetUserHandler()

    @pytest.mark.asyncio
    async def test_get_user_success(self, handler):
        # Arrange
        query = GetUserQuery(user_id="user123")

        # Act
        result = await handler.handle(query)

        # Assert
        assert result.is_success
        assert result.data.id == "user123"
        assert result.cache_info is not None

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, handler):
        # Arrange
        query = GetUserQuery(user_id="nonexistent")

        # Act
        result = await handler.handle(query)

        # Assert
        assert result.is_success
        assert result.data is None
```

### **3. Integration Testing**

```python
class TestUserManagementFlow:

    @pytest.mark.asyncio
    async def test_complete_user_lifecycle(self, cqrs_bus):
        # Create user
        create_command = CreateUserCommand(
            email="integration@example.com",
            username="integrationuser",
            password="securepass123",
            full_name="Integration User"
        )

        create_result = await cqrs_bus.execute_command(create_command)
        assert create_result.is_success
        user_id = create_result.data

        # Get user
        get_query = GetUserQuery(user_id=user_id)
        get_result = await cqrs_bus.execute_query(get_query)
        assert get_result.is_success
        assert get_result.data.email == "integration@example.com"

        # Update user
        update_command = UpdateUserCommand(
            user_id=user_id,
            full_name="Updated Integration User"
        )

        update_result = await cqrs_bus.execute_command(update_command)
        assert update_result.is_success

        # Verify update
        get_result = await cqrs_bus.execute_query(get_query)
        assert get_result.data.full_name == "Updated Integration User"
```

---

## 🚀 **Production Deployment**

### **1. Handler Registration**

```python
# In app/main.py or startup module
from app.core.cqrs import initialize_cqrs_bus
from app.handlers import user_handlers, order_handlers, payment_handlers

async def setup_cqrs():
    """Initialize CQRS bus with all handlers."""
    cqrs_bus = initialize_cqrs_bus(allow_handler_override=False)

    # Handlers auto-register via decorators, but you can also register manually:
    # cqrs_bus.register_command_handlers(user_handlers.get_command_handlers())
    # cqrs_bus.register_query_handlers(user_handlers.get_query_handlers())

    logger.info(f"CQRS bus initialized with {cqrs_bus.get_handler_count()['total']} handlers")
    return cqrs_bus

# In FastAPI startup
@app.on_event("startup")
async def startup_event():
    await setup_cqrs()
```

### **2. Monitoring and Metrics**

```python
# Custom middleware for metrics
async def metrics_middleware(operation, next_handler):
    """Collect metrics for all CQRS operations."""
    operation_type = "command" if hasattr(operation, 'get_command_name') else "query"
    operation_name = operation.get_command_name() if operation_type == "command" else operation.get_query_name()

    # Start timer
    start_time = time.time()

    # Increment counter
    CQRS_OPERATIONS_TOTAL.labels(
        operation_type=operation_type,
        operation_name=operation_name
    ).inc()

    try:
        result = await next_handler()

        # Record success metrics
        CQRS_OPERATIONS_DURATION.labels(
            operation_type=operation_type,
            operation_name=operation_name,
            status="success"
        ).observe(time.time() - start_time)

        return result

    except Exception as e:
        # Record error metrics
        CQRS_OPERATIONS_DURATION.labels(
            operation_type=operation_type,
            operation_name=operation_name,
            status="error"
        ).observe(time.time() - start_time)

        CQRS_OPERATIONS_ERRORS.labels(
            operation_type=operation_type,
            operation_name=operation_name,
            error_type=type(e).__name__
        ).inc()

        raise
```

### **3. Error Handling and Alerting**

```python
# Global error handler
async def error_handling_middleware(operation, next_handler):
    """Handle and report errors."""
    try:
        return await next_handler()
    except Exception as e:
        # Log error with context
        logger.error(
            f"CQRS operation failed: {operation.__class__.__name__}",
            extra={
                "operation_id": operation.metadata.operation_id,
                "user_id": operation.metadata.user_id,
                "error_type": type(e).__name__,
                "error_message": str(e)
            },
            exc_info=True
        )

        # Send alert for critical errors
        if isinstance(e, (DatabaseError, ExternalServiceError)):
            await alert_service.send_alert(
                level="critical",
                message=f"CQRS operation failed: {e}",
                context={"operation": operation.__class__.__name__}
            )

        raise
```

---

## 📚 **Best Practices**

### **1. Command Design**
- ✅ Use **imperative names** (CreateUser, UpdateOrder, CancelPayment)
- ✅ Include **all required data** for the operation
- ✅ Implement **thorough validation**
- ✅ Make commands **immutable** (dataclasses with frozen=True)
- ✅ Include **business context** in command names

### **2. Query Design**
- ✅ Use **descriptive names** (GetUser, FindActiveUsers, GetOrderHistory)
- ✅ Include **filtering and pagination** parameters
- ✅ Implement **caching strategies** for expensive queries
- ✅ Design for **specific use cases** rather than generic queries
- ✅ Consider **eventual consistency** in read models

### **3. Handler Implementation**
- ✅ Keep handlers **focused and single-purpose**
- ✅ Use **dependency injection** for external services
- ✅ Implement **proper error handling**
- ✅ Add **comprehensive logging** and tracing
- ✅ Use **transactions** for data consistency
- ✅ Validate **business rules** in command handlers
- ✅ Optimize **query performance** in query handlers

### **4. Testing Strategy**
- ✅ **Unit test** each handler independently
- ✅ **Mock external dependencies** in tests
- ✅ Test **validation logic** thoroughly
- ✅ Add **integration tests** for complete flows
- ✅ Test **error scenarios** and edge cases
- ✅ Use **test fixtures** for consistent test data

---

## 🎯 **Next Steps**

1. **Start Simple**: Begin with basic CQRS for one domain (e.g., User management)
2. **Add Decorators**: Use `@command_handler` and `@query_handler` decorators
3. **Implement Caching**: Add `@cached_query` for expensive queries
4. **Add Authorization**: Use `@authorize` decorator for secured operations
5. **Monitor Performance**: Add metrics and tracing to identify bottlenecks
6. **Scale Gradually**: Expand to other domains as you gain experience

---

**🎉 You now have enterprise-grade CQRS implementation!** Start with simple commands and queries, then gradually add advanced features like caching, transactions, and authorization as your application grows.
