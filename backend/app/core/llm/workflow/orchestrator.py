"""
Workflow Orchestrator for Product Review Analysis Workflow.

This module implements the central orchestration layer that manages execution plans,
coordinates parallel agents, handles retries, and ensures thread-safe state updates.
"""

import asyncio
import time
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass

from app.models.workflow import (
    ExecutionContext,
    RetryConfig,
    StepResult,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PlanStep:
    """
    Represents a single step in an execution plan.
    
    Attributes:
        step_id: Unique identifier for this step
        agent_type: Type of agent to execute (e.g., "data_retrieval", "sentiment")
        action: Specific action to perform
        parameters: Parameters for the action
        depends_on: List of step_ids that must complete before this step
        can_run_parallel_with: List of step_ids that can run concurrently
    """
    step_id: str
    agent_type: str
    action: str
    parameters: Dict[str, Any]
    depends_on: List[str]
    can_run_parallel_with: List[str] = None
    
    def __post_init__(self):
        if self.can_run_parallel_with is None:
            self.can_run_parallel_with = []


@dataclass
class ExecutionPlan:
    """
    Complete execution plan with ordered steps.
    
    Attributes:
        plan_id: Unique identifier for this plan
        steps: List of plan steps to execute
        metadata: Additional plan metadata
    """
    plan_id: str
    steps: List[PlanStep]
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ExecutionResult:
    """
    Result from executing a complete plan.
    
    Attributes:
        success: Whether the plan executed successfully
        outputs: Dictionary mapping step_id to step outputs
        insights: List of insights generated during execution
        failed_steps: Dictionary mapping step_id to error messages
        execution_time_ms: Total execution time in milliseconds
    """
    success: bool
    outputs: Dict[str, Any]
    insights: List[Any]
    failed_steps: Dict[str, str] = None
    execution_time_ms: Optional[float] = None
    
    def __post_init__(self):
        if self.failed_steps is None:
            self.failed_steps = {}


class WorkflowOrchestrator:
    """
    Central orchestration layer for the Product Review Analysis Workflow.
    
    Manages execution plans, coordinates parallel agents, handles retries,
    and ensures thread-safe state updates.
    """
    
    def __init__(
        self,
        retry_config: Optional[RetryConfig] = None,
        stream_callback: Optional[Callable] = None
    ):
        """
        Initialize the workflow orchestrator.
        
        Args:
            retry_config: Configuration for retry logic (uses defaults if not provided)
            stream_callback: Optional callback for streaming events
        """
        self.retry_config = retry_config or RetryConfig()
        self.stream_callback = stream_callback
        logger.info(
            f"Initialized WorkflowOrchestrator with max_retries={self.retry_config.max_retries}"
        )
    
    async def execute_plan(
        self,
        context: ExecutionContext,
        plan: ExecutionPlan
    ) -> ExecutionResult:
        """
        Execute a complete execution plan with dependency management.
        
        This method:
        1. Groups steps by dependency level for parallel execution
        2. Executes each level sequentially
        3. Within each level, executes independent steps in parallel
        4. Tracks results and failures in the execution context
        
        Args:
            context: Execution context with shared state
            plan: Execution plan to execute
            
        Returns:
            ExecutionResult with outputs and insights
        """
        logger.info(f"Executing plan {plan.plan_id} with {len(plan.steps)} steps")
        start_time = time.time()
        
        # Ensure context has a lock for thread-safe updates
        if context.lock is None:
            context.lock = asyncio.Lock()
        
        # Emit plan start event
        await self._emit_event("plan_start", {
            "plan_id": plan.plan_id,
            "total_steps": len(plan.steps),
            "metadata": plan.metadata
        })
        
        try:
            # Group steps by dependency level for parallel execution
            execution_levels = self._build_execution_levels(plan)
            logger.info(f"Built {len(execution_levels)} execution levels")
            
            # Execute each level sequentially
            for level_idx, level_steps in enumerate(execution_levels):
                logger.info(
                    f"Executing level {level_idx + 1}/{len(execution_levels)} "
                    f"with {len(level_steps)} steps"
                )
                
                if len(level_steps) == 1:
                    # Single step - execute directly
                    step = level_steps[0]
                    result = await self.execute_step(context, step)
                    
                    async with context.lock:
                        context.agent_outputs[step.step_id] = result.output
                        if result.success:
                            context.completed_steps.add(step.step_id)
                        else:
                            context.failed_steps[step.step_id] = result.error or "Unknown error"
                else:
                    # Multiple steps - execute in parallel
                    results = await self.execute_parallel_steps(context, level_steps)
                    
                    async with context.lock:
                        for step_id, result in results.items():
                            context.agent_outputs[step_id] = result.output
                            if result.success:
                                context.completed_steps.add(step_id)
                            else:
                                context.failed_steps[step_id] = result.error or "Unknown error"
            
            # Calculate execution time
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Emit plan complete event
            await self._emit_event("plan_complete", {
                "plan_id": plan.plan_id,
                "completed_steps": len(context.completed_steps),
                "failed_steps": len(context.failed_steps),
                "execution_time_ms": execution_time_ms
            })
            
            return ExecutionResult(
                success=len(context.failed_steps) == 0,
                outputs=context.agent_outputs,
                insights=context.insights,
                failed_steps=context.failed_steps,
                execution_time_ms=execution_time_ms
            )
            
        except Exception as e:
            logger.error(f"Plan execution failed: {e}", exc_info=True)
            
            # Emit plan error event
            await self._emit_event("plan_error", {
                "plan_id": plan.plan_id,
                "error": str(e)
            })
            
            return ExecutionResult(
                success=False,
                outputs=context.agent_outputs,
                insights=context.insights,
                failed_steps={"plan_execution": str(e)},
                execution_time_ms=(time.time() - start_time) * 1000
            )
    
    async def execute_step(
        self,
        context: ExecutionContext,
        step: PlanStep
    ) -> StepResult:
        """
        Execute a single workflow step.
        
        This method executes a single step with retry logic and error handling.
        It delegates to _execute_step_with_retry for the actual execution.
        
        Args:
            context: Execution context
            step: Step to execute
            
        Returns:
            StepResult with execution outcome
        """
        logger.info(f"Executing step {step.step_id}: {step.agent_type}.{step.action}")
        
        # Update current step in context
        async with context.lock:
            context.current_step = step.step_id
        
        # Execute with retry logic
        result = await self._execute_step_with_retry(context, step)
        
        return result
    
    async def execute_parallel_steps(
        self,
        context: ExecutionContext,
        steps: List[PlanStep]
    ) -> Dict[str, StepResult]:
        """
        Execute multiple steps in parallel using asyncio.gather.
        
        This method:
        1. Creates tasks for each step
        2. Executes them concurrently with asyncio.gather
        3. Handles exceptions gracefully
        4. Returns results for all steps
        
        Args:
            context: Execution context
            steps: List of steps to execute in parallel
            
        Returns:
            Dictionary mapping step_id to StepResult
        """
        logger.info(f"Executing {len(steps)} steps in parallel")
        
        # Emit parallel execution start event
        await self._emit_event("parallel_execution_start", {
            "step_ids": [step.step_id for step in steps],
            "step_count": len(steps)
        })
        
        # Create tasks for each step
        tasks = [
            self._execute_step_with_retry(context, step)
            for step in steps
        ]
        
        # Execute in parallel with exception handling
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        output = {}
        for step, result in zip(steps, results):
            if isinstance(result, Exception):
                logger.error(f"Step {step.step_id} failed with exception: {result}")
                
                # Track failure in context
                async with context.lock:
                    context.failed_steps[step.step_id] = str(result)
                
                output[step.step_id] = StepResult(
                    success=False,
                    output=None,
                    error=str(result)
                )
            else:
                output[step.step_id] = result
        
        # Emit parallel execution complete event
        await self._emit_event("parallel_execution_complete", {
            "step_ids": [step.step_id for step in steps],
            "successful": sum(1 for r in output.values() if r.success),
            "failed": sum(1 for r in output.values() if not r.success)
        })
        
        return output
    
    def _build_execution_levels(
        self,
        plan: ExecutionPlan
    ) -> List[List[PlanStep]]:
        """
        Group steps by dependency level for parallel execution.
        
        This method analyzes step dependencies and groups steps into levels
        where all steps in a level can be executed in parallel.
        
        Algorithm:
        1. Start with steps that have no dependencies (level 0)
        2. For each subsequent level, find steps whose dependencies are all completed
        3. Continue until all steps are assigned to a level
        4. Detect circular dependencies and raise an error
        
        Args:
            plan: Execution plan with steps
            
        Returns:
            List of levels, where each level is a list of steps that can run in parallel
            
        Raises:
            ValueError: If circular dependencies are detected
        """
        levels = []
        completed = set()
        step_map = {step.step_id: step for step in plan.steps}
        
        while len(completed) < len(plan.steps):
            # Find steps whose dependencies are all completed
            current_level = [
                step for step in plan.steps
                if step.step_id not in completed
                and all(dep in completed for dep in step.depends_on)
            ]
            
            if not current_level:
                # No progress made - circular dependency detected
                remaining_steps = [s.step_id for s in plan.steps if s.step_id not in completed]
                raise ValueError(
                    f"Circular dependency detected in execution plan. "
                    f"Remaining steps: {remaining_steps}"
                )
            
            levels.append(current_level)
            completed.update(step.step_id for step in current_level)
            
            logger.debug(
                f"Level {len(levels)}: {len(current_level)} steps - "
                f"{[s.step_id for s in current_level]}"
            )
        
        return levels
    
    async def _execute_step_with_retry(
        self,
        context: ExecutionContext,
        step: PlanStep
    ) -> StepResult:
        """
        Execute a step with retry logic and exponential backoff.
        
        This method implements the retry strategy defined in RetryConfig:
        1. Attempts execution up to max_retries times
        2. Uses exponential backoff between retries
        3. Tracks failures and logs errors
        4. Returns result or error after all retries exhausted
        
        Args:
            context: Execution context
            step: Step to execute
            
        Returns:
            StepResult with execution outcome
        """
        last_error = None
        delay = self.retry_config.initial_delay_seconds
        
        for attempt in range(self.retry_config.max_retries + 1):
            try:
                # Emit step start event
                await self._emit_event("agent_step_start", {
                    "step_id": step.step_id,
                    "agent_type": step.agent_type,
                    "action": step.action,
                    "attempt": attempt + 1,
                    "max_attempts": self.retry_config.max_retries + 1
                })
                
                start_time = time.time()
                
                # Execute the step (placeholder - actual agent execution will be implemented later)
                output = await self._execute_agent_action(context, step)
                
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Emit step complete event
                await self._emit_event("agent_step_complete", {
                    "step_id": step.step_id,
                    "agent_type": step.agent_type,
                    "action": step.action,
                    "success": True,
                    "duration_ms": duration_ms
                })
                
                logger.info(
                    f"Step {step.step_id} completed successfully in {duration_ms}ms "
                    f"(attempt {attempt + 1})"
                )
                
                return StepResult(
                    success=True,
                    output=output,
                    error=None,
                    duration_ms=duration_ms
                )
                
            except Exception as e:
                last_error = e
                logger.warning(
                    f"Step {step.step_id} failed on attempt {attempt + 1}: {e}"
                )
                
                # If this was the last attempt, don't retry
                if attempt >= self.retry_config.max_retries:
                    break
                
                # Wait before retrying with exponential backoff
                await asyncio.sleep(min(delay, self.retry_config.max_delay_seconds))
                delay *= self.retry_config.backoff_factor
        
        # All retries exhausted
        error_msg = f"Step failed after {self.retry_config.max_retries + 1} attempts: {last_error}"
        logger.error(f"Step {step.step_id}: {error_msg}")
        
        # Emit step error event
        await self._emit_event("agent_step_error", {
            "step_id": step.step_id,
            "agent_type": step.agent_type,
            "action": step.action,
            "error": str(last_error),
            "attempts": self.retry_config.max_retries + 1
        })
        
        return StepResult(
            success=False,
            output=None,
            error=error_msg
        )
    
    async def _execute_agent_action(
        self,
        context: ExecutionContext,
        step: PlanStep
    ) -> Any:
        """
        Execute the actual agent action.
        
        This is a placeholder method that will be implemented to call
        the appropriate agent based on step.agent_type and step.action.
        
        Args:
            context: Execution context
            step: Step to execute
            
        Returns:
            Output from the agent action
            
        Raises:
            NotImplementedError: This is a placeholder for future implementation
        """
        # TODO: Implement actual agent execution
        # This will be implemented when individual agents are created
        logger.debug(
            f"Executing agent action: {step.agent_type}.{step.action} "
            f"with parameters: {step.parameters}"
        )
        
        # For now, return a placeholder result
        return {
            "agent_type": step.agent_type,
            "action": step.action,
            "parameters": step.parameters,
            "status": "placeholder_execution"
        }
    
    async def _emit_event(
        self,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> None:
        """
        Emit a streaming event if callback is configured.
        
        This method sends events to the stream_callback for real-time updates.
        Events include:
        - plan_start: Plan execution started
        - plan_complete: Plan execution completed
        - plan_error: Plan execution failed
        - parallel_execution_start: Parallel execution started
        - parallel_execution_complete: Parallel execution completed
        - agent_step_start: Agent step started
        - agent_step_complete: Agent step completed
        - agent_step_error: Agent step failed
        - content: Content chunk for streaming response
        
        Args:
            event_type: Type of event
            event_data: Event data payload
        """
        if self.stream_callback:
            try:
                await self.stream_callback({
                    "event_type": event_type,
                    "data": event_data,
                    "timestamp": time.time()
                })
            except Exception as e:
                logger.error(f"Error emitting event {event_type}: {e}")
