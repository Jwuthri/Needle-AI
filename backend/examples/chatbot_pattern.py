"""
Recommended Chatbot Pattern for NeedleAI
Uses Team-based orchestration with specialized agents and tools
"""

import os
from typing import AsyncGenerator, Optional, Dict, Any
from pydantic import BaseModel, Field
from agno.agent import Agent
from agno.team import Team
from agno.models.openai import OpenAIChat


# ============================================================================
# 1. STRUCTURED OUTPUTS - Define schemas for agent communication
# ============================================================================

class QueryAnalysis(BaseModel):
    """Output from the query analyzer"""
    intent: str = Field(description="Primary intent: data_query, analysis, visualization, general")
    complexity: str = Field(description="Complexity: simple, medium, complex")
    requires_data: bool = Field(description="Whether external data is needed")
    requires_analysis: bool = Field(description="Whether analysis is needed")
    entities: Optional[Dict[str, Any]] = Field(default={}, description="Extracted entities")


class DataResult(BaseModel):
    """Output from data retrieval"""
    data_found: bool = Field(description="Whether relevant data was found")
    source: str = Field(description="Data source used: rag, web, database")
    summary: str = Field(description="Brief summary of retrieved data")
    data: Optional[Dict[str, Any]] = Field(default=None, description="The actual data")


# ============================================================================
# 2. SPECIALIZED AGENTS - Each handles specific tasks
# ============================================================================

def create_query_analyzer() -> Agent:
    """Analyzes user queries to determine what needs to be done"""
    return Agent(
        name="Query Analyzer",
        role="Analyze user queries and plan execution strategy",
        model=OpenAIChat(id="gpt-4o-mini"),
        instructions=[
            "Analyze the user's query and determine:",
            "1. What is the user asking for?",
            "2. Does it require data retrieval?",
            "3. Does it require analysis or computation?",
            "4. What entities or parameters are mentioned?",
            "Extract all relevant information for downstream agents."
        ],
        response_model=QueryAnalysis,
        markdown=False,
    )


def create_data_agent() -> Agent:
    """Retrieves data from various sources"""
    return Agent(
        name="Data Retriever",
        role="Fetch data from RAG, web, or databases",
        model=OpenAIChat(id="gpt-4o-mini"),
        tools=[
            # Add your actual tools here
            # RAGRetrievalTool(),
            # WebSearchTool(),
            # DatabaseQueryTool(),
        ],
        instructions=[
            "Retrieve relevant data based on the query analysis.",
            "Use the most appropriate data source.",
            "Return structured data with source citations.",
            "If data not found, clearly state that."
        ],
        markdown=False,
    )


def create_analysis_agent() -> Agent:
    """Performs analysis on retrieved data"""
    return Agent(
        name="Data Analyst",
        role="Analyze data and extract insights",
        model=OpenAIChat(id="gpt-4o-mini"),
        tools=[
            # Add your analysis tools
            # DataAnalysisTool(),
            # NLPTool(),
            # StatisticalAnalysisTool(),
        ],
        instructions=[
            "Perform analysis on the provided data.",
            "Extract key insights and patterns.",
            "Present findings clearly and concisely.",
            "Use visualizations when appropriate."
        ],
        markdown=True,
    )


def create_synthesis_agent() -> Agent:
    """Synthesizes final response for the user"""
    return Agent(
        name="Response Synthesizer",
        role="Create final user-facing response",
        model=OpenAIChat(id="gpt-4o-mini"),
        instructions=[
            "Synthesize all information into a clear, helpful response.",
            "Be conversational and friendly.",
            "Include citations for data sources.",
            "Format output with markdown for readability.",
            "If no data was found, suggest alternatives."
        ],
        markdown=True,
    )


# ============================================================================
# 3. TEAM ORCHESTRATION - Coordinates all agents
# ============================================================================

class ChatbotOrchestrator:
    """
    Main chatbot orchestrator using Team pattern.
    
    Features:
    - Parallel processing when possible
    - Real-time streaming
    - Execution tree tracking
    - Structured agent communication
    """
    
    def __init__(self):
        self.team = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the team and agents"""
        if self._initialized:
            return
        
        # Create all agents
        analyzer = create_query_analyzer()
        data_agent = create_data_agent()
        analysis_agent = create_analysis_agent()
        synthesis_agent = create_synthesis_agent()
        
        # Create the team
        self.team = Team(
            name="Chatbot Team",
            members=[analyzer, data_agent, analysis_agent, synthesis_agent],
            
            # STREAMING CONFIGURATION
            stream=True,
            stream_intermediate_steps=True,  # See each agent's work
            show_members_responses=True,     # Show which agent is responding
            
            # TEAM BEHAVIOR
            instructions=[
                "You are a helpful AI assistant that can:",
                "1. Answer questions using available data",
                "2. Perform analysis and computations",
                "3. Provide insights and recommendations",
                "",
                "Work together as a team:",
                "- Analyzer: First understand the query",
                "- Data Agent: Fetch needed data in parallel if possible",
                "- Analysis Agent: Process data and extract insights",
                "- Synthesizer: Create the final response",
                "",
                "Be efficient: Skip unnecessary steps for simple queries."
            ],
            
            markdown=True,  # Enable markdown in responses
        )
        
        self._initialized = True
    
    async def process_message_streaming(
        self,
        message: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process a chat message with streaming output.
        
        Yields events in format:
        {
            "type": "agent_start" | "content" | "tool_call" | "complete",
            "data": {...}
        }
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Stream the team's response
            async for chunk in self.team.arun(
                message,
                stream=True,
                stream_intermediate_steps=True,
                user_id=user_id,
                session_id=session_id
            ):
                # Parse different event types
                if hasattr(chunk, 'event'):
                    event_type = chunk.event
                    
                    # Agent started working
                    if event_type in ["AgentRunStarted", "RunStarted"]:
                        agent_name = getattr(chunk, 'agent', 'System')
                        yield {
                            "type": "agent_start",
                            "data": {"agent": agent_name}
                        }
                    
                    # Content chunk
                    elif event_type in ["RunResponse", "AgentRunContent"]:
                        if hasattr(chunk, 'content') and chunk.content:
                            # Handle structured output
                            if isinstance(chunk.content, BaseModel):
                                yield {
                                    "type": "structured_output",
                                    "data": chunk.content.dict()
                                }
                            # Handle text content
                            elif isinstance(chunk.content, str):
                                yield {
                                    "type": "content",
                                    "data": {"content": chunk.content}
                                }
                    
                    # Tool call
                    elif event_type in ["ToolCallStarted", "ToolCallCompleted"]:
                        tool_name = getattr(chunk, 'tool_name', 'unknown')
                        yield {
                            "type": "tool_call",
                            "data": {
                                "tool": tool_name,
                                "status": "started" if "Started" in event_type else "completed"
                            }
                        }
            
            # Final completion
            yield {
                "type": "complete",
                "data": {"status": "success"}
            }
            
        except Exception as e:
            yield {
                "type": "error",
                "data": {"error": str(e)}
            }
    
    async def process_message(
        self,
        message: str,
        session_id: Optional[str] = None
    ) -> str:
        """
        Process a message without streaming (for simple use cases).
        """
        if not self._initialized:
            await self.initialize()
        
        response = await self.team.arun(
            message,
            stream=False,
            session_id=session_id
        )
        
        return response.content if hasattr(response, 'content') else str(response)


# ============================================================================
# 4. USAGE EXAMPLES
# ============================================================================

async def main():
    """Example usage"""
    orchestrator = ChatbotOrchestrator()
    await orchestrator.initialize()
    
    # Example 1: Streaming (recommended for chatbot UI)
    print("\n=== STREAMING EXAMPLE ===\n")
    async for event in orchestrator.process_message_streaming(
        "What are the top 3 trends in AI this year? Provide data to support your answer."
    ):
        event_type = event["type"]
        data = event["data"]
        
        if event_type == "agent_start":
            print(f"\n🤖 [{data['agent']}] starting...")
        elif event_type == "content":
            print(data["content"], end="", flush=True)
        elif event_type == "tool_call":
            print(f"\n🔧 Using tool: {data['tool']}")
        elif event_type == "complete":
            print("\n\n✅ Complete!")
    
    # Example 2: Non-streaming (simpler, but no progress updates)
    print("\n\n=== NON-STREAMING EXAMPLE ===\n")
    response = await orchestrator.process_message(
        "Give me a summary of quantum computing."
    )
    print(response)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

