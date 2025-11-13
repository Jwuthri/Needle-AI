# Implementation Plan

- [x] 1. Set up project structure and core configuration
  - Create directory structure for `back_end/` with all necessary folders
  - Set up `pyproject.toml` with dependencies (FastAPI, SQLAlchemy, Pydantic, Alembic, Rich, etc.)
  - Create `.gitignore` file for Python project
  - _Requirements: 7.1, 7.2, 7.3_

- [x] 2. Implement configuration and logging
  - [x] 2.1 Create settings module with Pydantic validation
    - Implement `back_end/app/core/config/settings.py` with all configuration fields
    - Add field validators for CORS origins and secret key
    - Include `get_settings()` cached function
    - _Requirements: 7.1, 7.2, 7.6_

  - [x] 2.2 Implement Rich logging utility
    - Create `back_end/app/utils/logging.py` with Rich handler setup
    - Configure console output with tracebacks
    - Set up logger factory function
    - _Requirements: 7.6_

- [x] 3. Create database models (SQLAlchemy)
  - [x] 3.1 Set up database base and session management
    - Create `back_end/app/database/base.py` with declarative base
    - Implement `back_end/app/database/session.py` with async engine and session factory
    - Add dependency injection function for database sessions
    - _Requirements: 2.6, 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 3.2 Implement User model
    - Create `back_end/app/database/models/user.py` with User table definition
    - Include UUID primary key, clerk_user_id, email, timestamps
    - Define relationships to ChatSession and UserDataset
    - _Requirements: 1.1, 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 3.3 Implement Company model
    - Create `back_end/app/database/models/company.py` with Company table definition
    - Include UUID primary key, name, description, website, timestamps
    - Define relationship to ChatSession
    - _Requirements: 1.1, 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 3.4 Implement ChatSession model
    - Create `back_end/app/database/models/chat_session.py` with ChatSession table definition
    - Include foreign keys to User and Company with proper cascade deletes
    - Define relationship to ChatMessage
    - _Requirements: 1.1, 1.4, 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 3.5 Implement ChatMessage model
    - Create `back_end/app/database/models/chat_message.py` with ChatMessage table definition
    - Include role, content, metadata JSON field
    - Define relationship to ChatMessageStep
    - _Requirements: 1.1, 1.4, 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 3.6 Implement ChatMessageStep model
    - Create `back_end/app/database/models/chat_message_step.py` with ChatMessageStep table definition
    - Include step_type, content, metadata JSON field
    - Define relationship back to ChatMessage
    - _Requirements: 1.1, 1.4, 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 3.7 Implement LLMCall model
    - Create `back_end/app/database/models/llm_call.py` with LLMCall table definition
    - Include model, provider, token counts, latency, cost, status fields
    - Add metadata JSON field for additional information
    - _Requirements: 1.1, 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 3.8 Implement UserDataset model
    - Create `back_end/app/database/models/user_dataset.py` with UserDataset table definition
    - Include foreign key to User, file_path, file_size, row_count
    - Add metadata JSON field and timestamps
    - _Requirements: 1.1, 1.4, 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 3.9 Create models __init__.py
    - Import all models in `back_end/app/database/models/__init__.py`
    - Export all models for easy importing
    - _Requirements: 2.1_

- [x] 4. Create Pydantic models (API contracts)
  - [x] 4.1 Implement base Pydantic models
    - Create `back_end/app/models/base.py` with BaseSchema and TimestampMixin
    - Configure Pydantic v2 settings with from_attributes
    - _Requirements: 3.1, 3.4, 3.5, 3.6_

  - [x] 4.2 Implement User Pydantic schemas
    - Create `back_end/app/models/user.py` with UserBase, UserCreate, UserUpdate, UserResponse
    - Add field validation and example configurations
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [x] 4.3 Implement Company Pydantic schemas
    - Create `back_end/app/models/company.py` with CompanyBase, CompanyCreate, CompanyUpdate, CompanyResponse
    - Add field validation and example configurations
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [x] 4.4 Implement Chat Pydantic schemas
    - Create `back_end/app/models/chat.py` with all chat-related schemas
    - Include ChatMessageBase, ChatMessageCreate, ChatMessageResponse
    - Include ChatSessionBase, ChatSessionCreate, ChatSessionResponse
    - Include ChatRequest and ChatResponse with examples
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [x] 4.5 Implement UserDataset Pydantic schemas
    - Create `back_end/app/models/user_dataset.py` with dataset schemas
    - Include UserDatasetBase, UserDatasetCreate, UserDatasetUpdate, UserDatasetResponse
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

- [x] 5. Implement repository layer
  - [x] 5.1 Create base async repository
    - Implement `back_end/app/database/repositories/base_async.py` with generic CRUD operations
    - Include create, get_by_id, get_all, update, delete methods
    - Use async/await throughout
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 5.2 Implement User repository
    - Create `back_end/app/database/repositories/user.py` extending BaseAsyncRepository
    - Add get_by_clerk_id and get_by_email methods
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 5.3 Implement Company repository
    - Create `back_end/app/database/repositories/company.py` extending BaseAsyncRepository
    - Add company-specific query methods if needed
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 5.4 Implement ChatSession repository
    - Create `back_end/app/database/repositories/chat_session.py` extending BaseAsyncRepository
    - Add methods to get sessions by user_id
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 5.5 Implement ChatMessage repository
    - Create `back_end/app/database/repositories/chat_message.py` extending BaseAsyncRepository
    - Add methods to get messages by session_id
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 5.6 Implement ChatMessageStep repository
    - Create `back_end/app/database/repositories/chat_message_step.py` extending BaseAsyncRepository
    - Add methods to get steps by message_id
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 5.7 Implement LLMCall repository
    - Create `back_end/app/database/repositories/llm_call.py` extending BaseAsyncRepository
    - Add methods for querying LLM call logs
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 5.8 Implement UserDataset repository
    - Create `back_end/app/database/repositories/user_dataset.py` extending BaseAsyncRepository
    - Add methods to get datasets by user_id
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 5.9 Create repositories __init__.py
    - Import all repositories in `back_end/app/database/repositories/__init__.py`
    - Export all repositories for easy importing
    - _Requirements: 4.1_

- [x] 6. Implement service layer
  - [x] 6.1 Create ChatService
    - Implement `back_end/app/services/chat_service.py` with business logic
    - Add send_message method that creates sessions and messages
    - Include placeholder for LLM integration
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 6.2 Create UserService
    - Implement `back_end/app/services/user_service.py` with user management logic
    - Add methods for creating and retrieving users
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 6.3 Create CompanyService
    - Implement `back_end/app/services/company_service.py` with company management logic
    - Add methods for creating and retrieving companies
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 6.4 Create UserDatasetService
    - Implement `back_end/app/services/user_dataset_service.py` with dataset management logic
    - Add methods for creating and retrieving user datasets
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 7. Implement API layer
  - [x] 7.1 Create API dependencies
    - Implement `back_end/app/api/deps.py` with dependency injection functions
    - Add get_db, get_current_user, and service factory functions
    - _Requirements: 7.3, 7.4_

  - [x] 7.2 Create health check endpoint
    - Implement `back_end/app/api/v1/health.py` with health check endpoint
    - Return application status and database connectivity
    - _Requirements: 7.5_

  - [x] 7.3 Create chat endpoints
    - Implement `back_end/app/api/v1/chat.py` with chat endpoints
    - Add POST /chat/ endpoint for sending messages
    - Include proper request/response models and error handling
    - _Requirements: 7.3, 7.4_

  - [x] 7.4 Create user endpoints
    - Implement `back_end/app/api/v1/users.py` with user endpoints
    - Add GET and POST endpoints for user management
    - _Requirements: 7.3, 7.4_

  - [x] 7.5 Create company endpoints
    - Implement `back_end/app/api/v1/companies.py` with company endpoints
    - Add GET and POST endpoints for company management
    - _Requirements: 7.3, 7.4_

  - [x] 7.6 Create user dataset endpoints
    - Implement `back_end/app/api/v1/user_datasets.py` with dataset endpoints
    - Add GET and POST endpoints for dataset management
    - _Requirements: 7.3, 7.4_

  - [x] 7.7 Create API router
    - Implement `back_end/app/api/v1/router.py` to combine all endpoint routers
    - Include all routers with proper prefixes and tags
    - _Requirements: 7.3_

- [x] 8. Create main application
  - [x] 8.1 Implement FastAPI application
    - Create `back_end/app/main.py` with FastAPI app initialization
    - Add lifespan context manager for startup/shutdown
    - Configure CORS middleware
    - Include API router
    - Set up logging with Rich
    - _Requirements: 7.3, 7.4, 7.5, 7.6_

  - [x] 8.2 Create application dependencies
    - Implement `back_end/app/dependencies.py` with global dependencies
    - _Requirements: 7.3_

- [x] 9. Set up Alembic migrations
  - [x] 9.1 Create initial migration
    - use alembic command for this
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 6.2_

- [x] 10. Create project documentation
  - [x] 10.1 Create README.md
    - Document project setup instructions
    - Include database setup and migration commands
    - Add API endpoint documentation
    - _Requirements: 7.1, 7.2, 7.3_
