"""
Orchestrator Service - Coordinates multi-agent workflow for chat requests.
Uses Agno teams and tools to dynamically handle queries.
"""

import asyncio
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional
from pydantic import BaseModel, Field

from agno.agent import Agent
from agno.db.postgres import PostgresDb
from agno.models.openrouter import OpenRouter
from agno.team import Team

from app.agents.tools.query_planner_tool import QueryPlannerTool
from app.agents.tools.rag_retrieval_tool import RAGRetrievalTool
from app.agents.tools.web_search_tool import WebSearchTool
from app.agents.tools.data_analysis_tool import DataAnalysisTool
from app.agents.tools.nlp_tool import NLPTool
from app.agents.tools.visualization_tool import VisualizationTool
from app.agents.tools.citation_tool import CitationTool
from app.agents.tools.tool_registry import ToolRegistry
from app.config import get_settings
from app.models.chat import ChatRequest, ChatResponse
from app.database.models.llm_call import LLMCallTypeEnum, LLMCallStatusEnum
from app.database.repositories.chat_message_step import ChatMessageStepRepository
from app.utils.logging import get_logger

logger = get_logger("orchestrator_service")


# Agent Output Schemas

class IntentType(str, Enum):
    SUMMARIZATION = "summarization"
    AGGREGATION = "aggregation"
    FILTERING = "filtering"
    RANKING = "ranking"
    TREND_ANALYSIS = "trend_analysis"
    GAP_ANALYSIS = "gap_analysis"
    COMPETITIVE_ANALYSIS = "competitive_analysis"
    GENERAL_INQUIRY = "general_inquiry"

class OutputFormat(str, Enum):
    TEXT = "text"
    VISUALIZATION = "visualization"
    CITED_SUMMARY = "cited_summary"
    DETAILED_REPORT = "detailed_report"

class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class QueryPlan(BaseModel):
    """Query planner agent output schema."""
    intent: IntentType = Field(..., description="The identified intent of the user's query")
    required_data_sources: List[str] = Field(default_factory=list, description="List of required data sources")
    requires_analysis: bool = Field(default=False, description="Whether the query requires data analysis")
    requires_visualization: bool = Field(default=False, description="Whether visualizations would be helpful")
    output_format: OutputFormat = Field(default=OutputFormat.TEXT, description="Expected output format")
    key_topics: List[str] = Field(default_factory=list, description="Key topics or entities mentioned")

class DataRetrievalResult(BaseModel):
    """Data agent output schema."""
    summary: str = Field(..., description="Brief summary of retrieved data")
    total_sources: int = Field(default=0, description="Total number of sources retrieved")
    rag_results: List[Dict[str, Any]] = Field(default_factory=list, description="Results from RAG/vector database")
    web_results: List[Dict[str, Any]] = Field(default_factory=list, description="Results from web search")

class AnalysisResult(BaseModel):
    """Analysis agent output schema."""
    summary: str = Field(..., description="Brief summary of analysis findings")
    key_findings: List[str] = Field(default_factory=list, description="List of key findings from analysis")
    statistical_insights: Dict[str, Any] = Field(default_factory=dict, description="Statistical analysis results")
    nlp_insights: Dict[str, Any] = Field(default_factory=dict, description="NLP analysis results")
    visualizations: List[Dict[str, Any]] = Field(default_factory=list, description="Generated visualizations")

class SynthesisResult(BaseModel):
    """Synthesis agent output schema."""
    response: str = Field(..., description="Final synthesized response to user")
    confidence_level: ConfidenceLevel = Field(default=ConfidenceLevel.MEDIUM, description="Confidence level in the response")
    citations: List[Dict[str, Any]] = Field(default_factory=list, description="List of citations with sources")
    recommendations: List[str] = Field(default_factory=list, description="Actionable recommendations")


class OrchestratorService:
    """
    Orchestrates multi-agent workflow for processing chat requests.
    
    Uses Agno Team with specialized agents and tools to:
    1. Analyze query intent and requirements
    2. Retrieve data from RAG/web as needed
    3. Process data with analytics/NLP
    4. Generate visualizations
    5. Synthesize final response with citations
    """
    
    def __init__(self, settings: Any = None):
        self.settings = settings or get_settings()
        self.team: Optional[Team] = None
        self.tool_registry = ToolRegistry()
        self._initialized = False
    
    async def initialize(self):
        """Initialize the orchestrator with Agno team and tools."""
        if self._initialized:
            return
        
        try:
            # Register all tools
            self._register_tools()
            
            # Create database for persistence
            db = await self._create_persistence_db()
            
            # Create model
            model = self._create_model()
            
            # Create specialized agents
            planner_agent = await self._create_planner_agent(model, db)
            data_agent = await self._create_data_agent(model, db)
            analysis_agent = await self._create_analysis_agent(model, db)
            synthesis_agent = await self._create_synthesis_agent(model, db)
            
            # Create the team
            self.team = Team(
                name="Query Orchestration Team",
                members=[planner_agent, data_agent, analysis_agent, synthesis_agent],
                model=model,
                db=db,
                enable_user_memories=True if db else False,
                instructions=self._get_team_instructions(),
                stream_intermediate_steps=True,
                stream=True,
                stream_member_events=True,
                markdown=True,  # Enable markdown for better formatting
                show_members_responses=True,  # Show intermediate agent responses
                # debug_mode=True,
                # debug_level=3,
            )
            
            self._initialized = True
            logger.info("Orchestrator service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator: {e}")
            raise
    
    def _register_tools(self):
        """Register all available tools."""
        self.tool_registry.register(QueryPlannerTool())
        self.tool_registry.register(RAGRetrievalTool())
        self.tool_registry.register(WebSearchTool())
        self.tool_registry.register(DataAnalysisTool())
        self.tool_registry.register(NLPTool())
        self.tool_registry.register(VisualizationTool())
        self.tool_registry.register(CitationTool())
        
        logger.info(f"Registered {len(self.tool_registry)} tools")
    
    async def _create_persistence_db(self) -> Optional[PostgresDb]:
        """Create PostgreSQL database for persistence."""
        try:
            db_config = self.settings.parse_database_url()
            db_url = (
                f"postgresql+psycopg://{db_config['user']}:{db_config['password']}"
                f"@{db_config['host']}:{db_config['port']}"
                f"/{db_config['database']}"
            )
            
            db = PostgresDb(
                db_url=db_url,
                table_name="agno_orchestrator"
            )
            logger.info("Created PostgreSQL DB for orchestrator persistence")
            return db
        except Exception as e:
            logger.warning(f"Failed to create persistence DB: {e}")
            return None
    
    def _create_model(self):
        """Create OpenRouter model instance."""
        api_key = self.settings.get_secret("openrouter_api_key")
        if not api_key:
            raise ValueError("OpenRouter API key not configured")
        
        api_key_str = str(api_key) if hasattr(api_key, '__str__') else api_key
        
        return OpenRouter(
            id=self.settings.default_model,
            api_key=api_key_str,
            max_tokens=4096  # Increase from default to handle long function calls
        )
    
    async def _create_planner_agent(self, model, db) -> Agent:
        """Create query planning agent."""
        planner_tool = self.tool_registry.get("query_planner")
        
        return Agent(
            name="Query Planner",
            role="Analyze user queries and create execution plans",
            model=model,
            db=db,
            tools=[planner_tool.run] if planner_tool else [],
            output_schema=QueryPlan,
            instructions="""You are the Query Planner. Your role is to:
1. Analyze user queries to understand intent
2. Determine the optimal output format
3. Identify required data sources and processing

Always use the query_planner tool first to analyze the query.
Be thorough and strategic in your planning."""
        )
    
    async def _create_data_agent(self, model, db) -> Agent:
        """Create data retrieval agent."""
        rag_tool = self.tool_registry.get("rag_retrieval")
        web_tool = self.tool_registry.get("web_search")
        
        tools = []
        if rag_tool:
            tools.append(rag_tool.run)
        if web_tool:
            tools.append(web_tool.run)
        
        return Agent(
            name="Data Agent",
            role="Retrieve data from vector database and web",
            model=model,
            db=db,
            tools=tools,
            output_schema=DataRetrievalResult,
            instructions="""You are the Data Agent. Your role is to:
1. Search the vector database (RAG) for relevant reviews
2. Search the web for external information
3. Combine and organize retrieved data

Use rag_retrieval for internal reviews and web_search for external info.
Be selective and retrieve high-quality, relevant data."""
        )
    
    async def _create_analysis_agent(self, model, db) -> Agent:
        """Create data analysis agent."""
        analysis_tool = self.tool_registry.get("data_analysis")
        nlp_tool = self.tool_registry.get("nlp_analysis")
        viz_tool = self.tool_registry.get("visualization")
        
        tools = []
        if analysis_tool:
            tools.append(analysis_tool.run)
        if nlp_tool:
            tools.append(nlp_tool.run)
        if viz_tool:
            tools.append(viz_tool.run)
        
        return Agent(
            name="Analysis Agent",
            role="Process data with analytics and NLP",
            model=model,
            db=db,
            tools=tools,
            output_schema=AnalysisResult,
            instructions="""You are the Analysis Agent. Your role is to:
1. Perform statistical analysis on data
2. Extract insights using NLP
3. Generate visualizations

Use data_analysis for statistics, nlp_analysis for text, and visualization for charts.
Be insightful and find meaningful patterns in the data."""
        )
    
    async def _create_synthesis_agent(self, model, db) -> Agent:
        """Create response synthesis agent."""
        citation_tool = self.tool_registry.get("citation")
        
        return Agent(
            name="Synthesis Agent",
            role="Generate final response with proper citations",
            model=model,
            db=db,
            tools=[citation_tool.run] if citation_tool else [],
            output_schema=SynthesisResult,
            instructions="""You are the Synthesis Agent. Your role is to:
1. Combine insights from data and analysis
2. Format sources with proper citations
3. Generate clear, comprehensive responses

Use the citation tool to format sources properly.
Be clear, accurate, and well-structured in your responses."""
        )
    
    def _get_team_instructions(self) -> str:
        """Get instructions for the team coordinator."""
        return """You coordinate a team of AI agents to help users understand their product feedback and customer data.

Your team:
1. Query Planner - Analyzes what the user wants and determines the best approach (outputs structured QueryPlan)
2. Data Agent - Retrieves data from review database and web (outputs structured DataRetrievalResult)
3. Analysis Agent - Processes data with statistics and text analysis (outputs structured AnalysisResult)
4. Synthesis Agent - Creates clear, well-cited responses (outputs structured SynthesisResult)

Each agent outputs structured data that the next agent can use.

Process:
1. First, understand what the user needs
2. Delegate to appropriate agents based on the requirements
3. Coordinate data retrieval, analysis, and synthesis
4. Ensure responses are actionable and well-supported

Be flexible and adapt to the user's specific question - whether it's about reviews, features, competitors, or general questions."""
    
    async def process_message_stream(
        self,
        request: ChatRequest,
        user_id: Optional[str] = None,
        db: Optional[Any] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process a chat message with streaming updates.
        
        Yields progress updates including:
        - Agent step events (start, content, complete)
        - Final response streaming
        - Completion notification
        
        Args:
            request: Chat request
            user_id: User ID
            db: Database session
            
        Yields:
            Dict with update type and data
        """
        if not self._initialized:
            await self.initialize()
        
        session_id = request.session_id or "default"
        
        # State tracking for agent steps
        active_steps = {}  # step_id -> {agent_name, content_buffer, started_at, step_order}
        completed_steps = []  # For DB storage
        current_step_id = None
        current_agent = None  # Track which agent is currently active
        step_counter = 0
        
        try:
            # Send initial status
            yield {
                "type": "connected",
                "data": {}
            }
            
            # Build context message
            context_message = await self._build_context_message(request, db)
            
            # Send context built status
            yield {
                "type": "status",
                "data": {"status": "context_ready", "message": "Analyzing query..."}
            }
            
            logger.info(f"Starting team execution for session {session_id}")
            
            # Execute team with streaming
            response_content = ""
            chunk_count = 0
            
            try:
                logger.info("Creating team stream...")
                stream = self.team.arun(
                    context_message,
                    user_id=user_id,
                    session_id=session_id,
                    stream=True,
                    stream_intermediate_steps=True
                )
                
                logger.info("Team stream created, starting iteration...")
                
                # Send status that team is now executing
                yield {
                    "type": "status",
                    "data": {"status": "team_executing", "message": "Team is processing..."}
                }
                
                async for chunk in stream:
                    chunk_count += 1
                    event_type = getattr(chunk, 'event', 'N/A')
                    
                    # Skip duplicate events
                    if event_type in ["TeamRunCompleted", "TeamRunResponse"]:
                        continue
                    
                    logger.info(f"Chunk {chunk_count}: {type(chunk).__name__}, event: {event_type}")
                    
                    # Extract agent name from chunk
                    agent_name = getattr(chunk, 'agent_id', None) or getattr(chunk, 'agent', None)
                    
                    # Only emit agent_step_start when agent CHANGES
                    if agent_name and agent_name != current_agent:
                        # Complete previous agent step if exists
                        if current_step_id and current_step_id in active_steps:
                            prev_step_data = active_steps.pop(current_step_id)
                            
                            # Process buffered content from previous agent
                            if prev_step_data['content_buffer']:
                                # Check if buffer has structured (BaseModel) content
                                structured_items = [item for item in prev_step_data['content_buffer'] if isinstance(item, BaseModel)]
                                
                                if structured_items:
                                    # Use the last structured item
                                    full_content = structured_items[-1]
                                    is_structured = True
                                    try:
                                        content_dict = full_content.model_dump()
                                    except Exception as e:
                                        content_dict = str(full_content)
                                        is_structured = False
                                else:
                                    # Join only string items
                                    string_items = [str(item) for item in prev_step_data['content_buffer'] if isinstance(item, str)]
                                    full_content = ''.join(string_items)
                                    content_dict = full_content
                                    is_structured = False
                                
                                # Store completed step
                                completed_steps.append({
                                    'agent_name': prev_step_data['agent_name'],
                                    'content': content_dict,
                                    'is_structured': is_structured,
                                    'step_order': prev_step_data['step_order']
                                })
                                
                                # Emit completion to frontend
                                yield {
                                    "type": "agent_step_complete",
                                    "data": {
                                        "step_id": current_step_id,
                                        "agent_name": prev_step_data['agent_name'],
                                        "content": content_dict,
                                        "is_structured": is_structured,
                                        "step_order": prev_step_data['step_order']
                                    }
                                }
                        
                        # Start new agent step
                        current_agent = agent_name
                        step_id = str(uuid.uuid4())
                        current_step_id = step_id
                        
                        active_steps[step_id] = {
                            'agent_name': agent_name,
                            'content_buffer': [],
                            'started_at': datetime.utcnow(),
                            'step_order': step_counter
                        }
                        step_counter += 1
                        
                        logger.info(f"🤖 Agent switched to: {agent_name} (step_id: {step_id})")
                        
                        # Emit to frontend with step number
                        yield {
                            "type": "agent_step_start",
                            "data": {
                                "agent_name": agent_name,
                                "step_id": step_id,
                                "step_order": step_counter - 1,  # step_counter was already incremented
                                "timestamp": datetime.utcnow().isoformat()
                            }
                        }
                    
                    # Handle content from actual streaming events
                    if event_type in ["RunResponse", "RunContent", "AgentRunContent"] and current_step_id and current_step_id in active_steps:
                        if hasattr(chunk, 'content') and chunk.content:
                            content = chunk.content
                            
                            # If it's a BaseModel, store it as structured data
                            if isinstance(content, BaseModel):
                                active_steps[current_step_id]['content_buffer'].append(content)
                                logger.debug(f"Accumulating structured content for step {current_step_id}")
                            elif isinstance(content, str):
                                active_steps[current_step_id]['content_buffer'].append(content)
                                logger.debug(f"Accumulating text content for step {current_step_id}: {content[:50]}...")
                                
                                # Stream text content to frontend
                                yield {
                                    "type": "agent_step_content",
                                    "data": {
                                        "step_id": current_step_id,
                                        "content_chunk": content
                                    }
                                }
                    
                    # Note: Agent completion is handled when switching agents above
                    # TeamToolCallCompleted is mostly redundant but we can log it
                    if event_type == "TeamToolCallCompleted":
                        logger.debug("TeamToolCallCompleted event received")
                    
                    # Handle TeamRunContent - final response streaming (ONLY from team coordinator, not agents)
                    elif event_type == "TeamRunContent":
                        # Skip if this is an agent's structured output - we only want the final synthesis
                        if hasattr(chunk, 'content') and isinstance(chunk.content, BaseModel):
                            logger.debug(f"Skipping structured output from TeamRunContent")
                            continue
                        
                        content_chunk = chunk.content if hasattr(chunk, 'content') else str(chunk)
                        if isinstance(content_chunk, str):
                            response_content += content_chunk
                            logger.debug(f"Streaming final content: {content_chunk[:50]}...")
                            yield {
                                "type": "content",
                                "data": {"content": content_chunk}
                            }
                    
                    # Handle any chunk with 'content' for final response
                    elif hasattr(chunk, 'content') and chunk.content and event_type not in ["TeamRunResponse", "RunContent"]:
                        content_chunk = chunk.content
                        
                        # Skip structured outputs (they're handled by agent steps)
                        if isinstance(content_chunk, BaseModel):
                            continue
                        
                        # Only process string content
                        if isinstance(content_chunk, str):
                            # Only add new content (avoid duplicates)
                            if not response_content or not content_chunk.startswith(response_content):
                                if len(content_chunk) > len(response_content):
                                    # Extract only the new part
                                    new_content = content_chunk[len(response_content):]
                                    response_content = content_chunk
                                    logger.debug(f"Streaming new content: {new_content[:50]}...")
                                    yield {
                                        "type": "content",
                                        "data": {"content": new_content}
                                    }
                    
                    # Handle TeamRunResponse - final response
                    elif event_type == "TeamRunResponse":
                        logger.debug("Received TeamRunResponse")
                        if hasattr(chunk, 'content') and chunk.content:
                            full_content = chunk.content
                            logger.info(f"Got full response content: {len(full_content)} chars")
                            
                            # If we haven't streamed anything yet, stream it now
                            if len(response_content) == 0:
                                logger.info("No content was streamed - manually chunking response")
                                chunk_size = 50
                                for i in range(0, len(full_content), chunk_size):
                                    content_chunk = full_content[i:i+chunk_size]
                                    yield {
                                        "type": "content",
                                        "data": {"content": content_chunk}
                                    }
                                    await asyncio.sleep(0.01)
                            # If partially streamed, send remainder
                            elif len(full_content) > len(response_content):
                                remaining = full_content[len(response_content):]
                                logger.info(f"Streaming remaining content: {len(remaining)} chars")
                                yield {
                                    "type": "content",
                                    "data": {"content": remaining}
                                }
                            
                            response_content = full_content
                        
                        # Log LLM calls from messages if available
                        if hasattr(chunk, 'messages'):
                            for msg in chunk.messages:
                                if msg.role == 'assistant' and hasattr(msg, 'metrics') and msg.metrics:
                                    await self._log_llm_call(msg, user_id, session_id, db)
                
                # Complete any remaining active step
                if current_step_id and current_step_id in active_steps:
                    final_step_data = active_steps.pop(current_step_id)
                    
                    if final_step_data['content_buffer']:
                        # Check if buffer has structured (BaseModel) content
                        structured_items = [item for item in final_step_data['content_buffer'] if isinstance(item, BaseModel)]
                        
                        if structured_items:
                            # Use the last structured item
                            full_content = structured_items[-1]
                            is_structured = True
                            try:
                                content_dict = full_content.model_dump()
                            except Exception as e:
                                content_dict = str(full_content)
                                is_structured = False
                        else:
                            # Join only string items
                            string_items = [str(item) for item in final_step_data['content_buffer'] if isinstance(item, str)]
                            full_content = ''.join(string_items)
                            content_dict = full_content
                            is_structured = False
                        
                        # Store completed step
                        completed_steps.append({
                            'agent_name': final_step_data['agent_name'],
                            'content': content_dict,
                            'is_structured': is_structured,
                            'step_order': final_step_data['step_order']
                        })
                        
                        # Emit completion to frontend
                        yield {
                            "type": "agent_step_complete",
                            "data": {
                                "step_id": current_step_id,
                                "agent_name": final_step_data['agent_name'],
                                "content": content_dict,
                                "is_structured": is_structured
                            }
                        }
                        
                        # If this is the Synthesis Agent, extract the response text
                        if final_step_data['agent_name'] == 'Synthesis Agent' and is_structured and 'response' in content_dict:
                            response_content = content_dict['response']
                            logger.info(f"Extracted response from SynthesisResult: {len(response_content)} chars")
                
                logger.info(f"Team execution completed: {chunk_count} chunks, {len(completed_steps)} agent steps, {len(response_content)} chars")
                
            except Exception as stream_error:
                logger.error(f"Error during team streaming: {stream_error}", exc_info=True)
                # Fallback to non-streaming
                logger.info("Falling back to non-streaming execution")
                
                yield {
                    "type": "status",
                    "data": {"status": "processing", "message": "Processing query..."}
                }
                
                team_response = await self.team.arun(
                    context_message,
                    user_id=user_id,
                    session_id=session_id,
                    stream=False
                )
                
                # Extract response content
                if hasattr(team_response, 'content'):
                    response_content = team_response.content
                elif isinstance(team_response, str):
                    response_content = team_response
                else:
                    response_content = str(team_response)
                
                logger.info(f"Fallback execution got response: {len(response_content)} chars")
                
                # Send all content at once
                if response_content:
                    yield {
                        "type": "content",
                        "data": {"content": response_content}
                    }
            
            # Ensure we have response content - extract ONLY from Synthesis Agent
            if not response_content and completed_steps:
                # Find the Synthesis Agent step (should be the last one)
                synthesis_steps = [s for s in completed_steps if s['agent_name'] == 'Synthesis Agent']
                if synthesis_steps:
                    last_synthesis = synthesis_steps[-1]
                    if last_synthesis['is_structured'] and isinstance(last_synthesis['content'], dict):
                        if 'response' in last_synthesis['content']:
                            response_content = last_synthesis['content']['response']
                            logger.info(f"Extracted response from Synthesis Agent: {len(response_content)} chars")
            
            # If still no content, use a fallback message
            if not response_content:
                response_content = "I've processed your query, but couldn't generate a final response. Please check the agent steps for details."
            
            # Create final response
            chat_response = ChatResponse(
                message=response_content,
                session_id=session_id,
                message_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                metadata={
                    "model": self.settings.default_model,
                    "provider": "agno_team",
                    "user_id": user_id,
                    "agent_steps_count": len(completed_steps)
                }
            )
            
            # Store completed steps - will be done by chat API after getting message_id
            # Include steps in metadata for chat API to save
            chat_response.metadata['completed_steps'] = completed_steps
            
            # Send final response
            yield {
                "type": "complete",
                "data": chat_response.dict()
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            
            yield {
                "type": "error",
                "data": {
                    "error": str(e)
                }
            }
    
    async def process_message(
        self,
        request: ChatRequest,
        user_id: Optional[str] = None,
        db: Optional[Any] = None
    ) -> ChatResponse:
        """
        Process a chat message using the orchestrator team (non-streaming).
        
        Args:
            request: Chat request
            user_id: User ID
            db: Database session
            
        Returns:
            ChatResponse with result
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Run the team to process the query
            session_id = request.session_id or "default"
            
            # Build context message with NeedleAI info and company context
            context_message = await self._build_context_message(request, db)
            
            # Execute team
            team_response = await self.team.arun(
                context_message,
                user_id=user_id,
                session_id=session_id,
                stream=False
            )
            
            # Extract response content
            if hasattr(team_response, 'content'):
                response_content = team_response.content
                
                # If content is a SynthesisResult, extract the response field
                if isinstance(response_content, SynthesisResult):
                    response_content = response_content.response
                elif isinstance(response_content, BaseModel):
                    # Try to extract response field from any structured output
                    try:
                        content_dict = response_content.model_dump()
                        if 'response' in content_dict:
                            response_content = content_dict['response']
                        else:
                            response_content = str(content_dict)
                    except Exception:
                        response_content = str(response_content)
            elif isinstance(team_response, str):
                response_content = team_response
            else:
                response_content = str(team_response)
            
            # Log all LLM calls from team execution
            if hasattr(team_response, 'messages'):
                for msg in team_response.messages:
                    if msg.role == 'assistant' and hasattr(msg, 'metrics') and msg.metrics:
                        # Log this LLM call
                        await self._log_llm_call(msg, user_id, session_id, db)
            
            # Create response
            chat_response = ChatResponse(
                message=response_content,
                session_id=session_id,
                message_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                metadata={
                    "model": self.settings.default_model,
                    "provider": "agno_team",
                    "user_id": user_id
                }
            )
            
            logger.debug(f"Processed message for session {session_id}")
            return chat_response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            
            # Return error response
            return ChatResponse(
                message=f"I encountered an error processing your request: {str(e)}",
                session_id=request.session_id or "default",
                message_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                metadata={
                    "error": str(e)
                }
            )
    
    async def _log_llm_call(
        self,
        message: Any,
        user_id: Optional[str],
        session_id: str,
        db: Optional[Any]
    ):
        """
        Log an LLM call to the database.
        
        Args:
            message: Agno message object with metrics
            user_id: User ID
            session_id: Session ID
            db: Database session
        """
        if not db:
            logger.warning("No database session provided, skipping LLM call logging")
            return
        
        try:
            # Extract metrics
            metrics = getattr(message, 'metrics', None)
            if not metrics:
                return
            
            # Extract model info
            model = getattr(message, 'model', None)
            if not model:
                # Try to get from content or other fields
                model = "unknown"
            
            # Determine call type based on content
            call_type = LLMCallTypeEnum.CHAT
            if hasattr(message, 'tool_calls') and message.tool_calls:
                call_type = LLMCallTypeEnum.SYSTEM
            
            # Extract provider from model string
            provider = "openrouter"
            if "/" in model:
                provider_part = model.split("/")[0]
                if provider_part in ["openai", "anthropic", "google"]:
                    provider = provider_part
            
            # Prepare messages in correct format
            messages = []
            if hasattr(message, 'content') and message.content:
                messages = [{"role": getattr(message, 'role', 'assistant'), "content": str(message.content)[:1000]}]
            
            # Log the call using LLMCallRepository directly
            from app.database.repositories.llm_call import LLMCallRepository
            await LLMCallRepository.create(
                db,
                call_type=call_type,
                provider=provider,
                model=model,
                messages=messages,
                prompt_tokens=getattr(metrics, 'prompt_tokens', 0),
                completion_tokens=getattr(metrics, 'completion_tokens', 0),
                total_tokens=getattr(metrics, 'total_tokens', 0),
                user_id=user_id,
                session_id=session_id,
                status=LLMCallStatusEnum.SUCCESS,
                extra_metadata={
                    "agent": "orchestrator_team",
                    "role": getattr(message, 'role', 'assistant')
                }
            )
            await db.commit()
            logger.debug(f"Logged LLM call for model {model}")
        except Exception as e:
            logger.error(f"Failed to log LLM call: {e}", exc_info=True)
    
    async def _build_context_message(self, request: ChatRequest, db: Optional[Any]) -> str:
        """
        Build context message with NeedleAI info and company context.
        
        Args:
            request: Chat request
            db: Database session
            
        Returns:
            Formatted context message
        """
        # Start with NeedleAI context
        context = """You are NeedleAI, an AI-powered product analytics assistant that helps teams understand customer feedback.

You have access to:
- Product reviews and customer feedback from various sources (G2, Capterra, Trustpilot, etc.)
- Web search for external information
- Analytics tools for statistical analysis
- NLP tools for extracting insights from text
- Visualization tools for creating charts and graphs

Your goal is to provide actionable insights based on customer feedback and data."""
        
        # Add company context if provided
        if request.company_id and db:
            try:
                from app.database.repositories.company import CompanyRepository
                company = await CompanyRepository.get_by_id(db, request.company_id)
                if company:
                    context += f"\n\nCurrent context: Analyzing data for {company.name}"
                    # if company.website:
                    #     context += f" ({company.website})"
                else:
                    context += f"\n\nCurrent context: Analyzing data for company ID {request.company_id}"
            except Exception as e:
                logger.warning(f"Failed to load company info: {e}")
                context += f"\n\nCurrent context: Analyzing data for company ID {request.company_id}"
        
        # Add user's query
        context += f"\n\nUser query: {request.message}"
        
        return context
    
    async def cleanup(self):
        """Cleanup resources."""
        # Cleanup tools
        for tool in self.tool_registry.get_all_tools():
            if hasattr(tool, 'cleanup'):
                try:
                    await tool.cleanup()
                except Exception as e:
                    logger.warning(f"Error cleaning up tool {tool.name}: {e}")
        
        self._initialized = False
        logger.debug("Orchestrator service cleaned up")

