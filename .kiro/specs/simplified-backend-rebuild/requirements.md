# Requirements Document

## Introduction

This document outlines the requirements for building a simplified backend system in the `back_end` folder. The system will focus on core chat functionality with LLM integration and user dataset management, removing unnecessary complexity from the existing backend implementation. The database will be named `needle_ai`.

## Glossary

- **Backend System**: The FastAPI-based server application that handles API requests, database operations, and LLM interactions
- **Database Schema**: The PostgreSQL table definitions and relationships for the `needle_ai` database
- **Pydantic Models**: Python data validation models that define request/response schemas
- **Repository Pattern**: Data access layer that abstracts database operations
- **Chat Session**: A conversation thread between a user and the system
- **Chat Message**: An individual message within a chat session
- **Chat Message Step**: A sub-step or intermediate processing stage within a chat message
- **LLM Call**: A logged interaction with a Large Language Model
- **User Dataset**: Custom data uploaded or managed by users

## Requirements

### Requirement 1

**User Story:** As a developer, I want a clean database schema with only essential tables, so that the system is easier to maintain and understand

#### Acceptance Criteria

1. THE Backend System SHALL define a database schema containing exactly seven tables: User, Company, Chat Session, Chat Message, Chat Message Step, LLM Call, and User Dataset
2. THE Backend System SHALL use the database name `needle_ai` for all database connections
3. THE Backend System SHALL NOT include tables for Review, Scraping Job, Task Result, User Credit, Review Source, Credit Transaction, Data Import, or API Key
4. WHEN defining table relationships, THE Backend System SHALL establish appropriate foreign key constraints between related tables
5. THE Backend System SHALL include proper indexing on frequently queried columns

### Requirement 2

**User Story:** As a developer, I want SQLAlchemy models for each table, so that I can interact with the database using Python objects

#### Acceptance Criteria

1. THE Backend System SHALL create a SQLAlchemy model file for each of the seven tables in `back_end/app/database/models/`
2. WHEN defining models, THE Backend System SHALL include all necessary columns with appropriate data types
3. THE Backend System SHALL define relationships between models using SQLAlchemy relationship declarations
4. THE Backend System SHALL include timestamps (created_at, updated_at) on all models where appropriate
5. THE Backend System SHALL use UUID primary keys for all tables
6. THE Backend System SHALL use SQLAlchemy with async support following the repository pattern

### Requirement 3

**User Story:** As a developer, I want Pydantic schemas for request/response validation, so that API inputs and outputs are properly validated

#### Acceptance Criteria

1. THE Backend System SHALL create Pydantic model files in `back_end/app/models/` for each entity
2. WHEN defining Pydantic models, THE Backend System SHALL include separate schemas for Create, Update, and Response operations
3. THE Backend System SHALL include proper field validation rules in Pydantic models
4. THE Backend System SHALL use Pydantic v2 syntax and features with BaseModel
5. THE Backend System SHALL ensure Pydantic models align with SQLAlchemy model structures
6. THE Backend System SHALL include Config class with examples for API documentation

### Requirement 4

**User Story:** As a developer, I want repository classes for data access, so that database operations are abstracted and testable

#### Acceptance Criteria

1. THE Backend System SHALL create a repository class for each entity in `back_end/app/database/repositories/`
2. WHEN implementing repositories, THE Backend System SHALL provide CRUD operations (Create, Read, Update, Delete)
3. THE Backend System SHALL implement a base repository class with common operations
4. THE Backend System SHALL use async/await patterns for all database operations
5. THE Backend System SHALL include proper error handling in repository methods

### Requirement 5

**User Story:** As a developer, I want proper database session management, so that connections are handled efficiently

#### Acceptance Criteria

1. THE Backend System SHALL create a database session configuration file at `back_end/app/database/session.py`
2. WHEN establishing database connections, THE Backend System SHALL use SQLAlchemy async engine
3. THE Backend System SHALL implement a session factory for creating database sessions
4. THE Backend System SHALL provide dependency injection for database sessions in API endpoints
5. THE Backend System SHALL ensure proper session cleanup after requests

### Requirement 6

**User Story:** As a developer, I want Alembic migrations set up, so that database schema changes can be version controlled

#### Acceptance Criteria

1. THE Backend System SHALL configure Alembic in the `back_end/alembic/` directory
2. WHEN creating the initial migration, THE Backend System SHALL include all seven tables
3. THE Backend System SHALL configure Alembic to use the `needle_ai` database
4. THE Backend System SHALL include proper migration environment configuration
5. THE Backend System SHALL ensure migrations can be run both upgrade and downgrade

### Requirement 7

**User Story:** As a developer, I want a base project structure with configuration, so that the backend is properly organized

#### Acceptance Criteria

1. THE Backend System SHALL create a configuration file at `back_end/app/core/config/settings.py` with database settings using Pydantic validation
2. THE Backend System SHALL include environment variable loading from `.env` file
3. THE Backend System SHALL create a main application file at `back_end/app/main.py` with FastAPI setup and lifespan management
4. THE Backend System SHALL include proper CORS configuration
5. THE Backend System SHALL set up basic health check endpoint at `/health`
6. THE Backend System SHALL use Python 3.11+ features and type hints throughout
