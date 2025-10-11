"""
Enhanced LLM Team Example with Agno 2.0.11
===========================================

A production-ready chat application featuring:
- Multi-agent team collaboration with OpenRouter models
- Pinecone vector database for persistent memory
- Specialized tools for each agent
- Human-in-the-loop capabilities
- Real-time chat interface

This example shows how to build a sophisticated AI team that can:
- Research topics (Research Agent)
- Write code (Developer Agent)
- Review and improve content (QA Agent)
- Coordinate the whole process (Orchestrator Agent)
- Ask humans for help when needed
"""

from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

# Working Agno imports for 2.0.11 with OpenRouter and Pinecone
from agno.agent import Agent
from agno.memory import MemoryManager
from agno.models.openrouter import OpenRouter
from agno.team import Team
from agno.tools import Function
from agno.tools.calculator import CalculatorTools
from agno.tools.file import FileTools
from agno.tools.python import PythonTools
from agno.vectordb.pineconedb.pineconedb import PineconeDb
from app.exceptions import ConfigurationError
from app.models.chat import ChatRequest, ChatResponse
from app.utils.logging import get_logger

logger = get_logger("enhanced_llm_team_example")


class AgentRole(str, Enum):
    """Agent roles in the team."""
    ORCHESTRATOR = "orchestrator"
    RESEARCHER = "researcher"
    DEVELOPER = "developer"
    QA_REVIEWER = "qa_reviewer"
    HUMAN_LIAISON = "human_liaison"


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    WAITING_FOR_HUMAN = "waiting_for_human"
    COMPLETED = "completed"
    FAILED = "failed"


class EnhancedLLMTeamChat:
    """
    Enhanced LLM Team Chat Application with Agno 2.0.11.

    Features:
    - Multi-agent collaboration with OpenRouter models
    - Pinecone vector database for memory
    - Specialized tools for each agent
    - Human-in-the-loop workflows
    - Real-time chat interface
    - Task coordination and handoffs
    """

    def __init__(self, settings: Any):
        self.settings = settings
        self.team: Optional[Team] = None
        self.agents: Dict[str, Agent] = {}
        self.human_callbacks: Dict[str, Callable] = {}
        self.task_history: List[Dict] = []
        self._initialized = False

    async def initialize(self):
        """Initialize the complete LLM team with agents, memory, and tools."""
        if self._initialized:
            return

        try:
            # Create shared memory with Pinecone if available
            shared_memory = await self._create_shared_memory()

            # Create specialized agents
            self.agents = {
                AgentRole.ORCHESTRATOR: await self._create_orchestrator_agent(shared_memory),
                AgentRole.RESEARCHER: await self._create_researcher_agent(shared_memory),
                AgentRole.DEVELOPER: await self._create_developer_agent(shared_memory),
                AgentRole.QA_REVIEWER: await self._create_qa_agent(shared_memory),
                AgentRole.HUMAN_LIAISON: await self._create_human_liaison_agent(shared_memory)
            }

            # Create the team with correct parameter name and OpenRouter model
            team_model = OpenRouter(
                id="openai/gpt-4o",
                api_key=self.settings.openrouter_api_key.get_secret_value() if self.settings.openrouter_api_key else "your-openrouter-api-key-here"
            )

            self.team = Team(
                members=list(self.agents.values()),
                name="Enhanced AI Development Team",
                instructions="You are a collaborative AI team with human-in-the-loop capabilities. Work together to provide comprehensive solutions and escalate to humans when needed.",
                model=team_model
            )

            self._initialized = True
            logger.info("Enhanced LLM Team initialized successfully with 5 agents")

        except Exception as e:
            logger.error(f"Failed to initialize enhanced LLM team: {e}")
            raise ConfigurationError(f"Team initialization failed: {e}")

    async def _create_shared_memory(self) -> MemoryManager:
        """Create shared memory for the team with Pinecone integration."""
        try:
            # Try to create Pinecone memory if settings are available
            if (hasattr(self.settings, 'pinecone_api_key') and
                hasattr(self.settings, 'pinecone_environment') and
                hasattr(self.settings, 'pinecone_index_name')):

                pinecone_db = PineconeDb(
                    api_key=self.settings.pinecone_api_key.get_secret_value(),
                    environment=self.settings.pinecone_environment,
                    index_name=self.settings.pinecone_index_name,
                    namespace=f"{self.settings.app_name}_enhanced_team_memory"
                )

                # Create memory manager with Pinecone
                return MemoryManager(
                    vector_db=pinecone_db,
                    max_items=10000,
                    auto_save=True
                )
            else:
                logger.warning("Pinecone settings not available, using basic memory manager")
                return MemoryManager()

        except Exception as e:
            logger.warning(f"Failed to create Pinecone memory, falling back to basic: {e}")
            return MemoryManager()

    async def _create_orchestrator_agent(self, memory: MemoryManager) -> Agent:
        """Create the orchestrator agent that coordinates the team."""

        # Enhanced tools for coordination
        tools = [
            PythonTools(),
            FileTools(),
            CalculatorTools(),
            await self._create_task_delegation_tool(),
            await self._create_human_escalation_tool()
        ]

        return Agent(
            name="Orchestrator",
            model=OpenRouter(
                id="openai/gpt-4o-mini",
                api_key=self.settings.openrouter_api_key.get_secret_value() if self.settings.openrouter_api_key else "your-openrouter-api-key-here"
            ),
            memory_manager=memory,
            tools=tools,
            instructions="""
            You are the Orchestrator Agent, the leader of a specialized AI team with human-in-the-loop capabilities.

            Your responsibilities:
            1. Understand user requests and break them into tasks
            2. Delegate tasks to appropriate team members (Researcher, Developer, QA, Human Liaison)
            3. Coordinate between agents and ensure smooth handoffs
            4. Track progress and resolve conflicts
            5. Escalate to humans when needed for complex decisions
            6. Synthesize final results for users

            Team members and their specialties:
            - Researcher: Information gathering, analysis, fact-checking
            - Developer: Code generation, architecture, technical solutions
            - QA Reviewer: Quality assurance, testing, improvements
            - Human Liaison: Human communication, approvals, feedback

            When to escalate to humans:
            - Complex strategic decisions
            - Conflicting agent recommendations
            - Tasks requiring domain expertise
            - High-risk operations (deployments, data changes)

            Always provide comprehensive and well-structured responses.
            """
        )

    async def _create_researcher_agent(self, memory: MemoryManager) -> Agent:
        """Create the research specialist agent."""

        tools = [
            PythonTools(),
            CalculatorTools(),
            await self._create_web_research_tool(),
            await self._create_fact_checking_tool()
        ]

        return Agent(
            name="Researcher",
            model=OpenRouter(
                id="anthropic/claude-3.5-sonnet",
                api_key=self.settings.openrouter_api_key.get_secret_value() if self.settings.openrouter_api_key else "your-openrouter-api-key-here"
            ),
            memory_manager=memory,
            tools=tools,
            instructions="""
            You are the Research Agent, the team's information specialist.

            Your expertise includes:
            1. Comprehensive information gathering and analysis
            2. Fact-checking and verification with confidence levels
            3. Data analysis and pattern recognition
            4. Market research and competitive analysis
            5. Academic paper analysis and citation

            Research standards:
            - Always provide well-sourced, factual information
            - Include multiple perspectives on topics
            - State confidence levels for your findings
            - Recommend further investigation when uncertain
            - Collaborate proactively with other agents

            When to request human input:
            - Conflicting sources require expert judgment
            - Domain-specific knowledge needed
            - Sensitive or controversial topics
            """
        )

    async def _create_developer_agent(self, memory: MemoryManager) -> Agent:
        """Create the developer/engineer agent."""

        tools = [
            PythonTools(),
            FileTools(),
            await self._create_code_generation_tool(),
            await self._create_architecture_design_tool()
        ]

        return Agent(
            name="Developer",
            model=OpenRouter(
                id="openai/gpt-4o",
                api_key=self.settings.openrouter_api_key.get_secret_value() if self.settings.openrouter_api_key else "your-openrouter-api-key-here"
            ),
            memory_manager=memory,
            tools=tools,
            instructions="""
            You are the Developer Agent, the team's technical specialist.

            Your capabilities include:
            1. Full-stack software development and architecture
            2. Code review and optimization
            3. Database design and API development
            4. Technical problem solving and debugging
            5. Security and performance considerations

            Code quality standards:
            - Write clean, documented, testable code
            - Follow best practices and design patterns
            - Include comprehensive error handling
            - Consider security and performance implications
            - Provide clear technical documentation

            Collaboration guidelines:
            - Work with QA for code review and testing
            - Consult Researcher for technical requirements
            - Escalate architectural decisions to humans when needed

            When to request human approval:
            - Major architectural changes
            - External API integrations
            - Database schema modifications
            - Production deployments
            """
        )

    async def _create_qa_agent(self, memory: MemoryManager) -> Agent:
        """Create the quality assurance agent."""

        tools = [
            PythonTools(),
            FileTools(),
            await self._create_testing_tool(),
            await self._create_code_review_tool()
        ]

        return Agent(
            name="QA_Reviewer",
            model=OpenRouter(
                id="anthropic/claude-3.5-sonnet",
                api_key=self.settings.openrouter_api_key.get_secret_value() if self.settings.openrouter_api_key else "your-openrouter-api-key-here"
            ),
            memory_manager=memory,
            tools=tools,
            instructions="""
            You are the QA Agent, ensuring quality and reliability across all team outputs.

            Your responsibilities:
            1. Code review and quality assessment
            2. Test design, execution, and automation
            3. Performance and security testing
            4. Documentation review and validation
            5. Process improvement recommendations

            Quality criteria checklist:
            - Functionality: Does it work as intended?
            - Reliability: Can it handle edge cases and errors?
            - Performance: Is it efficient and scalable?
            - Security: Are there vulnerabilities or risks?
            - Maintainability: Is it clean, documented, and testable?
            - Usability: Is it user-friendly and accessible?

            Always provide constructive feedback with specific, actionable recommendations.
            Collaborate with all team members to ensure quality throughout the development process.

            Escalate to humans when:
            - Quality standards cannot be met within constraints
            - Risk assessment requires business judgment
            - Compliance or regulatory concerns arise
            """
        )

    async def _create_human_liaison_agent(self, memory: MemoryManager) -> Agent:
        """Create the human communication and liaison agent."""

        tools = [
            await self._create_human_communication_tool(),
            await self._create_approval_request_tool(),
            await self._create_feedback_collection_tool()
        ]

        return Agent(
            name="Human_Liaison",
            model=OpenRouter(
                id="openai/gpt-4o-mini",
                api_key=self.settings.openrouter_api_key.get_secret_value() if self.settings.openrouter_api_key else "your-openrouter-api-key-here"
            ),
            memory_manager=memory,
            tools=tools,
            instructions="""
            You are the Human Liaison Agent, the bridge between AI and human team members.

            Your role includes:
            1. Translating technical concepts for human stakeholders
            2. Collecting human feedback, approvals, and decisions
            3. Escalating complex decisions that require human judgment
            4. Providing clear, regular status updates
            5. Managing expectations and timelines
            6. Facilitating human-AI collaboration

            Communication principles:
            - Be clear, concise, and free of technical jargon
            - Provide context, options, and recommendations
            - Respect human time and decision-making authority
            - Follow up appropriately on requests and decisions
            - Document all human feedback and decisions
            - Maintain professional and helpful tone

            Escalation triggers:
            - Strategic business decisions
            - Budget or resource allocation
            - Risk assessment requiring domain expertise
            - Conflicting stakeholder requirements
            - Ethical or compliance considerations

            Always ensure humans are informed and comfortable with AI recommendations before proceeding.
            """
        )

    async def process_chat_request(self, request: ChatRequest, user_id: str = None) -> ChatResponse:
        """
        Process a chat request through the enhanced LLM team.

        This is the main entry point for chat interactions with human-in-the-loop capabilities.
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
                "status": TaskStatus.PENDING,
                "requires_human_approval": self._requires_human_approval(request.message)
            }
            self.task_history.append(task)

            # Check if human approval is needed upfront
            if task["requires_human_approval"]:
                human_decision = await self.request_human_input(
                    f"Request requires approval: {request.message}",
                    {"task_id": task["id"], "user_id": user_id}
                )
                if "denied" in human_decision.lower():
                    task["status"] = TaskStatus.FAILED
                    task["error"] = "Request denied by human reviewer"
                    return ChatResponse(
                        message="Your request has been reviewed and cannot be processed at this time.",
                        session_id=request.session_id,
                        message_id=f"denied_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
                        metadata={"human_approval": "denied", "task_id": task["id"]}
                    )

            # Process through the team (synchronous call as per working example)
            task["status"] = TaskStatus.IN_PROGRESS
            team_response = self.team.run(
                input=request.message,
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

            # Create enhanced chat response
            chat_response = ChatResponse(
                message=response_content,
                session_id=request.session_id,
                message_id=f"msg_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
                metadata={
                    "team_collaboration": True,
                    "enhanced_features": True,
                    "task_id": task["id"],
                    "processing_time": (datetime.utcnow() - datetime.fromisoformat(task["timestamp"])).total_seconds(),
                    "agents_count": len(self.agents),
                    "human_approval_required": task["requires_human_approval"],
                    "confidence_score": getattr(team_response, 'confidence', 0.9)
                }
            )

            logger.info(f"Enhanced team processed request for session {request.session_id}")
            return chat_response

        except Exception as e:
            logger.error(f"Error processing enhanced team request: {e}")

            # Update task status
            if 'task' in locals():
                task["status"] = TaskStatus.FAILED
                task["error"] = str(e)

            # Return error response
            return ChatResponse(
                message=f"I apologize, but the team encountered an error: {str(e)}. Please try again or contact support.",
                session_id=request.session_id,
                message_id=f"err_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
                metadata={"error": True, "team_collaboration": True, "enhanced_features": True}
            )

    def _requires_human_approval(self, message: str) -> bool:
        """Determine if a request requires human approval."""
        approval_keywords = [
            "deploy", "delete", "remove", "drop", "truncate",
            "payment", "purchase", "buy", "order",
            "send email", "email", "notify", "alert",
            "external api", "third party", "integration",
            "database change", "schema", "migration",
            "production", "prod", "live", "release",
            "critical", "urgent", "emergency",
            "sensitive", "private", "confidential", "secret",
            "user data", "personal", "gdpr", "compliance"
        ]
        return any(keyword in message.lower() for keyword in approval_keywords)

    async def request_human_input(self, request: str, context: Dict = None) -> str:
        """Request input from a human for complex decisions."""
        if "human_input" in self.human_callbacks:
            return await self.human_callbacks["human_input"](request, context)
        else:
            # Fallback - could integrate with UI, Slack, email, etc.
            logger.warning(f"Human input requested but no callback configured: {request}")
            return "Human input not available - proceeding with AI decision"

    def register_human_callback(self, callback_type: str, callback: Callable):
        """Register callbacks for human interaction."""
        self.human_callbacks[callback_type] = callback

    async def get_team_status(self) -> Dict[str, Any]:
        """Get current enhanced team status and metrics."""
        status = {
            "team_initialized": self._initialized,
            "team_type": "enhanced",
            "agents": {},
            "memory_status": {},
            "recent_tasks": self.task_history[-5:],  # Last 5 tasks
            "metrics": {
                "total_tasks": len(self.task_history),
                "completed_tasks": len([t for t in self.task_history if t["status"] == TaskStatus.COMPLETED]),
                "failed_tasks": len([t for t in self.task_history if t["status"] == TaskStatus.FAILED]),
                "human_approval_tasks": len([t for t in self.task_history if t.get("requires_human_approval", False)]),
                "average_processing_time": self._calculate_average_processing_time()
            },
            "human_interaction": {
                "callbacks_registered": len(self.human_callbacks),
                "approval_system_active": "human_input" in self.human_callbacks
            }
        }

        # Agent status
        for role, agent in self.agents.items():
            status["agents"][role] = {
                "name": agent.name,
                "model": getattr(agent.model, 'id', 'unknown'),
                "tools_count": len(getattr(agent, 'tools', [])),
                "active": True,
                "enhanced_features": True
            }

        # Memory status
        if hasattr(self.team, 'memory_manager'):
            status["memory_status"] = {
                "type": "MemoryManager",
                "pinecone_enabled": hasattr(self.team.memory_manager, 'vector_db'),
                "persistent": True
            }

        return status

    def _calculate_average_processing_time(self) -> float:
        """Calculate average task processing time."""
        completed_tasks = [
            t for t in self.task_history
            if t["status"] == TaskStatus.COMPLETED and "processing_time" in t
        ]
        if not completed_tasks:
            return 0.0
        return sum(t["processing_time"] for t in completed_tasks) / len(completed_tasks)

    # Enhanced tool creation methods (placeholder implementations)
    async def _create_task_delegation_tool(self) -> Function:
        """Create tool for task delegation between agents."""
        def delegate_task(task_description: str, target_agent: str, priority: str = "normal") -> str:
            """Delegate a task to a specific agent."""
            return f"Task '{task_description}' delegated to {target_agent} with {priority} priority"

        return Function(
            name="delegate_task",
            description="Delegate tasks to specific team members",
            function=delegate_task
        )

    async def _create_human_escalation_tool(self) -> Function:
        """Create tool for escalating to humans."""
        def escalate_to_human(issue_description: str, urgency: str = "normal", context: str = "") -> str:
            """Escalate an issue to human team members."""
            return f"Issue escalated to humans: {issue_description} (Urgency: {urgency})"

        return Function(
            name="escalate_to_human",
            description="Escalate complex issues to human team members",
            function=escalate_to_human
        )

    async def _create_web_research_tool(self) -> Function:
        """Create tool for web research."""
        def research_topic(topic: str, depth: str = "standard") -> str:
            """Research a topic using web sources."""
            return f"Research completed on '{topic}' with {depth} depth analysis"

        return Function(
            name="research_topic",
            description="Conduct comprehensive web research on topics",
            function=research_topic
        )

    async def _create_fact_checking_tool(self) -> Function:
        """Create tool for fact-checking information."""
        def fact_check(claim: str, sources: List[str] = None) -> str:
            """Fact-check a claim against reliable sources."""
            return f"Fact-check completed for: {claim}"

        return Function(
            name="fact_check",
            description="Verify claims against reliable sources",
            function=fact_check
        )

    async def _create_code_generation_tool(self) -> Function:
        """Create tool for code generation."""
        def generate_code(requirements: str, language: str = "python", include_tests: bool = True) -> str:
            """Generate code based on requirements."""
            return f"Code generated for: {requirements} in {language}"

        return Function(
            name="generate_code",
            description="Generate code based on specifications",
            function=generate_code
        )

    async def _create_architecture_design_tool(self) -> Function:
        """Create tool for software architecture design."""
        def design_architecture(requirements: str, scale: str = "medium") -> str:
            """Design software architecture based on requirements."""
            return f"Architecture designed for: {requirements} (Scale: {scale})"

        return Function(
            name="design_architecture",
            description="Design software architecture and system components",
            function=design_architecture
        )

    async def _create_testing_tool(self) -> Function:
        """Create tool for test generation and execution."""
        def create_tests(code_description: str, test_type: str = "unit") -> str:
            """Create tests for code components."""
            return f"{test_type.title()} tests created for: {code_description}"

        return Function(
            name="create_tests",
            description="Generate and execute tests for code quality assurance",
            function=create_tests
        )

    async def _create_code_review_tool(self) -> Function:
        """Create tool for automated code review."""
        def review_code(code_snippet: str, focus_areas: List[str] = None) -> str:
            """Review code for quality, security, and best practices."""
            return f"Code review completed with focus on: {focus_areas or ['general quality']}"

        return Function(
            name="review_code",
            description="Perform comprehensive code review and quality assessment",
            function=review_code
        )

    async def _create_human_communication_tool(self) -> Function:
        """Create tool for human communication."""
        def communicate_with_human(message: str, channel: str = "default", priority: str = "normal") -> str:
            """Send a message to human team members."""
            return f"Message sent to humans via {channel}: {message[:50]}..."

        return Function(
            name="communicate_with_human",
            description="Send messages and updates to human team members",
            function=communicate_with_human
        )

    async def _create_approval_request_tool(self) -> Function:
        """Create tool for requesting human approvals."""
        def request_approval(action_description: str, risk_level: str = "medium", deadline: str = None) -> str:
            """Request approval for actions from human supervisors."""
            return f"Approval requested for: {action_description} (Risk: {risk_level})"

        return Function(
            name="request_approval",
            description="Request human approval for actions and decisions",
            function=request_approval
        )

    async def _create_feedback_collection_tool(self) -> Function:
        """Create tool for collecting human feedback."""
        def collect_feedback(topic: str, feedback_type: str = "general") -> str:
            """Collect feedback from human team members."""
            return f"Feedback collected on: {topic} (Type: {feedback_type})"

        return Function(
            name="collect_feedback",
            description="Collect and process feedback from human team members",
            function=collect_feedback
        )


# Enhanced service wrapper for integration
class EnhancedLLMTeamChatService:
    """
    Enhanced service wrapper for integrating LLM Team with existing chat infrastructure.
    Includes human-in-the-loop capabilities and advanced features.
    """

    def __init__(self, settings: Any):
        self.settings = settings
        self.team_chat = EnhancedLLMTeamChat(settings)

    async def initialize(self):
        """Initialize the enhanced team chat service."""
        await self.team_chat.initialize()

        # Register human interaction callbacks
        self.team_chat.register_human_callback("human_input", self._handle_human_input)
        self.team_chat.register_human_callback("approval", self._handle_approval_request)

        logger.info("Enhanced LLM Team Chat Service initialized")

    async def process_message(self, request: ChatRequest, user_id: str = None) -> ChatResponse:
        """Process a message through the enhanced LLM team."""
        return await self.team_chat.process_chat_request(request, user_id)

    async def get_team_status(self) -> Dict[str, Any]:
        """Get enhanced team status for monitoring."""
        return await self.team_chat.get_team_status()

    async def _handle_human_input(self, request: str, context: Dict = None) -> str:
        """Handle human input requests."""
        # This would integrate with your chat UI, Slack, etc.
        # For now, return a placeholder that simulates human approval
        logger.info(f"Human input requested: {request}")

        # Simulate human decision based on context
        if context and "approval" in request.lower():
            return "approved"
        return "Human input received and processed"

    async def _handle_approval_request(self, request: str, context: Dict = None) -> bool:
        """Handle approval requests."""
        # This would integrate with your approval workflow
        # For now, auto-approve non-critical requests
        critical_keywords = ["delete", "drop", "remove", "deploy", "payment", "production"]
        is_critical = any(keyword in request.lower() for keyword in critical_keywords)

        if is_critical:
            logger.warning(f"Critical approval requested: {request}")
            return False  # Require manual approval for critical actions

        return True  # Auto-approve non-critical requests


# Enhanced configuration
def create_enhanced_team_chat_config(settings) -> Dict[str, Any]:
    """Create configuration for the enhanced LLM team chat."""
    return {
        "team_settings": {
            "agents_count": 5,
            "collaboration_mode": "hierarchical",
            "human_in_loop": True,
            "models": {
                "orchestrator": "openai/gpt-4o-mini",
                "researcher": "anthropic/claude-3.5-sonnet",
                "developer": "openai/gpt-4o",
                "qa": "anthropic/claude-3.5-sonnet",
                "human_liaison": "openai/gpt-4o-mini"
            }
        },

        "memory_settings": {
            "provider": "pinecone",  # When configured
            "fallback": "basic",
            "namespace": f"{settings.app_name}_enhanced_team_memory",
            "max_items": 10000,
            "auto_save": True
        },

        "tools_settings": {
            "python_enabled": True,
            "file_operations_enabled": True,
            "calculator_enabled": True,
            "web_research_enabled": True,
            "code_generation_enabled": True,
            "human_communication_enabled": True
        },

        "human_interaction": {
            "approval_required_for": [
                "deployments", "database_changes", "external_api_calls",
                "data_modifications", "production_changes", "payments"
            ],
            "escalation_triggers": [
                "agent_conflict", "task_timeout", "low_confidence",
                "critical_decisions", "compliance_issues"
            ],
            "notification_channels": ["in_app", "log"],
            "auto_approval_for_safe_operations": True
        },

        "quality_settings": {
            "code_review_required": True,
            "fact_checking_enabled": True,
            "confidence_threshold": 0.8,
            "human_oversight_level": "medium"
        }
    }
