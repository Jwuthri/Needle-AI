"""
Agno Tree Executor - Executes tree structure using Agno agents with streaming.

Implements step-by-step agent streaming with hooks to capture:
- When each agent starts (pre_hook)
- What each agent outputs (post_hook)
- Real-time streaming to frontend
- Database persistence of steps
"""

import uuid
from datetime import datetime
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional
from pydantic import BaseModel

from agno.agent import Agent
from agno.team import Team
from agno.tools import tool as agno_tool
from agno.models.openrouter import OpenRouter
from agno.db.postgres import PostgresDb

from app.agents.tree.base import Tree, Branch
from app.agents.tree.environment import TreeData, CollectionData
from app.agents.tree.tool import TreeTool
from app.agents.tree.returns import Return
from app.utils.logging import get_logger

logger = get_logger("agno_tree_executor")


class AgentStepCapture:
    """
    Capture agent execution from stream events (not hooks).
    
    Agno's post_hooks don't fire during streaming, only after entire run completes.
    Instead, we capture agent steps by parsing stream events directly.
    """
    
    def __init__(
        self,
        stream_callback: Callable[[Dict[str, Any]], None],
        db_session: Optional[Any] = None,
        message_id: Optional[str] = None
    ):
        """
        Initialize step capture.
        
        Args:
            stream_callback: Async callback to stream updates
            db_session: Database session for persistence
            message_id: Message ID for DB storage
        """
        self.stream_callback = stream_callback
        self.db_session = db_session
        self.message_id = message_id
        self.active_steps: Dict[str, Dict[str, Any]] = {}  # agent_name -> step_data
        self.completed_steps: List[Dict[str, Any]] = []
        self.step_counter = 0
        self.current_agent: Optional[str] = None
    
    async def handle_stream_event(self, chunk: Any) -> bool:
        """
        Handle a stream event and extract agent step information.
        
        Returns True if this event was handled (agent step related).
        
        Args:
            chunk: Stream chunk from Agno
            
        Returns:
            True if event was an agent step, False otherwise
        """
        event_type = getattr(chunk, 'event', None)
        
        # Extract agent name
        agent_name = None
        if hasattr(chunk, 'agent_id'):
            agent_name = chunk.agent_id
        elif hasattr(chunk, 'agent'):
            agent_name = chunk.agent
        
        # Debug: Log all events to understand what we're getting
        logger.debug(f"Stream event: {event_type}, agent: {agent_name}, has_content: {hasattr(chunk, 'content')}")
        
        if not agent_name:
            return False
        
        # Agent switch detected - complete previous, start new
        if agent_name != self.current_agent:
            # Complete previous agent if exists
            if self.current_agent and self.current_agent in self.active_steps:
                await self._complete_agent_step(self.current_agent)
            
            # Start new agent
            await self._start_agent_step(agent_name)
            self.current_agent = agent_name
        
        # Accumulate content for current agent - accept ANY event with content
        if agent_name in self.active_steps and hasattr(chunk, 'content'):
            content = chunk.content
            if content:  # Only add non-empty content
                logger.debug(f"Adding content to {agent_name}: {type(content).__name__} - {str(content)[:100]}")
                self.active_steps[agent_name]['content_buffer'].append(content)
                
                # Stream text content to frontend
                if isinstance(content, str):
                    await self.stream_callback({
                        "type": "agent_step_content",
                        "data": {
                            "agent_name": agent_name,
                            "content_chunk": content
                        }
                    })
        
        return True
    
    async def _start_agent_step(self, agent_name: str):
        """Start tracking a new agent step."""
        step_id = str(uuid.uuid4())
        
        self.active_steps[agent_name] = {
            'step_id': step_id,
            'agent_name': agent_name,
            'content_buffer': [],
            'started_at': datetime.utcnow(),
            'step_order': self.step_counter
        }
        
        # Stream to frontend
        await self.stream_callback({
            "type": "agent_step_start",
            "data": {
                "agent_name": agent_name,
                "step_id": step_id,
                "step_order": self.step_counter,
                "timestamp": datetime.utcnow().isoformat()
            }
        })
        
        logger.info(f"🤖 Agent started: {agent_name} (step {self.step_counter})")
        self.step_counter += 1
    
    async def _add_content(self, agent_name: str, content: Any):
        """Add content to active agent's buffer."""
        if agent_name in self.active_steps:
            self.active_steps[agent_name]['content_buffer'].append(content)
            
            # Stream text content to frontend
            if isinstance(content, str):
                await self.stream_callback({
                    "type": "agent_step_content",
                    "data": {
                        "agent_name": agent_name,
                        "content_chunk": content
                    }
                })
    
    async def _complete_agent_step(self, agent_name: str):
        """Complete an active agent step."""
        if agent_name not in self.active_steps:
            return
        
        step_data = self.active_steps.pop(agent_name)
        
        # Process buffered content
        content_buffer = step_data['content_buffer']
        if not content_buffer:
            logger.warning(f"No content for agent {agent_name}, buffered items: {len(content_buffer)}")
            # Still emit completion event, just with no content
            await self.stream_callback({
                "type": "agent_step_complete",
                "data": {
                    "step_id": step_data['step_id'],
                    "agent_name": agent_name,
                    "content": "",
                    "is_structured": False,
                    "step_order": step_data['step_order'],
                    "duration_ms": (datetime.utcnow() - step_data['started_at']).total_seconds() * 1000
                }
            })
            return
        
        # Check if buffer has structured (BaseModel) content
        structured_items = [item for item in content_buffer if isinstance(item, BaseModel)]
        
        if structured_items:
            # Use the last structured item
            content = structured_items[-1]
            is_structured = True
            try:
                content_dict = content.model_dump()
            except Exception:
                content_dict = str(content)
                is_structured = False
        else:
            # Join string items
            string_items = [str(item) for item in content_buffer if isinstance(item, str)]
            content = ''.join(string_items) if string_items else str(content_buffer)
            content_dict = content
            is_structured = False
        
        # Calculate duration
        duration_ms = (datetime.utcnow() - step_data['started_at']).total_seconds() * 1000
        
        # Store completed step
        step_info = {
            'step_id': step_data['step_id'],
            'agent_name': agent_name,
            'content': content_dict,
            'is_structured': is_structured,
            'step_order': step_data['step_order'],
            'duration_ms': duration_ms
        }
        self.completed_steps.append(step_info)
        
        # Stream to frontend
        await self.stream_callback({
            "type": "agent_step_complete",
            "data": step_info
        })
        
        logger.info(f"✅ Agent completed: {agent_name} ({duration_ms:.0f}ms)")
        
        # Save to database
        if self.db_session and self.message_id:
            await self._save_step_to_db(step_info)
    
    async def finalize(self):
        """Complete any remaining active steps."""
        if self.current_agent and self.current_agent in self.active_steps:
            await self._complete_agent_step(self.current_agent)
    
    async def _save_step_to_db(self, step_info: Dict[str, Any]):
        """
        Save step to database.
        
        Args:
            step_info: Step information dictionary
        """
        try:
            from app.database.repositories.chat_message_step import ChatMessageStepRepository
            
            # Determine which field to use based on is_structured
            if step_info['is_structured']:
                tool_call = step_info['content']
                prediction = None
            else:
                tool_call = None
                prediction = str(step_info['content'])
            
            await ChatMessageStepRepository.create(
                self.db_session,
                message_id=self.message_id,
                agent_name=step_info['agent_name'],
                step_order=step_info['step_order'],
                tool_call=tool_call,
                prediction=prediction
            )
            await self.db_session.commit()
            logger.debug(f"Saved step {step_info['step_order']} to database")
            
        except Exception as e:
            logger.error(f"Failed to save step to database: {e}", exc_info=True)


class AgnoTreeExecutor:
    """
    Execute a Tree using Agno agents and teams.
    
    Maps tree structure to Agno:
    - Branches -> Agents with decision-making roles
    - Tools -> Agno tools with async execution
    - DecisionNodes -> Agent coordination logic
    - Streaming -> Real-time updates via hooks
    """
    
    def __init__(
        self,
        tree: Tree,
        model: Optional[Any] = None,
        db: Optional[PostgresDb] = None,
        settings: Optional[Any] = None
    ):
        """
        Initialize executor.
        
        Args:
            tree: Tree instance to execute
            model: Agno model (OpenRouter, etc.)
            db: Agno database for persistence
            settings: Application settings
        """
        self.tree = tree
        self.model = model
        self.db = db
        self.settings = settings
        self.team: Optional[Team] = None
        self.step_capture: Optional[AgentStepCapture] = None
    
    def _create_agno_tool_from_tree_tool(self, tree_tool: TreeTool) -> Callable:
        """
        Convert TreeTool to Agno tool format.
        
        Args:
            tree_tool: TreeTool instance
            
        Returns:
            Agno-compatible tool function
        """
        @agno_tool
        async def agno_tool_wrapper(**kwargs):
            """Generated tool wrapper."""
            # Create minimal TreeData for tool execution
            # In real execution, this would use the actual tree_data
            tree_data = TreeData(
                user_prompt=kwargs.get('query', ''),
                environment=self.tree.tree_data.environment if self.tree.tree_data else None
            )
            
            # Execute tree tool and collect results
            results = []
            async for result in tree_tool(tree_data, **kwargs):
                results.append(result)
                
                # Store in environment
                if hasattr(result, 'data') and tree_data.environment:
                    tree_data.environment.add(
                        f"{tree_tool.name}.result",
                        result.data
                    )
            
            # Return last result's data if available
            if results:
                last_result = results[-1]
                if hasattr(last_result, 'data'):
                    return last_result.data
                elif hasattr(last_result, 'content'):
                    return last_result.content
                elif hasattr(last_result, 'message'):
                    return last_result.message
            
            return {"status": "completed", "tool": tree_tool.name}
        
        # Copy metadata
        agno_tool_wrapper.__name__ = tree_tool.name
        agno_tool_wrapper.__doc__ = tree_tool.description
        
        return agno_tool_wrapper
    
    async def create_team(
        self,
        stream_callback: Optional[Callable] = None,
        db_session: Optional[Any] = None,
        message_id: Optional[str] = None
    ) -> Team:
        """
        Create Agno team from tree structure.
        
        Args:
            stream_callback: Callback for streaming updates
            db_session: Database session for persistence
            message_id: Message ID for DB storage
            
        Returns:
            Configured Agno Team
        """
        # Create step capture if callback provided
        if stream_callback:
            self.step_capture = AgentStepCapture(
                stream_callback=stream_callback,
                db_session=db_session,
                message_id=message_id
            )
        
        # Create agents for each branch
        agents = []
        
        for branch_id, branch in self.tree.branches.items():
            agent = await self._create_agent_from_branch(branch)
            agents.append(agent)
        
        # Create team
        self.team = Team(
            name=self.tree.name,
            members=agents,
            model=self.model,
            db=self.db,
            instructions=self._get_team_instructions(),
            stream=True,
            stream_intermediate_steps=True,
            stream_member_events=True,
            markdown=True,
            show_members_responses=True
        )
        
        logger.info(f"Created Agno team with {len(agents)} agents")
        return self.team
    
    async def _create_agent_from_branch(self, branch: Branch) -> Agent:
        """
        Create Agno agent from a branch.
        
        Args:
            branch: Tree branch
            
        Returns:
            Agno Agent
        """
        # Convert branch tools to Agno tools
        agno_tools = []
        for tree_tool in branch.tools:
            agno_tool_func = self._create_agno_tool_from_tree_tool(tree_tool)
            agno_tools.append(agno_tool_func)
        
        # Create agent without hooks (they don't work in streaming)
        agent = Agent(
            name=branch.branch_id.replace("_", " ").title(),
            role=branch.description or branch.instruction,
            tools=agno_tools,
            instructions=branch.instruction,
            model=self.model,
            db=self.db,
            markdown=True
        )
        
        logger.debug(f"Created agent: {agent.name} with {len(agno_tools)} tools")
        return agent
    
    def _get_team_instructions(self) -> str:
        """
        Generate team coordination instructions.
        
        Returns:
            Instructions string
        """
        return f"""{self.tree.agent_description}

Style: {self.tree.style}
End Goal: {self.tree.end_goal}

Tree Structure:
{self._format_tree_structure()}

Coordinate the team to achieve the end goal by:
1. Following the tree structure from root to leaves
2. Making decisions at each branch based on available tools
3. Using tools to retrieve, analyze, and synthesize information
4. Maintaining environment state across all agents
5. Providing clear, well-structured responses
"""
    
    def _format_tree_structure(self) -> str:
        """Format tree structure for instructions."""
        if not self.tree.root_branch:
            return "No root branch defined"
        
        return self._format_branch(self.tree.root_branch, indent=0)
    
    def _format_branch(self, branch: Branch, indent: int = 0) -> str:
        """Recursively format branch structure."""
        prefix = "  " * indent
        lines = [f"{prefix}- {branch.branch_id}: {branch.instruction}"]
        
        for tool in branch.tools:
            lines.append(f"{prefix}  • Tool: {tool.name}")
        
        for child in branch.child_branches:
            lines.append(self._format_branch(child, indent + 1))
        
        return "\n".join(lines)
    
    async def run(
        self,
        user_prompt: str,
        stream_callback: Optional[Callable] = None,
        db_session: Optional[Any] = None,
        message_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute tree using manual agent orchestration (not Team).
        
        Agno Team doesn't expose per-agent events in streaming, so we manually
        orchestrate agents to get proper step tracking.
        
        Args:
            user_prompt: User's query
            stream_callback: Callback for streaming updates
            db_session: Database session
            message_id: Message ID for DB
            user_id: User ID
            session_id: Session ID
            **kwargs: Additional execution parameters
            
        Yields:
            Stream updates from agent execution
        """
        # Create team if not exists (we'll use agents from it)
        if not self.team:
            await self.create_team(
                stream_callback=stream_callback,
                db_session=db_session,
                message_id=message_id
            )
        
        # Initialize tree data
        self.tree.tree_data = TreeData(
            user_prompt=user_prompt,
            collections=kwargs.get('collections', []),
            conversation_history=kwargs.get('conversation_history', [])
        )
        
        logger.info(f"Executing tree '{self.tree.name}' via manual agent orchestration")
        
        # Execute agents manually for proper tracking
        # For multi-branch workflow: coordinator -> specialist -> ...
        agents = self.team.members
        
        for agent in agents:
            # Start agent step
            if self.step_capture:
                await self.step_capture._start_agent_step(agent.name)
            
            # Run agent
            try:
                async for chunk in agent.arun(
                    user_prompt,
                    user_id=user_id,
                    session_id=session_id,
                    stream=True
                ):
                    # Capture content
                    if self.step_capture and hasattr(chunk, 'content') and chunk.content:
                        await self.step_capture._add_content(agent.name, chunk.content)
                    
                    # Pass through chunks
                    yield chunk
            
            except Exception as e:
                logger.error(f"Agent {agent.name} failed: {e}")
            
            # Complete agent step
            if self.step_capture:
                await self.step_capture._complete_agent_step(agent.name)
        
        # Finalize
        if self.step_capture:
            logger.info(f"Completed {len(self.step_capture.completed_steps)} agent steps")

