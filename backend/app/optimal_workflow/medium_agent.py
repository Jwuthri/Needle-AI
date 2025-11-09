"""
Medium Agent Workflow using LlamaIndex.

This workflow uses multiple specialized agents working together:
- Router Agent: Analyzes query and delegates to appropriate specialist
- SQL Agent: Handles database queries and data retrieval
- Analysis Agent: Performs statistical analysis and comparisons
- Writer Agent: Formats and presents results

Each agent has access to specific tools relevant to its role.
"""

import asyncio
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime

from llama_index.core.workflow import (
    Workflow,
    StartEvent,
    StopEvent,
    Event,
    step,
    Context,
)
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.llms import ChatMessage, MessageRole
from pydantic import BaseModel, Field

from app.utils.logging import get_logger
from app.optimal_workflow.agents.base import get_llm
from app.optimal_workflow.tools import mock_tools

logger = get_logger(__name__)


# =============================================================================
# WORKFLOW EVENTS
# =============================================================================

class RouterEvent(Event):
    """Event after routing decision is made."""
    query: str
    route_to: str  # 'sql', 'analysis', 'writer', 'direct'
    reasoning: str
    context: Dict[str, Any]


class SQLCompleteEvent(Event):
    """Event after SQL operations complete."""
    query: str
    sql_results: Dict[str, Any]
    route_to: str  # Next destination: 'analysis', 'writer'
    context: Dict[str, Any]


class AnalysisCompleteEvent(Event):
    """Event after analysis operations complete."""
    query: str
    analysis_results: Dict[str, Any]
    sql_results: Optional[Dict[str, Any]]
    context: Dict[str, Any]


class DirectAnswerEvent(Event):
    """Event for questions that don't need tools."""
    query: str
    context: Dict[str, Any]


# =============================================================================
# ROUTING MODEL
# =============================================================================

class RoutingDecision(BaseModel):
    """Routing decision from the router agent."""
    route_to: str = Field(..., description="Where to route: 'sql', 'analysis', 'writer', or 'direct'")
    reasoning: str = Field(..., description="Why this routing decision was made")
    needs_sql: bool = Field(default=False, description="Whether SQL data retrieval is needed")
    needs_analysis: bool = Field(default=False, description="Whether statistical analysis is needed")


# =============================================================================
# SPECIALIZED AGENT TOOLS
# =============================================================================

def _create_sql_tools() -> List[FunctionTool]:
    """Create tools for SQL agent."""
    return [
        FunctionTool.from_defaults(
            fn=mock_tools.execute_query,
            name="execute_sql_query",
            description="Execute SQL SELECT query on database tables (products, sales, users). Returns rows, row_count, and query_time_ms."
        ),
        FunctionTool.from_defaults(
            fn=mock_tools.get_schema,
            name="get_table_schema",
            description="Get schema information for a table. Returns column definitions, types, indexes. Always check schema before querying."
        ),
        FunctionTool.from_defaults(
            fn=mock_tools.count_rows,
            name="count_table_rows",
            description="Count rows in a table with optional WHERE condition. More efficient than SELECT COUNT(*)."
        ),
    ]


def _create_analysis_tools() -> List[FunctionTool]:
    """Create tools for analysis agent."""
    return [
        FunctionTool.from_defaults(
            fn=mock_tools.calculate_stats,
            name="calculate_statistics",
            description="Calculate statistics (mean, median, std, min, max) for numeric data. Pass list of numbers and stat_type."
        ),
        FunctionTool.from_defaults(
            fn=mock_tools.compare_values,
            name="compare_two_values",
            description="Compare two numbers. Returns absolute difference, percentage change, ratio, and direction."
        ),
        FunctionTool.from_defaults(
            fn=mock_tools.find_trends,
            name="analyze_trends",
            description="Find trends in time-series data. Pass list of data points with x/y values. Returns trend direction and slope."
        ),
        FunctionTool.from_defaults(
            fn=mock_tools.calculator,
            name="calculate",
            description="Evaluate mathematical expressions. Pass expression string like '2 + 2 * 3'."
        ),
    ]


def _create_writer_tools() -> List[FunctionTool]:
    """Create tools for writer agent."""
    return [
        FunctionTool.from_defaults(
            fn=mock_tools.create_table,
            name="format_as_table",
            description="Format data as table. Pass list of dicts and format_type ('markdown', 'html', 'ascii')."
        ),
        FunctionTool.from_defaults(
            fn=mock_tools.create_chart,
            name="create_visualization",
            description="Create ASCII chart. Pass data points, chart_type ('bar', 'line'), x_key, y_key."
        ),
        FunctionTool.from_defaults(
            fn=mock_tools.format_markdown,
            name="format_markdown_content",
            description="Format content as structured markdown. Pass content and style ('report', 'article', 'list')."
        ),
    ]


# =============================================================================
# MEDIUM AGENT WORKFLOW
# =============================================================================

class MediumAgentWorkflow(Workflow):
    """
    Multi-agent workflow with specialized agents.
    
    Flow:
    1. Router analyzes query and decides which specialist to use
    2. SQL Agent retrieves data (if needed)
    3. Analysis Agent performs calculations (if needed)
    4. Writer Agent formats and presents results
    """
    
    def __init__(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        stream_callback: Optional[Callable] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.session_id = session_id
        self.stream_callback = stream_callback
        self.conversation_history = conversation_history or []
        
        # Create shared LLM
        self.llm = get_llm()
        
        # Create memory for conversation context
        self.memory = ChatMemoryBuffer.from_defaults(token_limit=3000)
        
        # Initialize conversation history
        if self.conversation_history:
            for msg in self.conversation_history[-5:]:
                role = MessageRole.USER if msg.get("role") == "user" else MessageRole.ASSISTANT
                self.memory.put(ChatMessage(role=role, content=msg.get("content", "")))
        
        logger.info(f"[MediumWorkflow] Initialized with {len(self.conversation_history)} history messages")
    
    def _emit_event(self, event_type: str, data: dict):
        """Emit a streaming event if callback is provided."""
        if self.stream_callback:
            try:
                event = {
                    "type": event_type,
                    "data": data,
                    "timestamp": datetime.utcnow().isoformat()
                }
                self.stream_callback(event)
            except Exception as e:
                logger.warning(f"Failed to emit event: {e}")
    
    @step
    async def route_query(self, ctx: Context, ev: StartEvent) -> RouterEvent | DirectAnswerEvent:
        """
        Step 1: Router agent analyzes query and decides routing.
        """
        query = ev.query
        logger.info(f"[Router] Processing query: {query[:100]}...")
        
        self._emit_event("agent_step_start", {
            "agent": "router",
            "query": query
        })
        
        # Create a simple routing prompt
        routing_prompt = f"""Analyze this query and determine the best route:

Query: {query}

Available routes:
- 'sql': If query needs database data (products, sales, users)
- 'analysis': If query needs calculations, statistics, comparisons
- 'writer': If query needs formatting or presentation
- 'direct': If query is simple and needs no special tools (greetings, general questions)

Decide the route and explain your reasoning briefly."""
        
        try:
            # Use LLM to make routing decision
            response = await self.llm.acomplete(routing_prompt)
            response_text = str(response).lower()
            
            # Simple routing logic based on keywords
            if any(word in query.lower() for word in ['hello', 'hi', 'how are you', 'thanks', 'thank you']):
                route = 'direct'
                reasoning = "Simple greeting or courtesy message"
            elif any(word in query.lower() for word in ['select', 'query', 'database', 'table', 'products', 'sales', 'users', 'data']):
                route = 'sql'
                reasoning = "Query requires database access"
            elif any(word in query.lower() for word in ['calculate', 'average', 'mean', 'statistics', 'compare', 'trend', 'analyze']):
                route = 'analysis'
                reasoning = "Query requires statistical analysis"
            elif any(word in query.lower() for word in ['format', 'table', 'chart', 'markdown', 'report']):
                route = 'writer'
                reasoning = "Query requires formatting or visualization"
            else:
                route = 'direct'
                reasoning = "General query, no special tools needed"
            
            logger.info(f"[Router] Routed to: {route} - {reasoning}")
            
            self._emit_event("agent_step_complete", {
                "agent": "router",
                "route": route,
                "reasoning": reasoning
            })
            
            # Route to appropriate event
            if route == 'direct':
                return DirectAnswerEvent(
                    query=query,
                    context={"routing_reasoning": reasoning}
                )
            else:
                return RouterEvent(
                    query=query,
                    route_to=route,
                    reasoning=reasoning,
                    context={}
                )
                
        except Exception as e:
            logger.error(f"[Router] Error: {e}", exc_info=True)
            # Default to direct answer on error
            return DirectAnswerEvent(
                query=query,
                context={"error": str(e)}
            )
    
    @step
    async def handle_sql(self, ctx: Context, ev: RouterEvent) -> SQLCompleteEvent | AnalysisCompleteEvent:
        """
        Step 2a: SQL agent handles database queries.
        """
        if ev.route_to != 'sql':
            # Not for us, pass through
            return AnalysisCompleteEvent(
                query=ev.query,
                analysis_results={},
                sql_results=None,
                context=ev.context
            )
        
        logger.info(f"[SQL Agent] Handling query: {ev.query[:100]}...")
        
        self._emit_event("agent_step_start", {
            "agent": "sql",
            "query": ev.query
        })
        
        # Create SQL agent
        sql_tools = _create_sql_tools()
        sql_agent = ReActAgent.from_tools(
            tools=sql_tools,
            llm=self.llm,
            memory=self.memory,
            max_iterations=5,
            verbose=True
        )
        
        try:
            # Run SQL agent
            response = await sql_agent.achat(ev.query)
            result = str(response)
            
            logger.info(f"[SQL Agent] Query complete: {len(result)} chars")
            
            self._emit_event("agent_step_complete", {
                "agent": "sql",
                "result_length": len(result)
            })
            
            # Check if we need analysis next
            needs_analysis = any(word in ev.query.lower() for word in ['average', 'mean', 'calculate', 'compare', 'statistics'])
            
            return SQLCompleteEvent(
                query=ev.query,
                sql_results={"response": result, "raw_data": []},
                route_to='analysis' if needs_analysis else 'writer',
                context=ev.context
            )
            
        except Exception as e:
            logger.error(f"[SQL Agent] Error: {e}", exc_info=True)
            return SQLCompleteEvent(
                query=ev.query,
                sql_results={"error": str(e)},
                route_to='writer',
                context=ev.context
            )
    
    @step
    async def handle_analysis(self, ctx: Context, ev: RouterEvent | SQLCompleteEvent) -> AnalysisCompleteEvent:
        """
        Step 2b: Analysis agent handles calculations and statistics.
        """
        # Determine if we should handle this
        if isinstance(ev, RouterEvent) and ev.route_to != 'analysis':
            # Not for us, skip
            return AnalysisCompleteEvent(
                query=ev.query,
                analysis_results={},
                sql_results=None,
                context=ev.context
            )
        
        if isinstance(ev, SQLCompleteEvent) and ev.route_to != 'analysis':
            # Not for us, pass through SQL results
            return AnalysisCompleteEvent(
                query=ev.query,
                analysis_results={},
                sql_results=ev.sql_results,
                context=ev.context
            )
        
        logger.info(f"[Analysis Agent] Handling query: {ev.query[:100]}...")
        
        self._emit_event("agent_step_start", {
            "agent": "analysis",
            "query": ev.query
        })
        
        # Create analysis agent
        analysis_tools = _create_analysis_tools()
        analysis_agent = ReActAgent.from_tools(
            tools=analysis_tools,
            llm=self.llm,
            memory=self.memory,
            max_iterations=5,
            verbose=True
        )
        
        try:
            # Build context for analysis
            if isinstance(ev, SQLCompleteEvent):
                analysis_query = f"Based on this SQL data: {ev.sql_results}, {ev.query}"
            else:
                analysis_query = ev.query
            
            # Run analysis agent
            response = await analysis_agent.achat(analysis_query)
            result = str(response)
            
            logger.info(f"[Analysis Agent] Analysis complete: {len(result)} chars")
            
            self._emit_event("agent_step_complete", {
                "agent": "analysis",
                "result_length": len(result)
            })
            
            return AnalysisCompleteEvent(
                query=ev.query,
                analysis_results={"response": result},
                sql_results=ev.sql_results if isinstance(ev, SQLCompleteEvent) else None,
                context=ev.context if hasattr(ev, 'context') else {}
            )
            
        except Exception as e:
            logger.error(f"[Analysis Agent] Error: {e}", exc_info=True)
            return AnalysisCompleteEvent(
                query=ev.query,
                analysis_results={"error": str(e)},
                sql_results=ev.sql_results if isinstance(ev, SQLCompleteEvent) else None,
                context=ev.context if hasattr(ev, 'context') else {}
            )
    
    @step
    async def handle_writer(self, ctx: Context, ev: RouterEvent | SQLCompleteEvent | AnalysisCompleteEvent) -> StopEvent:
        """
        Step 3: Writer agent formats and presents final results.
        """
        logger.info(f"[Writer Agent] Formatting results...")
        
        self._emit_event("agent_step_start", {
            "agent": "writer",
            "query": ev.query
        })
        
        # Create writer agent
        writer_tools = _create_writer_tools()
        writer_agent = ReActAgent.from_tools(
            tools=writer_tools,
            llm=self.llm,
            memory=self.memory,
            max_iterations=5,
            verbose=True
        )
        
        try:
            # Build comprehensive context for writer
            context_parts = [f"Original query: {ev.query}"]
            
            if isinstance(ev, AnalysisCompleteEvent):
                if ev.sql_results:
                    context_parts.append(f"SQL Results: {ev.sql_results}")
                if ev.analysis_results:
                    context_parts.append(f"Analysis Results: {ev.analysis_results}")
            elif isinstance(ev, SQLCompleteEvent):
                context_parts.append(f"SQL Results: {ev.sql_results}")
            
            writer_prompt = "\n\n".join(context_parts) + "\n\nPlease provide a clear, well-formatted response."
            
            # Run writer agent with streaming
            response = await writer_agent.astream_chat(writer_prompt)
            
            result_parts = []
            async for chunk in response.async_response_gen():
                chunk_text = str(chunk)
                result_parts.append(chunk_text)
                
                # Emit streaming content
                self._emit_event("content", {
                    "content": chunk_text
                })
            
            result = "".join(result_parts)
            
            logger.info(f"[Writer Agent] Formatting complete: {len(result)} chars")
            
            self._emit_event("agent_step_complete", {
                "agent": "writer",
                "result_length": len(result)
            })
            
            self._emit_event("workflow_complete", {
                "query": ev.query,
                "response_length": len(result)
            })
            
            return StopEvent(result=result)
            
        except Exception as e:
            logger.error(f"[Writer Agent] Error: {e}", exc_info=True)
            error_msg = f"I encountered an error while formatting the response: {str(e)}"
            
            self._emit_event("agent_error", {
                "agent": "writer",
                "error": str(e)
            })
            
            return StopEvent(result=error_msg)
    
    @step
    async def handle_direct(self, ctx: Context, ev: DirectAnswerEvent) -> StopEvent:
        """
        Step 4: Handle direct answers without tools.
        """
        logger.info(f"[Direct Handler] Answering directly: {ev.query[:100]}...")
        
        self._emit_event("agent_step_start", {
            "agent": "direct",
            "query": ev.query
        })
        
        try:
            # Simple direct response using LLM
            response = await self.llm.astream_complete(ev.query)
            
            result_parts = []
            async for chunk in response:
                chunk_text = str(chunk.delta) if hasattr(chunk, 'delta') else str(chunk)
                result_parts.append(chunk_text)
                
                # Emit streaming content
                self._emit_event("content", {
                    "content": chunk_text
                })
            
            result = "".join(result_parts)
            
            logger.info(f"[Direct Handler] Response complete: {len(result)} chars")
            
            self._emit_event("agent_step_complete", {
                "agent": "direct",
                "result_length": len(result)
            })
            
            self._emit_event("workflow_complete", {
                "query": ev.query,
                "response_length": len(result)
            })
            
            return StopEvent(result=result)
            
        except Exception as e:
            logger.error(f"[Direct Handler] Error: {e}", exc_info=True)
            return StopEvent(result=f"I apologize, but I encountered an error: {str(e)}")


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

async def run_medium_agent(
    query: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    stream_callback: Optional[Callable] = None,
    conversation_history: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    Run the medium agent workflow.
    
    Args:
        query: User's question
        user_id: User identifier
        session_id: Session identifier
        stream_callback: Optional callback for events
        conversation_history: Optional prior messages
        
    Returns:
        Final response from the workflow
    """
    workflow = MediumAgentWorkflow(
        user_id=user_id,
        session_id=session_id,
        stream_callback=stream_callback,
        conversation_history=conversation_history,
        timeout=120
    )
    
    result = await workflow.run(query=query)
    return str(result)


if __name__ == "__main__":
    # Test the medium agent workflow
    async def test():
        print("Testing Medium Agent Workflow\n" + "="*50)
        
        # Test 1: SQL query
        print("\n1. Testing SQL query...")
        result = await run_medium_agent("Show me all products in the database")
        print(f"Result: {result}\n")
        
        # Test 2: Analysis query
        print("\n2. Testing analysis...")
        result = await run_medium_agent("Calculate the average of 10, 20, 30, 40, 50")
        print(f"Result: {result}\n")
        
        # Test 3: Direct answer
        print("\n3. Testing direct answer...")
        result = await run_medium_agent("Hello! How are you?")
        print(f"Result: {result}\n")
        
        # Test 4: Complex query with SQL + Analysis
        print("\n4. Testing complex query...")
        result = await run_medium_agent("Get products from database and calculate the average price")
        print(f"Result: {result}\n")
    
    asyncio.run(test())

