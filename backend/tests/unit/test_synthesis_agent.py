"""
Unit tests for the Synthesis Agent.

Tests the synthesis agent's ability to combine insights into coherent responses.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.core.llm.workflow.agents.synthesis import SynthesisAgent
from app.models.workflow import ExecutionContext, Insight, SynthesisThought


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    client = AsyncMock()
    client.generate_completion = AsyncMock()
    return client


@pytest.fixture
def mock_visualization_agent():
    """Create a mock visualization agent."""
    agent = AsyncMock()
    agent.generate_visualization = AsyncMock()
    return agent


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return AsyncMock()


@pytest.fixture
def sample_insights():
    """Create sample insights for testing."""
    return [
        Insight(
            source_agent="sentiment",
            insight_text="Performance aspect has 78% negative sentiment across 35 reviews",
            severity_score=0.78,
            confidence_score=0.92,
            supporting_reviews=["rev_1", "rev_2", "rev_3"],
            visualization_hint="bar_chart",
            visualization_data={
                "x": ["Performance", "Features", "Support"],
                "y": [0.78, 0.45, 0.62],
                "chart_type": "bar",
                "title": "Negative Sentiment by Aspect"
            },
            metadata={"aspect": "performance", "total_reviews": 35}
        ),
        Insight(
            source_agent="topic_modeling",
            insight_text="'UI Slowness' is the most frequent complaint, appearing in 18 reviews",
            severity_score=0.85,
            confidence_score=0.90,
            supporting_reviews=["rev_4", "rev_5", "rev_6"],
            visualization_hint="bar_chart",
            visualization_data={
                "x": ["UI Slowness", "App Crashes", "Missing Features"],
                "y": [18, 12, 8],
                "chart_type": "bar",
                "title": "Top Complaint Topics"
            },
            metadata={"topic_id": "topic_1", "keywords": ["slow", "laggy"]}
        ),
        Insight(
            source_agent="anomaly_detection",
            insight_text="CRITICAL: 1-star reviews spiked 400% on Oct 10th",
            severity_score=0.95,
            confidence_score=0.93,
            supporting_reviews=["rev_7", "rev_8", "rev_9"],
            visualization_hint="line_chart",
            visualization_data={
                "x": ["Oct 8", "Oct 9", "Oct 10", "Oct 11"],
                "y": [3, 2, 12, 4],
                "chart_type": "line",
                "title": "1-Star Review Spike"
            },
            metadata={"anomaly_type": "rating_spike", "spike_date": "2025-10-10"}
        ),
        Insight(
            source_agent="summary",
            insight_text="Overall: Users praise content quality but criticize app performance",
            severity_score=0.60,
            confidence_score=0.88,
            supporting_reviews=["rev_10", "rev_11"],
            visualization_hint=None,
            visualization_data=None,
            metadata={
                "summary_type": "abstractive",
                "key_points": ["Content quality is highly rated", "Performance issues are widespread"]
            }
        )
    ]


@pytest.fixture
def execution_context():
    """Create a sample execution context."""
    return ExecutionContext(
        user_id="user_123",
        session_id="session_456",
        message_id="msg_789",
        query="What are my main product gaps?",
        user_datasets=[],
        insights=[]
    )


class TestSynthesisAgent:
    """Test suite for SynthesisAgent."""
    
    @pytest.mark.asyncio
    async def test_initialization(self, mock_llm_client):
        """Test agent initialization."""
        agent = SynthesisAgent(
            llm_client=mock_llm_client,
            stream_callback=None
        )
        
        assert agent.llm_client == mock_llm_client
        assert agent.visualization_agent is None
        assert agent.stream_callback is None
    
    @pytest.mark.asyncio
    async def test_generate_synthesis_plan(
        self,
        mock_llm_client,
        sample_insights,
        execution_context
    ):
        """Test synthesis plan generation."""
        # Mock LLM response
        mock_llm_client.generate_completion.return_value = """```json
{
    "outline": ["Executive Summary", "Critical Issues", "Common Themes", "Recommendations"],
    "key_insights": [0, 1, 2],
    "narrative_strategy": "severity-based",
    "reasoning": "Organizing by severity to highlight critical issues first"
}
```"""
        
        agent = SynthesisAgent(llm_client=mock_llm_client)
        
        plan = await agent.generate_synthesis_plan(
            query="What are my main product gaps?",
            insights=sample_insights,
            context=execution_context
        )
        
        assert isinstance(plan, SynthesisThought)
        assert len(plan.outline) == 4
        assert "Executive Summary" in plan.outline
        assert plan.narrative_strategy == "severity-based"
        assert len(plan.key_insights) > 0
        
        # Verify LLM was called
        mock_llm_client.generate_completion.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_synthesis_plan_fallback(
        self,
        mock_llm_client,
        sample_insights,
        execution_context
    ):
        """Test synthesis plan generation with fallback on error."""
        # Mock LLM to raise error
        mock_llm_client.generate_completion.side_effect = Exception("LLM error")
        
        agent = SynthesisAgent(llm_client=mock_llm_client)
        
        plan = await agent.generate_synthesis_plan(
            query="What are my main product gaps?",
            insights=sample_insights,
            context=execution_context
        )
        
        # Should return fallback plan
        assert isinstance(plan, SynthesisThought)
        assert len(plan.outline) > 0
        assert plan.narrative_strategy == "severity-based"
    
    @pytest.mark.asyncio
    async def test_prioritize_insights(self, mock_llm_client, sample_insights):
        """Test insight prioritization by severity and confidence."""
        agent = SynthesisAgent(llm_client=mock_llm_client)
        
        prioritized = agent._prioritize_insights(sample_insights)
        
        # Should be sorted by severity * confidence (descending)
        assert len(prioritized) == len(sample_insights)
        
        # Anomaly detection insight should be first (0.95 * 0.93 = 0.8835)
        assert prioritized[0].source_agent == "anomaly_detection"
        assert prioritized[0].severity_score == 0.95
        
        # Verify descending order
        for i in range(len(prioritized) - 1):
            score_i = prioritized[i].severity_score * prioritized[i].confidence_score
            score_next = prioritized[i + 1].severity_score * prioritized[i + 1].confidence_score
            assert score_i >= score_next
    
    @pytest.mark.asyncio
    async def test_group_insights_by_theme(self, mock_llm_client, sample_insights):
        """Test grouping insights by theme."""
        agent = SynthesisAgent(llm_client=mock_llm_client)
        
        grouped = agent._group_insights_by_theme(sample_insights)
        
        # Should have 4 groups (one per source agent)
        assert len(grouped) == 4
        assert "Sentiment Analysis" in grouped
        assert "Common Themes" in grouped
        assert "Critical Issues" in grouped
        assert "Overview" in grouped
        
        # Verify insights are in correct groups
        assert len(grouped["Sentiment Analysis"]) == 1
        assert grouped["Sentiment Analysis"][0].source_agent == "sentiment"
        
        # Groups should be sorted by highest severity
        group_names = list(grouped.keys())
        assert group_names[0] == "Critical Issues"  # Highest severity (0.95)
    
    @pytest.mark.asyncio
    async def test_generate_introduction(
        self,
        mock_llm_client,
        sample_insights
    ):
        """Test introduction generation."""
        agent = SynthesisAgent(llm_client=mock_llm_client)
        
        grouped = agent._group_insights_by_theme(sample_insights)
        intro = await agent._generate_introduction(
            query="What are my main product gaps?",
            grouped_insights=grouped
        )
        
        assert "# Analysis Results" in intro
        assert "What are my main product gaps?" in intro
        assert "4 key insights" in intro
        assert "4 categories" in intro
    
    @pytest.mark.asyncio
    async def test_generate_key_findings(
        self,
        mock_llm_client,
        sample_insights
    ):
        """Test key findings generation."""
        agent = SynthesisAgent(llm_client=mock_llm_client)
        
        grouped = agent._group_insights_by_theme(sample_insights)
        key_findings = await agent._generate_key_findings(
            grouped_insights=grouped,
            key_insight_ids=[]
        )
        
        assert "## 🔑 Key Findings" in key_findings
        assert "🔴" in key_findings  # High severity emoji
        assert "Confidence:" in key_findings
        
        # Should include top insights
        assert "CRITICAL: 1-star reviews spiked" in key_findings
    
    @pytest.mark.asyncio
    async def test_generate_citations(
        self,
        mock_llm_client,
        sample_insights
    ):
        """Test citations generation."""
        agent = SynthesisAgent(llm_client=mock_llm_client)
        
        grouped = agent._group_insights_by_theme(sample_insights)
        citations = await agent._generate_citations(grouped)
        
        assert "## 📚 Supporting Evidence" in citations
        assert "reviews" in citations.lower()
        
        # Should include review IDs
        assert "rev_" in citations
    
    @pytest.mark.asyncio
    async def test_generate_recommendations(
        self,
        mock_llm_client,
        sample_insights
    ):
        """Test recommendations generation."""
        agent = SynthesisAgent(llm_client=mock_llm_client)
        
        grouped = agent._group_insights_by_theme(sample_insights)
        recommendations = await agent._generate_recommendations(grouped)
        
        assert "## 💡 Recommendations" in recommendations
        assert "priority actions" in recommendations.lower()
        
        # Should include high-severity insights
        assert len(recommendations) > 100  # Should have content
    
    @pytest.mark.asyncio
    async def test_generate_fallback_response(
        self,
        mock_llm_client,
        sample_insights
    ):
        """Test fallback response generation."""
        agent = SynthesisAgent(llm_client=mock_llm_client)
        
        response = agent._generate_fallback_response(
            query="What are my main product gaps?",
            insights=sample_insights
        )
        
        assert "# Analysis Results" in response
        assert "What are my main product gaps?" in response
        assert "4 insights" in response
        
        # Should list insights
        for insight in sample_insights:
            assert insight.insight_text[:30] in response
    
    @pytest.mark.asyncio
    async def test_generate_fallback_response_no_insights(
        self,
        mock_llm_client
    ):
        """Test fallback response with no insights."""
        agent = SynthesisAgent(llm_client=mock_llm_client)
        
        response = agent._generate_fallback_response(
            query="What are my main product gaps?",
            insights=[]
        )
        
        assert "# Analysis Results" in response
        assert "couldn't generate" in response.lower()
    
    @pytest.mark.asyncio
    @patch('app.database.repositories.chat_message_step.ChatMessageStepRepository.create')
    async def test_synthesize_response_success(
        self,
        mock_create_step,
        mock_llm_client,
        mock_db,
        sample_insights,
        execution_context
    ):
        """Test successful response synthesis."""
        # Mock LLM response for synthesis plan
        mock_llm_client.generate_completion.return_value = """```json
{
    "outline": ["Executive Summary", "Key Findings", "Recommendations"],
    "key_insights": [0, 1],
    "narrative_strategy": "severity-based",
    "reasoning": "Organizing by severity"
}
```"""
        
        # Mock step creation
        mock_create_step.return_value = AsyncMock()
        
        agent = SynthesisAgent(llm_client=mock_llm_client)
        
        response = await agent.synthesize_response(
            query="What are my main product gaps?",
            insights=sample_insights,
            context=execution_context,
            db=mock_db,
            step_order=1
        )
        
        # Verify response structure
        assert isinstance(response, str)
        assert len(response) > 0
        assert "# Analysis Results" in response
        assert "## 🔑 Key Findings" in response
        assert "## 💡 Recommendations" in response
        assert "## 📚 Supporting Evidence" in response
        
        # Verify Chat Message Steps were created
        assert mock_create_step.call_count >= 2  # At least thought and output steps
    
    @pytest.mark.asyncio
    @patch('app.database.repositories.chat_message_step.ChatMessageStepRepository.create')
    async def test_synthesize_response_with_error(
        self,
        mock_create_step,
        mock_llm_client,
        mock_db,
        sample_insights,
        execution_context
    ):
        """Test response synthesis with error handling."""
        # Mock LLM to raise error
        mock_llm_client.generate_completion.side_effect = Exception("LLM error")
        
        # Mock step creation
        mock_create_step.return_value = AsyncMock()
        
        agent = SynthesisAgent(llm_client=mock_llm_client)
        
        response = await agent.synthesize_response(
            query="What are my main product gaps?",
            insights=sample_insights,
            context=execution_context,
            db=mock_db,
            step_order=1
        )
        
        # Should return fallback response
        assert isinstance(response, str)
        assert len(response) > 0
        assert "# Analysis Results" in response
        
        # Verify error was tracked
        assert mock_create_step.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_emit_event(self, mock_llm_client):
        """Test event emission."""
        callback = AsyncMock()
        agent = SynthesisAgent(
            llm_client=mock_llm_client,
            stream_callback=callback
        )
        
        await agent._emit_event("test_event", {"key": "value"})
        
        callback.assert_called_once_with({
            "event_type": "test_event",
            "data": {"key": "value"}
        })
    
    @pytest.mark.asyncio
    async def test_emit_event_no_callback(self, mock_llm_client):
        """Test event emission without callback."""
        agent = SynthesisAgent(llm_client=mock_llm_client)
        
        # Should not raise error
        await agent._emit_event("test_event", {"key": "value"})
    
    @pytest.mark.asyncio
    async def test_emit_event_with_error(self, mock_llm_client):
        """Test event emission with callback error."""
        callback = AsyncMock(side_effect=Exception("Callback error"))
        agent = SynthesisAgent(
            llm_client=mock_llm_client,
            stream_callback=callback
        )
        
        # Should not raise error (error is logged)
        await agent._emit_event("test_event", {"key": "value"})
