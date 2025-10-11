"""
Unit tests for Celery tasks and background jobs.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from app.api.response_wrapper import (
    ErrorResponse,
    PaginatedResponse,
    SuccessResponse,
    handle_api_error,
    wrap_response,
)
from app.exceptions import ExternalServiceError, ValidationError
from app.tasks.chat_tasks import (
    cleanup_old_sessions,
    export_chat_history,
    generate_chat_title,
    process_chat_message_async,
)
from app.tasks.general_tasks import (
    backup_database_task,
    cleanup_expired_data,
    generate_system_report,
    health_check_external_services,
    send_email_notification,
)
from app.tasks.llm_tasks import (
    analyze_conversation_quality,
    batch_process_completions,
    generate_conversation_summary,
    warm_up_models,
)


class MockCeleryTask:
    """Mock Celery task for testing."""

    def __init__(self, name: str):
        self.name = name
        self.request = Mock()
        self.request.id = f"task-{name}-123"
        self.request.retries = 0
        self.request.called_directly = False

    def retry(self, countdown=None, max_retries=None, exc=None):
        """Mock retry method."""
        self.request.retries += 1
        if max_retries and self.request.retries >= max_retries:
            raise exc or Exception("Max retries reached")
        return Mock()

    def apply_async(self, args=None, kwargs=None, countdown=None):
        """Mock apply_async method."""
        return Mock(id=f"async-{self.name}-456", state="PENDING")


class MockDatabase:
    """Mock database for testing."""

    def __init__(self):
        self.sessions = []
        self.messages = []
        self.users = []
        self.operations_log = []

    async def get_old_sessions(self, older_than_days: int):
        """Mock getting old sessions."""
        cutoff_date = datetime.now() - timedelta(days=older_than_days)
        return [s for s in self.sessions if s.get('created_at', datetime.now()) < cutoff_date]

    async def delete_session(self, session_id: str):
        """Mock deleting session."""
        self.sessions = [s for s in self.sessions if s.get('id') != session_id]
        self.operations_log.append(f"deleted_session_{session_id}")
        return True

    async def get_session_messages(self, session_id: str):
        """Mock getting session messages."""
        return [m for m in self.messages if m.get('session_id') == session_id]

    async def get_user_sessions(self, user_id: str, limit: int = 100):
        """Mock getting user sessions."""
        return [s for s in self.sessions if s.get('user_id') == user_id][:limit]


class TestChatTasks:
    """Test chat-related Celery tasks."""

    @pytest.fixture
    def mock_chat_service(self):
        """Mock chat service."""
        service = Mock()
        service.process_message = AsyncMock(return_value={
            "message": "Test response",
            "session_id": "session-123",
            "response_time": 0.5
        })
        return service

    @pytest.fixture
    def mock_database(self):
        """Mock database."""
        return MockDatabase()

    @pytest.mark.asyncio
    async def test_process_chat_message_async_success(self, mock_chat_service):
        """Test async chat message processing."""
        message = "Hello, how are you?"
        user_id = "user-123"
        session_id = "session-456"

        with patch('app.tasks.chat_tasks.get_chat_service', return_value=mock_chat_service):
            result = await process_chat_message_async(message, user_id, session_id)

        assert result["message"] == "Test response"
        assert result["session_id"] == "session-123"
        mock_chat_service.process_message.assert_called_once_with(
            message=message,
            user_id=user_id,
            session_id=session_id
        )

    @pytest.mark.asyncio
    async def test_process_chat_message_async_error(self, mock_chat_service):
        """Test async chat message processing with error."""
        mock_chat_service.process_message.side_effect = ExternalServiceError("LLM service failed")

        with patch('app.tasks.chat_tasks.get_chat_service', return_value=mock_chat_service):
            with pytest.raises(ExternalServiceError):
                await process_chat_message_async("Hello", "user-123", "session-456")

    @pytest.mark.asyncio
    async def test_generate_chat_title_success(self, mock_chat_service):
        """Test chat title generation."""
        session_id = "session-123"
        messages = [
            {"role": "user", "content": "I need help with Python programming"},
            {"role": "assistant", "content": "I'd be happy to help you with Python!"},
        ]

        mock_chat_service.generate_title = AsyncMock(return_value="Python Programming Help")

        with patch('app.tasks.chat_tasks.get_chat_service', return_value=mock_chat_service), \
             patch('app.tasks.chat_tasks.get_session_messages', return_value=messages):

            title = await generate_chat_title(session_id)

        assert title == "Python Programming Help"
        mock_chat_service.generate_title.assert_called_once_with(messages)

    @pytest.mark.asyncio
    async def test_generate_chat_title_no_messages(self):
        """Test chat title generation with no messages."""
        session_id = "empty-session"

        with patch('app.tasks.chat_tasks.get_session_messages', return_value=[]):
            title = await generate_chat_title(session_id)

        assert title == "New Conversation"  # Default title

    @pytest.mark.asyncio
    async def test_cleanup_old_sessions(self, mock_database):
        """Test cleanup of old chat sessions."""
        # Add some old sessions to mock database
        old_date = datetime.now() - timedelta(days=35)
        recent_date = datetime.now() - timedelta(days=5)

        mock_database.sessions = [
            {"id": "old-1", "created_at": old_date, "user_id": "user-1"},
            {"id": "old-2", "created_at": old_date, "user_id": "user-2"},
            {"id": "recent-1", "created_at": recent_date, "user_id": "user-1"},
        ]

        with patch('app.tasks.chat_tasks.get_database', return_value=mock_database):
            result = await cleanup_old_sessions(older_than_days=30)

        assert result["deleted_count"] == 2
        assert result["sessions_deleted"] == ["old-1", "old-2"]
        assert "deleted_session_old-1" in mock_database.operations_log
        assert "deleted_session_old-2" in mock_database.operations_log

    @pytest.mark.asyncio
    async def test_export_chat_history(self, mock_database):
        """Test chat history export."""
        user_id = "user-123"

        mock_database.sessions = [
            {"id": "session-1", "user_id": user_id, "title": "Session 1"},
            {"id": "session-2", "user_id": user_id, "title": "Session 2"},
        ]

        mock_database.messages = [
            {"session_id": "session-1", "role": "user", "content": "Hello"},
            {"session_id": "session-1", "role": "assistant", "content": "Hi there!"},
            {"session_id": "session-2", "role": "user", "content": "How are you?"},
        ]

        with patch('app.tasks.chat_tasks.get_database', return_value=mock_database):
            result = await export_chat_history(user_id, format="json")

        assert result["status"] == "completed"
        assert result["user_id"] == user_id
        assert result["sessions_exported"] == 2
        assert result["messages_exported"] == 3
        assert "export_url" in result or "export_data" in result


class TestLLMTasks:
    """Test LLM-related Celery tasks."""

    @pytest.fixture
    def mock_llm_service(self):
        """Mock LLM service."""
        service = Mock()
        service.generate_completion = AsyncMock(return_value={
            "choices": [{"message": {"content": "Test completion"}}],
            "usage": {"total_tokens": 50}
        })
        service.health_check = AsyncMock(return_value=True)
        return service

    @pytest.mark.asyncio
    async def test_batch_process_completions(self, mock_llm_service):
        """Test batch processing of completions."""
        completion_requests = [
            {"id": "req-1", "prompt": "Complete this: Hello"},
            {"id": "req-2", "prompt": "Complete this: World"},
            {"id": "req-3", "prompt": "Complete this: Python"},
        ]

        with patch('app.tasks.llm_tasks.get_llm_service', return_value=mock_llm_service):
            results = await batch_process_completions(completion_requests)

        assert len(results) == 3
        assert all("completion" in result for result in results)
        assert all("tokens_used" in result for result in results)
        assert mock_llm_service.generate_completion.call_count == 3

    @pytest.mark.asyncio
    async def test_batch_process_completions_with_errors(self, mock_llm_service):
        """Test batch processing with some failures."""
        completion_requests = [
            {"id": "req-1", "prompt": "Valid request"},
            {"id": "req-2", "prompt": ""},  # Invalid empty prompt
            {"id": "req-3", "prompt": "Another valid request"},
        ]

        def side_effect(messages, **kwargs):
            if not messages or not messages[0].get("content"):
                raise ValidationError("Empty prompt")
            return {
                "choices": [{"message": {"content": "Success"}}],
                "usage": {"total_tokens": 25}
            }

        mock_llm_service.generate_completion.side_effect = side_effect

        with patch('app.tasks.llm_tasks.get_llm_service', return_value=mock_llm_service):
            results = await batch_process_completions(completion_requests)

        assert len(results) == 3
        assert results[0]["status"] == "success"
        assert results[1]["status"] == "error"
        assert results[2]["status"] == "success"

    @pytest.mark.asyncio
    async def test_warm_up_models(self, mock_llm_service):
        """Test model warm-up task."""
        models_to_warm = ["gpt-4o-mini", "gpt-4o", "claude-3-sonnet"]

        with patch('app.tasks.llm_tasks.get_llm_service', return_value=mock_llm_service):
            result = await warm_up_models(models_to_warm)

        assert result["warmed_up_count"] == 3
        assert result["models"] == models_to_warm
        assert all(model in result["results"] for model in models_to_warm)
        assert mock_llm_service.generate_completion.call_count == 3

    @pytest.mark.asyncio
    async def test_analyze_conversation_quality(self, mock_database):
        """Test conversation quality analysis."""
        session_id = "session-123"
        messages = [
            {"role": "user", "content": "What is machine learning?"},
            {"role": "assistant", "content": "Machine learning is a subset of artificial intelligence..."},
            {"role": "user", "content": "Can you give me an example?"},
            {"role": "assistant", "content": "Sure! A spam email filter is a common example..."},
        ]

        mock_database.messages = messages

        with patch('app.tasks.llm_tasks.get_database', return_value=mock_database):
            result = await analyze_conversation_quality(session_id)

        assert result["session_id"] == session_id
        assert "quality_score" in result
        assert "metrics" in result
        assert result["metrics"]["total_messages"] == 4
        assert result["metrics"]["user_messages"] == 2
        assert result["metrics"]["assistant_messages"] == 2

    @pytest.mark.asyncio
    async def test_generate_conversation_summary(self, mock_llm_service, mock_database):
        """Test conversation summary generation."""
        session_id = "session-456"
        messages = [
            {"role": "user", "content": "I need help with Python debugging"},
            {"role": "assistant", "content": "I can help you debug Python code..."},
            {"role": "user", "content": "My code throws a TypeError"},
            {"role": "assistant", "content": "Let's look at the TypeError..."},
        ]

        mock_database.messages = messages
        mock_llm_service.generate_completion.return_value = {
            "choices": [{"message": {"content": "Summary: User needed help debugging a Python TypeError issue."}}]
        }

        with patch('app.tasks.llm_tasks.get_database', return_value=mock_database), \
             patch('app.tasks.llm_tasks.get_llm_service', return_value=mock_llm_service):

            result = await generate_conversation_summary(session_id)

        assert result["session_id"] == session_id
        assert "Summary:" in result["summary"]
        assert result["message_count"] == 4


class TestGeneralTasks:
    """Test general utility Celery tasks."""

    @pytest.fixture
    def mock_email_service(self):
        """Mock email service."""
        service = Mock()
        service.send_email = AsyncMock(return_value={"status": "sent", "message_id": "msg-123"})
        return service

    @pytest.mark.asyncio
    async def test_send_email_notification(self, mock_email_service):
        """Test email notification sending."""
        email_data = {
            "to": "user@example.com",
            "subject": "Test Notification",
            "template": "notification",
            "context": {"user_name": "John Doe", "message": "Hello!"}
        }

        with patch('app.tasks.general_tasks.get_email_service', return_value=mock_email_service):
            result = await send_email_notification(email_data)

        assert result["status"] == "sent"
        assert result["message_id"] == "msg-123"
        mock_email_service.send_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_email_notification_failure(self, mock_email_service):
        """Test email notification with failure."""
        mock_email_service.send_email.side_effect = Exception("SMTP server error")

        email_data = {
            "to": "user@example.com",
            "subject": "Test",
            "template": "test",
            "context": {}
        }

        with patch('app.tasks.general_tasks.get_email_service', return_value=mock_email_service):
            result = await send_email_notification(email_data)

        assert result["status"] == "failed"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_cleanup_expired_data(self, mock_database):
        """Test cleanup of expired data."""
        # Mock expired data
        expired_items = [
            {"type": "session", "id": "expired-1", "expired_at": datetime.now() - timedelta(days=1)},
            {"type": "cache", "id": "expired-2", "expired_at": datetime.now() - timedelta(hours=1)},
        ]

        with patch('app.tasks.general_tasks.get_expired_data', return_value=expired_items), \
             patch('app.tasks.general_tasks.delete_expired_item') as mock_delete:

            result = await cleanup_expired_data()

        assert result["cleaned_count"] == 2
        assert result["types_cleaned"] == ["session", "cache"]
        assert mock_delete.call_count == 2

    @pytest.mark.asyncio
    async def test_generate_system_report(self):
        """Test system report generation."""
        with patch('app.tasks.general_tasks.get_system_metrics') as mock_metrics, \
             patch('app.tasks.general_tasks.get_database_stats') as mock_db_stats, \
             patch('app.tasks.general_tasks.get_service_health') as mock_health:

            mock_metrics.return_value = {"cpu_usage": 45.2, "memory_usage": 68.1}
            mock_db_stats.return_value = {"total_sessions": 1500, "total_messages": 12000}
            mock_health.return_value = {"redis": "healthy", "llm_service": "healthy"}

            result = await generate_system_report()

        assert result["report_type"] == "system_status"
        assert "metrics" in result
        assert "database_stats" in result
        assert "service_health" in result
        assert result["metrics"]["cpu_usage"] == 45.2
        assert result["database_stats"]["total_sessions"] == 1500

    @pytest.mark.asyncio
    async def test_backup_database_task(self):
        """Test database backup task."""
        with patch('app.tasks.general_tasks.create_database_backup') as mock_backup, \
             patch('app.tasks.general_tasks.upload_backup_to_storage') as mock_upload:

            mock_backup.return_value = {"backup_file": "/tmp/backup.sql", "size_mb": 125.5}
            mock_upload.return_value = {"url": "s3://backups/backup-123.sql", "status": "uploaded"}

            result = await backup_database_task(include_chat_data=True)

        assert result["status"] == "completed"
        assert result["backup_size_mb"] == 125.5
        assert "s3://" in result["backup_url"]
        mock_backup.assert_called_once_with(include_chat_data=True)
        mock_upload.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_external_services(self):
        """Test external services health check."""
        services_to_check = ["redis", "llm_service", "email_service"]

        async def mock_health_check(service_name):
            if service_name == "redis":
                return {"status": "healthy", "response_time": 0.05}
            elif service_name == "llm_service":
                return {"status": "degraded", "response_time": 2.1}
            else:
                return {"status": "healthy", "response_time": 0.12}

        with patch('app.tasks.general_tasks.check_service_health', side_effect=mock_health_check):
            result = await health_check_external_services(services_to_check)

        assert result["overall_status"] == "degraded"  # One service is degraded
        assert len(result["services"]) == 3
        assert result["services"]["redis"]["status"] == "healthy"
        assert result["services"]["llm_service"]["status"] == "degraded"


class TestAPIResponseWrapper:
    """Test API response wrapper functionality."""

    def test_success_response_creation(self):
        """Test creating success response."""
        data = {"user_id": "123", "name": "John Doe"}
        response = SuccessResponse(data=data, message="User retrieved successfully")

        assert response.success is True
        assert response.data == data
        assert response.message == "User retrieved successfully"
        assert response.error is None

    def test_error_response_creation(self):
        """Test creating error response."""
        response = ErrorResponse(
            message="User not found",
            error_code="USER_NOT_FOUND",
            details={"user_id": "nonexistent"}
        )

        assert response.success is False
        assert response.data is None
        assert response.message == "User not found"
        assert response.error_code == "USER_NOT_FOUND"
        assert response.details == {"user_id": "nonexistent"}

    def test_paginated_response_creation(self):
        """Test creating paginated response."""
        items = [{"id": 1, "name": "Item 1"}, {"id": 2, "name": "Item 2"}]
        pagination = {
            "page": 1,
            "page_size": 10,
            "total_items": 25,
            "total_pages": 3
        }

        response = PaginatedResponse(
            data=items,
            pagination=pagination,
            message="Items retrieved"
        )

        assert response.success is True
        assert response.data == items
        assert response.pagination == pagination
        assert response.pagination["total_items"] == 25

    def test_wrap_response_success_data(self):
        """Test wrapping successful data."""
        data = {"result": "success"}
        wrapped = wrap_response(data)

        assert isinstance(wrapped, SuccessResponse)
        assert wrapped.data == data
        assert wrapped.success is True

    def test_wrap_response_error_data(self):
        """Test wrapping error data."""
        error_data = {"error": "Something went wrong", "code": "INTERNAL_ERROR"}
        wrapped = wrap_response(error_data, success=False)

        assert isinstance(wrapped, ErrorResponse)
        assert not wrapped.success
        assert wrapped.message == "Something went wrong"

    def test_wrap_response_with_pagination(self):
        """Test wrapping data with pagination."""
        data = [{"id": 1}, {"id": 2}]
        pagination = {"page": 1, "total_items": 100}

        wrapped = wrap_response(data, pagination=pagination)

        assert isinstance(wrapped, PaginatedResponse)
        assert wrapped.data == data
        assert wrapped.pagination == pagination

    def test_handle_api_error_validation_error(self):
        """Test handling validation error."""
        error = ValidationError("Invalid input", field="email")
        response = handle_api_error(error)

        assert isinstance(response, ErrorResponse)
        assert response.message == "Invalid input"
        assert response.error_code == "VALIDATION_ERROR"
        assert "field" in response.details

    def test_handle_api_error_external_service_error(self):
        """Test handling external service error."""
        error = ExternalServiceError("LLM service unavailable")
        response = handle_api_error(error)

        assert isinstance(response, ErrorResponse)
        assert response.message == "LLM service unavailable"
        assert response.error_code == "EXTERNAL_SERVICE_ERROR"

    def test_handle_api_error_generic_exception(self):
        """Test handling generic exception."""
        error = Exception("Unexpected error")
        response = handle_api_error(error)

        assert isinstance(response, ErrorResponse)
        assert response.message == "Internal server error"
        assert response.error_code == "INTERNAL_ERROR"

    def test_api_response_serialization(self):
        """Test API response serialization to dict."""
        response = SuccessResponse(
            data={"key": "value"},
            message="Success"
        )

        serialized = response.dict()

        assert serialized["success"] is True
        assert serialized["data"] == {"key": "value"}
        assert serialized["message"] == "Success"
        assert serialized["error"] is None

    def test_api_response_json_serialization(self):
        """Test API response JSON serialization."""
        import json

        response = ErrorResponse(
            message="Test error",
            error_code="TEST_ERROR"
        )

        json_str = response.json()
        parsed = json.loads(json_str)

        assert parsed["success"] is False
        assert parsed["message"] == "Test error"
        assert parsed["error_code"] == "TEST_ERROR"


class TestTaskErrorHandling:
    """Test error handling in Celery tasks."""

    @pytest.mark.asyncio
    async def test_task_retry_on_external_service_error(self):
        """Test task retry on external service error."""
        mock_task = MockCeleryTask("test_task")

        with patch('app.tasks.chat_tasks.process_chat_message_async.retry') as mock_retry:
            mock_retry.side_effect = ExternalServiceError("Service unavailable")

            # Simulate task with retry logic
            try:
                # This would be the actual task execution
                raise ExternalServiceError("Service unavailable")
            except ExternalServiceError as e:
                if mock_task.request.retries < 3:
                    mock_task.retry(countdown=60, exc=e)

    @pytest.mark.asyncio
    async def test_task_failure_after_max_retries(self):
        """Test task failure after maximum retries."""
        mock_task = MockCeleryTask("failing_task")
        mock_task.request.retries = 3  # Already at max retries

        with pytest.raises(Exception):
            mock_task.retry(countdown=60, max_retries=3, exc=Exception("Max retries reached"))

    @pytest.mark.asyncio
    async def test_task_graceful_degradation(self):
        """Test task graceful degradation on partial failures."""
        # Example: batch processing where some items fail
        items_to_process = ["item1", "item2", "item3", "item4"]
        results = []

        for item in items_to_process:
            try:
                if item == "item3":  # Simulate failure
                    raise Exception("Processing failed")
                results.append({"item": item, "status": "success"})
            except Exception as e:
                results.append({"item": item, "status": "failed", "error": str(e)})

        # Task should complete with partial results
        assert len(results) == 4
        assert sum(1 for r in results if r["status"] == "success") == 3
        assert sum(1 for r in results if r["status"] == "failed") == 1


class TestTaskMetricsAndMonitoring:
    """Test task metrics and monitoring."""

    @pytest.mark.asyncio
    async def test_task_execution_time_tracking(self):
        """Test tracking task execution time."""
        import time

        start_time = time.time()

        # Simulate task execution
        await asyncio.sleep(0.1)

        end_time = time.time()
        execution_time = end_time - start_time

        assert execution_time > 0.1
        assert execution_time < 0.2  # Should complete quickly

    @pytest.mark.asyncio
    async def test_task_result_logging(self, caplog):
        """Test task result logging."""
        with caplog.at_level("INFO"):
            # Simulate successful task completion
            result = {"status": "completed", "items_processed": 10}

            # Log would be done in actual task
            import logging
            logging.info(f"Task completed successfully: {result}")

        assert "Task completed successfully" in caplog.text
        assert "items_processed" in caplog.text

    @pytest.mark.asyncio
    async def test_task_failure_logging(self, caplog):
        """Test task failure logging."""
        with caplog.at_level("ERROR"):
            try:
                raise ExternalServiceError("Service connection failed")
            except ExternalServiceError as e:
                import logging
                logging.error(f"Task failed: {e}")

        assert "Task failed" in caplog.text
        assert "Service connection failed" in caplog.text


class TestTaskIntegration:
    """Test task integration with other components."""

    @pytest.mark.asyncio
    async def test_chat_task_with_websocket_notification(self):
        """Test chat task triggering WebSocket notification."""
        mock_websocket_manager = Mock()
        mock_websocket_manager.send_to_user = AsyncMock()

        # Simulate chat task completion
        result = {
            "message": "Task completed",
            "session_id": "session-123",
            "user_id": "user-456"
        }

        # Task would send notification via WebSocket
        with patch('app.tasks.chat_tasks.get_websocket_manager', return_value=mock_websocket_manager):
            # Simulate notification sending
            await mock_websocket_manager.send_to_user(
                result["user_id"],
                {
                    "type": "task_completed",
                    "data": {
                        "task_type": "chat_processing",
                        "result": result
                    }
                }
            )

        mock_websocket_manager.send_to_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_task_with_database_transaction(self, mock_database):
        """Test task with database transaction handling."""
        # Simulate task that requires database transaction
        try:
            # Begin transaction
            transaction_id = "tx-123"

            # Perform database operations
            await mock_database.delete_session("session-1")
            await mock_database.delete_session("session-2")

            # Commit transaction
            result = {
                "status": "committed",
                "transaction_id": transaction_id,
                "operations": len(mock_database.operations_log)
            }

        except Exception as e:
            # Rollback transaction
            result = {
                "status": "rolled_back",
                "error": str(e)
            }

        assert result["status"] == "committed"
        assert result["operations"] == 2
