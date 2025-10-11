"""
Completion repository for NeedleAi.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from ...utils.logging import get_logger
from ..models.completion import Completion

logger = get_logger("completion_repository")


class CompletionRepository:
    """Repository for Completion model operations."""

    @staticmethod
    def create(
        db: Session,
        prompt: str,
        model_name: str,
        user_id: str = None,
        **kwargs
    ) -> Completion:
        """Create a new completion request."""
        completion = Completion(
            user_id=user_id,
            prompt=prompt,
            model_name=model_name,
            **kwargs
        )
        db.add(completion)
        db.commit()
        db.refresh(completion)
        logger.info(f"Created completion: {completion.id}")
        return completion

    @staticmethod
    def get_by_id(db: Session, completion_id: str) -> Optional[Completion]:
        """Get completion by ID."""
        return db.query(Completion).filter(Completion.id == completion_id).first()

    @staticmethod
    def get_all(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        status: str = None,
        model_name: str = None
    ) -> List[Completion]:
        """Get all completions with pagination and filtering."""
        query = db.query(Completion)

        if status:
            query = query.filter(Completion.status == status)

        if model_name:
            query = query.filter(Completion.model_name == model_name)

        return query.order_by(desc(Completion.created_at)).offset(skip).limit(limit).all()

    @staticmethod
    def get_user_completions(
        db: Session,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        status: str = None
    ) -> List[Completion]:
        """Get user's completions."""
        query = db.query(Completion).filter(Completion.user_id == user_id)

        if status:
            query = query.filter(Completion.status == status)

        return (
            query
            .order_by(desc(Completion.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )

    @staticmethod
    def update(db: Session, completion_id: str, **kwargs) -> Optional[Completion]:
        """Update completion."""
        completion = CompletionRepository.get_by_id(db, completion_id)
        if not completion:
            return None

        for key, value in kwargs.items():
            if hasattr(completion, key):
                setattr(completion, key, value)

        db.commit()
        db.refresh(completion)
        return completion

    @staticmethod
    def update_completion_result(
        db: Session,
        completion_id: str,
        completion_text: str = None,
        status: str = None,
        **kwargs
    ) -> Optional[Completion]:
        """Update completion with result."""
        completion = CompletionRepository.get_by_id(db, completion_id)
        if not completion:
            return None

        if completion_text is not None:
            completion.completion_text = completion_text
        if status is not None:
            completion.status = status
        if status in ['completed', 'failed']:
            completion.completed_at = datetime.utcnow()

        for key, value in kwargs.items():
            if hasattr(completion, key):
                setattr(completion, key, value)

        db.commit()
        db.refresh(completion)

        # Update user usage if completed successfully
        if completion.user_id and status == 'completed':
            from .user import UserRepository
            UserRepository.increment_usage(db, completion.user_id, tokens=completion.total_tokens)

        return completion

    @staticmethod
    def delete(db: Session, completion_id: str) -> bool:
        """Delete completion by ID."""
        completion = CompletionRepository.get_by_id(db, completion_id)
        if completion:
            db.delete(completion)
            db.commit()
            logger.info(f"Deleted completion: {completion_id}")
            return True
        return False

    @staticmethod
    def count_by_status(db: Session, status: str, user_id: str = None) -> int:
        """Count completions by status."""
        query = db.query(Completion).filter(Completion.status == status)

        if user_id:
            query = query.filter(Completion.user_id == user_id)

        return query.count()

    @staticmethod
    def get_completion_stats(db: Session, user_id: str = None) -> dict:
        """Get completion statistics."""
        query = db.query(Completion)

        if user_id:
            query = query.filter(Completion.user_id == user_id)

        completions = query.all()

        stats = {
            "total_completions": len(completions),
            "completed": len([c for c in completions if c.status == "completed"]),
            "failed": len([c for c in completions if c.status == "failed"]),
            "pending": len([c for c in completions if c.status == "pending"]),
            "total_tokens": sum(c.total_tokens or 0 for c in completions),
            "avg_processing_time": None
        }

        # Calculate average processing time for completed requests
        completed_times = [c.processing_time_ms for c in completions
                          if c.status == "completed" and c.processing_time_ms]
        if completed_times:
            stats["avg_processing_time"] = sum(completed_times) / len(completed_times)

        return stats

    @staticmethod
    def search_completions(
        db: Session,
        search_term: str,
        user_id: str = None,
        model_name: str = None,
        status: str = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Completion]:
        """Search completions by prompt content."""
        query = db.query(Completion)

        if search_term:
            query = query.filter(
                Completion.prompt.ilike(f"%{search_term}%") |
                Completion.completion_text.ilike(f"%{search_term}%")
            )

        if user_id:
            query = query.filter(Completion.user_id == user_id)

        if model_name:
            query = query.filter(Completion.model_name == model_name)

        if status:
            query = query.filter(Completion.status == status)

        return query.order_by(desc(Completion.created_at)).offset(skip).limit(limit).all()
