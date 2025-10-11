"""
Unit tests for database repositories.
"""

from datetime import datetime, timedelta

import pytest
from app.database.models import MessageRoleEnum, UserStatusEnum
from app.database.repositories import (
    ChatMessageRepository,
    ChatSessionRepository,
    UserRepository,
)


@pytest.mark.asyncio
class TestUserRepository:
    """Test UserRepository class."""

    async def test_create_user(self, test_db_session):
        """Test user creation."""
        repo = UserRepository()

        user = repo.create(
            db=test_db_session,
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password",
            full_name="Test User"
        )

        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.is_active is True
        assert user.is_superuser is False
        assert user.status == UserStatusEnum.ACTIVE
        assert isinstance(user.created_at, datetime)

    async def test_get_user_by_id(self, test_db_session):
        """Test getting user by ID."""
        repo = UserRepository()

        # Create user
        user = repo.create(
            db=test_db_session,
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password"
        )
        await test_db_session.commit()

        # Get user by ID
        found_user = repo.get_by_id(test_db_session, user.id)
        assert found_user is not None
        assert found_user.id == user.id
        assert found_user.username == "testuser"

    async def test_get_user_by_username(self, test_db_session):
        """Test getting user by username."""
        repo = UserRepository()

        # Create user
        user = repo.create(
            db=test_db_session,
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password"
        )
        await test_db_session.commit()

        # Get user by username
        found_user = repo.get_by_username(test_db_session, "testuser")
        assert found_user is not None
        assert found_user.username == "testuser"
        assert found_user.id == user.id

    async def test_get_user_by_email(self, test_db_session):
        """Test getting user by email."""
        repo = UserRepository()

        # Create user
        user = repo.create(
            db=test_db_session,
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password"
        )
        await test_db_session.commit()

        # Get user by email
        found_user = repo.get_by_email(test_db_session, "test@example.com")
        assert found_user is not None
        assert found_user.email == "test@example.com"
        assert found_user.id == user.id

    async def test_update_user(self, test_db_session):
        """Test user update."""
        repo = UserRepository()

        # Create user
        user = repo.create(
            db=test_db_session,
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password"
        )
        await test_db_session.commit()

        # Update user
        updated_user = repo.update(
            db=test_db_session,
            user_id=user.id,
            full_name="Updated Name",
            preferences={"theme": "dark"}
        )

        assert updated_user.full_name == "Updated Name"
        assert updated_user.preferences == {"theme": "dark"}
        assert updated_user.updated_at is not None

    async def test_deactivate_user(self, test_db_session):
        """Test user deactivation."""
        repo = UserRepository()

        # Create user
        user = repo.create(
            db=test_db_session,
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password"
        )
        await test_db_session.commit()

        # Deactivate user
        success = repo.deactivate(test_db_session, user.id)
        assert success is True

        # Verify user is deactivated
        updated_user = repo.get_by_id(test_db_session, user.id)
        assert updated_user.is_active is False
        assert updated_user.status == UserStatusEnum.INACTIVE

    async def test_list_users(self, test_db_session):
        """Test listing users with pagination."""
        repo = UserRepository()

        # Create multiple users
        for i in range(5):
            repo.create(
                db=test_db_session,
                username=f"user{i}",
                email=f"user{i}@example.com",
                password_hash="hashed_password"
            )
        await test_db_session.commit()

        # List users with pagination
        users = repo.list_users(test_db_session, limit=3, offset=0)
        assert len(users) == 3

        # List next page
        users_page2 = repo.list_users(test_db_session, limit=3, offset=3)
        assert len(users_page2) == 2

    async def test_user_usage_tracking(self, test_db_session):
        """Test user usage tracking."""
        repo = UserRepository()

        # Create user
        user = repo.create(
            db=test_db_session,
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password"
        )
        await test_db_session.commit()

        # Increment usage
        repo.increment_usage(test_db_session, user.id, requests=5, tokens=1000)

        # Check usage
        updated_user = repo.get_by_id(test_db_session, user.id)
        assert updated_user.total_requests == 5
        assert updated_user.total_tokens == 1000


@pytest.mark.asyncio
class TestChatSessionRepository:
    """Test ChatSessionRepository class."""

    async def test_create_session(self, test_db_session, test_user):
        """Test chat session creation."""
        repo = ChatSessionRepository()

        session = repo.create(
            db=test_db_session,
            user_id=test_user["id"],
            title="Test Session",
            system_prompt="You are a helpful assistant.",
            model_name="gpt-4o-mini"
        )

        assert session.user_id == test_user["id"]
        assert session.title == "Test Session"
        assert session.system_prompt == "You are a helpful assistant."
        assert session.model_name == "gpt-4o-mini"
        assert session.is_active is True
        assert isinstance(session.created_at, datetime)

    async def test_get_session_by_id(self, test_db_session, test_user):
        """Test getting session by ID."""
        repo = ChatSessionRepository()

        # Create session
        session = repo.create(
            db=test_db_session,
            user_id=test_user["id"],
            title="Test Session",
            model_name="gpt-4o-mini"
        )
        await test_db_session.commit()

        # Get session by ID
        found_session = repo.get_by_id(test_db_session, session.id)
        assert found_session is not None
        assert found_session.id == session.id
        assert found_session.title == "Test Session"

    async def test_get_user_sessions(self, test_db_session, test_user):
        """Test getting user sessions."""
        repo = ChatSessionRepository()

        # Create multiple sessions for user
        for i in range(3):
            repo.create(
                db=test_db_session,
                user_id=test_user["id"],
                title=f"Session {i}",
                model_name="gpt-4o-mini"
            )
        await test_db_session.commit()

        # Get user sessions
        sessions = repo.get_user_sessions(test_db_session, test_user["id"])
        assert len(sessions) == 3

        # Verify all sessions belong to user
        for session in sessions:
            assert session.user_id == test_user["id"]

    async def test_update_session(self, test_db_session, test_user):
        """Test session update."""
        repo = ChatSessionRepository()

        # Create session
        session = repo.create(
            db=test_db_session,
            user_id=test_user["id"],
            title="Original Title",
            model_name="gpt-4o-mini"
        )
        await test_db_session.commit()

        # Update session
        updated_session = repo.update(
            db=test_db_session,
            session_id=session.id,
            title="Updated Title",
            settings={"temperature": 0.8}
        )

        assert updated_session.title == "Updated Title"
        assert updated_session.settings == {"temperature": 0.8}
        assert updated_session.updated_at is not None

    async def test_deactivate_session(self, test_db_session, test_user):
        """Test session deactivation."""
        repo = ChatSessionRepository()

        # Create session
        session = repo.create(
            db=test_db_session,
            user_id=test_user["id"],
            title="Test Session",
            model_name="gpt-4o-mini"
        )
        await test_db_session.commit()

        # Deactivate session
        success = repo.deactivate(test_db_session, session.id)
        assert success is True

        # Verify session is deactivated
        updated_session = repo.get_by_id(test_db_session, session.id)
        assert updated_session.is_active is False

    async def test_cleanup_old_sessions(self, test_db_session, test_user):
        """Test cleanup of old sessions."""
        repo = ChatSessionRepository()

        # Create old session (mock old timestamp)
        old_session = repo.create(
            db=test_db_session,
            user_id=test_user["id"],
            title="Old Session",
            model_name="gpt-4o-mini"
        )
        # Manually set old timestamp
        old_date = datetime.utcnow() - timedelta(days=35)
        old_session.created_at = old_date
        old_session.last_message_at = old_date

        # Create recent session
        recent_session = repo.create(
            db=test_db_session,
            user_id=test_user["id"],
            title="Recent Session",
            model_name="gpt-4o-mini"
        )

        await test_db_session.commit()

        # Cleanup sessions older than 30 days
        deleted_count = repo.cleanup_old_sessions(test_db_session, days_old=30)
        assert deleted_count == 1

        # Verify old session is deactivated
        old_session_updated = repo.get_by_id(test_db_session, old_session.id)
        assert old_session_updated.is_active is False

        # Verify recent session is still active
        recent_session_updated = repo.get_by_id(test_db_session, recent_session.id)
        assert recent_session_updated.is_active is True


@pytest.mark.asyncio
class TestChatMessageRepository:
    """Test ChatMessageRepository class."""

    async def test_create_message(self, test_db_session, test_user):
        """Test chat message creation."""
        # First create a session
        session_repo = ChatSessionRepository()
        session = session_repo.create(
            db=test_db_session,
            user_id=test_user["id"],
            title="Test Session",
            model_name="gpt-4o-mini"
        )
        await test_db_session.commit()

        # Create message
        message_repo = ChatMessageRepository()
        message = message_repo.create(
            db=test_db_session,
            session_id=session.id,
            content="Hello, how are you?",
            role=MessageRoleEnum.USER
        )

        assert message.session_id == session.id
        assert message.content == "Hello, how are you?"
        assert message.role == MessageRoleEnum.USER
        assert isinstance(message.created_at, datetime)

    async def test_get_session_messages(self, test_db_session, test_user):
        """Test getting messages for a session."""
        # Create session
        session_repo = ChatSessionRepository()
        session = session_repo.create(
            db=test_db_session,
            user_id=test_user["id"],
            title="Test Session",
            model_name="gpt-4o-mini"
        )
        await test_db_session.commit()

        # Create multiple messages
        message_repo = ChatMessageRepository()
        for i, role in enumerate([MessageRoleEnum.USER, MessageRoleEnum.ASSISTANT]):
            message_repo.create(
                db=test_db_session,
                session_id=session.id,
                content=f"Message {i}",
                role=role
            )
        await test_db_session.commit()

        # Get session messages
        messages = message_repo.get_session_messages(test_db_session, session.id)
        assert len(messages) == 2

        # Verify message order (should be chronological)
        assert messages[0].content == "Message 0"
        assert messages[1].content == "Message 1"

    async def test_get_recent_messages(self, test_db_session, test_user):
        """Test getting recent messages with limit."""
        # Create session
        session_repo = ChatSessionRepository()
        session = session_repo.create(
            db=test_db_session,
            user_id=test_user["id"],
            title="Test Session",
            model_name="gpt-4o-mini"
        )
        await test_db_session.commit()

        # Create multiple messages
        message_repo = ChatMessageRepository()
        for i in range(5):
            message_repo.create(
                db=test_db_session,
                session_id=session.id,
                content=f"Message {i}",
                role=MessageRoleEnum.USER if i % 2 == 0 else MessageRoleEnum.ASSISTANT
            )
        await test_db_session.commit()

        # Get recent messages (limited)
        recent_messages = message_repo.get_recent_messages(
            test_db_session,
            session.id,
            limit=3
        )
        assert len(recent_messages) == 3

        # Should be most recent first
        assert recent_messages[0].content == "Message 4"
        assert recent_messages[1].content == "Message 3"
        assert recent_messages[2].content == "Message 2"

    async def test_count_session_messages(self, test_db_session, test_user):
        """Test counting messages in a session."""
        # Create session
        session_repo = ChatSessionRepository()
        session = session_repo.create(
            db=test_db_session,
            user_id=test_user["id"],
            title="Test Session",
            model_name="gpt-4o-mini"
        )
        await test_db_session.commit()

        # Create messages
        message_repo = ChatMessageRepository()
        for i in range(7):
            message_repo.create(
                db=test_db_session,
                session_id=session.id,
                content=f"Message {i}",
                role=MessageRoleEnum.USER if i % 2 == 0 else MessageRoleEnum.ASSISTANT
            )
        await test_db_session.commit()

        # Count messages
        count = message_repo.count_session_messages(test_db_session, session.id)
        assert count == 7

    async def test_message_with_metadata(self, test_db_session, test_user):
        """Test creating message with metadata."""
        # Create session
        session_repo = ChatSessionRepository()
        session = session_repo.create(
            db=test_db_session,
            user_id=test_user["id"],
            title="Test Session",
            model_name="gpt-4o-mini"
        )
        await test_db_session.commit()

        # Create message with metadata
        message_repo = ChatMessageRepository()
        metadata = {
            "model_used": "gpt-4o-mini",
            "temperature": 0.7,
            "processing_time": 1.5
        }

        message = message_repo.create(
            db=test_db_session,
            session_id=session.id,
            content="AI response",
            role=MessageRoleEnum.ASSISTANT,
            model_name="gpt-4o-mini",
            token_count=50,
            processing_time_ms=1500,
            metadata=metadata
        )

        assert message.model_name == "gpt-4o-mini"
        assert message.token_count == 50
        assert message.processing_time_ms == 1500
        assert message.extra_metadata == metadata
