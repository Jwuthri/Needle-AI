# NeedleAi Backend

A FastAPI + Next.js AI agent application with OpenRouter and Agno

A modern, production-ready FastAPI backend for AI-powered chat applications with comprehensive LLM support, real-time messaging, enterprise-grade architecture, advanced monitoring, and robust security features.

## ✨ Recent Improvements (v2.0)

This cookiecutter template has been significantly enhanced with enterprise-ready features:

### 🏗️ **Dependency Injection Container**
- **Proper DI System**: Replaced globals with a comprehensive DI container supporting singleton, scoped, and transient services
- **Request Scoping**: Automatic cleanup of request-scoped services with proper lifecycle management
- **Service Health**: Built-in service initialization, health checking, and graceful shutdown

### 🗄️ **Async Database Architecture**
- **Full Async Support**: Complete async database layer with SQLAlchemy 2.0+ and asyncpg/aiosqlite
- **Transaction Management**: Proper async transaction handling with context managers and rollback support
- **Connection Pooling**: Production-ready connection pools with health checks and automatic reconnection
- **Enhanced Repositories**: Async base repository with bulk operations, eager loading, and error handling

### ⚙️ **Advanced Configuration System**
- **Environment-Specific Settings**: Separate configurations for development, testing, staging, and production
- **Secrets Management**: Multi-provider secrets support (env vars, Docker secrets, K8s secrets, files, Vault)
- **Comprehensive Validation**: Startup configuration validation with detailed error reporting and environment checks
- **Pydantic v2**: Full type safety with advanced validation and serialization

### 🚨 **Enhanced Error Handling**
- **Structured Exceptions**: Rich exception system with context, tracing, and categorization
- **Error Tracking**: Built-in error aggregation and reporting with severity levels
- **Retry Mechanisms**: Exponential backoff, circuit breakers, and resilience patterns
- **Request Context**: Automatic error correlation with request IDs, user context, and stack traces

### 🔧 **Production Enhancements**
- **Request Middleware**: Comprehensive middleware stack with logging, security headers, and cleanup
- **Health Monitoring**: Deep health checks for all service dependencies
- **Performance Monitoring**: Built-in metrics collection with Prometheus support
- **Security Hardening**: Environment-specific security policies and validation

## 🔄 Migration Guide (v1.x → v2.0)

If you're upgrading from v1.x, here are the key breaking changes:

### 🏗️ Dependency Injection
**Old:** Global service instances → **New:** DI container with request scoping
```python
# Before (v1.x)
redis_client = get_redis_client()  # Global instance

# After (v2.0)
async def endpoint(redis: RedisClient = Depends(get_redis_client)):
    # Properly scoped and managed
```

### 🗄️ Database Layer
**Old:** Sync operations → **New:** Full async with transaction management
```python
# Before (v1.x)
def create_user(db: Session, data: dict):
    user = User(**data)
    db.add(user); db.commit()

# After (v2.0)
async def create_user(session: AsyncSession, data: CreateSchema):
    async with get_async_transaction() as tx:
        repo = AsyncBaseRepository(User)
        return await repo.create(tx, data)
```

### ⚙️ Configuration System
**Old:** Basic settings → **New:** Environment-aware with secrets management
```python
# Before (v1.x)
settings = get_settings()

# After (v2.0)
settings = get_settings(environment="production", validate=True)
api_key = settings.get_secret("openrouter_api_key")  # Multi-provider secrets
```

### 🚨 Error Handling
**Old:** Basic HTTP exceptions → **New:** Rich context with tracking
```python
# Before (v1.x)
raise HTTPException(400, "Validation failed")

# After (v2.0)
raise ValidationError(
    message="User validation failed",
    field="email",
    context={"user_id": user.id}
)  # Auto-tracked with request correlation
```

## 🚀 Features

### Core Features
- **🤖 Multiple LLM Providers**: OpenAI, Anthropic, HuggingFace, and custom implementations
- **💬 Real-time Chat**: WebSocket support for instant messaging
- **🧠 Conversation Memory**: Redis-based session storage with fallback to in-memory
- **📊 Message Queuing**: Kafka and RabbitMQ integration for scalable event processing
- **🔐 Enterprise Security**: Database-backed authentication, password policies, JWT management
- **📚 Auto Documentation**: Interactive Swagger/ReDoc API documentation
- **⚙️ Background Tasks**: Celery worker support with Redis backend

### 🛡️ Security & Authentication
- **🔒 Database Authentication**: Secure user management with password policies
- **🔑 API Key Management**: Full API key lifecycle with permissions and usage tracking
- **⚡ JWT Tokens**: Secure, configurable token management with proper validation
- **📋 Configuration Validation**: Startup validation preventing insecure deployments
- **🛡️ Security Headers**: CORS, rate limiting, and comprehensive middleware
- **🔍 Input Validation**: Comprehensive request validation with detailed error responses

### 📊 Monitoring & Observability
- **📈 Application Metrics**: Request counts, response times, error rates, resource usage
- **🏥 Health Checks**: Comprehensive service dependency monitoring
- **💾 System Monitoring**: CPU, memory, disk usage tracking
- **🎯 Endpoint Analytics**: Per-endpoint performance statistics
- **📉 Prometheus Support**: Standard metrics format for external monitoring
- **🔔 Performance Tracking**: Function-level performance monitoring with decorators

### 🗄️ Database & Performance
- **💾 SQLAlchemy ORM**: Full database integration with PostgreSQL/SQLite
- **🔄 Transaction Management**: Atomic operations with rollback support
- **⚡ Query Optimization**: N+1 query prevention with eager loading
- **📦 Repository Pattern**: Clean data access layer with CRUD operations
- **🔍 Database Migrations**: Alembic integration for schema versioning
- **📊 Analytics Queries**: Optimized queries for reporting and statistics

### Architecture & Design
- **🏗️ Clean Architecture**: Layered design with clear separation of concerns
- **🔄 Dependency Injection**: Comprehensive DI container for all services
- **🏭 Factory Pattern**: Flexible LLM provider switching
- **📦 Repository Pattern**: Database abstraction with multiple backends
- **⚡ Service Layer**: Business logic separation with transaction support
- **🛡️ Exception Handling**: Standardized error responses with detailed validation

### 🧪 Testing & Quality
- **✅ Comprehensive Tests**: Unit tests, integration tests, and API testing
- **🎭 Mock Services**: Isolated testing with mocked external dependencies
- **📊 Test Coverage**: Database operations, authentication, API endpoints
- **🔧 Test Fixtures**: Reusable test data and service configurations
- **⚙️ Automated Testing**: Test suite ready for CI/CD integration

### Production Ready
- **🐳 Docker Support**: Multi-stage builds with development and production configurations
- **📊 Health Checks**: Comprehensive service monitoring with dependency checks
- **📝 Structured Logging**: Advanced logging with request tracing and performance metrics
- **🎯 Performance**: Optimized database queries and response caching
- **⚙️ Configuration Management**: Environment validation and secure defaults

## 🏗️ Architecture

```
├── app/
│   ├── main.py                 # FastAPI application entry point with lifespan management
│   ├── config.py               # Application configuration with validation
│   ├── dependencies.py         # Dependency injection container
│   ├── middleware.py           # Custom middleware stack
│   ├── exceptions.py           # Standardized exception handlers
│   │
│   ├── api/                    # API layer with standardized responses
│   │   ├── deps.py            # API-specific dependencies
│   │   ├── response_wrapper.py # Standardized response utilities
│   │   └── v1/                # API version 1
│   │       ├── router.py      # Main API router
│   │       ├── chat.py        # Chat endpoints
│   │       ├── completions.py # Text completion endpoints
│   │       ├── health.py      # Comprehensive health checks
│   │       ├── tasks.py       # Background task management
│   │       └── metrics.py     # Monitoring and metrics endpoints
│   │
│   ├── core/                   # Business logic core
│   │   ├── config_validator.py # Configuration validation utilities
│   │   ├── monitoring.py      # Metrics collection and observability
│   │   ├── celery_app.py      # Celery application configuration
│   │   ├── llm/               # LLM implementations
│   │   │   ├── base.py        # Abstract LLM interface
│   │   │   ├── openrouter_client.py
│   │   │   ├── custom_client.py
│   │   │   └── factory.py     # LLM provider factory
│   │   ├── memory/            # Conversation memory systems (Agno + custom)
│   │   │   ├── base.py        # Memory interface
│   │   │   ├── agno_memory.py # Agno-based implementations (preferred)
│   │   │   ├── factory.py     # Smart memory factory with Agno-first approach
│   │   │   ├── redis_memory.py # Custom Redis implementation (fallback)
│   │   │   └── in_memory.py   # Custom in-memory implementation (fallback)
│   │   └── security/          # Security and authentication
│   │       ├── auth.py        # Database-backed authentication
│   │       └── rate_limit.py  # Rate limiting middleware
│   │
│   ├── database/              # Database layer
│   │   ├── base.py           # SQLAlchemy base and session management
│   │   ├── transaction.py    # Transaction management utilities
│   │   ├── models/           # SQLAlchemy database models
│   │   │   ├── user.py       # User model
│   │   │   ├── chat_session.py # Chat session model
│   │   │   ├── chat_message.py # Chat message model
│   │   │   ├── completion.py # Completion model
│   │   │   ├── api_key.py    # API key model
│   │   │   └── task_result.py # Background task result model
│   │   └── repositories/     # Data access layer (CRUD operations)
│   │       ├── user.py       # User repository
│   │       ├── chat_session.py # Chat session repository
│   │       ├── chat_message.py # Chat message repository
│   │       ├── completion.py # Completion repository
│   │       ├── api_key.py    # API key repository
│   │       ├── task_result.py # Task result repository
│   │       └── model_converter.py # Model conversion utilities
│   │
│   ├── models/                 # Pydantic API models
│   │   ├── base.py            # Base response models and error handling
│   │   ├── chat.py            # Chat-related API models
│   │   ├── completion.py      # Completion API models
│   │   ├── user.py            # User management API models
│   │   ├── api_key.py         # API key management models
│   │   └── task.py            # Background task models
│   │
│   ├── services/               # Business services
│   │   ├── chat_service.py    # Chat business logic
│   │   ├── database_chat_service.py # Database-backed chat service
│   │   ├── completion_service.py
│   │   ├── conversation_service.py
│   │   ├── redis_client.py    # Redis integration
│   │   ├── kafka_client.py    # Kafka integration
│   │   └── rabbitmq_client.py # RabbitMQ integration
│   │
│   ├── tasks/                  # Celery background tasks
│   │   ├── llm_tasks.py       # LLM processing tasks
│   │   ├── chat_tasks.py      # Chat processing tasks
│   │   └── general_tasks.py   # General system tasks
│   │
│   ├── cli/                    # Command line interface
│   │   ├── main.py           # CLI entry point
│   │   ├── router.py         # CLI command routing
│   │   └── commands/         # CLI command implementations
│   │       ├── database.py   # Database management commands
│   │       ├── worker.py     # Celery worker management
│   │       ├── server.py     # Server management
│   │       └── health.py     # Health check commands
│   │
│   └── utils/                  # Utilities
│       ├── logging.py         # Logging configuration
│       └── helpers.py         # Helper functions
├── tests/                      # Comprehensive test suite
│   ├── conftest.py            # Test configuration and fixtures
│   ├── unit/                  # Unit tests
│   │   ├── test_auth.py       # Authentication tests
│   │   └── test_repositories.py # Database repository tests
│   └── integration/           # Integration tests
│       └── test_health_api.py # API integration tests
├── alembic/                    # Database migrations
│   ├── env.py                 # Alembic environment
│   └── versions/              # Migration files
├── config_template.env        # Environment configuration template
└── IMPROVEMENTS_SUMMARY.md    # Documentation of recent improvements
```

## 🚦 Quick Start

### Prerequisites

- **Python**: 3.11+
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **uv**: Latest (automatically installed in Docker)

### 1. Configuration Setup

**Create Environment Configuration:**

```bash
# Copy the configuration template
cp config_template.env .env

# Edit your configuration (IMPORTANT!)
nano .env  # or use your preferred editor
```

**Critical Settings to Configure:**

```bash
# Security (REQUIRED - Change these!)
SECRET_KEY=your-super-secret-key-minimum-32-characters-long
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/needleai
# or for SQLite: DATABASE_URL=sqlite:///./data/needleai.db

# LLM Provider
OPENROUTER_API_KEY=your-openrouter-api-key-here
DEFAULT_MODEL=gpt-5

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
```

**💡 Pro Tip:** The app validates your configuration on startup and will show helpful error messages if something is misconfigured!

### 2. Development Setup

```bash
# Start development environment with all services
docker-compose up -d

# Or use the convenience script
./scripts/start.sh development

# Check service status
./scripts/status.sh

# View logs
docker-compose logs -f backend
```

### 3. Database Setup

```bash
# Initialize database
uv run python -m app.cli database init

# Run migrations
uv run python -m app.cli database migrate

# Seed with sample data (optional)
uv run python -m app.cli database seed
```

# Database (if using PostgreSQL)

DATABASE_URL=postgresql://postgres:postgres@localhost:5432/needleai

```

### 4. Access the Application

Once started, the following services will be available:

| Service | URL | Description |
|---------|-----|-------------|
| **🚀 Backend API** | http://localhost:8000 | Main API server |
| **📚 API Documentation** | http://localhost:8000/docs | Interactive Swagger UI |
| **🏥 Health Checks** | http://localhost:8000/api/v1/health/ | Comprehensive service monitoring |
| **📊 Metrics Dashboard** | http://localhost:8000/api/v1/metrics/summary | Application performance metrics |
| **🔍 Health Status** | http://localhost:8000/api/v1/health/ready | Kubernetes readiness probe |
| **📈 Prometheus Metrics** | http://localhost:8000/api/v1/metrics/prometheus | Monitoring integration |

| **🗄️ pgAdmin** | http://localhost:5050 | Database management (admin@needleai.local / admin) |

| **🐰 RabbitMQ Management** | http://localhost:15672 | Message queue management (guest/guest) |
| **🌸 Flower (Celery)** | http://localhost:5555 | Task queue monitoring |

### ⚡ Quick Health Check

```bash
# Check if everything is running
curl "http://localhost:8000/api/v1/health/" | python -m json.tool

# Get metrics summary
curl "http://localhost:8000/api/v1/metrics/summary" | python -m json.tool

# Test a simple chat message
curl -X POST "http://localhost:8000/api/v1/chat/" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello! Are you working?"}' | python -m json.tool
```

## 🐳 Docker Usage

### Development

```bash
# Start all development services
./scripts/start.sh development

# Start with specific profiles (optional UIs)
docker-compose -f docker/docker-compose.dev.yml --profile kafka-ui --profile redis-ui up -d

# Stop services
./scripts/stop.sh development
```

### Production

```bash
# Deploy to production
./scripts/deploy.sh production

# Or start manually
./scripts/start.sh production

# Stop production services
./scripts/stop.sh production
```

## 📡 API Usage & New Features

### 🏥 Enhanced Health Checks

```bash
# Comprehensive health check (all services)
curl "http://localhost:8000/api/v1/health/"

# Individual service health checks
curl "http://localhost:8000/api/v1/health/database"
curl "http://localhost:8000/api/v1/health/redis"
curl "http://localhost:8000/api/v1/health/kafka"

# Kubernetes readiness probe
curl "http://localhost:8000/api/v1/health/ready"

# Liveness probe
curl "http://localhost:8000/api/v1/health/live"
```

### 📊 Monitoring & Metrics

```bash
# Application metrics overview
curl "http://localhost:8000/api/v1/metrics/"

# Quick metrics summary
curl "http://localhost:8000/api/v1/metrics/summary"

# Per-endpoint performance statistics
curl "http://localhost:8000/api/v1/metrics/endpoints"

# System resource usage
curl "http://localhost:8000/api/v1/metrics/system"

# Health checks status
curl "http://localhost:8000/api/v1/metrics/health-checks"

# Prometheus-format metrics (for external monitoring)
curl "http://localhost:8000/api/v1/metrics/prometheus"
```

### 💬 Chat Endpoints

```bash
# Send a chat message
curl -X POST "http://localhost:8000/api/v1/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, how are you?",
    "session_id": "optional-session-id",
    "context": {"user_preference": "casual"}
  }'

# Get chat history
curl "http://localhost:8000/api/v1/chat/sessions/SESSION_ID/messages?limit=50"

# List user sessions
curl "http://localhost:8000/api/v1/chat/sessions?limit=20"

# Create new chat session
curl -X POST "http://localhost:8000/api/v1/chat/sessions" \
  -H "Content-Type: application/json" \
  -d '{"title": "New Conversation", "model_name": "gpt-4o-mini"}'
```

### ⚡ Text Completion

```bash
# Generate text completion
curl -X POST "http://localhost:8000/api/v1/completions/" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Write a short story about AI",
    "max_tokens": 200,
    "temperature": 0.8,
    "model": "gpt-4o-mini"
  }'

# Streaming completion
curl -X POST "http://localhost:8000/api/v1/completions/stream" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Tell me about FastAPI", "max_tokens": 100}' \
  --no-buffer
```

### 🔧 Background Tasks

```bash
# Submit a background task
curl -X POST "http://localhost:8000/api/v1/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "app.tasks.llm_tasks.generate_completion",
    "task_kwargs": {
      "prompt": "Generate a summary",
      "max_tokens": 100
    },
    "priority": "normal"
  }'

# Check task status
curl "http://localhost:8000/api/v1/tasks/TASK_ID"

# List all tasks
curl "http://localhost:8000/api/v1/tasks/?limit=20&offset=0"

# Cancel a task
curl -X DELETE "http://localhost:8000/api/v1/tasks/TASK_ID"

# Task system status
curl "http://localhost:8000/api/v1/tasks/stats"
```

## 🧪 Testing

The backend now includes a comprehensive test suite covering all functionality.

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=app --cov-report=html --cov-report=term

# Run specific test categories
uv run pytest tests/unit/          # Unit tests only
uv run pytest tests/integration/   # Integration tests only

# Run specific test file
uv run pytest tests/unit/test_auth.py

# Run with detailed output
uv run pytest -v -s

# Run tests matching a pattern
uv run pytest -k "test_auth" -v
```

### Test Coverage

The test suite includes:

- **Authentication Tests**: Password validation, JWT tokens, database auth provider
- **Repository Tests**: Database CRUD operations, relationships, pagination
- **API Integration Tests**: Health checks, error handling, concurrent requests
- **Service Tests**: Business logic, external service integration
- **Configuration Tests**: Environment validation, security checks

### Test Environment

Tests use:
- In-memory SQLite database for isolation
- Mocked external services (LLM providers, Redis, etc.)
- Factory fixtures for test data generation
- Async test support for concurrent operations

## 🎯 CLI Commands

The backend provides a comprehensive CLI for management tasks.

### Database Management

```bash
# Initialize database
uv run python -m app.cli database init

# Run migrations
uv run python -m app.cli database migrate

# Create new migration
uv run python -m app.cli database migration "Add user table"

# Reset database (WARNING: Deletes all data)
uv run python -m app.cli database reset --confirm

# Seed with sample data
uv run python -m app.cli database seed

# Database status and statistics
uv run python -m app.cli database status

# Clean up old records
uv run python -m app.cli database cleanup --days 30
```

### Celery Worker Management

```bash
# Start Celery worker
uv run python -m app.cli worker start

# Start worker with specific concurrency
uv run python -m app.cli worker start --concurrency 4

# Start worker for specific queues
uv run python -m app.cli worker start --queues high_priority,normal

# Monitor worker status
uv run python -m app.cli worker status

# Stop all workers gracefully
uv run python -m app.cli worker stop

# Purge task queues
uv run python -m app.cli worker purge --confirm
```

### Server Management

```bash
# Start development server
uv run python -m app.cli server start --port 8000 --reload

# Check system health
uv run python -m app.cli health check

# Validate configuration
uv run python -m app.cli health config

# Service dependencies status
uv run python -m app.cli health services
```

### Cache Management

```bash
# Clear all cache
uv run python -m app.cli cache clear

# Show cache statistics
uv run python -m app.cli cache stats

# Clear specific cache keys
uv run python -m app.cli cache clear --pattern "user:*"
```

### Logging and Debugging

```bash
# Show recent logs
uv run python -m app.cli logs show --lines 100

# Follow logs in real-time
uv run python -m app.cli logs follow

# Show error logs only
uv run python -m app.cli logs show --level ERROR

# Export logs for debugging
uv run python -m app.cli logs export --output debug.log --hours 24
```

## 📊 Monitoring & Observability

### Application Metrics

The backend automatically collects comprehensive metrics:

- **Request Metrics**: Count, response time, error rate per endpoint
- **System Metrics**: CPU, memory, disk usage
- **Database Metrics**: Query count, slow queries, connection pool status
- **Task Metrics**: Celery task counts, success/failure rates, queue length
- **Security Metrics**: Failed authentication attempts, rate limiting hits

### Access Monitoring Data

**Via Web Interface:**
- API Documentation: http://localhost:8000/docs
- Metrics Summary: http://localhost:8000/api/v1/metrics/summary
- Health Dashboard: http://localhost:8000/api/v1/health/

**Via CLI:**
```bash
# Real-time metrics
uv run python -m app.cli health check --verbose

# System resource usage
uv run python -m app.cli health system

# Database performance
uv run python -m app.cli database status --performance
```

**Integration with External Monitoring:**

```bash
# Prometheus metrics endpoint
curl "http://localhost:8000/api/v1/metrics/prometheus"

# Health check for uptime monitoring
curl "http://localhost:8000/api/v1/health/ready"
```

### Performance Monitoring

Use the performance monitoring decorator in your code:

```python
from app.core.monitoring import performance_monitor, request_context

@performance_monitor("complex_operation")
async def complex_function():
    # Your code here
    pass

# Or use context manager
async with request_context("batch_processing"):
    # Batch processing code
    pass
```

## 🔧 Configuration

### LLM Providers

The application supports multiple LLM providers:



**Switch Providers:**
```bash
# Change to different provider
LLM_PROVIDER=custom  # Uses mock responses for testing
```

### Memory Storage

**Redis** (Recommended):
```bash
REDIS_URL=redis://localhost:6379/0
```

**In-Memory** (Fallback):
- Automatically used when Redis is unavailable
- Development and testing only

### Database Configuration


**PostgreSQL**:
```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/needleai
```


## 🧪 Development

### Local Development (without Docker)

```bash
# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .

# Start the development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

celery -A app.core.celery_app worker --loglevel=info
```

### Running Tests

```bash
# Install test dependencies
uv pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/

# With coverage
pytest tests/ --cov=app --cov-report=html
```

## 🔒 Security Features

The backend includes enterprise-grade security features:

### Authentication & Authorization

```bash
# Database-backed user authentication
# Password policies (length, complexity requirements)
# JWT token management with configurable expiration
# API key management with permissions and usage tracking

# Example: Create user with strong password
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "email": "john@example.com",
    "password": "SecurePass123!",
    "full_name": "John Doe"
  }'

# Login and get JWT token
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "password": "SecurePass123!"
  }'

# Create API key for programmatic access
curl -X POST "http://localhost:8000/api/v1/auth/api-keys" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production API Key",
    "permissions": {"chat": "read_write", "completions": "read"}
  }'
```

### Configuration Security

The backend validates all security settings on startup:

- **Secret Key Validation**: Ensures minimum 32-character secret keys
- **Token Expiration**: Enforces reasonable token lifetimes (max 2 hours in production)
- **Password Policies**: Configurable complexity requirements
- **CORS Validation**: Prevents wildcard origins in production
- **Environment Validation**: Checks for development settings in production

### Rate Limiting & Protection

- **Per-endpoint rate limiting**: Configurable request limits
- **Authentication attempt limiting**: Prevents brute force attacks
- **Input validation**: Comprehensive request validation with detailed errors
- **Security headers**: CORS, HSTS, content type validation

## 🚀 Production Deployment

### Production Checklist

Before deploying to production:

1. **✅ Configuration Validation**
   ```bash
   # Validate your production config
   uv run python -m app.cli health config --environment production
   ```

2. **✅ Security Settings**
   ```bash
   # Required production settings
   SECRET_KEY=your-32-character-minimum-secret-key
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   ENVIRONMENT=production
   DEBUG=false
   CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
   ```

3. **✅ Database Migration**
   ```bash
   # Run migrations
   uv run python -m app.cli database migrate

   # Verify database status
   uv run python -m app.cli database status
   ```

4. **✅ Performance Configuration**
   ```bash
   # Production server settings
   WORKERS=4  # Adjust based on CPU cores
   RELOAD=false
   REDIS_MAX_CONNECTIONS=100
   CELERY_WORKER_CONCURRENCY=4
   ```

### Docker Production Deployment

```bash
# Build production image
docker build -f Dockerfile -t needleai-backend:latest .

# Deploy with Docker Compose
docker-compose -f docker-compose.yml up -d

# Scale workers
docker-compose up --scale celery-worker=3 -d

# Monitor services
docker-compose ps
docker-compose logs -f backend
```

### Kubernetes Deployment

```yaml
# Example kubernetes deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: needleai-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: needleai-backend
  template:
    metadata:
      labels:
        app: needleai-backend
    spec:
      containers:
      - name: backend
        image: needleai-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: backend-secrets
              key: secret-key
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: backend-secrets
              key: database-url
        readinessProbe:
          httpGet:
            path: /api/v1/health/ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
        livenessProbe:
          httpGet:
            path: /api/v1/health/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
```

### External Monitoring Integration

```bash
# Prometheus metrics scraping
scrape_configs:
  - job_name: 'needleai-backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: /api/v1/metrics/prometheus
    scrape_interval: 15s

# Health check monitoring
curl -f "http://backend:8000/api/v1/health/ready" || exit 1
```

## 🔧 Troubleshooting

### Common Issues & Solutions

**1. Configuration Validation Errors**
```bash
# Problem: "Secret key must be at least 32 characters long"
# Solution: Generate a proper secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Problem: "Database connection failed"
# Solution: Check database URL and ensure database is running
uv run python -m app.cli health check --verbose
```

**2. Database Issues**
```bash
# Problem: Migration errors
# Solution: Check current migration status
uv run python -m app.cli database status

# Reset migrations if needed (WARNING: Loses data)
uv run python -m app.cli database reset --confirm
uv run python -m app.cli database migrate
```

**3. Performance Issues**
```bash
# Check system metrics
curl "http://localhost:8000/api/v1/metrics/system"

# Check slow endpoints
curl "http://localhost:8000/api/v1/metrics/endpoints"

# Enable detailed logging
LOG_LEVEL=DEBUG
```

**4. External Service Issues**
```bash
# Check all service health
curl "http://localhost:8000/api/v1/health/"

# Test individual services
curl "http://localhost:8000/api/v1/health/redis"
curl "http://localhost:8000/api/v1/health/database"
```

**5. Worker/Task Issues**
```bash
# Check Celery worker status
uv run python -m app.cli worker status

# Purge stuck tasks
uv run python -m app.cli worker purge --confirm

# Monitor task queue
curl "http://localhost:8000/api/v1/tasks/stats"
```

### Debug Mode

Enable debug mode for detailed error information:

```bash
# Development only - NEVER in production
DEBUG=true
LOG_LEVEL=DEBUG
CELERY_TASK_ALWAYS_EAGER=true  # Execute tasks synchronously
```

### Logging

```bash
# View application logs
docker-compose logs -f backend

# Export logs for analysis
uv run python -m app.cli logs export --output debug.log --hours 24 --level ERROR

# Real-time log monitoring
uv run python -m app.cli logs follow --level INFO
```

## 📈 Performance Optimization

### Database Performance

- **Connection Pooling**: SQLAlchemy connection pooling enabled
- **Query Optimization**: N+1 query prevention with eager loading
- **Indexing**: Proper database indexes on frequently queried fields
- **Transaction Management**: Efficient transaction handling

### Cache Configuration

```bash
# Redis cache settings
REDIS_MAX_CONNECTIONS=100
CACHE_TTL_SECONDS=3600
CACHE_MAX_SIZE=1000

# Enable query result caching
ENABLE_QUERY_CACHE=true
```

### Background Task Optimization

```bash
# Celery worker configuration
CELERY_WORKER_PREFETCH_MULTIPLIER=1
CELERY_WORKER_MAX_TASKS_PER_CHILD=1000
CELERY_WORKER_CONCURRENCY=4
```

## 📚 Additional Resources

- **[IMPROVEMENTS_SUMMARY.md](./IMPROVEMENTS_SUMMARY.md)**: Detailed documentation of recent improvements
- **[API Documentation](http://localhost:8000/docs)**: Interactive Swagger UI
- **[Health Dashboard](http://localhost:8000/api/v1/health/)**: Service health monitoring
- **[Metrics Overview](http://localhost:8000/api/v1/metrics/summary)**: Performance metrics

### Code Quality

```bash
# Install development tools
uv pip install black isort flake8 mypy

# Format code
black app/
isort app/

# Lint code
flake8 app/
mypy app/
```

## 📊 Monitoring

### Health Checks

The application provides comprehensive health checks:

- **`/health`**: Overall application health
- **`/api/v1/health/redis`**: Redis connectivity
- **`/api/v1/health/kafka`**: Kafka connectivity
- **`/api/v1/health/rabbitmq`**: RabbitMQ connectivity
- **`/api/v1/health/ready`**: Kubernetes readiness probe
- **`/api/v1/health/live`**: Kubernetes liveness probe

### Logging

Structured logging with request tracing:

```python
# View logs
docker-compose -f docker/docker-compose.dev.yml logs -f backend-dev

# Filter by service
docker-compose logs -f redis-dev kafka-dev
```

### Metrics

Integration points for monitoring:

- **Prometheus**: Metrics endpoint (configure as needed)
- **Grafana**: Visualization (configure as needed)
- **Jaeger**: Distributed tracing (configure as needed)

## 🚀 Deployment

### Production Deployment

```bash
# Quick deployment
./scripts/deploy.sh production

# With custom settings
ENVIRONMENT=production \
SECRET_KEY=your-production-secret \
OPENAI_API_KEY=your-api-key \
./scripts/deploy.sh production
```

### Environment Variables for Production

**Required**:
- `SECRET_KEY`: Strong random secret key
- `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`: LLM provider credentials
- `POSTGRES_PASSWORD`: Database password

**Optional**:
- `CORS_ORIGINS`: Allowed origins for CORS
- `RATE_LIMIT_REQUESTS`: Requests per minute limit
- `LOG_LEVEL`: Logging level (INFO, WARNING, ERROR)

### Scaling

**Horizontal Scaling**:
```bash
# Scale backend instances
docker-compose -f docker/docker-compose.yml up --scale backend=3 -d
```

**Load Balancing**:
- Use Nginx reverse proxy (included)
- Configure SSL certificates
- Add health check monitoring

## 🔒 Security

### Best Practices

1. **Environment Variables**: Never commit secrets to version control
2. **API Keys**: Use environment variables or secret management
3. **HTTPS**: Enable SSL/TLS in production (Nginx config provided)
4. **Rate Limiting**: Configure appropriate limits for your use case
5. **CORS**: Restrict origins to your domain
6. **Authentication**: Implement JWT or OAuth as needed

### Rate Limiting

```bash
# Configure rate limits
RATE_LIMIT_REQUESTS=100  # Requests per minute
RATE_LIMIT_WINDOW=60     # Time window in seconds
```

## 🐛 Troubleshooting

### Common Issues

**Port Conflicts**:
```bash
# Check port usage
lsof -i :8000
netstat -an | grep 8000
```

**Service Not Starting**:
```bash
# Check logs
docker-compose logs service-name

# Restart services
./scripts/stop.sh && ./scripts/start.sh
```

**Database Connection Issues**:
```bash
# Test database connection
docker exec needleai_postgres_dev pg_isready -U postgres

# Reset database
docker-compose down -v
docker-compose up -d
```

**LLM API Issues**:
- Verify API keys are set correctly
- Check API rate limits and quotas
- Test with `curl` commands
- Switch to custom provider for testing

### Debug Mode

```bash
# Enable debug mode
export DEBUG=true
export LOG_LEVEL=DEBUG

# Start with debug
./scripts/start.sh development
```

### Getting Help

1. **Check Logs**: `docker-compose logs -f backend-dev`
2. **Health Status**: `./scripts/status.sh`
3. **API Documentation**: http://localhost:8000/docs
4. **Service Status**: http://localhost:8000/health

## 📚 API Documentation

Interactive API documentation is automatically generated and available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## 🤝 Contributing

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/amazing-feature`
3. **Commit** changes: `git commit -m 'Add amazing feature'`
4. **Push** to branch: `git push origin feature/amazing-feature`
5. **Open** a Pull Request

### Development Guidelines

- Follow PEP 8 style guide
- Add type hints for all functions
- Write comprehensive tests
- Update documentation
- Ensure Docker builds succeed

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🏢 Support

- **Documentation**: Check `/docs` endpoint
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions

---

**Generated by [cookiecutter-fastapi-nextjs-llm](https://github.com/your-org/cookiecutter-fastapi-nextjs-llm)**
