"""
Unit tests for the WorkflowOrchestrator.

Tests the core orchestration functionality including:
- Execution plan building
- Parallel execution
- Retry logic
- Error handling
- Dependency management
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.llm.workflow.orchestrator import (
    WorkflowOrchestrator,
    PlanStep,
    ExecutionPlan,
    ExecutionResult,
)
from app.models.workflow import ExecutionContext, RetryConfig


@pytest.fixture
def execution_context():
    """Create a test execution context."""
    return ExecutionContext(
        user_id="test_user",
        session_id="test_session",
        message_id="test_message",
        query="Test query",
        user_datasets=[],
        lock=asyncio.Lock()
    )


@pytest.fixture
def retry_config():
    """Create a test retry configuration."""
    return RetryConfig(
        max_retries=2,
        backoff_factor=1.5,
        initial_delay_seconds=0.1,
        max_delay_seconds=1.0
    )


@pytest.fixture
def orchestrator(retry_config):
    """Create a test orchestrator."""
    return WorkflowOrchestrator(retry_config=retry_config)


class TestExecutionLevelBuilder:
    """Tests for the _build_execution_levels method."""
    
    def test_simple_sequential_plan(self, orchestrator):
        """Test building levels for a simple sequential plan."""
        plan = ExecutionPlan(
            plan_id="test_plan",
            steps=[
                PlanStep(
                    step_id="step1",
                    agent_type="data_retrieval",
                    action="get_datasets",
                    parameters={},
                    depends_on=[]
                ),
                PlanStep(
                    step_id="step2",
                    agent_type="sentiment",
                    action="analyze",
                    parameters={},
                    depends_on=["step1"]
                ),
                PlanStep(
                    step_id="step3",
                    agent_type="synthesis",
                    action="synthesize",
                    parameters={},
                    depends_on=["step2"]
                )
            ]
        )
        
        levels = orchestrator._build_execution_levels(plan)
        
        assert len(levels) == 3
        assert len(levels[0]) == 1
        assert levels[0][0].step_id == "step1"
        assert len(levels[1]) == 1
        assert levels[1][0].step_id == "step2"
        assert len(levels[2]) == 1
        assert levels[2][0].step_id == "step3"
    
    def test_parallel_execution_plan(self, orchestrator):
        """Test building levels for a plan with parallel steps."""
        plan = ExecutionPlan(
            plan_id="test_plan",
            steps=[
                PlanStep(
                    step_id="step1",
                    agent_type="data_retrieval",
                    action="get_datasets",
                    parameters={},
                    depends_on=[]
                ),
                PlanStep(
                    step_id="step2",
                    agent_type="sentiment",
                    action="analyze",
                    parameters={},
                    depends_on=["step1"],
                    can_run_parallel_with=["step3"]
                ),
                PlanStep(
                    step_id="step3",
                    agent_type="topic",
                    action="identify_topics",
                    parameters={},
                    depends_on=["step1"],
                    can_run_parallel_with=["step2"]
                ),
                PlanStep(
                    step_id="step4",
                    agent_type="synthesis",
                    action="synthesize",
                    parameters={},
                    depends_on=["step2", "step3"]
                )
            ]
        )
        
        levels = orchestrator._build_execution_levels(plan)
        
        assert len(levels) == 3
        assert len(levels[0]) == 1
        assert levels[0][0].step_id == "step1"
        assert len(levels[1]) == 2
        assert {s.step_id for s in levels[1]} == {"step2", "step3"}
        assert len(levels[2]) == 1
        assert levels[2][0].step_id == "step4"
    
    def test_circular_dependency_detection(self, orchestrator):
        """Test that circular dependencies are detected."""
        plan = ExecutionPlan(
            plan_id="test_plan",
            steps=[
                PlanStep(
                    step_id="step1",
                    agent_type="agent1",
                    action="action1",
                    parameters={},
                    depends_on=["step2"]
                ),
                PlanStep(
                    step_id="step2",
                    agent_type="agent2",
                    action="action2",
                    parameters={},
                    depends_on=["step1"]
                )
            ]
        )
        
        with pytest.raises(ValueError, match="Circular dependency detected"):
            orchestrator._build_execution_levels(plan)


class TestStepExecution:
    """Tests for step execution methods."""
    
    @pytest.mark.asyncio
    async def test_execute_step_success(self, orchestrator, execution_context):
        """Test successful step execution."""
        step = PlanStep(
            step_id="test_step",
            agent_type="data_retrieval",
            action="get_datasets",
            parameters={"user_id": "test_user"},
            depends_on=[]
        )
        
        result = await orchestrator.execute_step(execution_context, step)
        
        assert result.success is True
        assert result.output is not None
        assert result.error is None
        assert result.duration_ms is not None
    
    @pytest.mark.asyncio
    async def test_execute_parallel_steps(self, orchestrator, execution_context):
        """Test parallel step execution."""
        steps = [
            PlanStep(
                step_id="step1",
                agent_type="sentiment",
                action="analyze",
                parameters={},
                depends_on=[]
            ),
            PlanStep(
                step_id="step2",
                agent_type="topic",
                action="identify_topics",
                parameters={},
                depends_on=[]
            )
        ]
        
        results = await orchestrator.execute_parallel_steps(execution_context, steps)
        
        assert len(results) == 2
        assert "step1" in results
        assert "step2" in results
        assert results["step1"].success is True
        assert results["step2"].success is True


class TestPlanExecution:
    """Tests for complete plan execution."""
    
    @pytest.mark.asyncio
    async def test_execute_simple_plan(self, orchestrator, execution_context):
        """Test executing a simple plan."""
        plan = ExecutionPlan(
            plan_id="test_plan",
            steps=[
                PlanStep(
                    step_id="step1",
                    agent_type="data_retrieval",
                    action="get_datasets",
                    parameters={},
                    depends_on=[]
                ),
                PlanStep(
                    step_id="step2",
                    agent_type="sentiment",
                    action="analyze",
                    parameters={},
                    depends_on=["step1"]
                )
            ]
        )
        
        result = await orchestrator.execute_plan(execution_context, plan)
        
        assert result.success is True
        assert len(result.outputs) == 2
        assert "step1" in result.outputs
        assert "step2" in result.outputs
        assert len(result.failed_steps) == 0
        assert result.execution_time_ms is not None
    
    @pytest.mark.asyncio
    async def test_execute_plan_with_parallel_steps(self, orchestrator, execution_context):
        """Test executing a plan with parallel steps."""
        plan = ExecutionPlan(
            plan_id="test_plan",
            steps=[
                PlanStep(
                    step_id="step1",
                    agent_type="data_retrieval",
                    action="get_datasets",
                    parameters={},
                    depends_on=[]
                ),
                PlanStep(
                    step_id="step2",
                    agent_type="sentiment",
                    action="analyze",
                    parameters={},
                    depends_on=["step1"]
                ),
                PlanStep(
                    step_id="step3",
                    agent_type="topic",
                    action="identify_topics",
                    parameters={},
                    depends_on=["step1"]
                )
            ]
        )
        
        result = await orchestrator.execute_plan(execution_context, plan)
        
        assert result.success is True
        assert len(result.outputs) == 3
        assert len(execution_context.completed_steps) == 3


class TestStreamingEvents:
    """Tests for streaming event emission."""
    
    @pytest.mark.asyncio
    async def test_event_emission(self, execution_context, retry_config):
        """Test that events are emitted correctly."""
        events = []
        
        async def mock_callback(event):
            events.append(event)
        
        orchestrator = WorkflowOrchestrator(
            retry_config=retry_config,
            stream_callback=mock_callback
        )
        
        plan = ExecutionPlan(
            plan_id="test_plan",
            steps=[
                PlanStep(
                    step_id="step1",
                    agent_type="data_retrieval",
                    action="get_datasets",
                    parameters={},
                    depends_on=[]
                )
            ]
        )
        
        await orchestrator.execute_plan(execution_context, plan)
        
        # Check that events were emitted
        assert len(events) > 0
        event_types = [e["event_type"] for e in events]
        assert "plan_start" in event_types
        assert "agent_step_start" in event_types
        assert "agent_step_complete" in event_types
        assert "plan_complete" in event_types


class TestErrorHandling:
    """Tests for error handling and retry logic."""
    
    @pytest.mark.asyncio
    async def test_graceful_failure_handling(self, orchestrator, execution_context):
        """Test that failures are handled gracefully."""
        # Create a plan where we can simulate a failure
        plan = ExecutionPlan(
            plan_id="test_plan",
            steps=[
                PlanStep(
                    step_id="step1",
                    agent_type="data_retrieval",
                    action="get_datasets",
                    parameters={},
                    depends_on=[]
                )
            ]
        )
        
        # Mock the agent execution to raise an exception
        original_execute = orchestrator._execute_agent_action
        
        async def mock_execute_with_failure(context, step):
            raise ValueError("Simulated failure")
        
        orchestrator._execute_agent_action = mock_execute_with_failure
        
        result = await orchestrator.execute_plan(execution_context, plan)
        
        # Restore original method
        orchestrator._execute_agent_action = original_execute
        
        # Check that failure was tracked
        assert result.success is False
        assert len(result.failed_steps) > 0
        assert "step1" in result.failed_steps
