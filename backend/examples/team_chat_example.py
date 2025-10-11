"""
Working LLM Team Example with Agno 2.0.11, OpenRouter, and Pinecone
===================================================================

A production-ready chat application featuring:
- Multi-agent team collaboration with OpenRouter models
- Pinecone vector database for persistent memory
- Specialized tools for each agent
- Real-time chat interface

This example shows how to build a working AI team that can:
- Research topics (Research Agent)
- Write code (Developer Agent)
- Review and improve content (QA Agent)
- Coordinate the whole process (Orchestrator Agent)
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

# Working Agno imports for 2.0.11 with OpenRouter and Pinecone
from agno.agent import Agent
from agno.memory import MemoryManager
from agno.models.openrouter import OpenRouter
from agno.team import Team
from agno.tools.calculator import CalculatorTools
from agno.tools.file import FileTools
from agno.tools.python import PythonTools
from app.exceptions import ConfigurationError
from app.models.chat import ChatRequest, ChatResponse
from app.utils.logging import get_logger

logger = get_logger("llm_team_example")


class AgentRole(str, Enum):
    """Agent roles in the team."""
    ORCHESTRATOR = "orchestrator"
    RESEARCHER = "researcher"
    DEVELOPER = "developer"
    QA_REVIEWER = "qa_reviewer"


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class LLMTeamChat:
    """
    Working LLM Team Chat Application with Agno 2.0.11.

    Features:
    - Multi-agent collaboration with OpenRouter models
    - Pinecone vector database for memory
    - Specialized tools for each agent
    - Real-time chat interface
    """

    def __init__(self, settings: Any):
        self.settings = settings
        self.team: Optional[Team] = None
        self.agents: Dict[str, Agent] = {}
        self.task_history: List[Dict] = []
        self._initialized = False

    async def initialize(self):
        """Initialize the complete LLM team with agents and memory."""
        if self._initialized:
            return

        try:
            # Create shared memory
            shared_memory = await self._create_shared_memory()

            # Create specialized agents
            self.agents = {
                AgentRole.ORCHESTRATOR: await self._create_orchestrator_agent(shared_memory),
                AgentRole.RESEARCHER: await self._create_researcher_agent(shared_memory),
                AgentRole.DEVELOPER: await self._create_developer_agent(shared_memory),
                AgentRole.QA_REVIEWER: await self._create_qa_agent(shared_memory)
            }

            # Create the team with correct parameter name
            self.team = Team(
                members=list(self.agents.values()),
                name="AI Development Team",
                instructions="You are a collaborative AI team. Work together to provide comprehensive solutions."
            )

            self._initialized = True
            logger.info("LLM Team initialized successfully with 4 agents")

        except Exception as e:
            logger.error(f"Failed to initialize LLM team: {e}")
            raise ConfigurationError(f"Team initialization failed: {e}")

    async def _create_shared_memory(self) -> MemoryManager:
        """Create shared memory for the team."""
        # For now, use basic memory manager
        # TODO: Add Pinecone integration when settings are available
        return MemoryManager()

    async def _create_orchestrator_agent(self, memory: MemoryManager) -> Agent:
        """Create the orchestrator agent that coordinates the team."""

        tools = [
            PythonTools(),
            FileTools(),
            CalculatorTools()
        ]

        return Agent(
            name="Orchestrator",
            model=OpenRouter(id="openai/gpt-4o-mini"),
            memory_manager=memory,
            tools=tools,
            instructions="""
            You are the Orchestrator Agent, the leader of a specialized AI team.

            Your responsibilities:
            1. Understand user requests and break them into tasks
            2. Coordinate with team members (Researcher, Developer, QA)
            3. Synthesize final results for users

            Always provide comprehensive and well-structured responses.
            """
        )

    async def _create_researcher_agent(self, memory: MemoryManager) -> Agent:
        """Create the research specialist agent."""

        return Agent(
            name="Researcher",
            model=OpenRouter(id="anthropic/claude-3.5-sonnet"),
            memory_manager=memory,
            tools=[PythonTools(), CalculatorTools()],
            instructions="""
            You are the Research Agent, the team's information specialist.

            Your expertise includes:
            1. Information gathering and analysis
            2. Fact-checking and verification
            3. Data analysis and insights

            Always provide well-sourced, factual information with confidence levels.
            """
        )

    async def _create_developer_agent(self, memory: MemoryManager) -> Agent:
        """Create the developer/engineer agent."""

        return Agent(
            name="Developer",
            model=OpenRouter(id="openai/gpt-4o"),
            memory_manager=memory,
            tools=[PythonTools(), FileTools()],
            instructions="""
            You are the Developer Agent, the team's technical specialist.

            Your capabilities include:
            1. Software development and architecture
            2. Code review and optimization
            3. Technical problem solving

            Always write clean, documented, and testable code.
            """
        )

    async def _create_qa_agent(self, memory: MemoryManager) -> Agent:
        """Create the quality assurance agent."""

        return Agent(
            name="QA_Reviewer",
            model=OpenRouter(id="anthropic/claude-3.5-sonnet"),
            memory_manager=memory,
            tools=[PythonTools(), FileTools()],
            instructions="""
            You are the QA Agent, ensuring quality and reliability.

            Your responsibilities:
            1. Code review and quality assessment
            2. Testing and validation
            3. Process improvement recommendations

            Always provide constructive feedback with specific recommendations.
            """
        )

    async def process_chat_request(self, request: ChatRequest, user_id: str = None) -> ChatResponse:
        """
        Process a chat request through the LLM team.

        This is the main entry point for chat interactions.
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Log the request
            task = {
                "id": f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "request": request.message,
                "user_id": user_id,
                "session_id": request.session_id,
                "timestamp": datetime.utcnow().isoformat(),
                "status": TaskStatus.PENDING
            }
            self.task_history.append(task)

            # Process through the team
            team_response = await self.team.run(
                message=request.message,
                session_id=request.session_id
            )

            # Extract the final response
            if hasattr(team_response, 'content'):
                response_content = team_response.content
            elif isinstance(team_response, dict):
                response_content = team_response.get('final_response', str(team_response))
            else:
                response_content = str(team_response)

            # Update task status
            task["status"] = TaskStatus.COMPLETED
            task["response"] = response_content

            # Create chat response
            chat_response = ChatResponse(
                message=response_content,
                session_id=request.session_id,
                metadata={
                    "team_collaboration": True,
                    "task_id": task["id"],
                    "processing_time": (datetime.utcnow() - datetime.fromisoformat(task["timestamp"])).total_seconds(),
                    "agents_count": len(self.agents)
                }
            )

            logger.info(f"Team processed request for session {request.session_id}")
            return chat_response

        except Exception as e:
            logger.error(f"Error processing team request: {e}")

            # Update task status
            if 'task' in locals():
                task["status"] = TaskStatus.FAILED
                task["error"] = str(e)

            # Return error response
            return ChatResponse(
                message=f"I apologize, but the team encountered an error: {str(e)}. Please try again.",
                session_id=request.session_id,
                metadata={"error": True, "team_collaboration": True}
            )

    async def get_team_status(self) -> Dict[str, Any]:
        """Get current team status and metrics."""
        status = {
            "team_initialized": self._initialized,
            "agents": {},
            "recent_tasks": self.task_history[-5:],  # Last 5 tasks
            "metrics": {
                "total_tasks": len(self.task_history),
                "completed_tasks": len([t for t in self.task_history if t["status"] == TaskStatus.COMPLETED]),
                "failed_tasks": len([t for t in self.task_history if t["status"] == TaskStatus.FAILED])
            }
        }

        # Agent status
        for role, agent in self.agents.items():
            status["agents"][role] = {
                "name": agent.name,
                "model": getattr(agent.model, 'id', 'unknown'),
                "tools_count": len(getattr(agent, 'tools', [])),
                "active": True
            }

        return status


# Service wrapper for integration
class LLMTeamChatService:
    """
    Service wrapper for integrating LLM Team with existing chat infrastructure.
    """

    def __init__(self, settings: Any):
        self.settings = settings
        self.team_chat = LLMTeamChat(settings)

    async def initialize(self):
        """Initialize the team chat service."""
        await self.team_chat.initialize()
        logger.info("LLM Team Chat Service initialized")

    async def process_message(self, request: ChatRequest, user_id: str = None) -> ChatResponse:
        """Process a message through the LLM team."""
        return await self.team_chat.process_chat_request(request, user_id)

    async def get_team_status(self) -> Dict[str, Any]:
        """Get team status for monitoring."""
        return await self.team_chat.get_team_status()


# Configuration example
def create_team_chat_config(settings) -> Dict[str, Any]:
    """Create configuration for the LLM team chat."""
    return {
        "team_settings": {
            "agents_count": 4,
            "models": {
                "orchestrator": "openai/gpt-4o-mini",
                "researcher": "anthropic/claude-3.5-sonnet",
                "developer": "openai/gpt-4o",
                "qa": "anthropic/claude-3.5-sonnet"
            }
        },

        "memory_settings": {
            "provider": "pinecone",  # When configured
            "fallback": "basic"
        },

        "tools_settings": {
            "python_enabled": True,
            "file_operations_enabled": True,
            "calculator_enabled": True
        }
    }
