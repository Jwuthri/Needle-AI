"""
LLM Team Chat API Endpoints
===========================

FastAPI router for the LLM team chat functionality.
Integrates with existing chat infrastructure while providing
multi-agent collaboration capabilities.
"""

from typing import Any, Dict, List, Optional

from app.agents.llm_team_example import LLMTeamChatService
from app.api.deps import check_rate_limit, get_current_user
from app.config import get_settings
from app.core.security.clerk_auth import ClerkUser
from app.exceptions import ExternalServiceError, ValidationError
from app.models.base import SuccessResponse
from app.models.chat import ChatRequest, ChatResponse
from app.utils.logging import get_logger
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.security import HTTPBearer

logger = get_logger("team_chat_api")

router = APIRouter()
security = HTTPBearer()

# Global team service instance (initialized on startup)
_team_service: Optional[LLMTeamChatService] = None


async def get_team_service() -> LLMTeamChatService:
    """Get the initialized team service."""
    global _team_service
    if _team_service is None:
        settings = get_settings()
        _team_service = LLMTeamChatService(settings)
        await _team_service.initialize()
    return _team_service


@router.post("/message", response_model=ChatResponse)
async def send_team_message(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    team_service: LLMTeamChatService = Depends(get_team_service),
    current_user: Optional[ClerkUser] = Depends(get_current_user),
    _rate_limit_check = Depends(check_rate_limit)
) -> ChatResponse:
    """
    Send a message to the LLM team for collaborative processing.

    The team will automatically:
    1. Analyze the request and determine required expertise
    2. Delegate tasks to appropriate agents (Researcher, Developer, QA, etc.)
    3. Coordinate between agents for complex multi-step tasks
    4. Request human approval for sensitive operations
    5. Return a comprehensive, well-researched response

    Example requests that showcase team capabilities:
    - "Research the latest AI trends and create a strategic implementation plan"
    - "Build a user authentication system with security best practices"
    - "Analyze this data and create visualizations with recommendations"
    - "Review this code for security vulnerabilities and performance issues"
    """
    try:
        user_id = current_user.user_id if current_user else None

        # Validate request
        if not request.message or not request.message.strip():
            raise ValidationError("Message cannot be empty")

        # Process through the team
        response = await team_service.process_message(request, user_id)

        # Log team collaboration metrics
        background_tasks.add_task(
            _log_team_metrics,
            session_id=request.session_id,
            user_id=user_id,
            agents_involved=response.metadata.get("agents_involved", []),
            processing_time=response.metadata.get("processing_time", 0)
        )

        return response

    except ValidationError as e:
        logger.warning(f"Team chat validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except ExternalServiceError as e:
        logger.error(f"Team chat service error: {e}")
        raise HTTPException(status_code=503, detail=f"Team service unavailable: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected team chat error: {e}")
        raise HTTPException(status_code=500, detail="Internal team processing error")


@router.get("/status", response_model=Dict[str, Any])
async def get_team_status(
    team_service: LLMTeamChatService = Depends(get_team_service),
    current_user: Optional[ClerkUser] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current status of the LLM team.

    Returns information about:
    - Agent availability and health
    - Memory usage and persistence status
    - Recent task performance metrics
    - Tool availability and configuration
    """
    try:
        status = await team_service.get_team_status()

        # Add API-specific information
        status["api_info"] = {
            "endpoint": "/api/v1/team-chat",
            "authenticated": current_user is not None,
            "user_id": current_user.user_id if current_user else None,
            "rate_limits": {
                "requests_per_minute": 10,  # Adjust based on your limits
                "concurrent_sessions": 5
            }
        }

        return status

    except Exception as e:
        logger.error(f"Error getting team status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get team status")


@router.get("/agents", response_model=List[Dict[str, Any]])
async def list_team_agents(
    team_service: LLMTeamChatService = Depends(get_team_service),
    current_user: Optional[ClerkUser] = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    List all available agents in the team and their capabilities.

    Useful for understanding what expertise is available and
    how to best phrase requests for optimal agent selection.
    """
    try:
        team_status = await team_service.get_team_status()
        agents_info = []

        for agent_role, agent_data in team_status.get("agents", {}).items():
            agent_info = {
                "role": agent_role,
                "name": agent_data.get("name"),
                "description": _get_agent_description(agent_role),
                "capabilities": _get_agent_capabilities(agent_role),
                "tools_count": agent_data.get("tools_count", 0),
                "model": agent_data.get("model"),
                "specializes_in": _get_agent_specialization(agent_role),
                "active": agent_data.get("active", False)
            }
            agents_info.append(agent_info)

        return agents_info

    except Exception as e:
        logger.error(f"Error listing team agents: {e}")
        raise HTTPException(status_code=500, detail="Failed to list team agents")


@router.post("/human-input", response_model=SuccessResponse)
async def provide_human_input(
    request: Dict[str, Any],
    team_service: LLMTeamChatService = Depends(get_team_service),
    current_user: ClerkUser = Depends(get_current_user)  # Require authentication
) -> SuccessResponse:
    """
    Provide human input for team decisions.

    Used when the team requests human approval or input for:
    - Code deployments
    - External API calls
    - Data modifications
    - Complex decisions requiring human judgment
    """
    try:
        task_id = request.get("task_id")
        input_type = request.get("type")  # "approval", "feedback", "decision"
        response = request.get("response")

        if not all([task_id, input_type, response]):
            raise ValidationError("task_id, type, and response are required")

        # Process human input (implementation depends on your workflow)
        # This would typically:
        # 1. Find the waiting task
        # 2. Provide the human input to the team
        # 3. Resume processing

        logger.info(f"Human input provided for task {task_id}: {input_type}")

        return SuccessResponse(
            message="Human input received and processed",
            data={"task_id": task_id, "input_type": input_type}
        )

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Error processing human input: {e}")
        raise HTTPException(status_code=500, detail="Failed to process human input")


@router.websocket("/ws/{session_id}")
async def team_chat_websocket(
    websocket: WebSocket,
    session_id: str,
    team_service: LLMTeamChatService = Depends(get_team_service)
):
    """
    WebSocket endpoint for real-time team chat.

    Provides real-time updates on:
    - Agent task assignments and progress
    - Inter-agent communications
    - Human input requests
    - Final responses
    """
    await websocket.accept()

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message = data.get("message", "")

            if not message:
                await websocket.send_json({
                    "type": "error",
                    "message": "Empty message received"
                })
                continue

            # Create chat request
            request = ChatRequest(
                message=message,
                session_id=session_id,
                metadata=data.get("metadata", {})
            )

            # Send acknowledgment
            await websocket.send_json({
                "type": "received",
                "session_id": session_id,
                "timestamp": request.timestamp
            })

            # Process through team (with progress updates)
            try:
                # Send processing status
                await websocket.send_json({
                    "type": "processing",
                    "message": "Team is analyzing your request...",
                    "agents_involved": ["orchestrator"]
                })

                # Process the request
                response = await team_service.process_message(request)

                # Send final response
                await websocket.send_json({
                    "type": "response",
                    "message": response.message,
                    "session_id": response.session_id,
                    "metadata": response.metadata,
                    "timestamp": response.timestamp
                })

            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Team processing error: {str(e)}"
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        await websocket.close()


@router.get("/examples", response_model=List[Dict[str, Any]])
async def get_team_examples() -> List[Dict[str, Any]]:
    """
    Get example requests that showcase team capabilities.

    Helps users understand how to effectively use the team
    for different types of tasks.
    """
    return [
        {
            "category": "Research & Analysis",
            "examples": [
                {
                    "request": "Research the latest trends in AI and machine learning for 2024",
                    "agents_involved": ["Researcher", "Orchestrator"],
                    "expected_outcome": "Comprehensive research report with sources and analysis"
                },
                {
                    "request": "Analyze the competitive landscape for our SaaS product",
                    "agents_involved": ["Researcher", "QA_Reviewer"],
                    "expected_outcome": "Market analysis with recommendations"
                }
            ]
        },
        {
            "category": "Software Development",
            "examples": [
                {
                    "request": "Create a secure user authentication system with JWT tokens",
                    "agents_involved": ["Developer", "QA_Reviewer", "Human_Liaison"],
                    "expected_outcome": "Complete code implementation with tests and security review"
                },
                {
                    "request": "Review this Python code for performance and security issues",
                    "agents_involved": ["Developer", "QA_Reviewer"],
                    "expected_outcome": "Code review with specific improvement recommendations"
                }
            ]
        },
        {
            "category": "Multi-step Projects",
            "examples": [
                {
                    "request": "Research GraphQL best practices, then implement a GraphQL API for our blog",
                    "agents_involved": ["Researcher", "Developer", "QA_Reviewer", "Orchestrator"],
                    "expected_outcome": "Research report followed by working GraphQL implementation"
                },
                {
                    "request": "Design a database schema for an e-commerce platform and generate the migration scripts",
                    "agents_involved": ["Developer", "QA_Reviewer", "Human_Liaison"],
                    "expected_outcome": "Database design with migration scripts and approval workflow"
                }
            ]
        },
        {
            "category": "Human-in-the-Loop",
            "examples": [
                {
                    "request": "Deploy the new feature to production after running all tests",
                    "agents_involved": ["Developer", "QA_Reviewer", "Human_Liaison"],
                    "expected_outcome": "Automated testing followed by human approval for deployment"
                },
                {
                    "request": "Send a summary email to the team about our quarterly performance",
                    "agents_involved": ["Researcher", "Human_Liaison"],
                    "expected_outcome": "Draft email requiring human review before sending"
                }
            ]
        }
    ]


# Helper functions
async def _log_team_metrics(session_id: str, user_id: str, agents_involved: List[str], processing_time: float):
    """Log team collaboration metrics for analysis."""
    try:
        # This would typically log to your analytics system
        logger.info(f"Team metrics - Session: {session_id}, Agents: {agents_involved}, Time: {processing_time}s")
    except Exception as e:
        logger.error(f"Error logging team metrics: {e}")


def _get_agent_description(role: str) -> str:
    """Get human-readable description for an agent role."""
    descriptions = {
        "orchestrator": "Coordinates team activities and manages task delegation",
        "researcher": "Specializes in information gathering, analysis, and fact-checking",
        "developer": "Handles software development, architecture, and technical solutions",
        "qa_reviewer": "Ensures quality through testing, code review, and validation",
        "human_liaison": "Manages human interactions, approvals, and communication"
    }
    return descriptions.get(role, "Specialized AI agent")


def _get_agent_capabilities(role: str) -> List[str]:
    """Get list of capabilities for an agent role."""
    capabilities = {
        "orchestrator": [
            "Task delegation", "Progress tracking", "Conflict resolution",
            "Human escalation", "Team coordination"
        ],
        "researcher": [
            "Web research", "Fact checking", "Data analysis",
            "Market research", "Academic research", "Trend analysis"
        ],
        "developer": [
            "Code generation", "Architecture design", "Database design",
            "API development", "Testing", "Code review", "Security analysis"
        ],
        "qa_reviewer": [
            "Code review", "Test design", "Quality assurance",
            "Performance testing", "Security auditing", "Documentation review"
        ],
        "human_liaison": [
            "Human communication", "Approval coordination", "Feedback collection",
            "Status reporting", "Escalation management"
        ]
    }
    return capabilities.get(role, [])


def _get_agent_specialization(role: str) -> List[str]:
    """Get specialization areas for an agent role."""
    specializations = {
        "orchestrator": ["Project management", "Team coordination", "Decision making"],
        "researcher": ["Information science", "Data analysis", "Market intelligence"],
        "developer": ["Software engineering", "System architecture", "DevOps"],
        "qa_reviewer": ["Quality assurance", "Testing", "Security"],
        "human_liaison": ["Communication", "Change management", "Stakeholder relations"]
    }
    return specializations.get(role, [])
