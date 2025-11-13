# NeedleAI Backend - Simplified Architecture

A clean, simplified FastAPI backend focused on core chat functionality with LLM integration and user dataset management.

## Overview

This backend system provides a streamlined architecture with only essential features:
- **7 Core Tables**: User, Company, ChatSession, ChatMessage, ChatMessageStep, LLMCall, UserDataset
- **Async/Await Throughout**: Modern async patterns for all I/O operations
- **Repository Pattern**: Clean data access layer abstraction
- **Pydantic v2**: Type-safe API contracts with validation
- **Rich Logging**: Beautiful console output for development

## Tech Stack

- **Python**: 3.11+
- **Framework**: FastAPI 0.104+
- **Database**: PostgreSQL with SQLAlchemy 2.0 (async)
- **Migrations**: Alembic
- **Validation**: Pydantic v2
- **Authentication**: Clerk
- **Logging**: Rich

## Project Structure

```
back_end/
├── app/
│   ├── api/                    # API endpoints
│   │   ├── deps.py            # Dependency injection
│   │   └── v1/                # API version 1
│   │       ├── router.py      # Main router
│   │       ├── health.py      # Health check
│   │       ├── users.py       # User endpoints
│   │       ├── companies.py   # Company endpoints
│   │       ├── chat.py        # Chat endpoints
│   │       └── user_datasets.py
│   ├── core/
│   │   └── config/            # Configuration management
│   │       └── settings.py    # Pydantic settings
│   ├── database/
│   │   ├── base.py            # Base model class
│   │   ├── session.py         # Database session
│   │   ├── models/            # SQLAlchemy models
│   │   └── repositories/      # Data access layer
│   ├── models/                # Pydantic schemas
│   ├── services/              # Business logic
│   ├── utils/                 # Utilities
│   │   └── logging.py         # Rich logging setup
│   ├── dependencies.py        # Global dependencies
│   └── main.py               # FastAPI application
├── alembic/                   # Database migrations
├── .env                       # Environment variables
├── .env.template             # Environment template
├── pyproject.toml            # Dependencies
└── README.md                 # This file
```

## Getting Started

### Prerequisites

- Python 3.11 or higher
- PostgreSQL 14 or higher
- pip or uv package manager

### Installation

1. **Clone the repository** (if not already done)

2. **Navigate to the backend directory**
   ```bash
   cd back_end
   ```

3. **Create a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

4. **Install dependencies**
   ```bash
   pip install -e .
   
   # For development dependencies
   pip install -e ".[dev]"
   ```

### Database Setup

1. **Create PostgreSQL database**
   ```bash
   # Using psql
   psql -U postgres
   CREATE DATABASE needle_ai;
   \q
   ```

2. **Configure environment variables**
   ```bash
   # Copy the template
   cp .env.template .env
   
   # Edit .env with your settings
   # Update DATABASE_URL with your PostgreSQL credentials
   ```

3. **Run database migrations**
   ```bash
   # Initialize Alembic (if not already done)
   alembic upgrade head
   ```

### Running the Application

1. **Start the development server**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Access the API**
   - API: http://localhost:8000
   - Interactive Docs: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc
   - Health Check: http://localhost:8000/health

## Database Migrations

### Creating a New Migration

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Description of changes"

# Review the generated migration file in alembic/versions/
# Edit if necessary, then apply
alembic upgrade head
```

### Common Migration Commands

```bash
# Upgrade to latest version
alembic upgrade head

# Upgrade by one version
alembic upgrade +1

# Downgrade by one version
alembic downgrade -1

# Show current version
alembic current

# Show migration history
alembic history

# Downgrade to specific version
alembic downgrade <revision_id>
```

## API Endpoints

### Health Check
- `GET /health` - Application health status

### Users
- `GET /api/v1/users/` - List all users
- `GET /api/v1/users/{user_id}` - Get user by ID
- `POST /api/v1/users/` - Create new user
- `PUT /api/v1/users/{user_id}` - Update user
- `DELETE /api/v1/users/{user_id}` - Delete user

### Companies
- `GET /api/v1/companies/` - List all companies
- `GET /api/v1/companies/{company_id}` - Get company by ID
- `POST /api/v1/companies/` - Create new company
- `PUT /api/v1/companies/{company_id}` - Update company
- `DELETE /api/v1/companies/{company_id}` - Delete company

### Chat
- `POST /api/v1/chat/` - Send chat message and receive response
- `GET /api/v1/chat/sessions` - List user's chat sessions
- `GET /api/v1/chat/sessions/{session_id}` - Get session details
- `GET /api/v1/chat/sessions/{session_id}/messages` - Get session messages

### User Datasets
- `GET /api/v1/user-datasets/` - List user's datasets
- `GET /api/v1/user-datasets/{dataset_id}` - Get dataset by ID
- `POST /api/v1/user-datasets/` - Create new dataset
- `DELETE /api/v1/user-datasets/{dataset_id}` - Delete dataset

## Configuration

### Environment Variables

Key environment variables (see `.env.template` for complete list):

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Yes | - |
| `DATABASE_NAME` | Database name | Yes | `needle_ai` |
| `SECRET_KEY` | JWT secret key | Yes | - |
| `CLERK_SECRET_KEY` | Clerk authentication key | Yes | - |
| `CORS_ORIGINS` | Allowed CORS origins | No | `http://localhost:3000` |
| `OPENAI_API_KEY` | OpenAI API key | No | - |
| `ANTHROPIC_API_KEY` | Anthropic API key | No | - |
| `DEBUG` | Enable debug mode | No | `True` |
| `PORT` | Server port | No | `8000` |

### Database Connection String Format

```
postgresql+asyncpg://username:password@host:port/database_name
```

Example:
```
postgresql+asyncpg://postgres:mypassword@localhost:5432/needle_ai
```

## Development

### Code Style

This project follows these standards:
- **Formatter**: Black (88 character line length)
- **Import Sorting**: isort with Black profile
- **Linting**: Ruff
- **Type Checking**: mypy

### Running Code Quality Tools

```bash
# Format code
black app/

# Sort imports
isort app/

# Lint code
ruff check app/

# Type check
mypy app/
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_repositories.py

# Run with verbose output
pytest -v
```

## Database Schema

### Core Tables

1. **users** - User accounts with Clerk integration
2. **companies** - Company information
3. **chat_sessions** - Conversation threads
4. **chat_messages** - Individual messages in sessions
5. **chat_message_steps** - Sub-steps within messages (thinking, tool calls, etc.)
6. **llm_calls** - LLM API call logging and metrics
7. **user_datasets** - User-uploaded datasets

### Key Relationships

- User → ChatSession (one-to-many)
- User → UserDataset (one-to-many)
- Company → ChatSession (one-to-many)
- ChatSession → ChatMessage (one-to-many)
- ChatMessage → ChatMessageStep (one-to-many)

## Architecture Patterns

### Repository Pattern

Data access is abstracted through repository classes:

```python
# Using a repository
from app.database.repositories.user import UserRepository

async def get_user_by_email(email: str, db: AsyncSession):
    user_repo = UserRepository(db)
    return await user_repo.get_by_email(email)
```

### Service Layer

Business logic is encapsulated in service classes:

```python
# Using a service
from app.services.chat_service import ChatService

async def send_message(message: str, user_id: UUID):
    chat_service = ChatService(...)
    return await chat_service.send_message(user_id, message)
```

### Dependency Injection

FastAPI's dependency injection is used throughout:

```python
@router.post("/chat/")
async def chat_endpoint(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
    current_user = Depends(get_current_user)
):
    return await chat_service.send_message(...)
```

## Logging

The application uses Rich for beautiful console logging:

```python
from app.utils.logging import setup_logging

logger = setup_logging()
logger.info("[bold green]Application started[/bold green]")
logger.error("[bold red]Error occurred[/bold red]", exc_info=True)
```

## Authentication

Authentication is handled via Clerk:

1. Frontend obtains JWT token from Clerk
2. Token is sent in `Authorization` header
3. Backend validates token using Clerk secret key
4. User information is extracted and used for authorization

## Troubleshooting

### Database Connection Issues

```bash
# Test PostgreSQL connection
psql -U postgres -d needle_ai -c "SELECT 1;"

# Check if database exists
psql -U postgres -l | grep needle_ai
```

### Migration Issues

```bash
# Reset database (WARNING: destroys all data)
alembic downgrade base
alembic upgrade head

# Check migration status
alembic current
alembic history
```

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>
```

## Production Deployment

### Environment Setup

1. Set `ENVIRONMENT=production`
2. Set `DEBUG=False`
3. Use strong `SECRET_KEY`
4. Configure production database
5. Set up proper CORS origins
6. Use environment-specific secrets

### Running in Production

```bash
# Using uvicorn with workers
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Using gunicorn with uvicorn workers
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Health Monitoring

Monitor the `/health` endpoint for application status:

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "connected",
  "version": "0.1.0"
}
```

## Contributing

1. Follow the code style guidelines
2. Write tests for new features
3. Update documentation as needed
4. Run code quality tools before committing
5. Create descriptive commit messages

## License

[Your License Here]

## Support

For issues and questions:
- Create an issue in the repository
- Contact the development team
- Check the documentation

---

Built with ❤️ using FastAPI and Python
