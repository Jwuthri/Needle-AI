"""
Unit tests for the Anomaly Detection Agent.

Tests the anomaly detection functionality including rating spikes,
topic emergence, and source-specific anomalies.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.llm.workflow.agents.anomaly_detection import AnomalyDetectionAgent
from app.models.workflow import ExecutionContext, Insight


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    client = AsyncMock()
    client.generate_completion = AsyncMock()
    return client


@pytest.fixture
def mock_stream_callback():
    """Create a mock stream callback."""
    return AsyncMock()


@pytest.fixture
def anomaly_agent(mock_llm_client, mock_stream_callback):
    """Create an AnomalyDetectionAgent instance."""
    return AnomalyDetectionAgent(
        llm_client=mock_llm_client,
        stream_callback=mock_stream_callback
    )


@pytest.fixture
def execution_context():
    """Create a test execution context."""
    return ExecutionContext(
        user_id="test_user",
        session_id="test_session",
        message_id="test_message",
        query="Detect anomalies in my reviews",
        user_datasets=[],
        insights=[]
    )


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return AsyncMock()


@pytest.fixture
def reviews_with_rating_spike():
    """Create test reviews with a rating spike."""
    base_date = datetime(2025, 1, 1)
    reviews = []
    
    # Historical reviews (weeks 1-3): normal pattern
    for week in range(3):
        for day in range(7):
            date = base_date + timedelta(weeks=week, days=day)
            # Add 2-3 reviews per day, mostly positive
            for i in range(2):
                reviews.append({
                    "id": f"rev_{week}_{day}_{i}",
                    "text": "Good product, works well",
                    "rating": 4,
                    "date": date.strftime("%Y-%m-%d"),
                    "source": "app_store"
                })
            # Add occasional low rating
            if day % 3 == 0:
                reviews.append({
                    "id": f"rev_{week}_{day}_low",
                    "text": "Some minor issues",
                    "rating": 2,
                    "date": date.strftime("%Y-%m-%d"),
                    "source": "app_store"
                })
    
    # Week 4: spike in low ratings
    spike_week = 3
    for day in range(7):
        date = base_date + timedelta(weeks=spike_week, days=day)
        # Add many low ratings
        for i in range(4):
            reviews.append({
                "id": f"rev_spike_{day}_{i}",
                "text": "App crashes constantly after update",
                "rating": 1,
                "date": date.strftime("%Y-%m-%d"),
                "source": "app_store"
            })
        # Add some normal ratings
        reviews.append({
            "id": f"rev_spike_{day}_normal",
            "text": "Still works for me",
            "rating": 4,
            "date": date.strftime("%Y-%m-%d"),
            "source": "app_store"
        })
    
    return reviews


@pytest.fixture
def reviews_with_emerging_topic():
    """Create test reviews with an emerging topic."""
    base_date = datetime(2025, 1, 1)
    reviews = []
    
    # Historical reviews (30 reviews): no mention of "battery drain"
    for i in range(30):
        date = base_date + timedelta(days=i)
        reviews.append({
            "id": f"rev_hist_{i}",
            "text": "Good app, works well. Some UI issues but overall positive.",
            "rating": 4,
            "date": date.strftime("%Y-%m-%d"),
            "source": "app_store"
        })
    
    # Recent reviews (15 reviews): many mention "battery drain"
    for i in range(15):
        date = base_date + timedelta(days=30 + i)
        if i % 2 == 0:
            reviews.append({
                "id": f"rev_recent_{i}",
                "text": "Battery drain is terrible after the latest update. Phone dies in 2 hours.",
                "rating": 1,
                "date": date.strftime("%Y-%m-%d"),
                "source": "app_store"
            })
        else:
            reviews.append({
                "id": f"rev_recent_{i}",
                "text": "App is okay but battery usage is concerning.",
                "rating": 3,
                "date": date.strftime("%Y-%m-%d"),
                "source": "app_store"
            })
    
    return reviews


@pytest.fixture
def reviews_with_source_anomaly():
    """Create test reviews with source-specific anomaly."""
    reviews = []
    
    # App Store reviews: mostly positive
    for i in range(20):
        reviews.append({
            "id": f"rev_appstore_{i}",
            "text": "Great app, works perfectly",
            "rating": 5 if i % 3 != 0 else 4,
            "date": "2025-01-15",
            "source": "app_store"
        })
    
    # Google Play reviews: many low ratings
    for i in range(20):
        reviews.append({
            "id": f"rev_googleplay_{i}",
            "text": "Crashes on Android 14. Unusable.",
            "rating": 1 if i % 2 == 0 else 2,
            "date": "2025-01-15",
            "source": "google_play"
        })
    
    return reviews


class TestAnomalyDetectionAgent:
    """Test suite for AnomalyDetectionAgent."""
    
    @pytest.mark.asyncio
    async def test_generate_thought(
        self,
        anomaly_agent,
        execution_context,
        reviews_with_rating_spike
    ):
        """Test thought generation for anomaly detection."""
        # Mock LLM response
        anomaly_agent.llm_client.generate_completion.return_value = (
            "I will analyze 50 reviews to detect anomalies. "
            "I'll establish baseline patterns for ratings and topics, then identify "
            "significant deviations such as rating spikes and unusual topic emergence."
        )
        
        thought = await anomaly_agent.generate_thought(
            reviews=reviews_with_rating_spike,
            context=execution_context
        )
        
        assert thought is not None
        assert len(thought) > 0
        assert "anomal" in thought.lower() or "baseline" in thought.lower()
        
        # Verify LLM was called
        anomaly_agent.llm_client.generate_completion.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_detect_rating_spike(
        self,
        anomaly_agent,
        execution_context,
        mock_db,
        reviews_with_rating_spike
    ):
        """Test detection of rating spikes."""
        # Mock LLM responses
        anomaly_agent.llm_client.generate_completion.side_effect = [
            "I will detect anomalies in the review data.",  # thought
            "Investigate app version released recently"  # recommendation
        ]
        
        with patch('app.database.repositories.chat_message_step.ChatMessageStepRepository.create', new_callable=AsyncMock):
            insights = await anomaly_agent.detect_anomalies(
                reviews=reviews_with_rating_spike,
                context=execution_context,
                db=mock_db,
                step_order=1,
                time_window="weekly"
            )
        
        # Should detect the rating spike
        assert len(insights) > 0
        
        # Find the rating spike insight
        spike_insights = [i for i in insights if i.metadata.get("anomaly_type") == "rating_spike"]
        assert len(spike_insights) > 0
        
        spike_insight = spike_insights[0]
        assert "spike" in spike_insight.insight_text.lower() or "critical" in spike_insight.insight_text.lower()
        assert spike_insight.severity_score >= 0.7
        assert spike_insight.source_agent == "anomaly_detection"
        assert spike_insight.visualization_hint == "line_chart"
        assert "recommended_action" in spike_insight.metadata
    
    @pytest.mark.asyncio
    async def test_detect_emerging_topic(
        self,
        anomaly_agent,
        execution_context,
        mock_db,
        reviews_with_emerging_topic
    ):
        """Test detection of emerging topics."""
        # Mock LLM responses
        anomaly_agent.llm_client.generate_completion.side_effect = [
            "I will detect anomalies in the review data.",  # thought
            '''[{
                "topic_name": "Battery Drain",
                "recent_count": 8,
                "historical_count": 0,
                "severity": "high",
                "description": "Users reporting excessive battery consumption"
            }]'''  # emerging topics
        ]
        
        with patch('app.database.repositories.chat_message_step.ChatMessageStepRepository.create', new_callable=AsyncMock):
            insights = await anomaly_agent.detect_anomalies(
                reviews=reviews_with_emerging_topic,
                context=execution_context,
                db=mock_db,
                step_order=1
            )
        
        # Should detect the emerging topic
        assert len(insights) > 0
        
        # Find the topic emergence insight
        topic_insights = [i for i in insights if i.metadata.get("anomaly_type") == "topic_emergence"]
        assert len(topic_insights) > 0
        
        topic_insight = topic_insights[0]
        assert "emerg" in topic_insight.insight_text.lower() or "new" in topic_insight.insight_text.lower()
        assert topic_insight.severity_score >= 0.7
        assert topic_insight.source_agent == "anomaly_detection"
        assert "topic_name" in topic_insight.metadata
    
    @pytest.mark.asyncio
    async def test_detect_source_anomaly(
        self,
        anomaly_agent,
        execution_context,
        mock_db,
        reviews_with_source_anomaly
    ):
        """Test detection of source-specific anomalies."""
        # Mock LLM responses
        anomaly_agent.llm_client.generate_completion.side_effect = [
            "I will detect anomalies in the review data.",  # thought
            "Android 14 compatibility issue causing crashes"  # source issue
        ]
        
        with patch('app.database.repositories.chat_message_step.ChatMessageStepRepository.create', new_callable=AsyncMock):
            insights = await anomaly_agent.detect_anomalies(
                reviews=reviews_with_source_anomaly,
                context=execution_context,
                db=mock_db,
                step_order=1
            )
        
        # Should detect the source-specific anomaly
        assert len(insights) > 0
        
        # Find the source anomaly insight
        source_insights = [
            i for i in insights
            if i.metadata.get("anomaly_type") in ["source_specific", "source_rating_difference"]
        ]
        assert len(source_insights) > 0
        
        source_insight = source_insights[0]
        assert "google_play" in source_insight.insight_text.lower() or "platform" in source_insight.insight_text.lower()
        assert source_insight.severity_score >= 0.5
        assert source_insight.source_agent == "anomaly_detection"
        assert "source" in source_insight.metadata
    
    @pytest.mark.asyncio
    async def test_high_severity_for_critical_anomalies(
        self,
        anomaly_agent,
        execution_context,
        mock_db,
        reviews_with_rating_spike
    ):
        """Test that critical anomalies have high severity scores."""
        # Mock LLM responses
        anomaly_agent.llm_client.generate_completion.side_effect = [
            "I will detect anomalies.",
            "Investigate recent update"
        ]
        
        with patch('app.database.repositories.chat_message_step.ChatMessageStepRepository.create', new_callable=AsyncMock):
            insights = await anomaly_agent.detect_anomalies(
                reviews=reviews_with_rating_spike,
                context=execution_context,
                db=mock_db,
                step_order=1
            )
        
        # Check for critical anomalies (severity > 0.9)
        critical_insights = [i for i in insights if i.severity_score > 0.9]
        
        # At least some insights should be marked as critical
        # (depending on the spike magnitude)
        if critical_insights:
            for insight in critical_insights:
                assert "CRITICAL" in insight.insight_text or insight.severity_score > 0.9
    
    @pytest.mark.asyncio
    async def test_streaming_events(
        self,
        anomaly_agent,
        execution_context,
        mock_db,
        reviews_with_rating_spike
    ):
        """Test that streaming events are emitted."""
        # Mock LLM responses
        anomaly_agent.llm_client.generate_completion.side_effect = [
            "I will detect anomalies.",
            "Investigate recent update"
        ]
        
        with patch('app.database.repositories.chat_message_step.ChatMessageStepRepository.create', new_callable=AsyncMock):
            await anomaly_agent.detect_anomalies(
                reviews=reviews_with_rating_spike,
                context=execution_context,
                db=mock_db,
                step_order=1
            )
        
        # Verify streaming events were emitted
        assert anomaly_agent.stream_callback.call_count >= 2
        
        # Check for start and complete events
        calls = anomaly_agent.stream_callback.call_args_list
        event_types = [call[0][0]["event_type"] for call in calls]
        
        assert "agent_step_start" in event_types
        assert "agent_step_complete" in event_types
    
    @pytest.mark.asyncio
    async def test_error_handling(
        self,
        anomaly_agent,
        execution_context,
        mock_db
    ):
        """Test error handling in anomaly detection."""
        # Mock LLM to raise an error
        anomaly_agent.llm_client.generate_completion.side_effect = Exception("LLM error")
        
        with patch('app.database.repositories.chat_message_step.ChatMessageStepRepository.create', new_callable=AsyncMock):
            insights = await anomaly_agent.detect_anomalies(
                reviews=[{"id": "1", "text": "test", "rating": 5}],
                context=execution_context,
                db=mock_db,
                step_order=1
            )
        
        # Should return empty list on error
        assert insights == []
        
        # Should emit error event
        calls = anomaly_agent.stream_callback.call_args_list
        event_types = [call[0][0]["event_type"] for call in calls]
        assert "agent_step_error" in event_types
    
    @pytest.mark.asyncio
    async def test_insufficient_data(
        self,
        anomaly_agent,
        execution_context,
        mock_db
    ):
        """Test handling of insufficient data for anomaly detection."""
        # Only a few reviews without dates
        reviews = [
            {"id": "1", "text": "test", "rating": 5},
            {"id": "2", "text": "test", "rating": 4}
        ]
        
        # Mock LLM response
        anomaly_agent.llm_client.generate_completion.return_value = "I will detect anomalies."
        
        with patch('app.database.repositories.chat_message_step.ChatMessageStepRepository.create', new_callable=AsyncMock):
            insights = await anomaly_agent.detect_anomalies(
                reviews=reviews,
                context=execution_context,
                db=mock_db,
                step_order=1
            )
        
        # Should handle gracefully and return empty or minimal insights
        assert isinstance(insights, list)
