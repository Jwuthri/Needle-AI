"""
Unit tests for PlannerAgent.

Tests the iterative ReAct planning logic, adaptive planning, and parallel action identification.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.core.llm.workflow.agents.planner import PlannerAgent
from app.models.workflow import ExecutionContext, NextAction, ThoughtStep, Insight


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    client = AsyncMock()
    return client


@pytest.fixture
def planner_agent(mock_llm_client):
    """Create a PlannerAgent instance with mock LLM client."""
    return PlannerAgent(llm_client=mock_llm_client)


@pytest.fixture
def execution_context():
    """Create a basic execution context."""
    return ExecutionContext(
        user_id="test_user",
        session_id="test_session",
        message_id="test_message",
        query="What are my product gaps?",
        user_datasets=[
            {
                "dataset_id": "ds1",
                "table_name": "reviews",
                "row_count": 100
            }
        ]
    )


@pytest.mark.asyncio
async def test_determine_next_action_initial(planner_agent, mock_llm_client, execution_context):
    """Test determining the first action with no previous results."""
    # Mock LLM response
    mock_llm_client.generate_completion.return_value = """```json
{
    "thought": {
        "step_id": "thought_1",
        "rationale": "Need to get user datasets first",
        "alternatives_considered": ["Query reviews directly"],
        "expected_outcome": "Learn about available datasets"
    },
    "action": {
        "action_id": "action_1",
        "agent_type": "data_retrieval",
        "action": "get_user_datasets_with_eda",
        "parameters": {"user_id": "test_user"},
        "can_run_parallel_with": [],
        "is_final": false
    }
}
```"""
    
    # Mock database session
    mock_db = AsyncMock()
    
    # Call determine_next_action
    next_action = await planner_agent.determine_next_action(
        query="What are my product gaps?",
        context=execution_context,
        previous_results={},
        db=mock_db
    )
    
    # Verify the action
    assert next_action.agent_type == "data_retrieval"
    assert next_action.action == "get_user_datasets_with_eda"
    assert next_action.is_final is False
    assert next_action.thought.step_id == "thought_1"


@pytest.mark.asyncio
async def test_determine_next_action_with_data(planner_agent, mock_llm_client, execution_context):
    """Test determining next action after data retrieval."""
    # Mock LLM response for analysis action
    mock_llm_client.generate_completion.return_value = """```json
{
    "thought": {
        "step_id": "thought_2",
        "rationale": "Have reviews, now analyze sentiment",
        "alternatives_considered": ["Topic modeling first"],
        "expected_outcome": "Identify sentiment patterns"
    },
    "action": {
        "action_id": "action_2",
        "agent_type": "sentiment",
        "action": "analyze_sentiment",
        "parameters": {},
        "can_run_parallel_with": ["action_topic"],
        "is_final": false
    }
}
```"""
    
    # Add previous results
    previous_results = {
        "action_1": {
            "reviews": [{"id": "r1", "text": "Great product"}] * 50
        }
    }
    
    mock_db = AsyncMock()
    
    # Call determine_next_action
    next_action = await planner_agent.determine_next_action(
        query="What are my product gaps?",
        context=execution_context,
        previous_results=previous_results,
        db=mock_db
    )
    
    # Verify the action
    assert next_action.agent_type == "sentiment"
    assert next_action.action == "analyze_sentiment"
    assert "action_topic" in next_action.can_run_parallel_with


@pytest.mark.asyncio
async def test_is_query_complete_with_insights(planner_agent, mock_llm_client, execution_context):
    """Test query completion detection with sufficient insights."""
    # Add insights to context
    execution_context.insights = [
        Insight(
            source_agent="sentiment",
            insight_text="Negative sentiment on performance",
            severity_score=0.8,
            confidence_score=0.9,
            supporting_reviews=["r1", "r2"]
        ),
        Insight(
            source_agent="topic_modeling",
            insight_text="Main complaint: slow UI",
            severity_score=0.85,
            confidence_score=0.88,
            supporting_reviews=["r3", "r4"]
        )
    ]
    
    # Mock LLM response indicating completion
    mock_llm_client.generate_completion.return_value = """```json
{
    "is_complete": true,
    "reasoning": "We have sentiment and topic insights covering the main gaps",
    "missing_aspects": []
}
```"""
    
    # Check completion
    is_complete = await planner_agent.is_query_complete(
        query="What are my product gaps?",
        context=execution_context
    )
    
    assert is_complete is True


@pytest.mark.asyncio
async def test_is_query_complete_insufficient_data(planner_agent, mock_llm_client, execution_context):
    """Test query completion detection with insufficient insights."""
    # Mock LLM response indicating not complete
    mock_llm_client.generate_completion.return_value = """```json
{
    "is_complete": false,
    "reasoning": "No insights collected yet",
    "missing_aspects": ["sentiment analysis", "topic modeling"]
}
```"""
    
    # Check completion
    is_complete = await planner_agent.is_query_complete(
        query="What are my product gaps?",
        context=execution_context
    )
    
    assert is_complete is False


@pytest.mark.asyncio
async def test_adaptive_planning_empty_results(planner_agent, mock_llm_client, execution_context):
    """Test adaptive planning when previous query returned no results."""
    # Mock LLM response
    mock_llm_client.generate_completion.return_value = """```json
{
    "thought": {
        "step_id": "thought_2",
        "rationale": "Previous query returned no results, trying broader search",
        "alternatives_considered": [],
        "expected_outcome": "Get some reviews"
    },
    "action": {
        "action_id": "action_2",
        "agent_type": "data_retrieval",
        "action": "query_reviews",
        "parameters": {"rating_filter": "<=2", "limit": 100},
        "can_run_parallel_with": [],
        "is_final": false
    }
}
```"""
    
    # Previous results with empty data
    previous_results = {
        "action_1": {
            "reviews": []
        }
    }
    
    mock_db = AsyncMock()
    
    # Call determine_next_action
    next_action = await planner_agent.determine_next_action(
        query="What are my product gaps?",
        context=execution_context,
        previous_results=previous_results,
        db=mock_db
    )
    
    # Verify adaptive adjustments were applied
    # The rating_filter should be removed due to empty results
    assert "rating_filter" not in next_action.parameters or next_action.parameters.get("rating_filter") is None


@pytest.mark.asyncio
async def test_identify_parallel_actions(planner_agent, execution_context):
    """Test identification of parallel actions."""
    # Add some reviews to context
    execution_context.agent_outputs = {
        "action_1": {
            "reviews": [{"id": "r1"}] * 50
        }
    }
    
    # Create a sentiment action
    current_action = NextAction(
        action_id="action_sentiment",
        agent_type="sentiment",
        action="analyze_sentiment",
        parameters={},
        thought=ThoughtStep(
            step_id="thought_1",
            rationale="Analyze sentiment",
            alternatives_considered=[],
            expected_outcome="Sentiment insights"
        ),
        can_run_parallel_with=[],
        is_final=False
    )
    
    # Identify parallel actions
    parallel_actions = await planner_agent.identify_parallel_actions(
        query="What are my product gaps?",
        context=execution_context,
        current_action=current_action
    )
    
    # Should suggest topic_modeling, anomaly_detection, and summary
    assert len(parallel_actions) > 0
    agent_types = [action.agent_type for action in parallel_actions]
    assert "topic_modeling" in agent_types
    assert "anomaly_detection" in agent_types


def test_analyze_previous_results_empty(planner_agent, execution_context):
    """Test analysis of previous results with empty data."""
    previous_results = {
        "action_1": {
            "reviews": []
        }
    }
    
    adaptation_context = planner_agent._analyze_previous_results(
        previous_results,
        execution_context
    )
    
    assert adaptation_context["has_empty_results"] is True
    assert "action_1" in adaptation_context["empty_result_actions"]
    assert len(adaptation_context["adaptations_needed"]) > 0


def test_analyze_previous_results_with_data(planner_agent, execution_context):
    """Test analysis of previous results with data."""
    previous_results = {
        "action_1": {
            "reviews": [{"id": "r1"}] * 50
        }
    }
    
    adaptation_context = planner_agent._analyze_previous_results(
        previous_results,
        execution_context
    )
    
    assert adaptation_context["has_data"] is True
    assert adaptation_context["data_volume"] == 50
    assert adaptation_context["has_empty_results"] is False


def test_apply_adaptive_adjustments(planner_agent, execution_context):
    """Test application of adaptive adjustments to action parameters."""
    # Create adaptation context indicating empty results
    adaptation_context = {
        "has_empty_results": True,
        "empty_result_actions": ["action_1"]
    }
    
    # Create an action with restrictive filters
    next_action = NextAction(
        action_id="action_2",
        agent_type="data_retrieval",
        action="query_reviews",
        parameters={
            "rating_filter": "<=2",
            "date_range": ("2024-01-01", "2024-01-31"),
            "limit": 100
        },
        thought=ThoughtStep(
            step_id="thought_2",
            rationale="Query reviews",
            alternatives_considered=[],
            expected_outcome="Get reviews"
        ),
        can_run_parallel_with=[],
        is_final=False
    )
    
    # Apply adjustments
    adjusted_action = planner_agent._apply_adaptive_adjustments(
        next_action,
        adaptation_context,
        execution_context
    )
    
    # Verify filters were removed
    assert "rating_filter" not in adjusted_action.parameters
    assert "date_range" not in adjusted_action.parameters
    assert adjusted_action.parameters["limit"] == 1000
