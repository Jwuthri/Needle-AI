"""
Orchestrator Service - Coordinates multi-agent workflow for chat requests.
Uses Agno teams and tools to dynamically handle queries.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

from agno.agent import Agent
from agno.db.postgres import PostgresDb
from agno.models.openrouter import OpenRouter
from agno.team import Team

from app.agents.execution_tree import ExecutionTree, NodeType
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
from app.database.models.execution_tree import ExecutionNodeType, ExecutionNodeStatus
from app.database.repositories.execution_tree import ExecutionTreeRepository
from app.utils.logging import get_logger

logger = get_logger("orchestrator_service")


class OrchestratorService:
    """
    Orchestrates multi-agent workflow for processing chat requests.
    
    Uses Agno Team with specialized agents and tools to:
    1. Analyze query intent and requirements
    2. Retrieve data from RAG/web as needed
    3. Process data with analytics/NLP
    4. Generate visualizations
    5. Synthesize final response with citations
    
    Tracks all steps in an execution tree for UI visualization.
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
1. Query Planner - Analyzes what the user wants and determines the best approach
2. Data Agent - Retrieves data from review database and web
3. Analysis Agent - Processes data with statistics and text analysis
4. Synthesis Agent - Creates clear, well-cited responses

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
        - Execution tree updates
        - Intermediate steps
        - Tool calls
        - Final response
        
        Args:
            request: Chat request
            user_id: User ID
            db: Database session
            
        Yields:
            Dict with update type and data
        """
        if not self._initialized:
            await self.initialize()
        
        # Initialize execution tree
        tree = ExecutionTree(
            query=request.message,
            session_id=request.session_id
        )
        
        session_id = request.session_id or "default"
        
        # Create execution tree session in database
        db_tree_session = None
        if db:
            try:
                db_tree_session = await ExecutionTreeRepository.create_session(
                    db,
                    session_id=session_id,
                    query=request.message,
                    user_id=user_id,
                    extra_metadata={"model": self.settings.default_model}
                )
                await db.commit()
                logger.debug(f"Created execution tree session: {db_tree_session.id}")
            except Exception as e:
                logger.warning(f"Failed to create execution tree session: {e}")
        
        try:
            # Send initial status
            yield {
                "type": "status",
                "data": {"status": "starting", "message": "Initializing..."}
            }
            
            # Build context message
            context_message = await self._build_context_message(request, db)
            
            # Send context built status
            yield {
                "type": "status",
                "data": {"status": "context_ready", "message": "Analyzing query..."}
            }
            
            logger.info(f"Starting team execution for session {session_id}")
            
            # Execute team with streaming - team.arun returns iterator when stream=True
            response_content = ""
            chunk_count = 0
            
            try:
                stream = self.team.arun(
                    context_message,
                    user_id=user_id,
                    session_id=session_id,
                    stream=True,
                    stream_intermediate_steps=True
                )
                
                # Track active tool calls
                active_tool_nodes = {}  # Map tool_call_id to node_id
                
                async for chunk in stream:
                    chunk_count += 1
                    event_type = getattr(chunk, 'event', 'N/A')
                    logger.debug(f"Received chunk {chunk_count}: {type(chunk).__name__}, event: {event_type}")
                    
                    # Handle ToolCallStarted - agent is calling a tool
                    if event_type == "ToolCallStarted":
                        agent_id = getattr(chunk, 'agent_id', 'unknown')
                        tool_name = getattr(getattr(chunk, 'tool', None), 'tool_name', 'unknown')
                        tool_args = getattr(getattr(chunk, 'tool', None), 'tool_args', {})
                        tool_call_id = getattr(chunk, 'tool_call_id', None)
                        
                        logger.info(f"Tool started: {tool_name} by {agent_id}")
                        
                        # Add to execution tree
                        node_id = tree.start_node(
                            name=f"{agent_id}: {tool_name}",
                            node_type=NodeType.TOOL,
                            input_summary=str(tool_args)[:200] if tool_args else "No args"
                        )
                        
                        # Track this tool call
                        if tool_call_id:
                            active_tool_nodes[tool_call_id] = node_id
                        
                        # Save to database
                        if db and db_tree_session:
                            try:
                                await ExecutionTreeRepository.add_node(
                                    db,
                                    tree_session_id=db_tree_session.id,
                                    node_id=node_id,
                                    node_type=ExecutionNodeType.TOOL,
                                    name=f"{agent_id}: {tool_name}",
                                    agent_id=agent_id,
                                    tool_name=tool_name,
                                    tool_args=tool_args,
                                    input_summary=str(tool_args)[:500] if tool_args else None
                                )
                                await db.commit()
                            except Exception as e:
                                logger.warning(f"Failed to save tree node: {e}")
                        
                        # Send tool call update to frontend
                        yield {
                            "type": "tool_call_started",
                            "data": {
                                "agent_id": agent_id,
                                "tool_name": tool_name,
                                "tool_args": tool_args,
                                "node_id": node_id
                            }
                        }
                        
                        # Send tree update
                        yield {
                            "type": "tree_update",
                            "data": tree.to_dict()
                        }
                    
                    # Handle ToolCallCompleted - tool finished executing
                    elif event_type == "ToolCallCompleted":
                        tool_name = getattr(getattr(chunk, 'tool', None), 'tool_name', 'unknown')
                        tool_result = getattr(getattr(chunk, 'tool', None), 'result', None)
                        tool_call_id = getattr(chunk, 'tool_call_id', None)
                        
                        logger.info(f"Tool completed: {tool_name}")
                        
                        # Complete the node in execution tree
                        if tool_call_id and tool_call_id in active_tool_nodes:
                            node_id = active_tool_nodes[tool_call_id]
                            result_summary = str(tool_result)[:200] if tool_result else "No result"
                            tree.complete_node(node_id, output_summary=result_summary)
                            del active_tool_nodes[tool_call_id]
                            
                            # Update database
                            if db and db_tree_session:
                                try:
                                    await ExecutionTreeRepository.complete_node(
                                        db,
                                        tree_session_id=db_tree_session.id,
                                        node_id=node_id,
                                        output_summary=result_summary,
                                        tool_result=tool_result if isinstance(tool_result, dict) else None
                                    )
                                    await db.commit()
                                except Exception as e:
                                    logger.warning(f"Failed to complete tree node: {e}")
                        
                        # Send tool completion update to frontend
                        yield {
                            "type": "tool_call_completed",
                            "data": {
                                "tool_name": tool_name,
                                "result": str(tool_result)[:500] if tool_result else None
                            }
                        }
                        
                        # Send tree update
                        yield {
                            "type": "tree_update",
                            "data": tree.to_dict()
                        }
                    
                    # Handle TeamRunContent events - this is the main streaming content
                    elif event_type == "TeamRunContent":
                        content_chunk = chunk.content if hasattr(chunk, 'content') else str(chunk)
                        response_content += content_chunk
                        logger.debug(f"Streaming content chunk: {content_chunk[:50]}...")
                        yield {
                            "type": "content",
                            "data": {"content": content_chunk}
                        }
                    
                    # Handle any chunk with 'content' attribute - Agno may send various event types
                    elif hasattr(chunk, 'content') and chunk.content and event_type not in ["TeamRunResponse"]:
                        content_chunk = chunk.content
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
                    
                    # Handle TeamRunResponse - final response with full content
                    elif event_type == "TeamRunResponse":
                        logger.debug("Received TeamRunResponse")
                        if hasattr(chunk, 'content') and chunk.content:
                            full_content = chunk.content
                            logger.info(f"Got full response content: {len(full_content)} chars")
                            
                            # If we haven't streamed anything yet, stream it in chunks now
                            if len(response_content) == 0:
                                logger.info("No content was streamed - manually chunking response")
                                # Stream in reasonable chunks (every ~50 characters for smooth streaming)
                                chunk_size = 50
                                for i in range(0, len(full_content), chunk_size):
                                    content_chunk = full_content[i:i+chunk_size]
                                    yield {
                                        "type": "content",
                                        "data": {"content": content_chunk}
                                    }
                                    # Small delay to simulate streaming
                                    await asyncio.sleep(0.01)
                            # If we've partially streamed, send the remainder
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
                                    
                                    # Update execution tree
                                    node_id = tree.start_node(
                                        name=f"LLM Call: {getattr(msg, 'model', 'unknown')}",
                                        node_type=NodeType.TOOL,
                                        input_summary=str(msg.content)[:100] if msg.content else "Tool call",
                                    )
                                    tree.complete_node(
                                        node_id,
                                        output_summary=f"Tokens: {getattr(msg.metrics, 'total_tokens', 'unknown')}"
                                    )
                                    
                                    # Send tree update
                                    yield {
                                        "type": "tree_update",
                                        "data": tree.to_dict()
                                    }
                
                logger.info(f"Team execution completed with {chunk_count} chunks, response length: {len(response_content)}")
                
            except Exception as stream_error:
                logger.error(f"Error during team streaming: {stream_error}", exc_info=True)
                # If streaming fails, try non-streaming fallback
                logger.info("Falling back to non-streaming execution")
                
                yield {
                    "type": "status",
                    "data": {"status": "processing", "message": "Processing query..."}
                }
                
                team_response = await self.team.arun(
                    context_message,
                    user_id=user_id,
                    session_id=session_id,
                    stream=False,
                    stream_intermediate_steps=True
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
            
            # Complete the tree
            tree.complete_tree(response_content[:100] if response_content else "Complete")
            
            # Complete the tree session in database
            if db and db_tree_session:
                try:
                    await ExecutionTreeRepository.complete_session(
                        db,
                        tree_session_id=db_tree_session.id,
                        result_summary=response_content[:500] if response_content else "Complete"
                    )
                    await db.commit()
                except Exception as e:
                    logger.warning(f"Failed to complete tree session: {e}")
            
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
                    "execution_tree": tree.to_dict()
                }
            )
            
            # Send final response
            yield {
                "type": "complete",
                "data": chat_response.dict()
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            tree.fail_tree(str(e))
            
            # Mark tree session as failed in database
            if db and db_tree_session:
                try:
                    await ExecutionTreeRepository.complete_session(
                        db,
                        tree_session_id=db_tree_session.id,
                        error_message=str(e)
                    )
                    await db.commit()
                except Exception as db_error:
                    logger.warning(f"Failed to mark tree session as failed: {db_error}")
            
            yield {
                "type": "error",
                "data": {
                    "error": str(e),
                    "execution_tree": tree.to_dict()
                }
            }
    
    async def process_message(
        self,
        request: ChatRequest,
        user_id: Optional[str] = None,
        db: Optional[Any] = None
    ) -> ChatResponse:
        """
        Process a chat message using the orchestrator team.
        
        Args:
            request: Chat request
            user_id: User ID
            db: Database session
            
        Returns:
            ChatResponse with result and execution tree
        """
        if not self._initialized:
            await self.initialize()
        
        # Initialize execution tree
        tree = ExecutionTree(
            query=request.message,
            session_id=request.session_id
        )
        
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
                        
                        # Add to execution tree
                        node_id = tree.start_node(
                            name=f"LLM Call: {getattr(msg, 'model', 'unknown')}",
                            node_type=NodeType.TOOL,
                            input_summary=str(msg.content)[:100] if msg.content else "Tool call",
                        )
                        tree.complete_node(
                            node_id,
                            output_summary=f"Tokens: {getattr(msg.metrics, 'total_tokens', 'unknown')}"
                        )
            
            tree.complete_tree(response_content[:100] if response_content else "Complete")
            
            # Create response
            chat_response = ChatResponse(
                message=response_content,
                session_id=session_id,
                message_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                metadata={
                    "model": self.settings.default_model,
                    "provider": "agno_team",
                    "user_id": user_id,
                    "execution_tree": tree.to_dict()
                }
            )
            
            logger.debug(f"Processed message for session {session_id}")
            return chat_response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            tree.fail_tree(str(e))
            
            # Return error response with tree
            return ChatResponse(
                message=f"I encountered an error processing your request: {str(e)}",
                session_id=request.session_id or "default",
                message_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                metadata={
                    "error": str(e),
                    "execution_tree": tree.to_dict()
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

