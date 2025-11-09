"""
Simple ReAct Agent using LlamaIndex.

This agent uses a single ReActAgent with access to various tools (SQL, utilities, etc.)
and includes conversation memory for context-aware interactions.
"""

import asyncio
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime

from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.llms import ChatMessage, MessageRole

from app.utils.logging import get_logger
from app.optimal_workflow.agents.base import get_llm
from app.optimal_workflow.tools import mock_tools

logger = get_logger(__name__)


def _create_tools() -> List[FunctionTool]:
    """Create all tools for the simple agent."""
    
    tools = [
        # SQL Tools
        FunctionTool.from_defaults(
            fn=mock_tools.execute_query,
            name="sql_query",
            description="Execute a SQL query and return results. Use for querying database tables like products, sales, users. Returns rows, row_count, and query_time_ms."
        ),
        FunctionTool.from_defaults(
            fn=mock_tools.get_schema,
            name="get_table_schema",
            description="Get schema information for a database table. Returns column definitions, types, row counts, and indexes. Useful before writing queries."
        ),
        FunctionTool.from_defaults(
            fn=mock_tools.count_rows,
            name="count_rows",
            description="Count rows in a table with optional WHERE condition. Faster than full SELECT for counting."
        ),
        
        # Analysis Tools
        FunctionTool.from_defaults(
            fn=mock_tools.calculate_stats,
            name="calculate_statistics",
            description="Calculate statistical measures (mean, median, std dev, min, max) for numeric data. Pass list of numbers and stat_type ('all', 'mean', 'median', or 'std')."
        ),
        FunctionTool.from_defaults(
            fn=mock_tools.compare_values,
            name="compare_values",
            description="Compare two numeric values. Returns absolute difference, percentage change, and ratio. Useful for analyzing changes over time."
        ),
        FunctionTool.from_defaults(
            fn=mock_tools.find_trends,
            name="find_trends",
            description="Identify trends in time-series data. Pass list of data points with x and y values. Returns trend direction (increasing/decreasing/stable) and slope."
        ),
        
        # Utility Tools
        FunctionTool.from_defaults(
            fn=mock_tools.calculator,
            name="calculator",
            description="Evaluate mathematical expressions. Pass expression as string (e.g., '2 + 2 * 3'). Returns calculated result."
        ),
        FunctionTool.from_defaults(
            fn=mock_tools.weather,
            name="weather",
            description="Get weather information for a location. Pass city name and optional date. Returns temperature, conditions, humidity, wind speed."
        ),
        FunctionTool.from_defaults(
            fn=mock_tools.search,
            name="search",
            description="Search for information. Pass search query and optional num_results. Returns list of relevant results with titles, URLs, and snippets."
        ),
        
        # Format Tools
        FunctionTool.from_defaults(
            fn=mock_tools.create_table,
            name="create_table",
            description="Format data as a table. Pass list of dictionaries and format_type ('markdown', 'html', or 'ascii'). Returns formatted table string."
        ),
        FunctionTool.from_defaults(
            fn=mock_tools.create_chart,
            name="create_chart",
            description="Create ASCII art chart visualization. Pass data points, chart_type ('bar' or 'line'), and x/y keys. Returns text-based chart."
        ),
        FunctionTool.from_defaults(
            fn=mock_tools.format_markdown,
            name="format_markdown",
            description="Format content as structured markdown. Pass content and style ('report', 'article', or 'list'). Returns formatted markdown."
        ),
    ]
    
    return tools


class SimpleAgent:
    """
    Simple ReAct agent with tool access and conversation memory.
    
    This agent can:
    - Execute SQL queries
    - Perform statistical analysis
    - Use utility tools (calculator, weather, search)
    - Format output in various ways
    - Maintain conversation context
    """
    
    def __init__(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        stream_callback: Optional[Callable] = None,
        max_iterations: int = 10,
        verbose: bool = True
    ):
        """
        Initialize the simple agent.
        
        Args:
            user_id: User identifier
            session_id: Session identifier for tracking
            stream_callback: Optional callback for streaming events
            max_iterations: Maximum reasoning iterations
            verbose: Whether to log verbose output
        """
        self.user_id = user_id
        self.session_id = session_id
        self.stream_callback = stream_callback
        self.max_iterations = max_iterations
        self.verbose = verbose
        
        # Create LLM
        self.llm = get_llm()
        
        # Create tools
        self.tools = _create_tools()
        
        # Create memory buffer for conversation history
        self.memory = ChatMemoryBuffer.from_defaults(
            token_limit=3000  # Keep recent conversation context
        )
        
        # Create ReAct agent
        self.agent = ReActAgent.from_tools(
            tools=self.tools,
            llm=self.llm,
            memory=self.memory,
            max_iterations=max_iterations,
            verbose=verbose
        )
        
        logger.info(f"SimpleAgent initialized with {len(self.tools)} tools")
    
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
    
    async def run(self, query: str, conversation_history: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Run the agent on a query.
        
        Args:
            query: User's question or request
            conversation_history: Optional prior conversation messages
            
        Returns:
            Agent's response as string
        """
        logger.info(f"[SimpleAgent] Processing query: {query[:100]}...")
        
        # Emit start event
        self._emit_event("agent_start", {
            "agent_type": "simple",
            "query": query,
            "session_id": self.session_id
        })
        
        try:
            # Add conversation history to memory if provided
            if conversation_history:
                for msg in conversation_history[-5:]:  # Last 5 messages
                    role = MessageRole.USER if msg.get("role") == "user" else MessageRole.ASSISTANT
                    self.memory.put(ChatMessage(role=role, content=msg.get("content", "")))
            
            # Run the agent
            response = await self.agent.achat(query)
            
            result = str(response)
            
            # Emit completion event
            self._emit_event("agent_complete", {
                "agent_type": "simple",
                "response_length": len(result),
                "session_id": self.session_id
            })
            
            logger.info(f"[SimpleAgent] Response generated: {len(result)} characters")
            
            return result
            
        except Exception as e:
            logger.error(f"[SimpleAgent] Error: {e}", exc_info=True)
            self._emit_event("agent_error", {
                "agent_type": "simple",
                "error": str(e)
            })
            return f"I encountered an error: {str(e)}"
    
    async def stream_run(self, query: str, conversation_history: Optional[List[Dict[str, Any]]] = None):
        """
        Run the agent with streaming output.
        
        Args:
            query: User's question or request
            conversation_history: Optional prior conversation messages
            
        Yields:
            Response chunks as they're generated
        """
        logger.info(f"[SimpleAgent] Streaming query: {query[:100]}...")
        
        # Emit start event
        self._emit_event("agent_start", {
            "agent_type": "simple",
            "query": query,
            "session_id": self.session_id,
            "streaming": True
        })
        
        try:
            # Add conversation history to memory if provided
            if conversation_history:
                for msg in conversation_history[-5:]:  # Last 5 messages
                    role = MessageRole.USER if msg.get("role") == "user" else MessageRole.ASSISTANT
                    self.memory.put(ChatMessage(role=role, content=msg.get("content", "")))
            
            # Stream the response
            response = await self.agent.astream_chat(query)
            
            full_response = []
            async for chunk in response.async_response_gen():
                chunk_text = str(chunk)
                full_response.append(chunk_text)
                
                # Emit content event
                self._emit_event("content", {
                    "content": chunk_text
                })
                
                yield chunk_text
            
            result = "".join(full_response)
            
            # Emit completion event
            self._emit_event("agent_complete", {
                "agent_type": "simple",
                "response_length": len(result),
                "session_id": self.session_id
            })
            
            logger.info(f"[SimpleAgent] Streaming complete: {len(result)} characters")
            
        except Exception as e:
            logger.error(f"[SimpleAgent] Streaming error: {e}", exc_info=True)
            self._emit_event("agent_error", {
                "agent_type": "simple",
                "error": str(e)
            })
            yield f"I encountered an error: {str(e)}"
    
    def reset_memory(self):
        """Clear conversation memory."""
        self.memory.reset()
        logger.info("[SimpleAgent] Memory cleared")
    
    def get_chat_history(self) -> List[ChatMessage]:
        """Get current chat history from memory."""
        return self.memory.get_all()


async def run_simple_agent(
    query: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    stream_callback: Optional[Callable] = None,
    conversation_history: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    Convenience function to run a simple agent query.
    
    Args:
        query: User's question
        user_id: User identifier
        session_id: Session identifier
        stream_callback: Optional callback for events
        conversation_history: Optional prior messages
        
    Returns:
        Agent's response
    """
    agent = SimpleAgent(
        user_id=user_id,
        session_id=session_id,
        stream_callback=stream_callback
    )
    
    return await agent.run(query, conversation_history)


if __name__ == "__main__":
    # Test the simple agent
    async def test():
        print("Testing Simple Agent\n" + "="*50)
        
        agent = SimpleAgent(verbose=True)
        
        # Test 1: SQL query
        print("\n1. Testing SQL query...")
        response = await agent.run("Show me all products in the database")
        print(f"Response: {response}\n")
        
        # Test 2: Calculator
        print("\n2. Testing calculator...")
        response = await agent.run("What is 25 * 4 + 100?")
        print(f"Response: {response}\n")
        
        # Test 3: Weather
        print("\n3. Testing weather...")
        response = await agent.run("What's the weather in San Francisco?")
        print(f"Response: {response}\n")
        
        # Test 4: Complex query with multiple tools
        print("\n4. Testing complex query...")
        response = await agent.run("Get products from the database, calculate the average price, and format the results as a table")
        print(f"Response: {response}\n")
    
    asyncio.run(test())

