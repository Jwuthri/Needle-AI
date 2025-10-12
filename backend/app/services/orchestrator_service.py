"""
Orchestrator Service - Coordinates multi-agent workflow for chat requests.
Uses Agno teams and tools to dynamically handle queries.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

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
                instructions=self._get_team_instructions()
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
            password = self.settings.get_secret("database_password")
            db_url = (
                f"postgresql+psycopg://{self.settings.database_user}:{password}"
                f"@{self.settings.database_host}:{self.settings.database_port}"
                f"/{self.settings.database_name}"
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
            api_key=api_key_str
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
                session_id=session_id
            )
            
            # Extract response content
            if hasattr(team_response, 'content'):
                response_content = team_response.content
            elif isinstance(team_response, str):
                response_content = team_response
            else:
                response_content = str(team_response)
            
            # TODO: Extract execution steps from team_response
            # For now, mark tree as completed
            tree.complete_tree(response_content[:100])
            
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
                    if company.website:
                        context += f" ({company.website})"
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

