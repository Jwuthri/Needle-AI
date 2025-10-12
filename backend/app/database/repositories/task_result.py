"""
Task result repository for NeedleAi.
"""

from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ...utils.logging import get_logger
from ..models.task_result import TaskResult

logger = get_logger("task_result_repository")


class TaskResultRepository:
    """Repository for TaskResult model operations."""

    @staticmethod
    async def create(
        db: AsyncSession,
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
        await db.flush()
        await db.refresh(task_result)
        logger.info(f"Created task result: {task_result.id}")
        return task_result

    @staticmethod
    async def get_by_id(db: AsyncSession, task_id: str) -> Optional[TaskResult]:
        """Get task result by ID."""
        result = await db.execute(select(TaskResult).filter(TaskResult.id == task_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        status: str = None,
        task_name: str = None
    ) -> List[TaskResult]:
        """Get all task results with pagination and filtering."""
        query = select(TaskResult)

        if status:
            query = query.filter(TaskResult.status == status)

        if task_name:
            query = query.filter(TaskResult.task_name == task_name)

        query = query.order_by(desc(TaskResult.created_at)).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_user_tasks(
        db: AsyncSession,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
        status: str = None
    ) -> List[TaskResult]:
        """Get user's task results."""
        query = select(TaskResult).filter(TaskResult.user_id == user_id)

        if status:
            query = query.filter(TaskResult.status == status)

        query = query.order_by(desc(TaskResult.created_at)).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_by_task_name(
        db: AsyncSession,
        task_name: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[TaskResult]:
        """Get task results by task name."""
        query = (
            select(TaskResult)
            .filter(TaskResult.task_name == task_name)
            .order_by(desc(TaskResult.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def update(db: AsyncSession, task_id: str, **kwargs) -> Optional[TaskResult]:
        """Update task result."""
        task_result = await TaskResultRepository.get_by_id(db, task_id)
        if not task_result:
            return None

        for key, value in kwargs.items():
            if hasattr(task_result, key):
                setattr(task_result, key, value)

        await db.flush()
        await db.refresh(task_result)
        return task_result

    @staticmethod
    async def update_status(
        db: AsyncSession,
        task_id: str,
        status: str,
        result: dict = None,
        error_message: str = None,
        traceback: str = None
    ) -> Optional[TaskResult]:
        """Update task status and result."""
        task_result = await TaskResultRepository.get_by_id(db, task_id)
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

        await db.flush()
        await db.refresh(task_result)
        return task_result

    @staticmethod
    async def delete(db: AsyncSession, task_id: str) -> bool:
        """Delete task result by ID."""
        task_result = await TaskResultRepository.get_by_id(db, task_id)
        if task_result:
            await db.delete(task_result)
            await db.flush()
            logger.info(f"Deleted task result: {task_id}")
            return True
        return False

    @staticmethod
    async def cleanup_old_tasks(db: AsyncSession, days_old: int = 30) -> int:
        """Clean up old completed task results."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        result = await db.execute(
            select(TaskResult).filter(
                TaskResult.completed_at < cutoff_date,
                TaskResult.status.in_(["SUCCESS", "FAILURE", "REVOKED"])
            )
        )
        old_tasks = result.scalars().all()
        
        deleted_count = 0
        for task in old_tasks:
            await db.delete(task)
            deleted_count += 1

        await db.flush()
        logger.info(f"Cleaned up {deleted_count} old task results")
        return deleted_count

    @staticmethod
    async def count_by_status(db: AsyncSession, status: str, user_id: str = None) -> int:
        """Count task results by status."""
        query = select(TaskResult).filter(TaskResult.status == status)

        if user_id:
            query = query.filter(TaskResult.user_id == user_id)

        result = await db.execute(query)
        return len(list(result.scalars().all()))

    @staticmethod
    async def get_task_stats(db: AsyncSession, user_id: str = None) -> dict:
        """Get task statistics."""
        query = select(TaskResult)

        if user_id:
            query = query.filter(TaskResult.user_id == user_id)

        result = await db.execute(query)
        tasks = list(result.scalars().all())

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
    async def search_tasks(
        db: AsyncSession,
        search_term: str = None,
        user_id: str = None,
        status: str = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[TaskResult]:
        """Search task results by task name or result content."""
        query = select(TaskResult)

        if user_id:
            query = query.filter(TaskResult.user_id == user_id)

        if status:
            query = query.filter(TaskResult.status == status)

        if search_term:
            query = query.filter(TaskResult.task_name.ilike(f"%{search_term}%"))

        query = query.order_by(desc(TaskResult.created_at)).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())
