"""
Database configuration and session management for NeedleAi.
"""

import logging
from typing import Generator

from app.config import get_settings
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

# Get settings
settings = get_settings()

# Configure logging
logging.basicConfig()
logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

# Create Base class for declarative models (shared between sync and async)
Base = declarative_base()

# Legacy sync database support (for backwards compatibility)

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.environment == "development"
)


# Create SessionLocal class (legacy sync support)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Get database session for dependency injection (legacy sync).

    Note: This is deprecated. Use get_async_db_session() from session.py instead.

    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all database tables (legacy sync)."""
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """Drop all database tables (legacy sync)."""
    Base.metadata.drop_all(bind=engine)
