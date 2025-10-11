"""
Unit tests for chat services and chat service factory.
"""

from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest
from app.exceptions import ConfigurationError, ExternalServiceError, ValidationError
from app.services.chat_service import ChatService
from app.services.chat_service_factory import ChatServiceFactory, ChatServiceType
from app.services.database_chat_service import DatabaseChatService


# Mock settings class for testing
class MockSettings:
    """Mock settings for testing."""

    def __init__(self, **kwargs):
        self.llm_provider = kwargs.get("llm_provider", "openrouter")
        self.enable_agno = kwargs.get("enable_agno", True)
        self.openrouter_api_key = kwargs.get("openrouter_api_key", "test-key")
        self.model_name = kwargs.get("model_name", "gpt-4o-mini")
        self.max_tokens = kwargs.get("max_tokens", 1000)
        self.temperature = kwargs.get("temperature", 0.7)
        self.redis_url = kwargs.get("redis_url", "redis://localhost:6379")
        self.database_url = kwargs.get("database_url", "sqlite:///test.db")

    def get_secret(self, key: str) -> Optional[str]:
        """Mock get_secret method."""
        secrets = {
            "openrouter_api_key": self.openrouter_api_key,
            "anthropic_api_key": "test-anthropic-key",
            "openai_api_key": "test-openai-key"
        }
        return secrets.get(key)


class MockMemoryStore:
    """Mock memory store for testing."""

    def __init__(self):
        self.memories = {}

    async def store(self, key: str, value: Any) -> None:
        """Store memory."""
        self.memories[key] = value

    async def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve memory."""
        return self.memories.get(key)

    async def delete(self, key: str) -> bool:
        """Delete memory."""
        if key in self.memories:
            del self.memories[key]
            return True
        return False


class MockLLMService:
    """Mock LLM service for testing."""

    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.call_count = 0

    async def generate_completion(self, messages: list, **kwargs) -> Dict[str, Any]:
        """Mock completion generation."""
        self.call_count += 1

        if self.should_fail:
            raise ExternalServiceError("LLM service failed")

        return {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": f"Mock response {self.call_count}"
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30
            },
            "model": "mock-model"
        }


class TestChatServiceFactory:
    """Test chat service factory functionality."""

    @pytest.mark.asyncio
    async def test_create_chat_service_auto_agno_available(self):
        """Test auto selection chooses Agno when available."""
        settings = MockSettings(enable_agno=True)

        with patch('app.services.chat_service_factory.ChatServiceFactory._should_use_agno', return_value=True), \
             patch('app.services.chat_service_factory.ChatServiceFactory._create_agno_service') as mock_agno:

            mock_agno_service = MagicMock()
            mock_agno.return_value = mock_agno_service

            service = await ChatServiceFactory.create_chat_service(
                settings=settings,
                service_type=ChatServiceType.AUTO
            )

            assert service == mock_agno_service
            mock_agno.assert_called_once_with(settings)

    @pytest.mark.asyncio
    async def test_create_chat_service_auto_fallback_to_custom(self):
        """Test auto selection falls back to custom when Agno fails."""
        settings = MockSettings(enable_agno=True)

        with patch('app.services.chat_service_factory.ChatServiceFactory._should_use_agno', return_value=True), \
             patch('app.services.chat_service_factory.ChatServiceFactory._create_agno_service', side_effect=Exception("Agno failed")), \
             patch('app.services.chat_service_factory.ChatServiceFactory._create_custom_service') as mock_custom:

            mock_custom_service = MagicMock()
            mock_custom.return_value = mock_custom_service

            service = await ChatServiceFactory.create_chat_service(
                settings=settings,
                service_type=ChatServiceType.AUTO
            )

            assert service == mock_custom_service
            mock_custom.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_chat_service_explicit_agno(self):
        """Test explicit Agno selection doesn't fallback on failure."""
        settings = MockSettings(enable_agno=True)

        with patch('app.services.chat_service_factory.ChatServiceFactory._should_use_agno', return_value=True), \
             patch('app.services.chat_service_factory.ChatServiceFactory._create_agno_service', side_effect=Exception("Agno failed")):

            with pytest.raises(ConfigurationError) as exc_info:
                await ChatServiceFactory.create_chat_service(
                    settings=settings,
                    service_type=ChatServiceType.AGNO
                )

            assert "Failed to create Agno chat service" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_chat_service_explicit_custom(self):
        """Test explicit custom selection."""
        settings = MockSettings()
        memory_store = MockMemoryStore()
        llm_service = MockLLMService()

        with patch('app.services.chat_service_factory.ChatServiceFactory._create_custom_service') as mock_custom:
            mock_custom_service = MagicMock()
            mock_custom.return_value = mock_custom_service

            service = await ChatServiceFactory.create_chat_service(
                settings=settings,
                service_type=ChatServiceType.CUSTOM,
                memory_store=memory_store,
                llm_service=llm_service
            )

            assert service == mock_custom_service
            mock_custom.assert_called_once_with(settings, memory_store, llm_service)

    @pytest.mark.asyncio
    async def test_should_use_agno_when_enabled(self):
        """Test Agno is used when enabled in settings."""
        settings = MockSettings(enable_agno=True)

        with patch('app.services.chat_service_factory.ChatServiceFactory._is_agno_available', return_value=True):
            should_use = await ChatServiceFactory._should_use_agno(settings, ChatServiceType.AUTO)

            assert should_use is True

    @pytest.mark.asyncio
    async def test_should_use_agno_when_disabled(self):
        """Test Agno is not used when disabled in settings."""
        settings = MockSettings(enable_agno=False)

        should_use = await ChatServiceFactory._should_use_agno(settings, ChatServiceType.AUTO)

        assert should_use is False

    @pytest.mark.asyncio
    async def test_should_use_agno_explicit_type(self):
        """Test Agno is used when explicitly requested."""
        settings = MockSettings(enable_agno=False)  # Even when disabled

        with patch('app.services.chat_service_factory.ChatServiceFactory._is_agno_available', return_value=True):
            should_use = await ChatServiceFactory._should_use_agno(settings, ChatServiceType.AGNO)

            assert should_use is True

    @pytest.mark.asyncio
    async def test_is_agno_available_true(self):
        """Test Agno availability detection when available."""
        with patch.dict('sys.modules', {'agno': MagicMock()}):
            available = await ChatServiceFactory._is_agno_available()
            assert available is True

    @pytest.mark.asyncio
    async def test_is_agno_available_false(self):
        """Test Agno availability detection when not available."""
        with patch('builtins.__import__', side_effect=ImportError("No module named 'agno'")):
            available = await ChatServiceFactory._is_agno_available()
            assert available is False


class TestChatService:
    """Test custom ChatService implementation."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for ChatService."""
        memory_store = MockMemoryStore()
        llm_service = MockLLMService()
        settings = MockSettings()

        return {
            "memory_store": memory_store,
            "llm_service": llm_service,
            "settings": settings
        }

    def test_chat_service_initialization(self, mock_dependencies):
        """Test ChatService initializes properly."""
        service = ChatService(
            memory_store=mock_dependencies["memory_store"],
            llm_service=mock_dependencies["llm_service"],
            settings=mock_dependencies["settings"]
        )

        assert service.memory_store == mock_dependencies["memory_store"]
        assert service.llm_service == mock_dependencies["llm_service"]
        assert service.settings == mock_dependencies["settings"]

    @pytest.mark.asyncio
    async def test_process_message_success(self, mock_dependencies):
        """Test successful message processing."""
        service = ChatService(**mock_dependencies)

        message = "Hello, how are you?"
        session_id = "test-session"
        user_id = "test-user"

        with patch.object(service, '_get_conversation_context', return_value=[]), \
             patch.object(service, '_generate_response') as mock_generate, \
             patch.object(service, '_store_conversation'):

            mock_generate.return_value = {
                "content": "I'm doing well, thank you!",
                "role": "assistant"
            }

            response = await service.process_message(
                message=message,
                session_id=session_id,
                user_id=user_id
            )

            assert response["message"] == "I'm doing well, thank you!"
            assert response["session_id"] == session_id
            assert "response_time" in response

    @pytest.mark.asyncio
    async def test_process_message_with_context(self, mock_dependencies):
        """Test message processing with conversation context."""
        service = ChatService(**mock_dependencies)

        with patch.object(service, '_get_conversation_context') as mock_context, \
             patch.object(service, '_generate_response') as mock_generate, \
             patch.object(service, '_store_conversation'):

            # Mock conversation history
            mock_context.return_value = [
                {"role": "user", "content": "What's my name?"},
                {"role": "assistant", "content": "I don't know your name yet."}
            ]

            mock_generate.return_value = {
                "content": "You can tell me your name!",
                "role": "assistant"
            }

            response = await service.process_message(
                message="My name is Alice",
                session_id="test-session",
                user_id="test-user"
            )

            mock_context.assert_called_once()
            mock_generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_message_llm_failure(self, mock_dependencies):
        """Test message processing when LLM fails."""
        mock_dependencies["llm_service"] = MockLLMService(should_fail=True)
        service = ChatService(**mock_dependencies)

        with patch.object(service, '_get_conversation_context', return_value=[]):
            with pytest.raises(ExternalServiceError):
                await service.process_message(
                    message="Hello",
                    session_id="test-session",
                    user_id="test-user"
                )

    @pytest.mark.asyncio
    async def test_get_conversation_context(self, mock_dependencies):
        """Test conversation context retrieval."""
        service = ChatService(**mock_dependencies)

        # Store some conversation history
        session_id = "test-session"
        await service.memory_store.store(
            f"conversation:{session_id}",
            [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"}
            ]
        )

        context = await service._get_conversation_context(session_id, max_messages=10)

        assert len(context) == 2
        assert context[0]["content"] == "Hello"
        assert context[1]["content"] == "Hi there!"

    @pytest.mark.asyncio
    async def test_store_conversation(self, mock_dependencies):
        """Test conversation storage."""
        service = ChatService(**mock_dependencies)

        session_id = "test-session"
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]

        await service._store_conversation(session_id, messages)

        stored = await service.memory_store.retrieve(f"conversation:{session_id}")
        assert stored == messages

    @pytest.mark.asyncio
    async def test_generate_response_with_context(self, mock_dependencies):
        """Test response generation with context."""
        service = ChatService(**mock_dependencies)

        message = "What's the weather like?"
        context = [
            {"role": "user", "content": "I'm in New York"},
            {"role": "assistant", "content": "That's a great city!"}
        ]

        response = await service._generate_response(message, context)

        assert response["role"] == "assistant"
        assert response["content"] == "Mock response 1"

    @pytest.mark.asyncio
    async def test_health_check_success(self, mock_dependencies):
        """Test health check when service is healthy."""
        service = ChatService(**mock_dependencies)

        with patch.object(mock_dependencies["llm_service"], "generate_completion") as mock_llm:
            mock_llm.return_value = {"choices": [{"message": {"content": "OK"}}]}

            is_healthy = await service.health_check()

            assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, mock_dependencies):
        """Test health check when service is unhealthy."""
        mock_dependencies["llm_service"] = MockLLMService(should_fail=True)
        service = ChatService(**mock_dependencies)

        is_healthy = await service.health_check()

        assert is_healthy is False


class TestDatabaseChatService:
    """Test DatabaseChatService implementation."""

    @pytest.fixture
    def mock_repositories(self):
        """Create mock repositories for testing."""
        return {
            "session_repo": MagicMock(),
            "message_repo": MagicMock(),
            "user_repo": MagicMock()
        }

    @pytest.fixture
    def mock_llm_service(self):
        """Create mock LLM service."""
        return MockLLMService()

    def test_database_chat_service_initialization(self, mock_repositories, mock_llm_service):
        """Test DatabaseChatService initializes properly."""
        settings = MockSettings()

        service = DatabaseChatService(
            session_repository=mock_repositories["session_repo"],
            message_repository=mock_repositories["message_repo"],
            user_repository=mock_repositories["user_repo"],
            llm_service=mock_llm_service,
            settings=settings
        )

        assert service.session_repository == mock_repositories["session_repo"]
        assert service.message_repository == mock_repositories["message_repo"]
        assert service.llm_service == mock_llm_service

    @pytest.mark.asyncio
    async def test_process_message_new_session(self, mock_repositories, mock_llm_service):
        """Test processing message in new session."""
        service = DatabaseChatService(
            session_repository=mock_repositories["session_repo"],
            message_repository=mock_repositories["message_repo"],
            user_repository=mock_repositories["user_repo"],
            llm_service=mock_llm_service,
            settings=MockSettings()
        )

        # Mock repository responses
        mock_repositories["session_repo"].create.return_value = MagicMock(id="new-session-id")
        mock_repositories["message_repo"].create.return_value = MagicMock()
        mock_repositories["message_repo"].get_by_session_id.return_value = []

        response = await service.process_message(
            message="Hello",
            session_id=None,  # New session
            user_id="test-user"
        )

        assert "session_id" in response
        assert response["message"] == "Mock response 1"

        # Verify session and message creation
        mock_repositories["session_repo"].create.assert_called_once()
        assert mock_repositories["message_repo"].create.call_count == 2  # User message + assistant response

    @pytest.mark.asyncio
    async def test_process_message_existing_session(self, mock_repositories, mock_llm_service):
        """Test processing message in existing session."""
        service = DatabaseChatService(
            session_repository=mock_repositories["session_repo"],
            message_repository=mock_repositories["message_repo"],
            user_repository=mock_repositories["user_repo"],
            llm_service=mock_llm_service,
            settings=MockSettings()
        )

        session_id = "existing-session"

        # Mock existing session
        mock_session = MagicMock()
        mock_session.id = session_id
        mock_repositories["session_repo"].get_by_id.return_value = mock_session
        mock_repositories["message_repo"].get_by_session_id.return_value = [
            MagicMock(content="Previous message", role="user"),
            MagicMock(content="Previous response", role="assistant")
        ]
        mock_repositories["message_repo"].create.return_value = MagicMock()

        response = await service.process_message(
            message="Follow up question",
            session_id=session_id,
            user_id="test-user"
        )

        assert response["session_id"] == session_id
        mock_repositories["session_repo"].get_by_id.assert_called_once_with(session_id)

    @pytest.mark.asyncio
    async def test_list_sessions(self, mock_repositories, mock_llm_service):
        """Test listing user sessions."""
        service = DatabaseChatService(
            session_repository=mock_repositories["session_repo"],
            message_repository=mock_repositories["message_repo"],
            user_repository=mock_repositories["user_repo"],
            llm_service=mock_llm_service,
            settings=MockSettings()
        )

        user_id = "test-user"

        # Mock sessions
        mock_sessions = [
            MagicMock(id="session-1", title="Session 1", message_count=5),
            MagicMock(id="session-2", title="Session 2", message_count=3)
        ]
        mock_repositories["session_repo"].get_by_user_id.return_value = mock_sessions

        sessions = await service.list_sessions(user_id, limit=10, offset=0)

        assert len(sessions) == 2
        assert sessions[0].id == "session-1"
        assert sessions[1].id == "session-2"

        mock_repositories["session_repo"].get_by_user_id.assert_called_once_with(
            user_id, limit=10, offset=0
        )

    @pytest.mark.asyncio
    async def test_get_session(self, mock_repositories, mock_llm_service):
        """Test getting specific session with messages."""
        service = DatabaseChatService(
            session_repository=mock_repositories["session_repo"],
            message_repository=mock_repositories["message_repo"],
            user_repository=mock_repositories["user_repo"],
            llm_service=mock_llm_service,
            settings=MockSettings()
        )

        session_id = "test-session"

        # Mock session and messages
        mock_session = MagicMock(id=session_id, title="Test Session")
        mock_repositories["session_repo"].get_by_id.return_value = mock_session
        mock_repositories["message_repo"].get_by_session_id.return_value = [
            MagicMock(content="Hello", role="user"),
            MagicMock(content="Hi there!", role="assistant")
        ]

        session = await service.get_session(session_id, user_id="test-user")

        assert session.id == session_id
        mock_repositories["message_repo"].get_by_session_id.assert_called_once_with(session_id)

    @pytest.mark.asyncio
    async def test_delete_session(self, mock_repositories, mock_llm_service):
        """Test session deletion."""
        service = DatabaseChatService(
            session_repository=mock_repositories["session_repo"],
            message_repository=mock_repositories["message_repo"],
            user_repository=mock_repositories["user_repo"],
            llm_service=mock_llm_service,
            settings=MockSettings()
        )

        session_id = "test-session"

        mock_repositories["session_repo"].delete.return_value = True

        result = await service.delete_session(session_id, user_id="test-user")

        assert result is True
        mock_repositories["session_repo"].delete.assert_called_once_with(session_id)

    @pytest.mark.asyncio
    async def test_health_check(self, mock_repositories, mock_llm_service):
        """Test health check for database chat service."""
        service = DatabaseChatService(
            session_repository=mock_repositories["session_repo"],
            message_repository=mock_repositories["message_repo"],
            user_repository=mock_repositories["user_repo"],
            llm_service=mock_llm_service,
            settings=MockSettings()
        )

        # Mock successful database check
        mock_repositories["session_repo"].health_check.return_value = True

        is_healthy = await service.health_check()

        assert is_healthy is True
        mock_repositories["session_repo"].health_check.assert_called_once()


class TestChatServiceProtocol:
    """Test that services implement the ChatServiceProtocol correctly."""

    def test_chat_service_implements_protocol(self):
        """Test ChatService implements required protocol methods."""
        memory_store = MockMemoryStore()
        llm_service = MockLLMService()
        settings = MockSettings()

        service = ChatService(
            memory_store=memory_store,
            llm_service=llm_service,
            settings=settings
        )

        # Verify protocol methods exist
        assert hasattr(service, 'process_message')
        assert hasattr(service, 'list_sessions')
        assert hasattr(service, 'get_session')
        assert hasattr(service, 'delete_session')
        assert hasattr(service, 'health_check')

        # Verify methods are callable
        assert callable(getattr(service, 'process_message'))
        assert callable(getattr(service, 'health_check'))

    def test_database_chat_service_implements_protocol(self):
        """Test DatabaseChatService implements required protocol methods."""
        service = DatabaseChatService(
            session_repository=MagicMock(),
            message_repository=MagicMock(),
            user_repository=MagicMock(),
            llm_service=MockLLMService(),
            settings=MockSettings()
        )

        # Verify protocol methods exist
        assert hasattr(service, 'process_message')
        assert hasattr(service, 'list_sessions')
        assert hasattr(service, 'get_session')
        assert hasattr(service, 'delete_session')
        assert hasattr(service, 'health_check')


class TestChatServiceErrorHandling:
    """Test error handling in chat services."""

    @pytest.mark.asyncio
    async def test_chat_service_handles_memory_errors(self):
        """Test ChatService handles memory store errors gracefully."""
        memory_store = MagicMock()
        memory_store.retrieve.side_effect = Exception("Memory error")
        memory_store.store.side_effect = Exception("Memory error")

        service = ChatService(
            memory_store=memory_store,
            llm_service=MockLLMService(),
            settings=MockSettings()
        )

        # Should handle memory errors gracefully
        with pytest.raises(Exception):  # Should propagate or handle gracefully
            await service.process_message("Hello", "session", "user")

    @pytest.mark.asyncio
    async def test_database_service_handles_database_errors(self):
        """Test DatabaseChatService handles database errors gracefully."""
        session_repo = MagicMock()
        session_repo.create.side_effect = Exception("Database error")

        service = DatabaseChatService(
            session_repository=session_repo,
            message_repository=MagicMock(),
            user_repository=MagicMock(),
            llm_service=MockLLMService(),
            settings=MockSettings()
        )

        with pytest.raises(Exception):  # Should handle database errors
            await service.process_message("Hello", None, "user")

    @pytest.mark.asyncio
    async def test_chat_service_validates_input(self):
        """Test ChatService validates input parameters."""
        service = ChatService(
            memory_store=MockMemoryStore(),
            llm_service=MockLLMService(),
            settings=MockSettings()
        )

        # Test empty message
        with pytest.raises(ValidationError):
            await service.process_message("", "session", "user")

        # Test None message
        with pytest.raises(ValidationError):
            await service.process_message(None, "session", "user")

    @pytest.mark.asyncio
    async def test_service_factory_handles_configuration_errors(self):
        """Test factory handles configuration errors properly."""
        invalid_settings = MockSettings(openrouter_api_key=None)

        with patch('app.services.chat_service_factory.ChatServiceFactory._create_custom_service',
                   side_effect=ConfigurationError("Missing API key")):

            with pytest.raises(ConfigurationError):
                await ChatServiceFactory.create_chat_service(
                    settings=invalid_settings,
                    service_type=ChatServiceType.CUSTOM
                )
