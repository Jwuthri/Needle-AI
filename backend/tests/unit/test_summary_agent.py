"""
Unit tests for Summary Agent.

Tests the summarization functionality including extractive and abstractive
summarization, key point extraction, and insight generation.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch

from app.core.llm.workflow.agents.summary import SummaryAgent
from app.models.workflow import ExecutionContext


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
    return [
        {
            "id": "rev_1",
            "text": "The app is very slow and crashes frequently. Performance is terrible.",
            "rating": 1,
            "date": datetime.now().isoformat()
        },
        {
            "id": "rev_2",
            "text": "Great features but the UI is confusing and hard to navigate.",
            "rating": 3,
            "date": datetime.now().isoformat()
        },
        {
            "id": "rev_3",
            "text": "Love the content but app performance needs improvement. Laggy interface.",
            "rating": 3,
            "date": datetime.now().isoformat()
        },
        {
            "id": "rev_4",
            "text": "Customer support is unresponsive. Waited days for a reply.",
            "rating": 2,
            "date": datetime.now().isoformat()
        },
        {
            "id": "rev_5",
            "text": "App keeps freezing. Very frustrating experience with performance.",
            "rating": 1,
            "date": datetime.now().isoformat()
        },
        {
            "id": "rev_6",
            "text": "Excellent features and great value for money!",
            "rating": 5,
            "date": datetime.now().isoformat()
        },
        {
            "id": "rev_7",
            "text": "The app crashes constantly. Performance issues are unbearable.",
            "rating": 1,
            "date": datetime.now().isoformat()
        },
    ]


@pytest.fixture
def execution_context():
    """Create a sample execution context."""
    return ExecutionContext(
        user_id="test_user",
        session_id="test_session",
        message_id="test_message",
        query="Summarize my reviews",
        user_datasets=[{
            "dataset_id": "ds_1",
            "table_name": "reviews",
            "row_count": 7
        }]
    )


@pytest.mark.asyncio
async def test_summary_agent_initialization(mock_llm_client):
    """Test that SummaryAgent initializes correctly."""
    agent = SummaryAgent(llm_client=mock_llm_client)
    
    assert agent.llm_client == mock_llm_client
    assert agent.stream_callback is None


@pytest.mark.asyncio
async def test_generate_thought(mock_llm_client, sample_reviews, execution_context):
    """Test thought generation before summarization."""
    agent = SummaryAgent(llm_client=mock_llm_client)
    
    # Mock LLM response
    mock_llm_client.generate_completion.return_value = (
        "I will create an extractive summary of 7 reviews. "
        "I'll extract key points about positive and negative feedback, "
        "organize them by theme, and highlight the most important insights."
    )
    
    thought = await agent.generate_thought(
        reviews=sample_reviews,
        context=execution_context,
        summary_type="extractive"
    )
    
    assert thought is not None
    assert len(thought) > 0
    assert "summary" in thought.lower() or "extract" in thought.lower()
    mock_llm_client.generate_completion.assert_called_once()


@pytest.mark.asyncio
async def test_extractive_summarization(mock_llm_client, sample_reviews, execution_context, mock_db):
    """Test extractive summarization."""
    agent = SummaryAgent(llm_client=mock_llm_client)
    
    # Mock LLM responses
    mock_llm_client.generate_completion.side_effect = [
        # Thought generation
        "I will perform extractive summarization.",
        # Extractive summary
        "Users praise the features and content quality but consistently criticize app performance. "
        "The app crashes frequently and has a laggy interface. Customer support responsiveness is also a concern.",
        # Key points extraction
        '["Users praise features and content", "App performance is poor with crashes", "Customer support needs improvement"]'
    ]
    
    with patch('app.core.llm.workflow.agents.summary.ChatMessageStepRepository') as mock_repo:
        mock_repo.create = AsyncMock()
        
        insights = await agent.summarize_reviews(
            reviews=sample_reviews,
            context=execution_context,
            db=mock_db,
            step_order=1,
            summary_type="extractive"
        )
    
    # Should have one summary insight
    assert len(insights) == 1
    
    # Check summary insight
    summary_insight = insights[0]
    assert summary_insight.source_agent == "summary"
    assert summary_insight.metadata["summary_type"] == "extractive"
    assert summary_insight.metadata["total_reviews_summarized"] == 7
    assert "key_points" in summary_insight.metadata
    assert len(summary_insight.metadata["key_points"]) > 0
    assert summary_insight.confidence_score > 0
    assert summary_insight.severity_score > 0


@pytest.mark.asyncio
async def test_abstractive_summarization(mock_llm_client, sample_reviews, execution_context, mock_db):
    """Test abstractive summarization."""
    agent = SummaryAgent(llm_client=mock_llm_client)
    
    # Mock LLM responses
    mock_llm_client.generate_completion.side_effect = [
        # Thought generation
        "I will perform abstractive summarization.",
        # Abstractive summary
        "Overall, users appreciate the app's features and content but are frustrated by persistent performance issues. "
        "The app frequently crashes and has a laggy interface, which significantly impacts user experience. "
        "Additionally, customer support responsiveness needs improvement.",
        # Key points extraction
        '["Features and content are well-received", "Performance issues are widespread", "Support responsiveness is lacking"]'
    ]
    
    with patch('app.core.llm.workflow.agents.summary.ChatMessageStepRepository') as mock_repo:
        mock_repo.create = AsyncMock()
        
        insights = await agent.summarize_reviews(
            reviews=sample_reviews,
            context=execution_context,
            db=mock_db,
            step_order=1,
            summary_type="abstractive"
        )
    
    # Should have one summary insight
    assert len(insights) == 1
    
    # Check summary insight
    summary_insight = insights[0]
    assert summary_insight.source_agent == "summary"
    assert summary_insight.metadata["summary_type"] == "abstractive"
    assert summary_insight.metadata["total_reviews_summarized"] == 7
    assert "key_points" in summary_insight.metadata
    assert len(summary_insight.metadata["key_points"]) > 0
    assert "full_summary" in summary_insight.metadata


@pytest.mark.asyncio
async def test_summarize_with_streaming(mock_llm_client, sample_reviews, execution_context, mock_db):
    """Test summarization with streaming callback."""
    stream_callback = AsyncMock()
    agent = SummaryAgent(
        llm_client=mock_llm_client,
        stream_callback=stream_callback
    )
    
    # Mock LLM responses
    mock_llm_client.generate_completion.side_effect = [
        "Thought",
        "Summary text here.",
        '["Key point 1", "Key point 2"]'
    ]
    
    with patch('app.core.llm.workflow.agents.summary.ChatMessageStepRepository') as mock_repo:
        mock_repo.create = AsyncMock()
        
        await agent.summarize_reviews(
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
async def test_summarize_error_handling(mock_llm_client, sample_reviews, execution_context, mock_db):
    """Test error handling in summarization."""
    agent = SummaryAgent(llm_client=mock_llm_client)
    
    # Mock LLM to raise an error
    mock_llm_client.generate_completion.side_effect = Exception("LLM API error")
    
    with patch('app.core.llm.workflow.agents.summary.ChatMessageStepRepository') as mock_repo:
        mock_repo.create = AsyncMock()
        
        # The agent should handle errors gracefully
        insights = await agent.summarize_reviews(
            reviews=sample_reviews,
            context=execution_context,
            db=mock_db,
            step_order=1
        )
        
        # Should return empty insights when summarization fails
        assert len(insights) == 0
        
        # Verify error was tracked in Chat Message Steps
        assert mock_repo.create.called


@pytest.mark.asyncio
async def test_insights_added_to_context(mock_llm_client, sample_reviews, execution_context, mock_db):
    """Test that generated insights are added to execution context."""
    agent = SummaryAgent(llm_client=mock_llm_client)
    
    # Mock LLM responses
    mock_llm_client.generate_completion.side_effect = [
        "Thought",
        "Summary text.",
        '["Key point"]'
    ]
    
    initial_insight_count = len(execution_context.insights)
    
    with patch('app.core.llm.workflow.agents.summary.ChatMessageStepRepository') as mock_repo:
        mock_repo.create = AsyncMock()
        
        insights = await agent.summarize_reviews(
            reviews=sample_reviews,
            context=execution_context,
            db=mock_db,
            step_order=1
        )
    
    # Verify insights were added to context
    assert len(execution_context.insights) > initial_insight_count
    assert len(execution_context.insights) == initial_insight_count + len(insights)


@pytest.mark.asyncio
async def test_empty_reviews_handling(mock_llm_client, execution_context, mock_db):
    """Test handling of empty review list."""
    agent = SummaryAgent(llm_client=mock_llm_client)
    
    # Mock LLM responses
    mock_llm_client.generate_completion.side_effect = [
        "Thought",
        "No reviews to summarize.",
        '[]'
    ]
    
    with patch('app.core.llm.workflow.agents.summary.ChatMessageStepRepository') as mock_repo:
        mock_repo.create = AsyncMock()
        
        insights = await agent.summarize_reviews(
            reviews=[],
            context=execution_context,
            db=mock_db,
            step_order=1
        )
    
    # Should handle empty reviews gracefully
    # May return empty insights or a minimal insight
    assert isinstance(insights, list)


@pytest.mark.asyncio
async def test_supporting_reviews_included(mock_llm_client, sample_reviews, execution_context, mock_db):
    """Test that supporting reviews are included in insights."""
    agent = SummaryAgent(llm_client=mock_llm_client)
    
    # Mock LLM responses
    mock_llm_client.generate_completion.side_effect = [
        "Thought",
        "Summary text.",
        '["Key point"]'
    ]
    
    with patch('app.core.llm.workflow.agents.summary.ChatMessageStepRepository') as mock_repo:
        mock_repo.create = AsyncMock()
        
        insights = await agent.summarize_reviews(
            reviews=sample_reviews,
            context=execution_context,
            db=mock_db,
            step_order=1
        )
    
    # Check that insights include supporting reviews
    if len(insights) > 0:
        summary_insight = insights[0]
        assert len(summary_insight.supporting_reviews) > 0
        # Should include review IDs from the sample
        assert all(isinstance(rid, str) for rid in summary_insight.supporting_reviews)


@pytest.mark.asyncio
async def test_confidence_score_calculation(mock_llm_client, execution_context, mock_db):
    """Test that confidence score varies with review count."""
    agent = SummaryAgent(llm_client=mock_llm_client)
    
    # Test with few reviews
    few_reviews = [
        {"id": "rev_1", "text": "Good", "rating": 4},
        {"id": "rev_2", "text": "Bad", "rating": 2}
    ]
    
    # Test with many reviews
    many_reviews = [
        {"id": f"rev_{i}", "text": f"Review {i}", "rating": 3}
        for i in range(50)
    ]
    
    # Mock LLM responses
    mock_llm_client.generate_completion.side_effect = [
        "Thought", "Summary", '["Point"]',  # Few reviews
        "Thought", "Summary", '["Point"]'   # Many reviews
    ]
    
    with patch('app.core.llm.workflow.agents.summary.ChatMessageStepRepository') as mock_repo:
        mock_repo.create = AsyncMock()
        
        insights_few = await agent.summarize_reviews(
            reviews=few_reviews,
            context=execution_context,
            db=mock_db,
            step_order=1
        )
        
        insights_many = await agent.summarize_reviews(
            reviews=many_reviews,
            context=execution_context,
            db=mock_db,
            step_order=3
        )
    
    # Confidence should be higher with more reviews
    if len(insights_few) > 0 and len(insights_many) > 0:
        assert insights_many[0].confidence_score >= insights_few[0].confidence_score
