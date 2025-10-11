"""
Task management API endpoints for NeedleAi.
"""

from typing import Any, Dict, List, Optional

from app.api.deps import get_user_id_from_header
from app.core.celery_app import celery_app
from app.tasks.chat_tasks import clean_old_sessions, process_chat_message_async
from app.tasks.general_tasks import (
    cleanup_expired_cache,
    health_check_services,
    send_notification,
)
from app.tasks.llm_tasks import batch_process_messages, generate_completion_async
from app.utils.logging import get_logger
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

logger = get_logger("tasks_api")
router = APIRouter()


# Request/Response Models
class TaskTriggerRequest(BaseModel):
    """Request model for triggering tasks."""
    task_name: str
    args: List[Any] = []
    kwargs: Dict[str, Any] = {}
    queue: Optional[str] = None
    countdown: Optional[int] = None  # Delay in seconds
    eta: Optional[str] = None  # ISO timestamp


class TaskStatusResponse(BaseModel):
    """Response model for task status."""
    task_id: str
    status: str  # PENDING, STARTED, SUCCESS, FAILURE, RETRY, REVOKED
    result: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class LLMCompletionRequest(BaseModel):
    """Request model for LLM completion task."""
    prompt: str
    model: Optional[str] = None
    max_tokens: Optional[int] = 1000
    temperature: Optional[float] = 0.7
    delay_seconds: Optional[int] = None


class BatchProcessRequest(BaseModel):
    """Request model for batch processing."""
    messages: List[Dict[str, Any]]
    model: Optional[str] = None


class ChatProcessRequest(BaseModel):
    """Request model for chat processing."""
    message: str
    session_id: str
    user_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class NotificationRequest(BaseModel):
    """Request model for notifications."""
    recipient: str
    message: str
    notification_type: str = "info"
    metadata: Optional[Dict[str, Any]] = None


@router.get("/")
async def list_active_tasks() -> Dict[str, Any]:
    """List all active tasks."""
    try:
        # Get active tasks using Celery's inspect
        inspect = celery_app.control.inspect()

        active_tasks = inspect.active()
        scheduled_tasks = inspect.scheduled()
        reserved_tasks = inspect.reserved()

        return {
            "active": active_tasks or {},
            "scheduled": scheduled_tasks or {},
            "reserved": reserved_tasks or {},
            "total_active": sum(len(tasks) for tasks in (active_tasks or {}).values()),
            "total_scheduled": sum(len(tasks) for tasks in (scheduled_tasks or {}).values()),
            "total_reserved": sum(len(tasks) for tasks in (reserved_tasks or {}).values())
        }

    except Exception as e:
        logger.error(f"Error listing tasks: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list tasks: {str(e)}")


@router.get("/{task_id}")
async def get_task_status(task_id: str) -> TaskStatusResponse:
    """Get task status and result."""
    try:
        result = celery_app.AsyncResult(task_id)

        response_data = {
            "task_id": task_id,
            "status": result.status,
        }

        if result.ready():
            if result.successful():
                response_data["result"] = result.result
            else:
                response_data["error"] = str(result.info)
        else:
            # Task is still processing, get progress if available
            if hasattr(result.info, 'get') and result.info:
                response_data["meta"] = result.info

        return TaskStatusResponse(**response_data)

    except Exception as e:
        logger.error(f"Error getting task status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get task status: {str(e)}")


@router.delete("/{task_id}")
async def cancel_task(task_id: str) -> Dict[str, Any]:
    """Cancel a task."""
    try:
        celery_app.control.revoke(task_id, terminate=True)

        return {
            "task_id": task_id,
            "status": "cancelled",
            "message": "Task cancellation requested"
        }

    except Exception as e:
        logger.error(f"Error cancelling task: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel task: {str(e)}")


# LLM Task Endpoints
@router.post("/llm/completion")
async def trigger_llm_completion(
    request: LLMCompletionRequest,
    user_id: Optional[str] = Depends(get_user_id_from_header)
) -> Dict[str, Any]:
    """Trigger asynchronous LLM completion."""
    try:
        task_kwargs = {
            "prompt": request.prompt,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature
        }

        if request.model:
            task_kwargs["model"] = request.model

        # Trigger task
        if request.delay_seconds:
            result = generate_completion_async.apply_async(
                kwargs=task_kwargs,
                countdown=request.delay_seconds,
                queue="llm"
            )
        else:
            result = generate_completion_async.apply_async(
                kwargs=task_kwargs,
                queue="llm"
            )

        logger.info(f"LLM completion task triggered: {result.id} by user {user_id}")

        return {
            "task_id": result.id,
            "status": "submitted",
            "queue": "llm",
            "estimated_duration": "30-60 seconds"
        }

    except Exception as e:
        logger.error(f"Error triggering LLM completion: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger LLM completion: {str(e)}")


@router.post("/llm/batch")
async def trigger_batch_processing(
    request: BatchProcessRequest,
    user_id: Optional[str] = Depends(get_user_id_from_header)
) -> Dict[str, Any]:
    """Trigger batch message processing."""
    try:
        task_kwargs = {
            "messages": request.messages,
            "model": request.model
        }

        result = batch_process_messages.apply_async(
            kwargs=task_kwargs,
            queue="llm"
        )

        logger.info(f"Batch processing task triggered: {result.id} by user {user_id}")

        return {
            "task_id": result.id,
            "status": "submitted",
            "queue": "llm",
            "message_count": len(request.messages),
            "estimated_duration": f"{len(request.messages) * 2}-{len(request.messages) * 5} seconds"
        }

    except Exception as e:
        logger.error(f"Error triggering batch processing: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger batch processing: {str(e)}")


# Chat Task Endpoints
@router.post("/chat/process")
async def trigger_chat_processing(
    request: ChatProcessRequest,
    user_id: Optional[str] = Depends(get_user_id_from_header)
) -> Dict[str, Any]:
    """Trigger asynchronous chat message processing."""
    try:
        task_kwargs = {
            "message": request.message,
            "session_id": request.session_id,
            "user_id": request.user_id or user_id,
            "context": request.context
        }

        result = process_chat_message_async.apply_async(
            kwargs=task_kwargs,
            queue="chat"
        )

        logger.info(f"Chat processing task triggered: {result.id} for session {request.session_id}")

        return {
            "task_id": result.id,
            "status": "submitted",
            "queue": "chat",
            "session_id": request.session_id,
            "estimated_duration": "10-30 seconds"
        }

    except Exception as e:
        logger.error(f"Error triggering chat processing: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger chat processing: {str(e)}")


@router.post("/chat/cleanup")
async def trigger_session_cleanup(
    days_old: int = 7,
    user_id: Optional[str] = Depends(get_user_id_from_header)
) -> Dict[str, Any]:
    """Trigger cleanup of old chat sessions."""
    try:
        result = clean_old_sessions.apply_async(
            kwargs={"days_old": days_old},
            queue="general"
        )

        logger.info(f"Session cleanup task triggered: {result.id} by user {user_id}")

        return {
            "task_id": result.id,
            "status": "submitted",
            "queue": "general",
            "days_old": days_old,
            "estimated_duration": "1-5 minutes"
        }

    except Exception as e:
        logger.error(f"Error triggering session cleanup: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger session cleanup: {str(e)}")


# General Task Endpoints
@router.post("/notifications")
async def trigger_notification(
    request: NotificationRequest,
    user_id: Optional[str] = Depends(get_user_id_from_header)
) -> Dict[str, Any]:
    """Trigger notification sending."""
    try:
        task_kwargs = {
            "recipient": request.recipient,
            "message": request.message,
            "notification_type": request.notification_type,
            "metadata": request.metadata
        }

        result = send_notification.apply_async(
            kwargs=task_kwargs,
            queue="general"
        )

        logger.info(f"Notification task triggered: {result.id} by user {user_id}")

        return {
            "task_id": result.id,
            "status": "submitted",
            "queue": "general",
            "recipient": request.recipient,
            "estimated_duration": "5-15 seconds"
        }

    except Exception as e:
        logger.error(f"Error triggering notification: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger notification: {str(e)}")


@router.post("/system/health-check")
async def trigger_health_check(
    user_id: Optional[str] = Depends(get_user_id_from_header)
) -> Dict[str, Any]:
    """Trigger system health check."""
    try:
        result = health_check_services.apply_async(queue="general")

        logger.info(f"Health check task triggered: {result.id} by user {user_id}")

        return {
            "task_id": result.id,
            "status": "submitted",
            "queue": "general",
            "estimated_duration": "30-60 seconds"
        }

    except Exception as e:
        logger.error(f"Error triggering health check: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger health check: {str(e)}")


@router.post("/system/cache-cleanup")
async def trigger_cache_cleanup(
    pattern: str = "*",
    max_age_hours: int = 24,
    user_id: Optional[str] = Depends(get_user_id_from_header)
) -> Dict[str, Any]:
    """Trigger cache cleanup."""
    try:
        task_kwargs = {
            "pattern": pattern,
            "max_age_hours": max_age_hours
        }

        result = cleanup_expired_cache.apply_async(
            kwargs=task_kwargs,
            queue="general"
        )

        logger.info(f"Cache cleanup task triggered: {result.id} by user {user_id}")

        return {
            "task_id": result.id,
            "status": "submitted",
            "queue": "general",
            "pattern": pattern,
            "max_age_hours": max_age_hours,
            "estimated_duration": "1-3 minutes"
        }

    except Exception as e:
        logger.error(f"Error triggering cache cleanup: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger cache cleanup: {str(e)}")


@router.get("/stats")
async def get_task_stats() -> Dict[str, Any]:
    """Get overall task statistics."""
    try:
        inspect = celery_app.control.inspect()

        stats = inspect.stats()
        active = inspect.active()

        total_active = sum(len(tasks) for tasks in (active or {}).values())

        # Worker information
        worker_info = {}
        if stats:
            for worker, worker_stats in stats.items():
                worker_info[worker] = {
                    "status": "online",
                    "total_tasks": worker_stats.get("total", 0),
                    "pool_processes": worker_stats.get("pool", {}).get("processes", 0),
                    "rusage": worker_stats.get("rusage", {})
                }

        return {
            "total_active_tasks": total_active,
            "workers": worker_info,
            "queues": ["general", "chat", "llm"],
            "task_types": [
                "generate_completion_async",
                "batch_process_messages",
                "process_chat_message_async",
                "clean_old_sessions",
                "send_notification",
                "cleanup_expired_cache",
                "health_check_services",
                "generate_report"
            ]
        }

    except Exception as e:
        logger.error(f"Error getting task stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get task stats: {str(e)}")
