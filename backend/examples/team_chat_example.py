"""
LLM Team Example with Latest Agno API
======================================

A production-ready chat application featuring:
- Multi-agent team collaboration with OpenRouter models
- Latest Agno API with db parameter for persistence
- Specialized tools for each agent
- Real-time async chat interface
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from agno.agent import Agent
from agno.db.postgres import PostgresDb
from agno.models.openrouter import OpenRouter
from agno.models.openai import OpenAIChat
from agno.team import Team
from agno.tools.calculator import Calculator
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
    LLM Team Chat Application using latest Agno API.
    
    Features:
    - Multi-agent collaboration with OpenRouter/OpenAI models
    - PostgreSQL persistence for conversation history
    - Specialized tools for each agent
    - Async processing with arun()
    """

    def __init__(self, settings: Any):
        self.settings = settings
        self.team: Optional[Team] = None
        self.agents: Dict[str, Agent] = {}
        self.task_history: List[Dict] = []
        self._initialized = False

    async def initialize(self):
        """Initialize the complete LLM team with agents."""
        if self._initialized:
            return

        try:
            # Create shared database for persistence
            db = await self._create_shared_db()

            # Create specialized agents
            self.agents = {
                AgentRole.ORCHESTRATOR: await self._create_orchestrator_agent(db),
                AgentRole.RESEARCHER: await self._create_researcher_agent(db),
                AgentRole.DEVELOPER: await self._create_developer_agent(db),
                AgentRole.QA_REVIEWER: await self._create_qa_agent(db)
            }

            # Create the team
            self.team = Team(
                agents=list(self.agents.values()),
                name="AI Development Team",
                description="Collaborative AI team for comprehensive solutions",
            )

            self._initialized = True
            logger.info("LLM Team initialized successfully with 4 agents")

        except Exception as e:
            logger.error(f"Failed to initialize LLM team: {e}")
            raise ConfigurationError(f"Team initialization failed: {e}")

    async def _create_shared_db(self) -> Optional[PostgresDb]:
        """Create shared database for team persistence."""
        try:
            password = self.settings.get_secret("database_password")
            db_url = (
                f"postgresql+psycopg://{self.settings.database_user}:{password}"
                f"@{self.settings.database_host}:{self.settings.database_port}"
                f"/{self.settings.database_name}"
            )
            
            db = PostgresDb(
                db_url=db_url,
                table_name="agno_team",
            )
            logger.info("Created shared PostgreSQL database for team")
            return db
        except Exception as e:
            logger.warning(f"Failed to create shared db: {e}, continuing without persistence")
            return None

    async def _create_orchestrator_agent(self, db: Optional[PostgresDb]) -> Agent:
        """Create the orchestrator agent that coordinates the team."""

        tools = [
            PythonTools(),
            FileTools(),
            Calculator(),
        ]

        return Agent(
            name="Orchestrator",
            role="Team Coordinator",
            model=self._get_model("openai/gpt-4o-mini"),
            db=db,
            enable_user_memories=True if db else False,
            read_chat_history=True,
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

    async def _create_researcher_agent(self, db: Optional[PostgresDb]) -> Agent:
        """Create the research specialist agent."""

        return Agent(
            name="Researcher",
            role="Information Specialist",
            model=self._get_model("anthropic/claude-3.5-sonnet"),
            db=db,
            enable_user_memories=True if db else False,
            read_chat_history=True,
            tools=[PythonTools(), Calculator()],
            instructions="""
            You are the Research Agent, the team's information specialist.
            
            Your expertise includes:
            1. Information gathering and analysis
            2. Fact-checking and verification
            3. Data analysis and insights
            
            Always provide well-sourced, factual information with confidence levels.
            """
        )

    async def _create_developer_agent(self, db: Optional[PostgresDb]) -> Agent:
        """Create the developer/engineer agent."""

        return Agent(
            name="Developer",
            role="Technical Specialist",
            model=self._get_model("openai/gpt-4o"),
            db=db,
            enable_user_memories=True if db else False,
            read_chat_history=True,
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

    async def _create_qa_agent(self, db: Optional[PostgresDb]) -> Agent:
        """Create the quality assurance agent."""

        return Agent(
            name="QA_Reviewer",
            role="Quality Assurance",
            model=self._get_model("anthropic/claude-3.5-sonnet"),
            db=db,
            enable_user_memories=True if db else False,
            read_chat_history=True,
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

    def _get_model(self, model_id: str):
        """Get model instance based on provider."""
        if model_id.startswith("openai/") or model_id.startswith("anthropic/"):
            # OpenRouter model
            api_key = self.settings.get_secret("openrouter_api_key")
            api_key_str = str(api_key) if hasattr(api_key, '__str__') else api_key
            return OpenRouter(id=model_id, api_key=api_key_str)
        else:
            # OpenAI model
            api_key = self.settings.get_secret("openai_api_key")
            api_key_str = str(api_key) if hasattr(api_key, '__str__') else api_key
            return OpenAIChat(id=model_id, api_key=api_key_str)

    async def process_chat_request(self, request: ChatRequest, user_id: str = None) -> ChatResponse:
        """
        Process a chat request through the LLM team.
        Uses latest async API with arun().
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

            # Process through the team using async arun()
            run_response = await self.team.arun(
                request.message,
                stream=False,
                session_id=request.session_id,
                user_id=user_id,
            )

            # Extract the final response
            if hasattr(run_response, 'content'):
                response_content = run_response.content
            elif isinstance(run_response, str):
                response_content = run_response
            else:
                response_content = str(run_response)

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
                "role": getattr(agent, 'role', 'unknown'),
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

        "persistence_settings": {
            "provider": "postgres",
            "enable_user_memories": True,
            "read_chat_history": True,
        },

        "tools_settings": {
            "python_enabled": True,
            "file_operations_enabled": True,
            "calculator_enabled": True
        }
    }
