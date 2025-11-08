"""
Base Specialist Service - Common ReAct loop logic for all specialists.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional
from datetime import datetime

from agno.agent import Agent
from agno.models.openrouter import OpenRouter

from app.agents.tools.base_tool import BaseTool
from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger("base_specialist")


class BaseSpecialist(ABC):
    """
    Base class for specialist agents with ReAct loop.
    
    Each specialist:
    - Has domain-specific system prompt
    - Has curated tools
    - Runs ReAct reasoning loop
    - Streams events to frontend
    """
    
    def __init__(self, settings: Any = None):
        self.settings = settings or get_settings()
        self.tools: List[BaseTool] = []
        self.agent: Optional[Agent] = None
        self._initialized = False
        self.logger = get_logger(self.name)
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Specialist name (product, research, analytics, general)."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Specialist description."""
        pass
    
    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """System prompt for the specialist."""
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Model to use for this specialist."""
        pass
    
    @abstractmethod
    def _initialize_tools(self) -> List[BaseTool]:
        """Initialize tools for this specialist."""
        pass
    
    async def initialize(self):
        """Initialize the specialist agent."""
        if self._initialized:
            return
        
        try:
            # Initialize tools
            self.tools = self._initialize_tools()
            self.logger.info(f"Initialized {len(self.tools)} tools: {[t.name for t in self.tools]}")
            
            # Create model
            model = self._create_model()
            
            # Create Agno agent
            self.agent = Agent(
                name=self.name.replace("_", " ").title(),
                model=model,
                tools=[self._convert_tool_to_agno(t) for t in self.tools],
                instructions=self.system_prompt,
                markdown=True,
                # show_tool_calls=True,
                stream=True
            )
            
            self._initialized = True
            self.logger.info(f"{self.name} specialist initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize {self.name} specialist: {e}")
            raise
    
    def _create_model(self) -> OpenRouter:
        """Create OpenRouter model for this specialist."""
        api_key = self.settings.get_secret("openrouter_api_key")
        if not api_key:
            raise ValueError("OpenRouter API key not configured")
        
        return OpenRouter(
            id=self.model_name,
            api_key=str(api_key),
            max_tokens=4096
        )
    
    def _convert_tool_to_agno(self, tool: BaseTool) -> Callable:
        """Convert our BaseTool to Agno-compatible function."""
        from agno.tools import tool as agno_tool
        
        # Get tool metadata
        tool_name = tool.name
        tool_description = tool.description
        tool_params = tool.parameters
        
        # Create async function
        async def tool_function(**kwargs):
            """Execute tool and return result."""
            result = await tool.execute(**kwargs)
            
            if result.success:
                # Return data for agent to use
                if result.data:
                    return f"{result.summary}\n\nData: {result.data}"
                return result.summary
            else:
                return f"Error: {result.summary}"
        
        # Set function metadata
        tool_function.__name__ = tool_name
        tool_function.__doc__ = tool_description
        
        # Wrap with agno decorator
        return agno_tool()(tool_function)
    
    async def process_query(
        self,
        query: str,
        context: Dict[str, Any],
        stream_callback: Optional[Callable] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process query with ReAct loop and streaming.
        
        Args:
            query: User's question
            context: Additional context (company_id, etc.)
            stream_callback: Optional callback for each event
            
        Yields:
            Stream events (specialist_start, reasoning, tool_call, content, complete)
        """
        if not self._initialized:
            await self.initialize()
        
        if not self.agent:
            yield {
                "type": "error",
                "data": {"error": f"{self.name} agent not initialized"}
            }
            return
        
        start_time = datetime.now()
        
        try:
            # Stream: specialist_start
            yield {
                "type": "specialist_start",
                "data": {
                    "specialist": self.name,
                    "initial_plan": f"I'll analyze your question and determine the best approach...",
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            # Build messages
            messages = [{"role": "user", "content": query}]
            
            # Add context if available
            if context:
                context_str = "\n".join([f"{k}: {v}" for k, v in context.items() if v])
                if context_str:
                    messages[0]["content"] = f"{context_str}\n\n{query}"
            
            # Run agent with streaming
            accumulated_content = ""
            reasoning_step = 0
            tools_used = []
            
            async for chunk in self.agent.arun_stream(
                message=messages[0]["content"],
                stream=True
            ):
                # Parse and emit events
                event_type = getattr(chunk, 'event', None)
                
                # Handle different event types
                if hasattr(chunk, 'content') and chunk.content:
                    content = chunk.content
                    
                    # Check if this looks like reasoning (contains "I need to" or similar)
                    if any(phrase in content.lower() for phrase in ["i need to", "i should", "i'll", "let me", "first,"]):
                        reasoning_step += 1
                        yield {
                            "type": "reasoning",
                            "data": {
                                "thought": content,
                                "step_number": reasoning_step,
                                "timestamp": datetime.now().isoformat()
                            }
                        }
                    else:
                        # Regular content streaming
                        accumulated_content += content
                        yield {
                            "type": "content",
                            "data": {
                                "content": content,
                                "delta": content,
                                "timestamp": datetime.now().isoformat()
                            }
                        }
                
                # Tool calls (if Agno exposes them in stream)
                if hasattr(chunk, 'tool_calls'):
                    for tool_call in chunk.tool_calls:
                        tool_name = tool_call.get("name", "unknown")
                        tool_args = tool_call.get("arguments", {})
                        
                        yield {
                            "type": "tool_selection",
                            "data": {
                                "tool_name": tool_name,
                                "reasoning": f"Calling {tool_name} to get required data",
                                "parameters": tool_args,
                                "timestamp": datetime.now().isoformat()
                            }
                        }
                        
                        yield {
                            "type": "tool_start",
                            "data": {
                                "tool_name": tool_name,
                                "timestamp": datetime.now().isoformat()
                            }
                        }
                        
                        tools_used.append(tool_name)
            
            # Stream: complete
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            yield {
                "type": "complete",
                "data": {
                    "message": accumulated_content,
                    "specialist": self.name,
                    "tools_used": tools_used,
                    "metadata": {
                        "total_duration_ms": duration_ms,
                        "reasoning_steps": reasoning_step,
                        "tools_called": len(tools_used)
                    },
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            self.logger.error(f"Query processing failed: {e}", exc_info=True)
            yield {
                "type": "error",
                "data": {
                    "error": str(e),
                    "specialist": self.name,
                    "timestamp": datetime.now().isoformat()
                }
            }
    
    async def set_db_session(self, db: Any):
        """Set database session for tools that need it."""
        for tool in self.tools:
            if hasattr(tool, 'set_db_session'):
                tool.set_db_session(db)

