"""
Task-related Pydantic models for API serialization (Celery background tasks).
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Task status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"
    REVOKED = "revoked"


class TaskPriority(str, Enum):
    """Task priority enumeration."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


# Request models
class TaskSubmissionRequest(BaseModel):
    """Task submission request model."""
    task_name: str = Field(..., description="Name of the task to execute")
    task_args: Optional[List[Any]] = Field(None, description="Positional arguments for the task")
    task_kwargs: Optional[Dict[str, Any]] = Field(None, description="Keyword arguments for the task")
    priority: TaskPriority = Field(TaskPriority.NORMAL, description="Task execution priority")
    eta: Optional[datetime] = Field(None, description="Estimated time of arrival (when to execute)")
    countdown: Optional[int] = Field(None, description="Delay in seconds before execution")
    expires: Optional[datetime] = Field(None, description="Task expiration time")
    retry_policy: Optional[Dict[str, Any]] = Field(None, description="Custom retry policy")

    class Config:
        json_schema_extra = {
            "example": {
                "task_name": "app.tasks.llm_tasks.generate_completion",
                "task_args": [],
                "task_kwargs": {
                    "prompt": "Complete this sentence: The weather today is",
                    "max_tokens": 50,
                    "temperature": 0.7
                },
                "priority": "normal",
                "countdown": 5,
                "retry_policy": {
                    "max_retries": 3,
                    "retry_backoff": True
                }
            }
        }


class TaskCancelRequest(BaseModel):
    """Task cancellation request model."""
    terminate: bool = Field(False, description="Whether to terminate the task immediately")

    class Config:
        json_schema_extra = {
            "example": {
                "terminate": False
            }
        }


# Response models
class TaskInfo(BaseModel):
    """Task information response model."""
    id: str = Field(..., description="Task ID")
    task_name: str = Field(..., description="Name of the task")
    status: TaskStatus = Field(..., description="Current task status")
    user_id: Optional[int] = Field(None, description="User who submitted the task")
    created_at: datetime = Field(..., description="Task creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Task start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Task completion timestamp")
    result: Optional[Any] = Field(None, description="Task result if completed successfully")
    error_message: Optional[str] = Field(None, description="Error message if task failed")
    traceback: Optional[str] = Field(None, description="Full error traceback if task failed")
    progress: Optional[float] = Field(None, description="Task progress percentage (0-100)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional task metadata")
    priority: TaskPriority = Field(TaskPriority.NORMAL, description="Task priority")
    retry_count: int = Field(0, description="Number of retry attempts")
    max_retries: int = Field(3, description="Maximum retry attempts")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")

    class Config:
        from_attributes = True  # For SQLAlchemy model conversion
        json_schema_extra = {
            "example": {
                "id": "12345678-1234-1234-1234-123456789abc",
                "task_name": "app.tasks.llm_tasks.generate_completion",
                "status": "success",
                "user_id": 1,
                "created_at": "2024-01-15T10:00:00Z",
                "started_at": "2024-01-15T10:00:05Z",
                "completed_at": "2024-01-15T10:00:15Z",
                "result": {
                    "completion": "sunny and warm with a gentle breeze.",
                    "tokens_used": 12,
                    "model": "gpt-4o-mini"
                },
                "error_message": None,
                "progress": 100.0,
                "metadata": {
                    "model_used": "gpt-4o-mini",
                    "temperature": 0.7,
                    "processing_time": 10.2
                },
                "priority": "normal",
                "retry_count": 0,
                "max_retries": 3
            }
        }


class TaskSubmissionResponse(BaseModel):
    """Task submission response model."""
    task_id: str = Field(..., description="Unique task identifier")
    task_name: str = Field(..., description="Name of the submitted task")
    status: TaskStatus = Field(..., description="Initial task status")
    created_at: datetime = Field(..., description="Task creation timestamp")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")
    status_url: str = Field(..., description="URL to check task status")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "12345678-1234-1234-1234-123456789abc",
                "task_name": "app.tasks.llm_tasks.generate_completion",
                "status": "pending",
                "created_at": "2024-01-15T10:00:00Z",
                "estimated_completion": "2024-01-15T10:00:30Z",
                "status_url": "/api/v1/tasks/12345678-1234-1234-1234-123456789abc"
            }
        }


class TaskProgressUpdate(BaseModel):
    """Task progress update model."""
    task_id: str = Field(..., description="Task ID")
    progress: float = Field(..., ge=0, le=100, description="Progress percentage (0-100)")
    status_message: Optional[str] = Field(None, description="Human-readable status message")
    intermediate_result: Optional[Any] = Field(None, description="Intermediate result data")
    estimated_completion: Optional[datetime] = Field(None, description="Updated completion estimate")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "12345678-1234-1234-1234-123456789abc",
                "progress": 75.0,
                "status_message": "Processing completion request...",
                "intermediate_result": {
                    "partial_text": "The weather today is sunny and"
                },
                "estimated_completion": "2024-01-15T10:00:25Z"
            }
        }


class TaskStatistics(BaseModel):
    """Task statistics response model."""
    total_tasks: int = Field(0, description="Total number of tasks")
    pending_tasks: int = Field(0, description="Number of pending tasks")
    running_tasks: int = Field(0, description="Number of running tasks")
    completed_tasks: int = Field(0, description="Number of completed tasks")
    failed_tasks: int = Field(0, description="Number of failed tasks")
    average_execution_time: float = Field(0.0, description="Average execution time in seconds")
    tasks_per_hour: float = Field(0.0, description="Tasks processed per hour")
    success_rate: float = Field(0.0, description="Success rate percentage")

    class Config:
        json_schema_extra = {
            "example": {
                "total_tasks": 1250,
                "pending_tasks": 5,
                "running_tasks": 3,
                "completed_tasks": 1200,
                "failed_tasks": 42,
                "average_execution_time": 8.7,
                "tasks_per_hour": 120.5,
                "success_rate": 96.6
            }
        }


# List models
class TaskListItem(BaseModel):
    """Task list item for paginated responses."""
    id: str = Field(..., description="Task ID")
    task_name: str = Field(..., description="Name of the task")
    status: TaskStatus = Field(..., description="Current task status")
    user_id: Optional[int] = Field(None, description="User who submitted the task")
    created_at: datetime = Field(..., description="Task creation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Task completion timestamp")
    progress: Optional[float] = Field(None, description="Task progress percentage")
    priority: TaskPriority = Field(TaskPriority.NORMAL, description="Task priority")
    retry_count: int = Field(0, description="Number of retry attempts")
    execution_time: Optional[float] = Field(None, description="Execution time in seconds")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "12345678-1234-1234-1234-123456789abc",
                "task_name": "app.tasks.llm_tasks.generate_completion",
                "status": "success",
                "user_id": 1,
                "created_at": "2024-01-15T10:00:00Z",
                "completed_at": "2024-01-15T10:00:15Z",
                "progress": 100.0,
                "priority": "normal",
                "retry_count": 0,
                "execution_time": 10.2
            }
        }


class TaskListResponse(BaseModel):
    """Paginated task list response."""
    tasks: List[TaskListItem] = Field(..., description="List of tasks")
    total: int = Field(..., description="Total number of tasks")
    limit: int = Field(..., description="Items per page")
    offset: int = Field(..., description="Items skipped")
    has_more: bool = Field(..., description="Whether there are more items")
    statistics: Optional[TaskStatistics] = Field(None, description="Task statistics")

    class Config:
        json_schema_extra = {
            "example": {
                "tasks": [
                    {
                        "id": "12345678-1234-1234-1234-123456789abc",
                        "task_name": "app.tasks.llm_tasks.generate_completion",
                        "status": "success",
                        "user_id": 1,
                        "created_at": "2024-01-15T10:00:00Z",
                        "completed_at": "2024-01-15T10:00:15Z",
                        "progress": 100.0,
                        "priority": "normal",
                        "retry_count": 0,
                        "execution_time": 10.2
                    }
                ],
                "total": 1,
                "limit": 50,
                "offset": 0,
                "has_more": False,
                "statistics": {
                    "total_tasks": 1250,
                    "pending_tasks": 5,
                    "running_tasks": 3,
                    "completed_tasks": 1200,
                    "failed_tasks": 42,
                    "success_rate": 96.6
                }
            }
        }


# Queue models
class QueueInfo(BaseModel):
    """Queue information model."""
    name: str = Field(..., description="Queue name")
    pending_tasks: int = Field(0, description="Number of pending tasks in queue")
    active_tasks: int = Field(0, description="Number of active tasks in queue")
    workers: int = Field(0, description="Number of workers processing this queue")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "llm",
                "pending_tasks": 5,
                "active_tasks": 2,
                "workers": 3
            }
        }


class WorkerInfo(BaseModel):
    """Worker information model."""
    name: str = Field(..., description="Worker name")
    status: str = Field(..., description="Worker status")
    active_tasks: int = Field(0, description="Number of active tasks")
    processed_tasks: int = Field(0, description="Total processed tasks")
    queues: List[str] = Field(..., description="Queues this worker processes")
    last_heartbeat: Optional[datetime] = Field(None, description="Last heartbeat timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "worker-1@hostname",
                "status": "online",
                "active_tasks": 2,
                "processed_tasks": 1250,
                "queues": ["llm", "chat"],
                "last_heartbeat": "2024-01-15T10:00:00Z"
            }
        }


class TaskSystemStatus(BaseModel):
    """Overall task system status."""
    queues: List[QueueInfo] = Field(..., description="Queue information")
    workers: List[WorkerInfo] = Field(..., description="Worker information")
    statistics: TaskStatistics = Field(..., description="Overall task statistics")
    system_health: str = Field(..., description="Overall system health status")

    class Config:
        json_schema_extra = {
            "example": {
                "queues": [
                    {
                        "name": "llm",
                        "pending_tasks": 5,
                        "active_tasks": 2,
                        "workers": 3
                    }
                ],
                "workers": [
                    {
                        "name": "worker-1@hostname",
                        "status": "online",
                        "active_tasks": 2,
                        "processed_tasks": 1250,
                        "queues": ["llm", "chat"],
                        "last_heartbeat": "2024-01-15T10:00:00Z"
                    }
                ],
                "statistics": {
                    "total_tasks": 1250,
                    "success_rate": 96.6
                },
                "system_health": "healthy"
            }
        }
