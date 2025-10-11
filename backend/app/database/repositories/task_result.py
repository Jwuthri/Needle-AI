"""
Task result repository for NeedleAi.
"""

from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from ...utils.logging import get_logger
from ..models.task_result import TaskResult

logger = get_logger("task_result_repository")


class TaskResultRepository:
    """Repository for TaskResult model operations."""

    @staticmethod
    def create(
        db: Session,
        task_id: str,
        task_name: str,
        user_id: str = None,
        **kwargs
    ) -> TaskResult:
        """Create a new task result."""
        task_result = TaskResult(
            id=task_id,
            task_name=task_name,
            user_id=user_id,
            **kwargs
        )
        db.add(task_result)
        db.commit()
        db.refresh(task_result)
        logger.info(f"Created task result: {task_result.id}")
        return task_result

    @staticmethod
    def get_by_id(db: Session, task_id: str) -> Optional[TaskResult]:
        """Get task result by ID."""
        return db.query(TaskResult).filter(TaskResult.id == task_id).first()

    @staticmethod
    def get_all(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        status: str = None,
        task_name: str = None
    ) -> List[TaskResult]:
        """Get all task results with pagination and filtering."""
        query = db.query(TaskResult)

        if status:
            query = query.filter(TaskResult.status == status)

        if task_name:
            query = query.filter(TaskResult.task_name == task_name)

        return query.order_by(desc(TaskResult.created_at)).offset(skip).limit(limit).all()

    @staticmethod
    def get_user_tasks(
        db: Session,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
        status: str = None
    ) -> List[TaskResult]:
        """Get user's task results."""
        query = db.query(TaskResult).filter(TaskResult.user_id == user_id)

        if status:
            query = query.filter(TaskResult.status == status)

        return query.order_by(desc(TaskResult.created_at)).offset(skip).limit(limit).all()

    @staticmethod
    def get_by_task_name(
        db: Session,
        task_name: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[TaskResult]:
        """Get task results by task name."""
        return (
            db.query(TaskResult)
            .filter(TaskResult.task_name == task_name)
            .order_by(desc(TaskResult.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def update(db: Session, task_id: str, **kwargs) -> Optional[TaskResult]:
        """Update task result."""
        task_result = TaskResultRepository.get_by_id(db, task_id)
        if not task_result:
            return None

        for key, value in kwargs.items():
            if hasattr(task_result, key):
                setattr(task_result, key, value)

        db.commit()
        db.refresh(task_result)
        return task_result

    @staticmethod
    def update_status(
        db: Session,
        task_id: str,
        status: str,
        result: dict = None,
        error_message: str = None,
        traceback: str = None
    ) -> Optional[TaskResult]:
        """Update task status and result."""
        task_result = TaskResultRepository.get_by_id(db, task_id)
        if not task_result:
            return None

        task_result.status = status

        if status == "STARTED" and not task_result.started_at:
            task_result.started_at = datetime.utcnow()

        if status in ["SUCCESS", "FAILURE", "REVOKED"]:
            task_result.completed_at = datetime.utcnow()

        if result is not None:
            task_result.result = result

        if error_message:
            task_result.error_message = error_message

        if traceback:
            task_result.traceback = traceback

        db.commit()
        db.refresh(task_result)
        return task_result

    @staticmethod
    def delete(db: Session, task_id: str) -> bool:
        """Delete task result by ID."""
        task_result = TaskResultRepository.get_by_id(db, task_id)
        if task_result:
            db.delete(task_result)
            db.commit()
            logger.info(f"Deleted task result: {task_id}")
            return True
        return False

    @staticmethod
    def cleanup_old_tasks(db: Session, days_old: int = 30) -> int:
        """Clean up old completed task results."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        deleted_count = (
            db.query(TaskResult)
            .filter(
                TaskResult.completed_at < cutoff_date,
                TaskResult.status.in_(["SUCCESS", "FAILURE", "REVOKED"])
            )
            .delete(synchronize_session=False)
        )

        db.commit()
        logger.info(f"Cleaned up {deleted_count} old task results")
        return deleted_count

    @staticmethod
    def count_by_status(db: Session, status: str, user_id: str = None) -> int:
        """Count task results by status."""
        query = db.query(TaskResult).filter(TaskResult.status == status)

        if user_id:
            query = query.filter(TaskResult.user_id == user_id)

        return query.count()

    @staticmethod
    def get_task_stats(db: Session, user_id: str = None) -> dict:
        """Get task statistics."""
        query = db.query(TaskResult)

        if user_id:
            query = query.filter(TaskResult.user_id == user_id)

        tasks = query.all()

        stats = {
            "total_tasks": len(tasks),
            "pending": len([t for t in tasks if t.status == "PENDING"]),
            "started": len([t for t in tasks if t.status == "STARTED"]),
            "success": len([t for t in tasks if t.status == "SUCCESS"]),
            "failure": len([t for t in tasks if t.status == "FAILURE"]),
            "revoked": len([t for t in tasks if t.status == "REVOKED"]),
            "avg_execution_time": None
        }

        # Calculate average execution time for completed tasks
        completed_tasks = [t for t in tasks if t.started_at and t.completed_at]
        if completed_tasks:
            execution_times = [
                (t.completed_at - t.started_at).total_seconds()
                for t in completed_tasks
            ]
            stats["avg_execution_time"] = sum(execution_times) / len(execution_times)

        return stats

    @staticmethod
    def search_tasks(
        db: Session,
        search_term: str = None,
        user_id: str = None,
        status: str = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[TaskResult]:
        """Search task results by task name or result content."""
        query = db.query(TaskResult)

        if user_id:
            query = query.filter(TaskResult.user_id == user_id)

        if status:
            query = query.filter(TaskResult.status == status)

        if search_term:
            query = query.filter(TaskResult.task_name.ilike(f"%{search_term}%"))

        return query.order_by(desc(TaskResult.created_at)).offset(skip).limit(limit).all()
