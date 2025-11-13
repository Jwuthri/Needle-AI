"""
Tests for Conversational Context Manager integration.

Tests the context persistence and follow-up query handling.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.core.llm.workflow.context_manager import ConversationalContextManager
from app.models.workflow import ExecutionContext, Insight


class TestConversationalContextManager:
    """Test suite for ConversationalContextManager."""
    
    @pytest.fixture
    def mock_redis_client(self):
        """Create a mock Redis client."""
        redis_client = MagicMock()
        redis_client.get = AsyncMock(return_value=None)
        redis_client.set = AsyncMock(return_value=True)
        redis_client.connect = AsyncMock()
        return redis_client
    
    @pytest.fixture
    def context_manager(self, mock_redis_client):
        """Create a ConversationalContextManager with mock Redis."""
        return ConversationalContextManager(redis_client=mock_redis_client)
    
    @pytest.fixture
    def sample_insights(self):
        """Create sample insights for testing."""
        return [
            Insight(
                source_agent="sentiment",
                insight_text="Performance issues detected",
                severity_score=0.8,
                confidence_score=0.9,
                supporting_reviews=["rev_1", "rev_2"],
                metadata={"aspect": "performance"}
            ),
            Insight(
                source_agent="topic_modeling",
                insight_text="UI complaints are common",
                severity_score=0.7,
                confidence_score=0.85,
                supporting_reviews=["rev_3", "rev_4"],
                metadata={"topic_id": "topic_1"}
            )
        ]
    
    @pytest.mark.asyncio
    async def test_save_context_success(self, context_manager, mock_redis_client, sample_insights):
        """Test saving context successfully."""
        # Arrange
        session_id = "test_session_123"
        query = "What are the main product gaps?"
        agent_outputs = {"action_1": {"reviews": []}}
        metadata = {"steps": 5}
        
        # Act
        result = await context_manager.save_context(
            session_id=session_id,
            query=query,
            insights=sample_insights,
            agent_outputs=agent_outputs,
            metadata=metadata
        )
        
        # Assert
        assert result is True
        mock_redis_client.set.assert_called_once()
        
        # Verify the saved data structure
        call_args = mock_redis_client.set.call_args
        saved_key = call_args[0][0]
        saved_data = call_args[0][1]
        
        assert saved_key == f"conversation_context:{session_id}"
        assert "history" in saved_data
        assert len(saved_data["history"]) == 1
        assert saved_data["history"][0]["query"] == query
        assert len(saved_data["history"][0]["insights"]) == 2
    
    @pytest.mark.asyncio
    async def test_load_context_with_existing_data(self, context_manager, mock_redis_client):
        """Test loading existing context."""
        # Arrange
        session_id = "test_session_123"
        stored_context = {
            "session_id": session_id,
            "history": [
                {
                    "query": "Previous query",
                    "insights": [
                        {
                            "source_agent": "sentiment",
                            "insight_text": "Test insight",
                            "severity_score": 0.5,
                            "confidence_score": 0.8,
                            "supporting_reviews": [],
                            "metadata": {}
                        }
                    ],
                    "agent_outputs": {"action_1": {}},
                    "metadata": {},
                    "timestamp": datetime.utcnow().isoformat()
                }
            ],
            "last_updated": datetime.utcnow().isoformat()
        }
        
        mock_redis_client.get = AsyncMock(return_value=stored_context)
        
        # Act
        context = await context_manager.load_context(session_id)
        
        # Assert
        assert context is not None
        assert context.session_id == session_id
        assert len(context.conversation_history) == 1
        assert context.conversation_history[0]["query"] == "Previous query"
        assert len(context.cached_results) > 0
    
    @pytest.mark.asyncio
    async def test_load_context_no_data(self, context_manager, mock_redis_client):
        """Test loading context when no data exists."""
        # Arrange
        session_id = "new_session"
        mock_redis_client.get = AsyncMock(return_value=None)
        
        # Act
        context = await context_manager.load_context(session_id)
        
        # Assert
        assert context is None
    
    @pytest.mark.asyncio
    async def test_is_follow_up_query_with_keywords(self, context_manager):
        """Test follow-up detection with keywords."""
        # Arrange
        query = "Show me more about that"
        previous_context = ExecutionContext(
            user_id="user_1",
            session_id="session_1",
            message_id="msg_1",
            query="Previous query",
            conversation_history=[{"query": "Previous query"}]
        )
        
        # Act
        is_follow_up = await context_manager.is_follow_up_query(query, previous_context)
        
        # Assert
        assert is_follow_up is True
    
    @pytest.mark.asyncio
    async def test_is_follow_up_query_with_pronouns(self, context_manager):
        """Test follow-up detection with pronouns."""
        # Arrange
        query = "What about those reviews?"
        previous_context = ExecutionContext(
            user_id="user_1",
            session_id="session_1",
            message_id="msg_1",
            query="Previous query",
            conversation_history=[{"query": "Previous query"}]
        )
        
        # Act
        is_follow_up = await context_manager.is_follow_up_query(query, previous_context)
        
        # Assert
        assert is_follow_up is True
    
    @pytest.mark.asyncio
    async def test_is_follow_up_query_short_query(self, context_manager):
        """Test follow-up detection with short query."""
        # Arrange
        query = "What about positive?"
        previous_context = ExecutionContext(
            user_id="user_1",
            session_id="session_1",
            message_id="msg_1",
            query="Previous query",
            conversation_history=[{"query": "Previous query"}]
        )
        
        # Act
        is_follow_up = await context_manager.is_follow_up_query(query, previous_context)
        
        # Assert
        assert is_follow_up is True
    
    @pytest.mark.asyncio
    async def test_is_follow_up_query_new_query(self, context_manager):
        """Test that new independent queries are not detected as follow-ups."""
        # Arrange
        query = "What are the main product gaps in my Netflix reviews?"
        previous_context = ExecutionContext(
            user_id="user_1",
            session_id="session_1",
            message_id="msg_1",
            query="Previous query",
            conversation_history=[{"query": "Previous query"}]
        )
        
        # Act
        is_follow_up = await context_manager.is_follow_up_query(query, previous_context)
        
        # Assert
        assert is_follow_up is False
    
    @pytest.mark.asyncio
    async def test_is_follow_up_query_no_previous_context(self, context_manager):
        """Test that queries without previous context are not follow-ups."""
        # Arrange
        query = "Show me that"
        previous_context = None
        
        # Act
        is_follow_up = await context_manager.is_follow_up_query(query, previous_context)
        
        # Assert
        assert is_follow_up is False
    
    @pytest.mark.asyncio
    async def test_get_context_for_planning(self, context_manager, mock_redis_client):
        """Test getting context for planning."""
        # Arrange
        session_id = "test_session"
        current_query = "Compare that to last month"
        
        stored_context = {
            "session_id": session_id,
            "history": [
                {
                    "query": "What are product gaps?",
                    "insights": [
                        {
                            "source_agent": "topic_modeling",
                            "insight_text": "UI issues",
                            "severity_score": 0.8,
                            "confidence_score": 0.9,
                            "supporting_reviews": [],
                            "metadata": {}
                        }
                    ],
                    "agent_outputs": {},
                    "metadata": {},
                    "timestamp": datetime.utcnow().isoformat()
                }
            ]
        }
        
        mock_redis_client.get = AsyncMock(return_value=stored_context)
        
        # Act
        planning_context = await context_manager.get_context_for_planning(
            session_id=session_id,
            current_query=current_query
        )
        
        # Assert
        assert "previous_queries" in planning_context
        assert "available_insights" in planning_context
        assert "cached_data" in planning_context
        assert "suggested_shortcuts" in planning_context
        
        assert len(planning_context["previous_queries"]) == 1
        assert len(planning_context["available_insights"]) == 1
        assert "reuse_previous_data" in planning_context["suggested_shortcuts"]
    
    @pytest.mark.asyncio
    async def test_save_context_appends_to_history(self, context_manager, mock_redis_client, sample_insights):
        """Test that saving context appends to existing history."""
        # Arrange
        session_id = "test_session"
        
        # Existing context with one turn
        existing_context = {
            "session_id": session_id,
            "history": [
                {
                    "query": "First query",
                    "insights": [],
                    "agent_outputs": {},
                    "metadata": {},
                    "timestamp": datetime.utcnow().isoformat()
                }
            ],
            "last_updated": datetime.utcnow().isoformat()
        }
        
        mock_redis_client.get = AsyncMock(return_value=existing_context)
        
        # Act
        await context_manager.save_context(
            session_id=session_id,
            query="Second query",
            insights=sample_insights,
            agent_outputs={}
        )
        
        # Assert
        call_args = mock_redis_client.set.call_args
        saved_data = call_args[0][1]
        
        assert len(saved_data["history"]) == 2
        assert saved_data["history"][0]["query"] == "First query"
        assert saved_data["history"][1]["query"] == "Second query"
    
    @pytest.mark.asyncio
    async def test_save_context_limits_history_size(self, context_manager, mock_redis_client):
        """Test that history is limited to 10 turns."""
        # Arrange
        session_id = "test_session"
        
        # Create existing context with 10 turns
        existing_history = [
            {
                "query": f"Query {i}",
                "insights": [],
                "agent_outputs": {},
                "metadata": {},
                "timestamp": datetime.utcnow().isoformat()
            }
            for i in range(10)
        ]
        
        existing_context = {
            "session_id": session_id,
            "history": existing_history,
            "last_updated": datetime.utcnow().isoformat()
        }
        
        mock_redis_client.get = AsyncMock(return_value=existing_context)
        
        # Act
        await context_manager.save_context(
            session_id=session_id,
            query="New query",
            insights=[],
            agent_outputs={}
        )
        
        # Assert
        call_args = mock_redis_client.set.call_args
        saved_data = call_args[0][1]
        
        # Should still be 10 (oldest removed, new one added)
        assert len(saved_data["history"]) == 10
        assert saved_data["history"][-1]["query"] == "New query"
        assert saved_data["history"][0]["query"] == "Query 1"  # Query 0 was removed
