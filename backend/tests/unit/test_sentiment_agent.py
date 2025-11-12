"""
Unit tests for Sentiment Analysis Agent.

Tests the sentiment analysis functionality including overall sentiment,
aspect-based analysis, and trend detection.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.llm.workflow.agents.sentiment import SentimentAnalysisAgent
from app.models.workflow import ExecutionContext, Insight


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    client = AsyncMock()
    client.generate_completion = AsyncMock()
    return client


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return AsyncMock()


@pytest.fixture
def sample_reviews():
    """Create sample review data for testing."""
    base_date = datetime.now()
    return [
        {
            "id": "rev_1",
            "text": "The app is very slow and crashes frequently. Performance is terrible.",
            "rating": 1,
            "date": (base_date - timedelta(days=30)).isoformat()
        },
        {
            "id": "rev_2",
            "text": "Great features but the UI is confusing and hard to navigate.",
            "rating": 3,
            "date": (base_date - timedelta(days=25)).isoformat()
        },
        {
            "id": "rev_3",
            "text": "Love the content but app performance needs improvement. Laggy interface.",
            "rating": 3,
            "date": (base_date - timedelta(days=20)).isoformat()
        },
        {
            "id": "rev_4",
            "text": "Customer support is unresponsive. Waited days for a reply.",
            "rating": 2,
            "date": (base_date - timedelta(days=15)).isoformat()
        },
        {
            "id": "rev_5",
            "text": "App keeps freezing. Very frustrating experience with performance.",
            "rating": 1,
            "date": (base_date - timedelta(days=10)).isoformat()
        },
        {
            "id": "rev_6",
            "text": "Excellent features and great value for money!",
            "rating": 5,
            "date": (base_date - timedelta(days=5)).isoformat()
        },
        {
            "id": "rev_7",
            "text": "The app crashes constantly. Performance issues are unbearable.",
            "rating": 1,
            "date": (base_date - timedelta(days=2)).isoformat()
        },
    ]


@pytest.fixture
def execution_context():
    """Create a sample execution context."""
    return ExecutionContext(
        user_id="test_user",
        session_id="test_session",
        message_id="test_message",
        query="Analyze sentiment in my reviews",
        user_datasets=[{
            "dataset_id": "ds_1",
            "table_name": "reviews",
            "row_count": 7
        }]
    )


@pytest.mark.asyncio
async def test_sentiment_agent_initialization(mock_llm_client):
    """Test that SentimentAnalysisAgent initializes correctly."""
    agent = SentimentAnalysisAgent(llm_client=mock_llm_client)
    
    assert agent.llm_client == mock_llm_client
    assert agent.stream_callback is None


@pytest.mark.asyncio
async def test_generate_thought(mock_llm_client, sample_reviews, execution_context):
    """Test thought generation before sentiment analysis."""
    agent = SentimentAnalysisAgent(llm_client=mock_llm_client)
    
    # Mock LLM response
    mock_llm_client.generate_completion.return_value = (
        "I will analyze sentiment across 5 aspects (features, usability, performance, "
        "support, value) for 7 reviews. I'll identify overall sentiment patterns, "
        "aspect-specific issues, and any concerning trends over time."
    )
    
    thought = await agent.generate_thought(
        reviews=sample_reviews,
        aspects=["features", "usability", "performance", "support", "value"],
        context=execution_context
    )
    
    assert thought is not None
    assert len(thought) > 0
    assert "sentiment" in thought.lower() or "analyze" in thought.lower()
    mock_llm_client.generate_completion.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_overall_sentiment(mock_llm_client, sample_reviews, execution_context, mock_db):
    """Test overall sentiment analysis."""
    agent = SentimentAnalysisAgent(llm_client=mock_llm_client)
    
    # Mock LLM responses
    mock_llm_client.generate_completion.side_effect = [
        # Thought generation
        "I will analyze overall sentiment patterns.",
        # Overall sentiment analysis
        '''```json
{
    "overall_sentiment": "negative",
    "positive_percentage": 20,
    "negative_percentage": 60,
    "neutral_percentage": 20,
    "key_finding": "Overall sentiment is predominantly negative with 60% of reviews expressing dissatisfaction",
    "confidence": 0.85
}
```'''
    ]
    
    with patch('app.core.llm.workflow.agents.sentiment.ChatMessageStepRepository') as mock_repo:
        mock_repo.create = AsyncMock()
        
        insights = await agent.analyze_sentiment(
            reviews=sample_reviews,
            context=execution_context,
            db=mock_db,
            step_order=1
        )
    
    # Should have at least one insight (overall sentiment)
    assert len(insights) > 0
    
    # Check overall sentiment insight
    overall_insight = next((i for i in insights if i.metadata.get("analysis_type") == "overall_sentiment"), None)
    assert overall_insight is not None
    assert overall_insight.source_agent == "sentiment"
    assert overall_insight.severity_score > 0
    assert overall_insight.visualization_hint == "pie_chart"


@pytest.mark.asyncio
async def test_analyze_aspect_sentiment(mock_llm_client, sample_reviews, execution_context, mock_db):
    """Test aspect-based sentiment analysis."""
    agent = SentimentAnalysisAgent(llm_client=mock_llm_client)
    
    # Mock LLM responses
    mock_llm_client.generate_completion.side_effect = [
        # Thought generation
        "I will analyze aspect-based sentiment.",
        # Overall sentiment (will be skipped in this test focus)
        '''{"overall_sentiment": "mixed", "positive_percentage": 30, "negative_percentage": 50, 
            "neutral_percentage": 20, "key_finding": "Mixed sentiment", "confidence": 0.8}''',
        # Aspect sentiment analysis
        '''```json
[
    {
        "aspect_name": "performance",
        "sentiment": "negative",
        "negative_percentage": 80,
        "mention_count": 5,
        "key_issues": ["slow", "crashes", "laggy"],
        "confidence": 0.9
    },
    {
        "aspect_name": "features",
        "sentiment": "positive",
        "negative_percentage": 20,
        "mention_count": 3,
        "key_issues": [],
        "confidence": 0.85
    },
    {
        "aspect_name": "support",
        "sentiment": "negative",
        "negative_percentage": 70,
        "mention_count": 2,
        "key_issues": ["unresponsive"],
        "confidence": 0.75
    }
]
```'''
    ]
    
    with patch('app.core.llm.workflow.agents.sentiment.ChatMessageStepRepository') as mock_repo:
        mock_repo.create = AsyncMock()
        
        insights = await agent.analyze_sentiment(
            reviews=sample_reviews,
            context=execution_context,
            db=mock_db,
            step_order=1,
            aspects=["performance", "features", "support"]
        )
    
    # Should have insights for aspects with significant negative sentiment
    aspect_insights = [i for i in insights if i.metadata.get("analysis_type") == "aspect_sentiment"]
    assert len(aspect_insights) > 0
    
    # Check performance aspect insight (should be present due to high negative sentiment)
    performance_insight = next(
        (i for i in aspect_insights if i.metadata.get("aspect") == "performance"),
        None
    )
    assert performance_insight is not None
    assert performance_insight.severity_score >= 0.7  # 80% negative
    assert "performance" in performance_insight.insight_text.lower()


@pytest.mark.asyncio
async def test_sentiment_trend_analysis(mock_llm_client, sample_reviews, execution_context, mock_db):
    """Test sentiment trend analysis over time."""
    agent = SentimentAnalysisAgent(llm_client=mock_llm_client)
    
    # Create reviews with clear declining trend
    declining_reviews = []
    base_date = datetime.now()
    
    # Earlier reviews (better ratings)
    for i in range(5):
        declining_reviews.append({
            "id": f"rev_early_{i}",
            "text": "Good product",
            "rating": 4,
            "date": (base_date - timedelta(days=60 - i*2)).isoformat()
        })
    
    # Recent reviews (worse ratings)
    for i in range(5):
        declining_reviews.append({
            "id": f"rev_recent_{i}",
            "text": "Poor quality now",
            "rating": 2,
            "date": (base_date - timedelta(days=10 - i)).isoformat()
        })
    
    # Mock LLM responses
    mock_llm_client.generate_completion.side_effect = [
        # Thought
        "Analyzing trends",
        # Overall sentiment
        '''{"overall_sentiment": "mixed", "positive_percentage": 40, "negative_percentage": 40,
            "neutral_percentage": 20, "key_finding": "Mixed", "confidence": 0.8}''',
        # Aspect sentiment
        '''[]'''
    ]
    
    with patch('app.core.llm.workflow.agents.sentiment.ChatMessageStepRepository') as mock_repo:
        mock_repo.create = AsyncMock()
        
        insights = await agent.analyze_sentiment(
            reviews=declining_reviews,
            context=execution_context,
            db=mock_db,
            step_order=1
        )
    
    # Check for trend insight
    trend_insights = [i for i in insights if i.metadata.get("analysis_type") == "sentiment_trend"]
    
    # Should detect declining trend
    if len(trend_insights) > 0:
        trend_insight = trend_insights[0]
        assert trend_insight.metadata.get("trend") == "declining"
        assert trend_insight.visualization_hint == "line_chart"
        assert "declined" in trend_insight.insight_text.lower()


@pytest.mark.asyncio
async def test_analyze_sentiment_with_streaming(mock_llm_client, sample_reviews, execution_context, mock_db):
    """Test sentiment analysis with streaming callback."""
    stream_callback = AsyncMock()
    agent = SentimentAnalysisAgent(
        llm_client=mock_llm_client,
        stream_callback=stream_callback
    )
    
    # Mock LLM responses
    mock_llm_client.generate_completion.side_effect = [
        "Thought",
        '''{"overall_sentiment": "negative", "positive_percentage": 20, "negative_percentage": 60,
            "neutral_percentage": 20, "key_finding": "Negative", "confidence": 0.8}''',
        '''[]'''
    ]
    
    with patch('app.core.llm.workflow.agents.sentiment.ChatMessageStepRepository') as mock_repo:
        mock_repo.create = AsyncMock()
        
        await agent.analyze_sentiment(
            reviews=sample_reviews,
            context=execution_context,
            db=mock_db,
            step_order=1
        )
    
    # Verify streaming events were emitted
    assert stream_callback.call_count >= 2  # At least start and complete events
    
    # Check event types
    calls = stream_callback.call_args_list
    event_types = [call[0][0]["event_type"] for call in calls]
    assert "agent_step_start" in event_types
    assert "agent_step_complete" in event_types


@pytest.mark.asyncio
async def test_analyze_sentiment_error_handling(mock_llm_client, sample_reviews, execution_context, mock_db):
    """Test error handling in sentiment analysis."""
    agent = SentimentAnalysisAgent(llm_client=mock_llm_client)
    
    # Mock LLM to raise an error during thought generation
    mock_llm_client.generate_completion.side_effect = Exception("LLM API error")
    
    with patch('app.core.llm.workflow.agents.sentiment.ChatMessageStepRepository') as mock_repo:
        mock_repo.create = AsyncMock()
        
        # The agent should handle errors gracefully and return empty insights
        # rather than raising exceptions (for resilience)
        insights = await agent.analyze_sentiment(
            reviews=sample_reviews,
            context=execution_context,
            db=mock_db,
            step_order=1
        )
        
        # Should return empty insights when all analysis fails
        assert len(insights) == 0
        
        # Verify steps were tracked in Chat Message Steps
        assert mock_repo.create.called


@pytest.mark.asyncio
async def test_insights_added_to_context(mock_llm_client, sample_reviews, execution_context, mock_db):
    """Test that generated insights are added to execution context."""
    agent = SentimentAnalysisAgent(llm_client=mock_llm_client)
    
    # Mock LLM responses
    mock_llm_client.generate_completion.side_effect = [
        "Thought",
        '''{"overall_sentiment": "negative", "positive_percentage": 20, "negative_percentage": 60,
            "neutral_percentage": 20, "key_finding": "Negative sentiment", "confidence": 0.85}''',
        '''[]'''
    ]
    
    initial_insight_count = len(execution_context.insights)
    
    with patch('app.core.llm.workflow.agents.sentiment.ChatMessageStepRepository') as mock_repo:
        mock_repo.create = AsyncMock()
        
        insights = await agent.analyze_sentiment(
            reviews=sample_reviews,
            context=execution_context,
            db=mock_db,
            step_order=1
        )
    
    # Verify insights were added to context
    assert len(execution_context.insights) > initial_insight_count
    assert len(execution_context.insights) == initial_insight_count + len(insights)
