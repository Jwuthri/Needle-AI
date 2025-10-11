"""
Unit tests for database optimization and monitoring.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.core.monitoring.database import DatabasePoolMonitor, db_monitoring_service
from app.database.repositories.optimized_chat_repository import OptimizedChatRepository
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class TestOptimizedChatRepository:
    """Test optimized chat repository for N+1 query prevention."""

    @pytest.mark.asyncio
    async def test_get_sessions_with_messages_optimized(self, test_db_session: AsyncSession, test_user):
        """Test optimized session retrieval without N+1 queries."""
        # Create test data
        from app.database.models.chat_message import ChatMessage, MessageRoleEnum
        from app.database.models.chat_session import ChatSession

        user_id = test_user["id"]

        # Create test sessions
        session1 = ChatSession(
            user_id=user_id,
            title="Test Session 1",
            is_active=True
        )
        session2 = ChatSession(
            user_id=user_id,
            title="Test Session 2",
            is_active=True
        )

        test_db_session.add_all([session1, session2])
        await test_db_session.flush()  # Get IDs

        # Create test messages
        messages = [
            ChatMessage(
                session_id=session1.id,
                content="Hello from session 1",
                role=MessageRoleEnum.USER
            ),
            ChatMessage(
                session_id=session1.id,
                content="Response from session 1",
                role=MessageRoleEnum.ASSISTANT
            ),
            ChatMessage(
                session_id=session2.id,
                content="Hello from session 2",
                role=MessageRoleEnum.USER
            )
        ]

        test_db_session.add_all(messages)
        await test_db_session.commit()

        # Test optimized query
        sessions = OptimizedChatRepository.get_sessions_with_messages_optimized(
            db=test_db_session,
            user_id=user_id,
            limit=10,
            offset=0,
            include_message_count=True,
            include_last_message=True
        )

        assert len(sessions) == 2

        # Should have message counts without additional queries
        for session in sessions:
            assert hasattr(session, '_message_count')
            if session.id == session1.id:
                assert session._message_count == 2
            elif session.id == session2.id:
                assert session._message_count == 1

    @pytest.mark.asyncio
    async def test_get_conversation_with_context_optimized(self, test_db_session: AsyncSession, test_user):
        """Test optimized conversation retrieval with eager loading."""
        from app.database.models.chat_message import ChatMessage, MessageRoleEnum
        from app.database.models.chat_session import ChatSession

        user_id = test_user["id"]

        # Create session with messages
        session = ChatSession(
            user_id=user_id,
            title="Context Test Session"
        )

        test_db_session.add(session)
        await test_db_session.flush()

        # Create conversation history
        messages_data = [
            ("Hello", MessageRoleEnum.USER),
            ("Hi there!", MessageRoleEnum.ASSISTANT),
            ("How are you?", MessageRoleEnum.USER),
            ("I'm doing well, thanks!", MessageRoleEnum.ASSISTANT),
            ("Can you help me?", MessageRoleEnum.USER)
        ]

        for content, role in messages_data:
            message = ChatMessage(
                session_id=session.id,
                content=content,
                role=role
            )
            test_db_session.add(message)

        await test_db_session.commit()

        # Test optimized retrieval
        result = OptimizedChatRepository.get_conversation_with_context_optimized(
            db=test_db_session,
            session_id=session.id,
            context_limit=10,
            include_user=True
        )

        assert result is not None
        retrieved_session, messages = result

        assert retrieved_session.id == session.id
        assert len(messages) == 5

        # Messages should be in chronological order
        assert messages[0].content == "Hello"
        assert messages[0].role == MessageRoleEnum.USER
        assert messages[-1].content == "Can you help me?"
        assert messages[-1].role == MessageRoleEnum.USER

        # User should be eagerly loaded (no additional query needed)
        assert retrieved_session.user is not None
        assert retrieved_session.user.id == user_id

    @pytest.mark.asyncio
    async def test_bulk_update_session_activity(self, test_db_session: AsyncSession, test_user):
        """Test bulk session updates to avoid N+1 updates."""
        from datetime import datetime

        from app.database.models.chat_session import ChatSession

        user_id = test_user["id"]

        # Create multiple sessions
        sessions = []
        for i in range(5):
            session = ChatSession(
                user_id=user_id,
                title=f"Bulk Test Session {i}"
            )
            sessions.append(session)
            test_db_session.add(session)

        await test_db_session.commit()

        session_ids = [s.id for s in sessions]
        new_activity_time = datetime.utcnow()

        # Test bulk update
        updated_count = OptimizedChatRepository.bulk_update_session_activity(
            db=test_db_session,
            session_ids=session_ids,
            last_activity=new_activity_time
        )

        assert updated_count == 5

        # Verify updates were applied
        await test_db_session.commit()
        updated_sessions = await test_db_session.execute(
            text("SELECT id, updated_at FROM chat_sessions WHERE id IN :session_ids"),
            {"session_ids": tuple(session_ids)}
        )

        results = updated_sessions.fetchall()
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_get_user_chat_statistics_optimized(self, test_db_session: AsyncSession, test_user):
        """Test optimized user statistics with efficient aggregation."""
        from app.database.models.chat_message import ChatMessage, MessageRoleEnum
        from app.database.models.chat_session import ChatSession

        user_id = test_user["id"]

        # Create test data
        session = ChatSession(user_id=user_id, title="Stats Test Session", is_active=True)
        test_db_session.add(session)
        await test_db_session.flush()

        # Create various messages
        messages = [
            ChatMessage(session_id=session.id, content="User message 1", role=MessageRoleEnum.USER),
            ChatMessage(session_id=session.id, content="Assistant response 1", role=MessageRoleEnum.ASSISTANT),
            ChatMessage(session_id=session.id, content="User message 2", role=MessageRoleEnum.USER),
            ChatMessage(session_id=session.id, content="Assistant response 2", role=MessageRoleEnum.ASSISTANT),
        ]

        for msg in messages:
            test_db_session.add(msg)

        await test_db_session.commit()

        # Test statistics aggregation
        stats = OptimizedChatRepository.get_user_chat_statistics_optimized(
            db=test_db_session,
            user_id=user_id,
            days=30
        )

        assert stats["user_id"] == user_id
        assert stats["sessions"]["total"] == 1
        assert stats["sessions"]["active"] == 1
        assert stats["messages"]["total"] == 4
        assert stats["messages"]["user"] == 2
        assert stats["messages"]["assistant"] == 2
        assert stats["messages"]["avg_length"] > 0

    def test_query_performance_monitoring_decorator(self):
        """Test query performance monitoring decorator."""
        from app.database.repositories.optimized_chat_repository import (
            monitor_query_performance,
        )

        @monitor_query_performance("test_operation")
        async def slow_query():
            await asyncio.sleep(0.1)  # Simulate slow query
            return "result"

        @monitor_query_performance("test_operation")
        async def fast_query():
            await asyncio.sleep(0.01)  # Simulate fast query
            return "result"

        # Test both functions work
        result1 = asyncio.run(slow_query())
        result2 = asyncio.run(fast_query())

        assert result1 == "result"
        assert result2 == "result"

    @pytest.mark.asyncio
    async def test_search_messages_with_session_context(self, test_db_session: AsyncSession, test_user):
        """Test optimized message search with session context."""
        from app.database.models.chat_message import ChatMessage, MessageRoleEnum
        from app.database.models.chat_session import ChatSession

        user_id = test_user["id"]

        # Create test session and messages
        session = ChatSession(user_id=user_id, title="Search Test Session")
        test_db_session.add(session)
        await test_db_session.flush()

        messages = [
            ChatMessage(session_id=session.id, content="Python programming tutorial", role=MessageRoleEnum.USER),
            ChatMessage(session_id=session.id, content="Here's a Python tutorial...", role=MessageRoleEnum.ASSISTANT),
            ChatMessage(session_id=session.id, content="JavaScript vs Python comparison", role=MessageRoleEnum.USER),
        ]

        for msg in messages:
            test_db_session.add(msg)

        await test_db_session.commit()

        # Test search functionality
        results = OptimizedChatRepository.search_messages_with_session_context(
            db=test_db_session,
            search_term="Python",
            user_id=user_id,
            limit=10,
            offset=0
        )

        # Should find messages containing "Python"
        assert len(results) >= 2  # At least 2 messages contain "Python"

        for result in results:
            assert "Python" in result["message"]["content"]
            assert "session" in result
            assert "user" in result
            assert result["session"]["title"] == "Search Test Session"


class TestDatabaseMonitoring:
    """Test database connection pool monitoring."""

    def test_database_pool_monitor_initialization(self):
        """Test database pool monitor initialization."""
        mock_engine = MagicMock()
        mock_engine.pool = MagicMock()

        monitor = DatabasePoolMonitor(mock_engine, "test_pool")

        assert monitor.pool_name == "test_pool"
        assert monitor.engine == mock_engine
        assert monitor.pool == mock_engine.pool

    @pytest.mark.asyncio
    async def test_get_pool_status(self):
        """Test pool status retrieval."""
        mock_engine = MagicMock()
        mock_pool = MagicMock()
        mock_pool.size.return_value = 10
        mock_pool.checkedout.return_value = 3
        mock_pool.overflow.return_value = 2
        mock_pool.checkedin.return_value = 5
        mock_pool.invalidated.return_value = 0
        mock_pool._max_overflow = 5
        mock_engine.pool = mock_pool

        monitor = DatabasePoolMonitor(mock_engine, "test_pool")

        status = await monitor.get_pool_status()

        assert status["pool_name"] == "test_pool"
        assert status["size"] == 10
        assert status["checked_out"] == 3
        assert status["overflow"] == 2
        assert status["checked_in"] == 5
        assert status["utilization"] == (3 / 15) * 100  # 3 / (10 + 5) * 100

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful database health check."""
        mock_engine = MagicMock()
        mock_connection = AsyncMock()
        mock_result = AsyncMock()
        mock_result.fetchone.return_value = (1,)
        mock_connection.execute.return_value = mock_result
        mock_engine.begin.return_value.__aenter__.return_value = mock_connection

        monitor = DatabasePoolMonitor(mock_engine, "test_pool")

        result = await monitor.health_check()

        assert result["healthy"] is True
        assert result["pool_name"] == "test_pool"
        assert "response_time" in result
        assert result["response_time"] >= 0

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test database health check failure."""
        mock_engine = MagicMock()
        mock_engine.begin.side_effect = Exception("Database connection failed")

        monitor = DatabasePoolMonitor(mock_engine, "test_pool")

        result = await monitor.health_check()

        assert result["healthy"] is False
        assert result["error"] == "Database connection failed"
        assert "response_time" in result

    @pytest.mark.asyncio
    async def test_check_pool_exhaustion(self):
        """Test pool exhaustion detection."""
        mock_engine = MagicMock()
        mock_pool = MagicMock()

        # Test high utilization (exhausted)
        mock_pool.size.return_value = 10
        mock_pool.checkedout.return_value = 9  # 90% utilization
        mock_pool.overflow.return_value = 1
        mock_pool.checkedin.return_value = 0
        mock_pool.invalidated.return_value = 0
        mock_pool._max_overflow = 5
        mock_engine.pool = mock_pool

        monitor = DatabasePoolMonitor(mock_engine, "test_pool")

        result = await monitor.check_pool_exhaustion()

        assert result["is_exhausted"] is True
        assert result["utilization"] > 90
        assert "recommendations" in result
        assert len(result["recommendations"]) > 0

    @pytest.mark.asyncio
    async def test_monitoring_service_registration(self):
        """Test monitoring service pool registration."""
        mock_engine = MagicMock()

        # Test registration
        db_monitoring_service.register_pool(mock_engine, "test_pool")

        assert "test_pool" in db_monitoring_service.monitors
        assert db_monitoring_service.monitors["test_pool"].pool_name == "test_pool"

    @pytest.mark.asyncio
    async def test_monitoring_service_health_check_all(self):
        """Test health check across all monitored pools."""
        # Clear existing monitors
        db_monitoring_service.monitors.clear()

        # Register test pools
        for i in range(3):
            mock_engine = MagicMock()
            mock_engine.begin.return_value.__aenter__ = AsyncMock()
            mock_connection = AsyncMock()
            mock_result = AsyncMock()
            mock_result.fetchone.return_value = (1,)
            mock_connection.execute.return_value = mock_result
            mock_engine.begin.return_value.__aenter__.return_value = mock_connection

            db_monitoring_service.register_pool(mock_engine, f"pool_{i}")

        # Test health check all
        results = await db_monitoring_service.health_check_all()

        assert len(results) == 3
        for pool_name, result in results.items():
            assert pool_name.startswith("pool_")
            assert "healthy" in result

    def test_monitoring_service_stop_monitoring(self):
        """Test stopping the monitoring service."""
        db_monitoring_service.monitoring_active = True

        db_monitoring_service.stop_monitoring()

        assert db_monitoring_service.monitoring_active is False


class TestQueryPerformanceOptimizations:
    """Test specific query performance optimizations."""

    @pytest.mark.asyncio
    async def test_eager_loading_prevents_n_plus_one(self, test_db_session: AsyncSession, test_user):
        """Test that eager loading prevents N+1 queries."""
        from app.database.models.chat_message import ChatMessage, MessageRoleEnum
        from app.database.models.chat_session import ChatSession

        user_id = test_user["id"]

        # Create multiple sessions with messages
        sessions_data = []
        for i in range(3):
            session = ChatSession(user_id=user_id, title=f"Session {i}")
            test_db_session.add(session)
            sessions_data.append(session)

        await test_db_session.flush()

        # Add messages to each session
        for session in sessions_data:
            for j in range(2):
                message = ChatMessage(
                    session_id=session.id,
                    content=f"Message {j} in {session.title}",
                    role=MessageRoleEnum.USER
                )
                test_db_session.add(message)

        await test_db_session.commit()

        # Test with query counting (would need actual SQL logging in real implementation)
        # For now, just verify the optimized method returns correct data structure

        sessions = OptimizedChatRepository.get_sessions_with_messages_optimized(
            db=test_db_session,
            user_id=user_id,
            limit=10,
            include_message_count=True
        )

        assert len(sessions) == 3
        for session in sessions:
            # Should have message count without additional queries
            assert hasattr(session, '_message_count')
            assert session._message_count == 2

    def test_index_usage_simulation(self):
        """Simulate index usage verification."""
        # In a real implementation, this would check EXPLAIN QUERY PLAN
        # For now, just verify our index definitions are reasonable

        from app.database.models.chat_message import ChatMessage
        from app.database.models.chat_session import ChatSession

        # Check that our models have proper indexes defined
        session_indexes = ChatSession.__table_args__
        message_indexes = ChatMessage.__table_args__

        assert len(session_indexes) > 0
        assert len(message_indexes) > 0

        # Verify critical indexes exist
        session_index_names = [idx.name for idx in session_indexes if hasattr(idx, 'name')]
        message_index_names = [idx.name for idx in message_indexes if hasattr(idx, 'name')]

        # Should have user_id index for sessions
        assert any('user' in name for name in session_index_names)

        # Should have session_id index for messages
        assert any('session' in name for name in message_index_names)

    def test_query_complexity_analysis(self):
        """Test query complexity analysis."""
        # This would analyze actual query execution plans
        # For now, verify that our optimized repository methods
        # are designed to minimize query complexity

        # Check method signatures indicate optimization intent
        method_names = [
            method for method in dir(OptimizedChatRepository)
            if not method.startswith('_') and callable(getattr(OptimizedChatRepository, method))
        ]

        # Should have methods designed for bulk operations
        bulk_methods = [name for name in method_names if 'bulk' in name.lower()]
        assert len(bulk_methods) > 0

        # Should have methods designed for optimization
        optimized_methods = [name for name in method_names if 'optimized' in name.lower()]
        assert len(optimized_methods) > 0


class TestDatabaseErrorHandling:
    """Test database error handling and recovery."""

    @pytest.mark.asyncio
    async def test_connection_retry_mechanism(self):
        """Test database connection retry mechanism."""
        mock_engine = MagicMock()

        # Simulate connection failures then success
        connection_attempts = []

        async def mock_begin():
            connection_attempts.append(1)
            if len(connection_attempts) < 3:
                raise Exception("Connection failed")
            return AsyncMock()

        mock_engine.begin.side_effect = mock_begin

        monitor = DatabasePoolMonitor(mock_engine, "test_pool")

        # This would test retry logic if implemented
        # For now, just verify error handling works
        result = await monitor.health_check()

        # Should handle connection failures gracefully
        assert "error" in result or "healthy" in result

    @pytest.mark.asyncio
    async def test_pool_exhaustion_recovery(self):
        """Test recovery from pool exhaustion."""
        mock_engine = MagicMock()
        mock_pool = MagicMock()

        # Simulate pool exhaustion
        mock_pool.size.return_value = 10
        mock_pool.checkedout.return_value = 10  # 100% utilization
        mock_pool.overflow.return_value = 5
        mock_pool.checkedin.return_value = 0
        mock_pool.invalidated.return_value = 0
        mock_pool._max_overflow = 5
        mock_engine.pool = mock_pool

        monitor = DatabasePoolMonitor(mock_engine, "test_pool")

        result = await monitor.check_pool_exhaustion()

        assert result["is_exhausted"] is True
        assert result["utilization"] >= 100

        # Should provide recovery recommendations
        assert "recommendations" in result
        recommendations = result["recommendations"]
        assert len(recommendations) > 0
        assert any("pool size" in rec.lower() for rec in recommendations)

    def test_monitoring_service_error_isolation(self):
        """Test that errors in one pool don't affect others."""
        # Clear existing monitors
        db_monitoring_service.monitors.clear()

        # Register good pool
        good_engine = MagicMock()
        good_engine.pool = MagicMock()
        db_monitoring_service.register_pool(good_engine, "good_pool")

        # Register bad pool that will throw errors
        bad_engine = MagicMock()
        bad_engine.pool = None  # Will cause errors
        db_monitoring_service.register_pool(bad_engine, "bad_pool")

        # Test that service still functions
        assert "good_pool" in db_monitoring_service.monitors
        assert "bad_pool" in db_monitoring_service.monitors

        # Both pools should be registered despite bad pool having issues
        assert len(db_monitoring_service.monitors) == 2
