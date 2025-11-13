"""
Product Review Analysis Workflow using LlamaIndex.

This workflow implements the multi-agent product review analysis system with:
- Intelligent query routing via Coordinator Agent
- Adaptive planning with ReAct pattern via Planner Agent
- Parallel agent execution via Orchestrator
- Comprehensive execution tracking via Chat Message Steps
- Conversational context management for follow-up queries
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, List, Callable

from llama_index.core.workflow import (
    Workflow,
    StartEvent,
    StopEvent,
    Event,
    step,
    Context,
)

from app.utils.logging import get_logger
from app.models.chat import ChatResponse

logger = get_logger(__name__)


# Define custom events for workflow steps
class CoordinatorCompleteEvent(Event):
    """Event triggered after coordinator classifies the query."""
    query: str
    user_id: str
    classification: Dict[str, Any]
    context: Dict[str, Any]


class PlanningCompleteEvent(Event):
    """Event triggered after planner determines next action."""
    query: str
    user_id: str
    context: Dict[str, Any]
    next_action: Dict[str, Any]


class ActionExecutedEvent(Event):
    """Event triggered after an action is executed."""
    query: str
    user_id: str
    context: Dict[str, Any]
    action_result: Dict[str, Any]


class QueryCompleteEvent(Event):
    """Event triggered when query processing is complete."""
    query: str
    user_id: str
    context: Dict[str, Any]


class ProductReviewAnalysisWorkflow(Workflow):
    """
    Product Review Analysis Workflow using LlamaIndex.
    
    Multi-step Flow:
    1. Start -> Load Context (if follow-up query)
    2. Coordinator -> Classify query complexity
    3. If simple -> Direct response
    4. If complex -> Iterative Planning Loop:
       a. Planner determines next action
       b. Execute action (possibly in parallel)
       c. Check if query is complete
       d. Repeat until complete
    5. Synthesis -> Combine all insights
    6. Save Context -> Store for follow-up queries
    """

    def __init__(
        self,
        user_id: str = None,
        session_id: str = None,
        assistant_message_id: int = None,
        stream_callback: Optional[Callable] = None,
        **kwargs
    ):
        """
        Initialize the Product Review Analysis Workflow.
        
        Args:
            user_id: User ID for data access
            session_id: Session ID for conversation context
            assistant_message_id: ID of assistant message for saving steps to DB
            stream_callback: Callback function for streaming events
            **kwargs: Additional arguments for Workflow base class
        """
        super().__init__(**kwargs)
        self.user_id = user_id
        self.session_id = session_id
        self.assistant_message_id = assistant_message_id
        self.stream_callback = stream_callback
        self.step_counter = 0
    
    def _emit_event(self, event_type: str, data: dict):
        """Emit a streaming event if callback is provided."""
        if self.stream_callback:
            try:
                event = {
                    "type": event_type,
                    "data": data
                }
                logger.debug(f"Emitting event: {event_type}")
                self.stream_callback(event)
            except Exception as e:
                logger.warning(f"Failed to emit event: {e}")
    
    async def _track_step_in_db(
        self,
        agent_name: str,
        step_order: int,
        content: Any = None,
        is_structured: bool = False,
        thought: Optional[str] = None,
        tool_call: Optional[Dict[str, Any]] = None
    ):
        """
        Track workflow step in database immediately.
        
        This method ensures comprehensive tracking of all agent actions:
        - Thoughts (reasoning before action)
        - Tool calls (with parameters and results)
        - Structured outputs (Pydantic models, dicts)
        - Text predictions (LLM responses)
        
        Args:
            agent_name: Name of the agent executing the step
            step_order: Order of the step in the workflow
            content: Content to store (structured output or prediction)
            is_structured: Whether content is structured (JSON) or text
            thought: Optional reasoning trace from the agent
            tool_call: Optional tool call information (name, parameters, result)
            
        Returns:
            The created ChatMessageStep object, or None if tracking failed
        """
        if not self.assistant_message_id:
            logger.warning(f"Cannot save step {agent_name} - no assistant_message_id set")
            return None
            
        try:
            from app.database.session import get_async_session
            from app.database.repositories.chat_message_step import ChatMessageStepRepository
            
            async with get_async_session() as db:
                logger.info(f"[WORKFLOW DB] Saving step: {agent_name} (order: {step_order})")
                
                # Prepare step data
                step_data = {
                    "message_id": self.assistant_message_id,
                    "agent_name": agent_name,
                    "step_order": step_order,
                    "thought": thought
                }
                
                # Add content based on type
                if tool_call:
                    step_data["tool_call"] = tool_call
                elif is_structured and content is not None:
                    # Ensure content is JSON-serializable
                    if hasattr(content, 'dict'):
                        step_data["structured_output"] = content.dict()
                    elif isinstance(content, dict):
                        step_data["structured_output"] = content
                    else:
                        step_data["structured_output"] = {"data": str(content)}
                elif content is not None:
                    step_data["prediction"] = content if isinstance(content, str) else str(content)
                
                step = await ChatMessageStepRepository.create(db=db, **step_data)
                await db.commit()
                logger.info(f"[WORKFLOW DB] ✅ Saved step: {agent_name} (id: {step.id})")
                return step
        except Exception as e:
            logger.error(f"[WORKFLOW DB] Failed to save step {agent_name}: {e}", exc_info=True)
            return None
    
    def _get_next_step_order(self) -> int:
        """Get the next step order number."""
        self.step_counter += 1
        return self.step_counter
    
    async def _track_tool_call(
        self,
        agent_name: str,
        tool_name: str,
        parameters: Dict[str, Any],
        result: Any,
        thought: Optional[str] = None
    ):
        """
        Track a tool call as a workflow step.
        
        Args:
            agent_name: Name of the agent making the tool call
            tool_name: Name of the tool being called
            parameters: Parameters passed to the tool
            result: Result returned by the tool
            thought: Optional reasoning about why this tool was called
            
        Returns:
            The created ChatMessageStep object
        """
        step_order = self._get_next_step_order()
        
        # Emit tool call event
        self._emit_event("tool_call", {
            "agent_name": agent_name,
            "tool_name": tool_name,
            "parameters": parameters,
            "step_order": step_order
        })
        
        # Prepare tool call data
        tool_call_data = {
            "tool_name": tool_name,
            "parameters": parameters,
            "result": result if isinstance(result, (dict, list, str, int, float, bool, type(None))) else str(result)
        }
        
        # Track in database
        step = await self._track_step_in_db(
            agent_name=agent_name,
            step_order=step_order,
            tool_call=tool_call_data,
            thought=thought
        )
        
        # Emit tool call complete event
        self._emit_event("tool_call_complete", {
            "agent_name": agent_name,
            "tool_name": tool_name,
            "step_order": step_order
        })
        
        return step

    @step
    async def start_workflow(self, ctx: Context, ev: StartEvent) -> CoordinatorCompleteEvent:
        """
        Step 1: Initialize workflow and load conversational context.
        
        This step:
        - Loads previous context if this is a follow-up query
        - Initializes execution context
        - Prepares for coordinator step
        
        Requirements: 12.1, 12.2, 12.3
        """
        query = ev.query
        logger.info(f"🚀 Product Review Analysis Workflow started")
        logger.info(f"   └─ Query: {query[:100]}{'...' if len(query) > 100 else ''}")
        
        # Initialize execution context
        execution_context = {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "query": query,
            "user_datasets": [],
            "agent_outputs": {},
            "insights": [],
            "completed_steps": set(),
            "failed_steps": {},
            "conversation_history": ev.get("conversation_history", []),
            "cached_results": {},
        }
        
        # Load conversational context if available
        try:
            from app.core.llm.workflow.context_manager import ConversationalContextManager
            from app.services.redis_client import RedisClient
            
            # Initialize Redis client
            redis_client = RedisClient()
            await redis_client.connect()
            
            # Initialize context manager with Redis client
            context_manager = ConversationalContextManager(redis_client=redis_client)
            
            # Load previous context for this session
            previous_context = await context_manager.load_context(self.session_id)
            
            if previous_context:
                logger.info("📚 Loaded previous context for follow-up query")
                # Merge cached results from previous context
                execution_context["cached_results"] = previous_context.cached_results or {}
                # Store previous insights for reference
                if hasattr(previous_context, 'insights'):
                    execution_context["previous_insights"] = previous_context.insights
                # Store last visualization data for "show me more" queries
                if previous_context.last_visualization_data:
                    execution_context["last_visualization_data"] = previous_context.last_visualization_data
                
                logger.info(f"   └─ Loaded {len(previous_context.conversation_history)} previous turns")
                logger.info(f"   └─ Cached results: {len(execution_context['cached_results'])} items")
            else:
                logger.info("📝 No previous context found - starting fresh conversation")
            
            # Store context manager for later use
            await ctx.set("context_manager", context_manager)
            
        except Exception as e:
            logger.warning(f"Could not load previous context: {e}")
            logger.debug("Continuing without previous context", exc_info=True)
            # Store None to indicate context manager is not available
            await ctx.set("context_manager", None)
        
        # Store context in workflow context
        await ctx.set("execution_context", execution_context)
        
        # Proceed to coordinator
        return CoordinatorCompleteEvent(
            query=query,
            user_id=self.user_id,
            classification={},  # Will be filled by coordinator
            context=execution_context
        )

    @step
    async def coordinator_step(
        self,
        ctx: Context,
        ev: CoordinatorCompleteEvent
    ) -> PlanningCompleteEvent | StopEvent:
        """
        Step 2: Coordinator Agent classifies query and routes appropriately.
        
        This step:
        - Classifies query complexity (simple/medium/complex)
        - Determines if data retrieval is needed
        - Routes simple queries to direct response
        - Delegates complex queries to Planner Agent
        """
        step_id = str(uuid.uuid4())
        step_order = self._get_next_step_order()
        
        self._emit_event("agent_step_start", {
            "agent_name": "Coordinator",
            "step_id": step_id,
            "timestamp": datetime.utcnow().isoformat(),
            "step_order": step_order
        })
        
        logger.info("▶️  Step: Coordinator - Query Classification")
        
        try:
            # Import coordinator agent
            from app.optimal_workflow.agents.coordinator_agent import CoordinatorAgent
            
            # Check if this is a follow-up query
            is_follow_up = False
            context_manager = await ctx.get("context_manager", default=None)
            
            if context_manager and ev.context.get("conversation_history"):
                try:
                    from app.models.workflow import ExecutionContext
                    
                    # Create minimal ExecutionContext for follow-up detection
                    previous_context = ExecutionContext(
                        user_id=ev.user_id,
                        session_id=self.session_id,
                        message_id="",
                        query="",
                        conversation_history=ev.context.get("conversation_history", [])
                    )
                    
                    is_follow_up = await context_manager.is_follow_up_query(
                        query=ev.query,
                        previous_context=previous_context
                    )
                    
                    if is_follow_up:
                        logger.info("🔗 Detected follow-up query - will use previous context")
                except Exception as e:
                    logger.debug(f"Could not detect follow-up query: {e}")
            
            coordinator = CoordinatorAgent()
            classification = await coordinator.classify_query(
                query=ev.query,
                user_id=ev.user_id
            )
            
            # Add follow-up flag to classification
            classification["is_follow_up"] = is_follow_up
            
            logger.info(f"✓ Query classified as: {classification.get('complexity', 'unknown')}")
            if is_follow_up:
                logger.info("   └─ Follow-up query detected")
            
            # Extract thought and action from classification
            thought = classification.get("reasoning") or f"Analyzing query complexity and determining routing strategy"
            
            # Emit completion event
            self._emit_event("agent_step_complete", {
                "step_id": step_id,
                "agent_name": "Coordinator",
                "content": classification,
                "is_structured": True,
                "step_order": step_order
            })
            
            # Save to database with thought and structured output
            await self._track_step_in_db(
                agent_name="Coordinator",
                step_order=step_order,
                content=classification,
                is_structured=True,
                thought=thought
            )
            
            # Update context
            execution_context = ev.context
            execution_context["classification"] = classification
            execution_context["completed_steps"].add("coordinator")
            await ctx.set("execution_context", execution_context)
            
            # Route based on complexity
            if classification.get("complexity") == "simple":
                # Handle simple query directly
                logger.info("🎯 Simple query detected - generating direct response")
                
                # Generate simple response
                response = await self._generate_simple_response(ev.query, classification)
                
                # Stream the response
                for chunk in self._chunk_text(response):
                    self._emit_event("content", {"content": chunk})
                
                # Update assistant message
                await self._update_assistant_message(response)
                
                # Emit completion
                chat_response = ChatResponse(
                    message=response,
                    session_id=self.session_id,
                    message_id=str(self.assistant_message_id) if self.assistant_message_id else str(uuid.uuid4()),
                    timestamp=datetime.utcnow(),
                    completed_at=datetime.utcnow(),
                    metadata={"workflow": "product_review_analysis", "complexity": "simple"}
                )
                self._emit_event("complete", chat_response.dict())
                
                return StopEvent(result=response)
            
            else:
                # Proceed to planning for complex queries
                return PlanningCompleteEvent(
                    query=ev.query,
                    user_id=ev.user_id,
                    context=execution_context,
                    next_action={}
                )
                
        except Exception as e:
            logger.error(f"Error in coordinator step: {e}", exc_info=True)
            raise

    async def _generate_simple_response(self, query: str, classification: Dict) -> str:
        """Generate a simple response for non-data queries."""
        # This would use a simple LLM call for general questions
        return f"I understand you're asking: {query}. However, this appears to be a general question that doesn't require data analysis."
    
    def _chunk_text(self, text: str, chunk_size: int = 30) -> List[str]:
        """Split text into chunks for streaming."""
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
    
    async def _update_assistant_message(self, content: str):
        """Update the assistant message with final content."""
        if not self.assistant_message_id:
            return
        
        try:
            from app.database.session import get_async_session
            from app.database.repositories.chat_message import ChatMessageRepository
            
            async with get_async_session() as db:
                assistant_msg = await ChatMessageRepository.get_by_id(db, self.assistant_message_id)
                if assistant_msg:
                    assistant_msg.content = content
                    assistant_msg.completed_at = datetime.utcnow()
                    await db.commit()
                    logger.info(f"Updated assistant message {self.assistant_message_id}")
        except Exception as e:
            logger.error(f"Failed to update assistant message: {e}", exc_info=True)


if __name__ == "__main__":
    # Test the workflow
    workflow = ProductReviewAnalysisWorkflow()
    workflow.draw_steps("product_review_workflow.html")

    @step
    async def iterative_planning_loop(
        self,
        ctx: Context,
        ev: PlanningCompleteEvent
    ) -> ActionExecutedEvent | QueryCompleteEvent:
        """
        Step 3: Iterative Planning Loop with ReAct pattern.
        
        This step:
        - Calls Planner Agent to determine next action
        - Executes the action (possibly in parallel with others)
        - Checks if query is complete
        - Repeats until all necessary information is gathered
        """
        step_id = str(uuid.uuid4())
        step_order = self._get_next_step_order()
        
        self._emit_event("agent_step_start", {
            "agent_name": "Planner",
            "step_id": step_id,
            "timestamp": datetime.utcnow().isoformat(),
            "step_order": step_order
        })
        
        logger.info("▶️  Step: Planner - Determine Next Action")
        
        try:
            # Import planner agent
            from app.optimal_workflow.agents.planner_agent import PlannerAgent
            
            execution_context = ev.context
            planner = PlannerAgent()
            
            # Get context-aware planning hints if this is a follow-up query
            planning_context = {}
            context_manager = await ctx.get("context_manager", default=None)
            
            if context_manager and execution_context.get("classification", {}).get("is_follow_up"):
                try:
                    planning_context = await context_manager.get_context_for_planning(
                        session_id=self.session_id,
                        current_query=ev.query
                    )
                    
                    if planning_context.get("suggested_shortcuts"):
                        logger.info(f"💡 Planning shortcuts available: {planning_context['suggested_shortcuts']}")
                    
                    # Add planning context to execution context for planner to use
                    execution_context["planning_hints"] = planning_context
                    
                except Exception as e:
                    logger.debug(f"Could not get planning context: {e}")
            
            # Determine next action based on current state
            next_action = await planner.determine_next_action(
                query=ev.query,
                context=execution_context,
                previous_results=execution_context.get("agent_outputs", {})
            )
            
            logger.info(f"✓ Next action determined: {next_action.get('agent_type', 'unknown')}")
            
            # Extract thought from next_action
            thought_data = next_action.get("thought", {})
            thought_text = thought_data.get("rationale") or "Determining next action based on current context"
            
            # Emit completion event
            self._emit_event("agent_step_complete", {
                "step_id": step_id,
                "agent_name": "Planner",
                "content": next_action,
                "is_structured": True,
                "step_order": step_order
            })
            
            # Save to database with thought and structured output
            await self._track_step_in_db(
                agent_name="Planner",
                step_order=step_order,
                content=next_action,
                is_structured=True,
                thought=thought_text
            )
            
            # Update context
            execution_context["completed_steps"].add(f"planner_{step_order}")
            await ctx.set("execution_context", execution_context)
            
            # Check if this is the final action (synthesis)
            if next_action.get("is_final", False):
                logger.info("🏁 Final action detected - proceeding to synthesis")
                return QueryCompleteEvent(
                    query=ev.query,
                    user_id=ev.user_id,
                    context=execution_context
                )
            
            # Execute the action
            return ActionExecutedEvent(
                query=ev.query,
                user_id=ev.user_id,
                context=execution_context,
                action_result=next_action
            )
            
        except Exception as e:
            logger.error(f"Error in planning step: {e}", exc_info=True)
            raise

    @step
    async def execute_action(
        self,
        ctx: Context,
        ev: ActionExecutedEvent
    ) -> PlanningCompleteEvent | QueryCompleteEvent:
        """
        Step 4: Execute the planned action.
        
        This step:
        - Executes the action determined by the Planner
        - Handles parallel execution if multiple actions can run concurrently
        - Stores results in execution context
        - Returns to planning loop or proceeds to synthesis
        """
        action = ev.action_result
        agent_type = action.get("agent_type")
        action_id = action.get("action_id")
        
        step_id = str(uuid.uuid4())
        step_order = self._get_next_step_order()
        
        self._emit_event("agent_step_start", {
            "agent_name": agent_type,
            "step_id": step_id,
            "timestamp": datetime.utcnow().isoformat(),
            "step_order": step_order
        })
        
        logger.info(f"▶️  Step: Execute Action - {agent_type}")
        
        try:
            execution_context = ev.context
            
            # Check if there are parallel actions
            parallel_actions = action.get("can_run_parallel_with", [])
            
            if parallel_actions:
                # Execute in parallel
                result = await self._execute_parallel_actions(
                    action,
                    parallel_actions,
                    execution_context,
                    step_order
                )
            else:
                # Execute single action
                result = await self._execute_single_action(
                    action,
                    execution_context,
                    step_order
                )
            
            # Store result in context
            execution_context["agent_outputs"][action_id] = result
            execution_context["completed_steps"].add(action_id)
            
            # Extract insights if present
            if isinstance(result, dict) and "insights" in result:
                execution_context["insights"].extend(result["insights"])
            
            await ctx.set("execution_context", execution_context)
            
            # Prepare result summary for tracking
            result_summary = {
                "action_id": action_id,
                "status": "completed",
                "result_type": type(result).__name__
            }
            
            # Add insights count if present
            if isinstance(result, dict) and "insights" in result:
                result_summary["insights_count"] = len(result["insights"])
            
            # Emit completion event
            self._emit_event("agent_step_complete", {
                "step_id": step_id,
                "agent_name": agent_type,
                "content": result_summary,
                "is_structured": True,
                "step_order": step_order
            })
            
            # Save to database with result summary
            await self._track_step_in_db(
                agent_name=agent_type,
                step_order=step_order,
                content=result_summary,
                is_structured=True,
                thought=f"Executed {action.get('action', 'unknown')} action"
            )
            
            # Check if query is complete
            from app.optimal_workflow.agents.planner_agent import PlannerAgent
            planner = PlannerAgent()
            
            is_complete = await planner.is_query_complete(
                query=ev.query,
                context=execution_context
            )
            
            if is_complete:
                logger.info("✓ Query processing complete - proceeding to synthesis")
                return QueryCompleteEvent(
                    query=ev.query,
                    user_id=ev.user_id,
                    context=execution_context
                )
            else:
                logger.info("↻ Query not complete - returning to planning")
                return PlanningCompleteEvent(
                    query=ev.query,
                    user_id=ev.user_id,
                    context=execution_context,
                    next_action={}
                )
                
        except Exception as e:
            logger.error(f"Error executing action: {e}", exc_info=True)
            # Store error and continue
            execution_context["failed_steps"][action_id] = str(e)
            await ctx.set("execution_context", execution_context)
            
            # Return to planning to adapt
            return PlanningCompleteEvent(
                query=ev.query,
                user_id=ev.user_id,
                context=execution_context,
                next_action={}
            )

    async def _execute_single_action(
        self,
        action: Dict[str, Any],
        context: Dict[str, Any],
        step_order: int
    ) -> Dict[str, Any]:
        """
        Execute a single agent action and track tool calls.
        
        This method routes to the appropriate agent and tracks any tool calls
        made during execution as separate workflow steps.
        """
        agent_type = action.get("agent_type")
        parameters = action.get("parameters", {})
        action_name = action.get("action")
        
        logger.info(f"Executing {agent_type}.{action_name} with parameters: {parameters}")
        
        # Route to appropriate agent
        if agent_type == "data_retrieval":
            from app.optimal_workflow.agents.data_retrieval_agent import DataRetrievalAgent
            agent = DataRetrievalAgent(user_id=context["user_id"])
            
            if action_name == "get_user_datasets_with_eda":
                # Track tool call
                result = await agent.get_user_datasets_with_eda(context["user_id"])
                await self._track_tool_call(
                    agent_name="DataRetrieval",
                    tool_name="get_user_datasets_with_eda",
                    parameters={"user_id": context["user_id"]},
                    result={"dataset_count": len(result) if isinstance(result, list) else 0},
                    thought="Retrieving user datasets with EDA metadata to understand available data"
                )
            elif action_name == "query_reviews":
                # Track tool call
                result = await agent.query_reviews(**parameters)
                await self._track_tool_call(
                    agent_name="DataRetrieval",
                    tool_name="query_reviews",
                    parameters=parameters,
                    result={"review_count": len(result.get("reviews", [])) if isinstance(result, dict) else 0},
                    thought=f"Querying reviews with filters: {parameters}"
                )
            elif action_name == "semantic_search":
                # Track tool call
                result = await agent.semantic_search(**parameters)
                await self._track_tool_call(
                    agent_name="DataRetrieval",
                    tool_name="semantic_search",
                    parameters=parameters,
                    result={"review_count": len(result) if isinstance(result, list) else 0},
                    thought=f"Performing semantic search for: {parameters.get('query_text', 'N/A')}"
                )
            else:
                result = {"error": f"Unknown data retrieval action: {action_name}"}
        
        elif agent_type == "sentiment":
            from app.optimal_workflow.agents.sentiment_agent import SentimentAnalysisAgent
            agent = SentimentAnalysisAgent()
            
            # Get reviews from context
            reviews = parameters.get("reviews", [])
            result = await agent.analyze_sentiment(reviews, parameters.get("aspects"))
            
            # Track analysis step
            await self._track_step_in_db(
                agent_name="SentimentAnalysis",
                step_order=self._get_next_step_order(),
                content={"insights_generated": len(result.get("insights", [])) if isinstance(result, dict) else 0},
                is_structured=True,
                thought=f"Analyzing sentiment for {len(reviews)} reviews"
            )
        
        elif agent_type == "topic_modeling":
            from app.optimal_workflow.agents.topic_modeling_agent import TopicModelingAgent
            agent = TopicModelingAgent()
            
            reviews = parameters.get("reviews", [])
            result = await agent.identify_topics(
                reviews,
                num_topics=parameters.get("num_topics", 10)
            )
            
            # Track analysis step
            await self._track_step_in_db(
                agent_name="TopicModeling",
                step_order=self._get_next_step_order(),
                content={"insights_generated": len(result.get("insights", [])) if isinstance(result, dict) else 0},
                is_structured=True,
                thought=f"Identifying topics in {len(reviews)} reviews"
            )
        
        elif agent_type == "anomaly_detection":
            from app.optimal_workflow.agents.anomaly_detection_agent import AnomalyDetectionAgent
            agent = AnomalyDetectionAgent()
            
            reviews = parameters.get("reviews", [])
            result = await agent.detect_anomalies(reviews)
            
            # Track analysis step
            await self._track_step_in_db(
                agent_name="AnomalyDetection",
                step_order=self._get_next_step_order(),
                content={"anomalies_detected": len(result.get("insights", [])) if isinstance(result, dict) else 0},
                is_structured=True,
                thought=f"Detecting anomalies in {len(reviews)} reviews"
            )
        
        elif agent_type == "summary":
            from app.optimal_workflow.agents.summary_agent import SummaryAgent
            agent = SummaryAgent()
            
            reviews = parameters.get("reviews", [])
            result = await agent.summarize_reviews(reviews)
            
            # Track analysis step
            await self._track_step_in_db(
                agent_name="Summary",
                step_order=self._get_next_step_order(),
                content={"summary_length": len(str(result)) if result else 0},
                is_structured=True,
                thought=f"Summarizing {len(reviews)} reviews"
            )
        
        else:
            result = {"error": f"Unknown agent type: {agent_type}"}
        
        return result

    async def _execute_parallel_actions(
        self,
        primary_action: Dict[str, Any],
        parallel_action_ids: List[str],
        context: Dict[str, Any],
        base_step_order: int
    ) -> Dict[str, Any]:
        """Execute multiple actions in parallel."""
        logger.info(f"Executing {len(parallel_action_ids) + 1} actions in parallel")
        
        # Import orchestrator
        from app.optimal_workflow.agents.orchestrator import WorkflowOrchestrator
        
        orchestrator = WorkflowOrchestrator()
        
        # Build list of actions to execute
        actions = [primary_action]
        # Note: parallel_action_ids would need to be resolved to actual action objects
        # This is a simplified version
        
        # Execute in parallel
        results = await orchestrator.execute_parallel_steps(context, actions)
        
        return results.get(primary_action.get("action_id"), {})

    @step
    async def synthesis_step(
        self,
        ctx: Context,
        ev: QueryCompleteEvent
    ) -> StopEvent:
        """
        Step 5: Synthesis - Combine all insights into final response.
        
        This step:
        - Collects all insights from execution context
        - Calls Synthesis Agent to create coherent narrative
        - Generates visualizations if needed
        - Streams final response
        - Saves conversational context for follow-ups
        """
        step_id = str(uuid.uuid4())
        step_order = self._get_next_step_order()
        
        self._emit_event("agent_step_start", {
            "agent_name": "Synthesis",
            "step_id": step_id,
            "timestamp": datetime.utcnow().isoformat(),
            "step_order": step_order
        })
        
        logger.info("▶️  Step: Synthesis - Generate Final Response")
        
        try:
            execution_context = ev.context
            
            # Import synthesis agent
            from app.optimal_workflow.agents.synthesis_agent import SynthesisAgent
            
            synthesis_agent = SynthesisAgent()
            
            # Generate synthesis plan (thought)
            synthesis_plan = await synthesis_agent.generate_synthesis_plan(
                query=ev.query,
                insights=execution_context.get("insights", [])
            )
            
            logger.info(f"✓ Synthesis plan created: {len(synthesis_plan.get('outline', []))} sections")
            
            # Generate final response
            synthesis_result = await synthesis_agent.synthesize_response(
                query=ev.query,
                insights=execution_context.get("insights", []),
                format_type="markdown"
            )
            
            final_response = synthesis_result.get("response", "")
            
            logger.info(f"✓ Synthesis complete: {len(final_response)} characters")
            
            # Stream the response
            for chunk in self._chunk_text(final_response):
                self._emit_event("content", {"content": chunk})
            
            # Extract synthesis thought
            synthesis_thought = synthesis_plan.get("reasoning") or "Synthesizing insights into coherent narrative response"
            
            # Prepare synthesis metadata
            synthesis_metadata = {
                "insights_used": synthesis_result.get("insights_used", []),
                "insights_omitted": synthesis_result.get("insights_omitted", []),
                "response_length": len(final_response),
                "sections": synthesis_plan.get("outline", [])
            }
            
            # Emit completion event
            self._emit_event("agent_step_complete", {
                "step_id": step_id,
                "agent_name": "Synthesis",
                "content": {
                    "insights_used": len(synthesis_result.get("insights_used", [])),
                    "response_length": len(final_response)
                },
                "is_structured": True,
                "step_order": step_order
            })
            
            # Save to database with thought and structured output
            await self._track_step_in_db(
                agent_name="Synthesis",
                step_order=step_order,
                content=synthesis_metadata,
                is_structured=True,
                thought=synthesis_thought
            )
            
            # Update assistant message
            await self._update_assistant_message(final_response)
            
            # Save conversational context for follow-up queries
            # Retrieve context manager from workflow context
            context_manager = await ctx.get("context_manager", default=None)
            await self._save_conversational_context(execution_context, context_manager)
            
            # Emit final completion
            chat_response = ChatResponse(
                message=final_response,
                session_id=self.session_id,
                message_id=str(self.assistant_message_id) if self.assistant_message_id else str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                metadata={
                    "workflow": "product_review_analysis",
                    "insights_count": len(execution_context.get("insights", [])),
                    "steps_executed": len(execution_context.get("completed_steps", set()))
                }
            )
            self._emit_event("complete", chat_response.dict())
            
            logger.info("🏁 Workflow completed successfully")
            
            return StopEvent(result=final_response)
            
        except Exception as e:
            logger.error(f"Error in synthesis step: {e}", exc_info=True)
            raise

    async def _save_conversational_context(self, execution_context: Dict[str, Any], context_manager=None):
        """
        Save execution context for follow-up queries.
        
        This method persists the execution results to Redis so that follow-up
        queries can reference previous insights and reuse cached data.
        
        Args:
            execution_context: The execution context containing insights and outputs
            context_manager: Optional context manager instance (from workflow context)
            
        Requirements: 12.1, 12.2
        """
        try:
            # Use provided context manager or create new one
            if context_manager is None:
                from app.core.llm.workflow.context_manager import ConversationalContextManager
                from app.services.redis_client import RedisClient
                
                redis_client = RedisClient()
                await redis_client.connect()
                context_manager = ConversationalContextManager(redis_client=redis_client)
            
            # Prepare metadata about this execution
            metadata = {
                "steps_executed": len(execution_context.get("completed_steps", set())),
                "failed_steps": len(execution_context.get("failed_steps", {})),
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": execution_context.get("user_id"),
            }
            
            # Save context with all execution results
            success = await context_manager.save_context(
                session_id=self.session_id,
                query=execution_context.get("query"),
                insights=execution_context.get("insights", []),
                agent_outputs=execution_context.get("agent_outputs", {}),
                metadata=metadata
            )
            
            if success:
                logger.info("✓ Conversational context saved successfully")
                logger.info(f"   └─ Session: {self.session_id}")
                logger.info(f"   └─ Insights: {len(execution_context.get('insights', []))}")
                logger.info(f"   └─ Agent outputs: {len(execution_context.get('agent_outputs', {}))}")
            else:
                logger.warning("⚠️  Failed to save conversational context (Redis may be unavailable)")
                
        except Exception as e:
            logger.warning(f"Could not save conversational context: {e}")
            logger.debug("Context save error details", exc_info=True)
