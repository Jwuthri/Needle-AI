"""
User repository for NeedleAi.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from ...utils.logging import get_logger
from ..models.user import User

logger = get_logger("user_repository")


class UserRepository:
    """Repository for User model operations."""

    @staticmethod
    def create(db: Session, email: str, username: str = None, full_name: str = None, **kwargs) -> User:
        """Create a new user."""
        user = User(
            email=email,
            username=username,
            full_name=full_name,
            **kwargs
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"Created user: {user.id}")
        return user

    @staticmethod
    def get_by_id(db: Session, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email."""
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_by_username(db: Session, username: str) -> Optional[User]:
        """Get user by username."""
        return db.query(User).filter(User.username == username).first()

    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        """Get all users with pagination."""
        return db.query(User).offset(skip).limit(limit).all()

    @staticmethod
    def update(db: Session, user_id: str, **kwargs) -> Optional[User]:
        """Update user."""
        user = UserRepository.get_by_id(db, user_id)
        if not user:
            return None

        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)

        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def delete(db: Session, user_id: str) -> bool:
        """Delete user by ID."""
        user = UserRepository.get_by_id(db, user_id)
        if user:
            db.delete(user)
            db.commit()
            logger.info(f"Deleted user: {user_id}")
            return True
        return False

    @staticmethod
    def increment_usage(db: Session, user_id: str, requests: int = 1, tokens: int = 0):
        """Increment user usage counters."""
        user = UserRepository.get_by_id(db, user_id)
        if user:
            user.total_requests += requests
            user.total_tokens_used += tokens
            user.updated_at = datetime.utcnow()
            db.commit()

    @staticmethod
    def update_last_login(db: Session, user_id: str) -> Optional[User]:
        """Update user's last login timestamp."""
        user = UserRepository.get_by_id(db, user_id)
        if user:
            user.last_login_at = datetime.utcnow()
            user.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(user)
        return user

    @staticmethod
    def search_users(db: Session, search_term: str, skip: int = 0, limit: int = 50) -> List[User]:
        """Search users by email, username or full name."""
        return (
            db.query(User)
            .filter(
                User.email.ilike(f"%{search_term}%") |
                User.username.ilike(f"%{search_term}%") |
                User.full_name.ilike(f"%{search_term}%")
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
