"""
Chat-related background tasks for NeedleAi.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.config import get_settings
from app.core.celery_app import celery_app
from app.services.redis_client import RedisClient
from app.utils.logging import get_logger

logger = get_logger("chat_tasks")
settings = get_settings()


@celery_app.task(bind=True, max_retries=3)
def process_chat_message_async(
    self,
    message: str,
    session_id: str,
    user_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Process chat message asynchronously for complex operations.

    Args:
        message: User message content
        session_id: Chat session ID
        user_id: Optional user ID
        context: Additional context data

    Returns:
        Dict with processing result
    """
    try:
        logger.info(f"Processing async chat message for session {session_id}")

        self.update_state(
            state='PROGRESS',
            meta={'current': 20, 'total': 100, 'status': 'Analyzing message...'}
        )

        # Simulate message analysis (sentiment, intent, etc.)
        import time
        time.sleep(1)

        self.update_state(
            state='PROGRESS',
            meta={'current': 60, 'total': 100, 'status': 'Generating response...'}
        )

        # Here you could integrate with your chat service
        # For now, returning a processed result

        self.update_state(
            state='PROGRESS',
            meta={'current': 100, 'total': 100, 'status': 'Message processed!'}
        )

        result = {
            "task_id": self.request.id,
            "session_id": session_id,
            "user_id": user_id,
            "processed_message": message,
            "analysis": {
                "sentiment": "positive",  # Mock analysis
                "intent": "general_question",
                "complexity": "medium"
            },
            "timestamp": datetime.utcnow().isoformat(),
            "status": "completed"
        }

        logger.info(f"Completed async chat processing for session {session_id}")
        return result

    except Exception as exc:
        logger.error(f"Error in async chat processing: {str(exc)}")

        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=30)

        return {
            "task_id": self.request.id,
            "session_id": session_id,
            "error": str(exc),
            "status": "failed"
        }


@celery_app.task(bind=True, max_retries=2)
def clean_old_sessions(self, days_old: int = 7) -> Dict[str, Any]:
    """
    Clean up old chat sessions and their data.

    Args:
        days_old: Remove sessions older than this many days

    Returns:
        Dict with cleanup statistics
    """
    try:
        logger.info(f"Starting cleanup of sessions older than {days_old} days")

        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        # Initialize Redis client
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            async def cleanup_task():
                redis_client = RedisClient(redis_url=settings.redis_url)
                await redis_client.connect()

                # Get all session keys
                session_keys = await redis_client.redis.keys("session:*")
                old_sessions = []

                # Check each session's timestamp
                for key in session_keys:
                    session_data = await redis_client.get(key.decode())
                    if session_data:
                        session_timestamp = datetime.fromisoformat(
                            session_data.get("created_at", datetime.utcnow().isoformat())
                        )
                        if session_timestamp < cutoff_date:
                            old_sessions.append(key.decode())

                # Remove old sessions
                deleted_count = 0
                for session_key in old_sessions:
                    try:
                        await redis_client.delete(session_key)
                        # Also remove associated message history
                        await redis_client.delete(f"{session_key}:messages")
                        deleted_count += 1
                    except Exception as e:
                        logger.error(f"Error deleting session {session_key}: {str(e)}")

                await redis_client.disconnect()
                return len(session_keys), deleted_count

            self.update_state(
                state='PROGRESS',
                meta={'current': 25, 'total': 100, 'status': 'Scanning for old sessions...'}
            )

            session_count, deleted_count = loop.run_until_complete(cleanup_task())

            self.update_state(
                state='PROGRESS',
                meta={'current': 50, 'total': 100, 'status': f'Checking {session_count} sessions...'}
            )

            self.update_state(
                state='PROGRESS',
                meta={'current': 75, 'total': 100, 'status': f'Removing {deleted_count} old sessions...'}
            )

        finally:
            loop.close()

        logger.info(f"Cleanup completed: {deleted_count} sessions removed")

        return {
            "task_id": self.request.id,
            "sessions_scanned": session_count,
            "sessions_deleted": deleted_count,
            "cutoff_date": cutoff_date.isoformat(),
            "status": "completed"
        }

    except Exception as exc:
        logger.error(f"Error in session cleanup: {str(exc)}")

        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=300)  # 5 minute delay

        return {
            "task_id": self.request.id,
            "error": str(exc),
            "status": "failed"
        }


@celery_app.task(bind=True, max_retries=2)
def backup_conversation_history(self, session_ids: List[str] = None) -> Dict[str, Any]:
    """
    Backup conversation history to long-term storage.

    Args:
        session_ids: Specific session IDs to backup (optional)

    Returns:
        Dict with backup results
    """
    try:
        logger.info("Starting conversation history backup")

        # This would integrate with your chosen backup storage (S3, etc.)
        # For now, simulating backup process

        self.update_state(
            state='PROGRESS',
            meta={'current': 30, 'total': 100, 'status': 'Collecting conversation data...'}
        )

        import time
        time.sleep(2)

        self.update_state(
            state='PROGRESS',
            meta={'current': 70, 'total': 100, 'status': 'Uploading to backup storage...'}
        )

        time.sleep(2)

        self.update_state(
            state='PROGRESS',
            meta={'current': 100, 'total': 100, 'status': 'Backup completed!'}
        )

        # Mock backup results
        backed_up_sessions = session_ids if session_ids else ["session_1", "session_2", "session_3"]

        return {
            "task_id": self.request.id,
            "backed_up_sessions": len(backed_up_sessions),
            "session_ids": backed_up_sessions,
            "backup_timestamp": datetime.utcnow().isoformat(),
            "backup_location": "s3://backups/conversations/",
            "status": "completed"
        }

    except Exception as exc:
        logger.error(f"Error in conversation backup: {str(exc)}")

        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=600)  # 10 minute delay

        return {
            "task_id": self.request.id,
            "error": str(exc),
            "status": "failed"
        }
