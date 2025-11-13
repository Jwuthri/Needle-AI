"""
Unit tests for the ConversationalContextManager.

Tests the conversational context management functionality including:
- Saving context to Redis
- Loading context from Redis
- Follow-up query detection
- Context-aware planning
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.core.llm.workflow.context_manager import ConversationalContextManager
from app.models.workflow import ExecutionContext, Insight
from app.services.redis_client import RedisClient


@pytest.fixture
def mock_redis_client():
    """Create a mock Redis client."""
    client = AsyncMock(spec=RedisClient)
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock(return_value=True)
    return client


@pytest.fixture
def context_manager(mock_redis_client):
    """Create a test context manager."""
    return ConversationalContextManager(redis_client=mock_redis_client)


@pytest.fixture
def sample_insights():
    """Create sample insights for testing."""
    return [
        Insight(
            source_agent="sentiment",
            insight_text="Performance aspect has 78% negative sentiment",
            severity_score=0.78,
            confidence_score=0.92,
            supporting_reviews=["rev_123", "rev_456"],
            visualization_hint="bar_chart",
            visualization_data={
                "x": ["Performance", "Features"],
                "y": [0.78, 0.45],
                "chart_type": "bar"
            },
            metadata={"aspect": "performance"}
        ),
        Insight(
            source_agent="topic_modeling",
            insight_text="UI Slowness is the most frequent complaint",
            severity_score=0.85,
            confidence_score=0.90,
            supporting_reviews=["rev_101", "rev_102"],
            visualization_hint="bar_chart",
            visualization_data={
                "x": ["UI Slowness", "App Crashes"],
                "y": [18, 12],
                "chart_type": "bar"
            },
            metadata={"topic_id": "topic_1"}
        )
    ]


@pytest.fixture
def sample_agent_outputs():
    """Create sample agent outputs for testing."""
    return {
        "step1": {"reviews": [{"id": "rev_1", "text": "Great app"}]},
        "step2": {"sentiment": "positive", "score": 0.85}
    }


class TestSaveContext:
    """Tests for the save_context method."""
    
    @pytest.mark.asyncio
    async def test_save_context_new_session(
        self,
        context_manager,
        mock_redis_client,
        sample_insights,
        sample_agent_outputs
    ):
        """Test saving context for a new session."""
        # Mock Redis to return None (no existing context)
        mock_redis_client.get.return_value = None
        
        result = await context_manager.save_context(
            session_id="test_session",
            query="What are my main product gaps?",
            insights=sample_insights,
            agent_outputs=sample_agent_outputs,
            metadata={"execution_time": 1500}
        )
        
        assert result is True
        
        # Verify Redis set was called
        mock_redis_client.set.assert_called_once()
        call_args = mock_redis_client.set.call_args
        
        # Check the key
        assert call_args[0][0] == "conversation_context:test_session"
        
        # Check the data structure
        saved_data = call_args[0][1]
        assert "session_id" in saved_data
        assert "history" in saved_data
        assert len(saved_data["history"]) == 1
        
        # Check the first history entry
        first_entry = saved_data["history"][0]
        assert first_entry["query"] == "What are my main product gaps?"
        assert len(first_entry["insights"]) == 2
        assert first_entry["agent_outputs"] == sample_agent_outputs
        assert first_entry["metadata"]["execution_time"] == 1500
    
    @pytest.mark.asyncio
    async def test_save_context_existing_session(
        self,
        context_manager,
        mock_redis_client,
        sample_insights,
        sample_agent_outputs
    ):
        """Test saving context for an existing session."""
        # Mock Redis to return existing context
        existing_context = {
            "session_id": "test_session",
            "history": [
                {
                    "query": "Previous query",
                    "insights": [],
                    "agent_outputs": {},
                    "metadata": {},
                    "timestamp": "2025-01-01T00:00:00"
                }
            ],
            "last_updated": "2025-01-01T00:00:00"
        }
        mock_redis_client.get.return_value = existing_context
        
        result = await context_manager.save_context(
            session_id="test_session",
            query="Follow-up query",
            insights=sample_insights,
            agent_outputs=sample_agent_outputs
        )
        
        assert result is True
        
        # Verify the history was appended
        call_args = mock_redis_client.set.call_args
        saved_data = call_args[0][1]
        assert len(saved_data["history"]) == 2
        assert saved_data["history"][0]["query"] == "Previous query"
        assert saved_data["history"][1]["query"] == "Follow-up query"
    
    @pytest.mark.asyncio
    async def test_save_context_limits_history(
        self,
        context_manager,
        mock_redis_client,
        sample_insights,
        sample_agent_outputs
    ):
        """Test that history is limited to 10 turns."""
        # Create existing context with 10 entries
        existing_history = [
            {
                "query": f"Query {i}",
                "insights": [],
                "agent_outputs": {},
                "metadata": {},
                "timestamp": "2025-01-01T00:00:00"
            }
            for i in range(10)
        ]
        existing_context = {
            "session_id": "test_session",
            "history": existing_history,
            "last_updated": "2025-01-01T00:00:00"
        }
        mock_redis_client.get.return_value = existing_context
        
        result = await context_manager.save_context(
            session_id="test_session",
            query="New query",
            insights=sample_insights,
            agent_outputs=sample_agent_outputs
        )
        
        assert result is True
        
        # Verify history is still 10 entries (oldest removed)
        call_args = mock_redis_client.set.call_args
        saved_data = call_args[0][1]
        assert len(saved_data["history"]) == 10
        assert saved_data["history"][0]["query"] == "Query 1"  # Query 0 removed
        assert saved_data["history"][-1]["query"] == "New query"
    
    @pytest.mark.asyncio
    async def test_save_context_handles_errors(
        self,
        context_manager,
        mock_redis_client,
        sample_insights,
        sample_agent_outputs
    ):
        """Test that errors are handled gracefully."""
        # Mock Redis to raise an exception
        mock_redis_client.get.side_effect = Exception("Redis error")
        
        result = await context_manager.save_context(
            session_id="test_session",
            query="Test query",
            insights=sample_insights,
            agent_outputs=sample_agent_outputs
        )
        
        assert result is False


class TestLoadContext:
    """Tests for the load_context method."""
    
    @pytest.mark.asyncio
    async def test_load_context_success(
        self,
        context_manager,
        mock_redis_client
    ):
        """Test loading context successfully."""
        # Mock Redis to return context
        stored_context = {
            "session_id": "test_session",
            "history": [
                {
                    "query": "What are my main product gaps?",
                    "insights": [
                        {
                            "source_agent": "sentiment",
                            "insight_text": "Test insight",
                            "severity_score": 0.8,
                            "confidence_score": 0.9,
                            "supporting_reviews": [],
                            "visualization_hint": None,
                            "visualization_data": {"x": [1, 2], "y": [3, 4]},
                            "metadata": {}
                        }
                    ],
                    "agent_outputs": {"step1": {"data": "test"}},
                    "metadata": {},
                    "timestamp": "2025-01-01T00:00:00"
                }
            ],
            "last_updated": "2025-01-01T00:00:00"
        }
        mock_redis_client.get.return_value = stored_context
        
        context = await context_manager.load_context("test_session")
        
        assert context is not None
        assert context.session_id == "test_session"
        assert len(context.conversation_history) == 1
        assert context.conversation_history[0]["query"] == "What are my main product gaps?"
        assert "step1" in context.cached_results.get("turn_0_outputs", {})
        assert context.last_visualization_data is not None
        assert context.last_visualization_data["x"] == [1, 2]
    
    @pytest.mark.asyncio
    async def test_load_context_not_found(
        self,
        context_manager,
        mock_redis_client
    ):
        """Test loading context when none exists."""
        mock_redis_client.get.return_value = None
        
        context = await context_manager.load_context("test_session")
        
        assert context is None
    
    @pytest.mark.asyncio
    async def test_load_context_empty_history(
        self,
        context_manager,
        mock_redis_client
    ):
        """Test loading context with empty history."""
        stored_context = {
            "session_id": "test_session",
            "history": [],
            "last_updated": "2025-01-01T00:00:00"
        }
        mock_redis_client.get.return_value = stored_context
        
        context = await context_manager.load_context("test_session")
        
        assert context is None
    
    @pytest.mark.asyncio
    async def test_load_context_handles_errors(
        self,
        context_manager,
        mock_redis_client
    ):
        """Test that errors are handled gracefully."""
        mock_redis_client.get.side_effect = Exception("Redis error")
        
        context = await context_manager.load_context("test_session")
        
        assert context is None


class TestFollowUpDetection:
    """Tests for the is_follow_up_query method."""
    
    @pytest.mark.asyncio
    async def test_detect_follow_up_with_keywords(
        self,
        context_manager
    ):
        """Test follow-up detection using keywords."""
        context = ExecutionContext(
            user_id="test_user",
            session_id="test_session",
            message_id="test_message",
            query="Previous query",
            conversation_history=[{"query": "What are my main product gaps?"}]
        )
        
        # Test various follow-up keywords
        follow_up_queries = [
            "Show me more about that",
            "What about the biggest one?",
            "Compare those results",
            "Tell me more",
            "How about positive feedback?"
        ]
        
        for query in follow_up_queries:
            result = await context_manager.is_follow_up_query(query, context)
            assert result is True, f"Failed to detect follow-up: {query}"
    
    @pytest.mark.asyncio
    async def test_detect_follow_up_with_pronouns(
        self,
        context_manager
    ):
        """Test follow-up detection using pronouns."""
        context = ExecutionContext(
            user_id="test_user",
            session_id="test_session",
            message_id="test_message",
            query="Previous query",
            conversation_history=[{"query": "What are my main product gaps?"}]
        )
        
        # Test pronoun starters
        pronoun_queries = [
            "It seems interesting",
            "They are important",
            "Those look critical",
            "That is concerning"
        ]
        
        for query in pronoun_queries:
            result = await context_manager.is_follow_up_query(query, context)
            assert result is True, f"Failed to detect follow-up: {query}"
    
    @pytest.mark.asyncio
    async def test_detect_follow_up_short_queries(
        self,
        context_manager
    ):
        """Test follow-up detection for short queries."""
        context = ExecutionContext(
            user_id="test_user",
            session_id="test_session",
            message_id="test_message",
            query="Previous query",
            conversation_history=[{"query": "What are my main product gaps?"}]
        )
        
        # Short queries are likely follow-ups
        short_queries = [
            "What about positive?",
            "Show me",
            "More details"
        ]
        
        for query in short_queries:
            result = await context_manager.is_follow_up_query(query, context)
            assert result is True, f"Failed to detect follow-up: {query}"
    
    @pytest.mark.asyncio
    async def test_not_follow_up_new_query(
        self,
        context_manager
    ):
        """Test that new queries are not detected as follow-ups."""
        context = ExecutionContext(
            user_id="test_user",
            session_id="test_session",
            message_id="test_message",
            query="Previous query",
            conversation_history=[{"query": "What are my main product gaps?"}]
        )
        
        # These should not be detected as follow-ups
        new_queries = [
            "What is the sentiment distribution across all reviews?",
            "Analyze the topic trends over the last month",
            "Generate a summary of positive feedback"
        ]
        
        for query in new_queries:
            result = await context_manager.is_follow_up_query(query, context)
            assert result is False, f"Incorrectly detected as follow-up: {query}"
    
    @pytest.mark.asyncio
    async def test_not_follow_up_no_context(
        self,
        context_manager
    ):
        """Test that queries without context are not follow-ups."""
        result = await context_manager.is_follow_up_query(
            "Show me that",
            None
        )
        
        assert result is False


class TestContextAwarePlanning:
    """Tests for the get_context_for_planning method."""
    
    @pytest.mark.asyncio
    async def test_get_planning_context_with_history(
        self,
        context_manager,
        mock_redis_client
    ):
        """Test getting planning context with history."""
        # Mock Redis to return context
        stored_context = {
            "session_id": "test_session",
            "history": [
                {
                    "query": "What are my main product gaps?",
                    "insights": [
                        {
                            "source_agent": "topic_modeling",
                            "insight_text": "UI Slowness is the most frequent complaint",
                            "severity_score": 0.85,
                            "confidence_score": 0.90,
                            "supporting_reviews": [],
                            "visualization_hint": "bar_chart",
                            "visualization_data": None,
                            "metadata": {}
                        }
                    ],
                    "agent_outputs": {"step1": {"data": "test"}},
                    "metadata": {},
                    "timestamp": "2025-01-01T00:00:00"
                }
            ],
            "last_updated": "2025-01-01T00:00:00"
        }
        mock_redis_client.get.return_value = stored_context
        
        planning_context = await context_manager.get_context_for_planning(
            session_id="test_session",
            current_query="Show me the biggest gap"
        )
        
        assert len(planning_context["previous_queries"]) == 1
        assert planning_context["previous_queries"][0] == "What are my main product gaps?"
        assert len(planning_context["available_insights"]) == 1
        assert planning_context["available_insights"][0]["insight_text"] == "UI Slowness is the most frequent complaint"
        assert "turn_0_outputs" in planning_context["cached_data"]
        assert len(planning_context["suggested_shortcuts"]) > 0
        assert "reuse_top_insight" in planning_context["suggested_shortcuts"]
    
    @pytest.mark.asyncio
    async def test_get_planning_context_no_history(
        self,
        context_manager,
        mock_redis_client
    ):
        """Test getting planning context with no history."""
        mock_redis_client.get.return_value = None
        
        planning_context = await context_manager.get_context_for_planning(
            session_id="test_session",
            current_query="What are my main product gaps?"
        )
        
        assert planning_context["previous_queries"] == []
        assert planning_context["available_insights"] == []
        assert planning_context["cached_data"] == {}
        assert planning_context["suggested_shortcuts"] == []
    
    @pytest.mark.asyncio
    async def test_shortcut_generation_comparison(
        self,
        context_manager,
        mock_redis_client
    ):
        """Test shortcut generation for comparison queries."""
        stored_context = {
            "session_id": "test_session",
            "history": [{"query": "Previous query", "insights": [], "agent_outputs": {}}],
            "last_updated": "2025-01-01T00:00:00"
        }
        mock_redis_client.get.return_value = stored_context
        
        planning_context = await context_manager.get_context_for_planning(
            session_id="test_session",
            current_query="Compare that to last month"
        )
        
        assert "reuse_previous_data" in planning_context["suggested_shortcuts"]
    
    @pytest.mark.asyncio
    async def test_shortcut_generation_details(
        self,
        context_manager,
        mock_redis_client
    ):
        """Test shortcut generation for detail queries."""
        stored_context = {
            "session_id": "test_session",
            "history": [{"query": "Previous query", "insights": [], "agent_outputs": {}}],
            "last_updated": "2025-01-01T00:00:00"
        }
        mock_redis_client.get.return_value = stored_context
        
        planning_context = await context_manager.get_context_for_planning(
            session_id="test_session",
            current_query="Tell me more details about that"
        )
        
        assert "expand_previous_insight" in planning_context["suggested_shortcuts"]


class TestHelperMethods:
    """Tests for helper methods."""
    
    def test_serialize_insight(self, context_manager):
        """Test insight serialization."""
        insight = Insight(
            source_agent="sentiment",
            insight_text="Test insight",
            severity_score=0.8,
            confidence_score=0.9,
            supporting_reviews=["rev_1"],
            metadata={"key": "value"}
        )
        
        serialized = context_manager._serialize_insight(insight)
        
        assert isinstance(serialized, dict)
        assert serialized["source_agent"] == "sentiment"
        assert serialized["insight_text"] == "Test insight"
        assert serialized["severity_score"] == 0.8
    
    def test_extract_cached_results(self, context_manager):
        """Test extracting cached results from history."""
        history = [
            {
                "query": "Query 1",
                "insights": [{"text": "Insight 1"}],
                "agent_outputs": {"step1": {"data": "test1"}}
            },
            {
                "query": "Query 2",
                "insights": [{"text": "Insight 2"}],
                "agent_outputs": {"step2": {"data": "test2"}}
            }
        ]
        
        cached = context_manager._extract_cached_results(history)
        
        assert "turn_0_outputs" in cached
        assert "turn_1_outputs" in cached
        assert "turn_0_insights" in cached
        assert "turn_1_insights" in cached
        assert cached["turn_0_query"] == "Query 1"
        assert cached["turn_1_query"] == "Query 2"
    
    def test_extract_last_visualization(self, context_manager):
        """Test extracting visualization data."""
        latest_context = {
            "insights": [
                {
                    "source_agent": "sentiment",
                    "visualization_data": None
                },
                {
                    "source_agent": "topic",
                    "visualization_data": {
                        "x": [1, 2, 3],
                        "y": [4, 5, 6],
                        "chart_type": "bar"
                    }
                }
            ]
        }
        
        viz_data = context_manager._extract_last_visualization(latest_context)
        
        assert viz_data is not None
        assert viz_data["chart_type"] == "bar"
        assert viz_data["x"] == [1, 2, 3]
    
    def test_generate_shortcuts(self, context_manager):
        """Test shortcut generation."""
        shortcuts = context_manager._generate_shortcuts(
            current_query="Show me the biggest gap",
            previous_queries=["What are my main product gaps?"],
            available_insights=[{"text": "Insight 1"}]
        )
        
        assert "reuse_top_insight" in shortcuts
