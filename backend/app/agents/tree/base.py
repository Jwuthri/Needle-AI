"""
Core tree classes for decision-based orchestration.

Implements:
- Tree: Main orchestrator
- DecisionNode: Decision points in the tree
- Branch: Sub-trees for organizing decision flow
"""

from typing import Any, AsyncGenerator, Dict, List, Optional, Callable
from datetime import datetime
import uuid

from app.agents.tree.environment import TreeData, Environment, CollectionData
from app.agents.tree.tool import TreeTool
from app.agents.tree.returns import Return, Status, Error, Completed
from app.utils.logging import get_logger

logger = get_logger("tree")


class Branch:
    """
    A branch in the decision tree.
    
    Branches organize tools and sub-decisions into logical groups.
    """
    
    def __init__(
        self,
        branch_id: str,
        instruction: str,
        status_message: Optional[str] = None,
        description: Optional[str] = None,
        parent_branch_id: Optional[str] = None,
        is_root: bool = False
    ):
        """
        Initialize branch.
        
        Args:
            branch_id: Unique branch identifier
            instruction: Instructions for decision at this branch
            status_message: Status to show when entering branch
            description: Human-readable description
            parent_branch_id: Parent branch ID (None for root)
            is_root: Whether this is the root branch
        """
        self.branch_id = branch_id
        self.instruction = instruction
        self.status_message = status_message or f"Processing {branch_id}..."
        self.description = description
        self.parent_branch_id = parent_branch_id
        self.is_root = is_root
        self.tools: List[TreeTool] = []
        self.child_branches: List['Branch'] = []
    
    def add_tool(self, tool: TreeTool):
        """Add a tool to this branch."""
        tool.branch_id = self.branch_id
        self.tools.append(tool)
    
    def add_child_branch(self, branch: 'Branch'):
        """Add a child branch."""
        branch.parent_branch_id = self.branch_id
        self.child_branches.append(branch)
    
    def get_all_options(self) -> List[str]:
        """Get all available options (tools + child branches)."""
        options = [tool.name for tool in self.tools]
        options.extend([branch.branch_id for branch in self.child_branches])
        return options


class DecisionNode:
    """
    A decision point in the tree.
    
    DecisionNodes use LLMs to choose the next action based on:
    - Available tools
    - Current environment state
    - User's query
    - Previous actions
    """
    
    def __init__(
        self,
        instruction: str,
        available_options: List[str],
        decision_callback: Optional[Callable] = None
    ):
        """
        Initialize decision node.
        
        Args:
            instruction: Instructions for the decision
            available_options: List of available option names
            decision_callback: Optional callback function to make decision
        """
        self.instruction = instruction
        self.available_options = available_options
        self.decision_callback = decision_callback
    
    async def make_decision(
        self,
        tree_data: TreeData,
        **kwargs
    ) -> str:
        """
        Make a decision based on context.
        
        Args:
            tree_data: Tree data with context
            **kwargs: Additional decision parameters
            
        Returns:
            Name of chosen option
        """
        if self.decision_callback:
            return await self.decision_callback(
                instruction=self.instruction,
                options=self.available_options,
                tree_data=tree_data,
                **kwargs
            )
        
        # Default: choose first available option
        if self.available_options:
            return self.available_options[0]
        
        raise ValueError("No available options for decision")


class Tree:
    """
    Main tree orchestrator.
    
    Coordinates:
    - Branch structure
    - Tool registration
    - Decision making
    - Execution flow
    - State management
    """
    
    def __init__(
        self,
        name: str = "Tree",
        description: str = "No description provided",
        style: str = "No style provided",
        agent_description: str = "No agent description provided",
        end_goal: str = "No end goal provided"
    ):
        """
        Initialize tree.
        
        Args:
            name: Tree name
            description: Tree description
            style: Response style guidance
            agent_description: Agent personality/role description
            end_goal: Overall goal for the tree
        """
        self.name = name
        self.description = description
        self.style = style
        self.agent_description = agent_description
        self.end_goal = end_goal
        
        # Structure
        self.branches: Dict[str, Branch] = {}
        self.tools: Dict[str, TreeTool] = {}
        self.root_branch: Optional[Branch] = None
        
        # State
        self.tree_data: Optional[TreeData] = None
    
    def add_branch(
        self,
        branch_id: str,
        instruction: str,
        status: Optional[str] = None,
        description: Optional[str] = None,
        root: bool = False,
        from_branch_id: Optional[str] = None
    ):
        """
        Add a branch to the tree.
        
        Args:
            branch_id: Unique branch identifier
            instruction: Decision instruction
            status: Status message when entering branch
            description: Branch description
            root: Whether this is the root branch
            from_branch_id: Parent branch ID
        """
        branch = Branch(
            branch_id=branch_id,
            instruction=instruction,
            status_message=status,
            description=description,
            parent_branch_id=from_branch_id,
            is_root=root
        )
        
        self.branches[branch_id] = branch
        
        if root:
            self.root_branch = branch
        
        if from_branch_id and from_branch_id in self.branches:
            self.branches[from_branch_id].add_child_branch(branch)
        
        logger.debug(f"Added branch: {branch_id} (root={root})")
    
    def add_tool(
        self,
        tool: TreeTool,
        branch_id: str,
        from_tool_ids: Optional[List[str]] = None
    ):
        """
        Add a tool to a branch.
        
        Args:
            tool: TreeTool instance
            branch_id: Branch to add tool to
            from_tool_ids: Tools that must run before this one (chaining)
        """
        if branch_id not in self.branches:
            raise ValueError(f"Branch {branch_id} not found")
        
        tool.branch_id = branch_id
        if from_tool_ids:
            tool.metadata["from_tool_ids"] = from_tool_ids
        
        self.branches[branch_id].add_tool(tool)
        self.tools[tool.name] = tool
        
        logger.debug(f"Added tool: {tool.name} to branch {branch_id}")
    
    def remove_branch(self, branch_id: str):
        """Remove a branch from the tree."""
        if branch_id in self.branches:
            del self.branches[branch_id]
            logger.debug(f"Removed branch: {branch_id}")
    
    def remove_tool(self, tool_name: str):
        """Remove a tool from the tree."""
        if tool_name in self.tools:
            tool = self.tools[tool_name]
            if tool.branch_id and tool.branch_id in self.branches:
                branch = self.branches[tool.branch_id]
                branch.tools = [t for t in branch.tools if t.name != tool_name]
            del self.tools[tool_name]
            logger.debug(f"Removed tool: {tool_name}")
    
    async def run(
        self,
        user_prompt: str,
        collections: Optional[List[CollectionData]] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        decision_callback: Optional[Callable] = None
    ) -> AsyncGenerator[Return, None]:
        """
        Execute the tree.
        
        Args:
            user_prompt: User's query
            collections: Available data collections
            conversation_history: Previous messages
            metadata: Additional metadata
            decision_callback: Callback for making decisions
            
        Yields:
            Return objects from tool execution
        """
        # Initialize tree data
        self.tree_data = TreeData(
            user_prompt=user_prompt,
            collections=collections or [],
            conversation_history=conversation_history or [],
            environment=Environment(),
            metadata=metadata or {}
        )
        
        logger.info(f"Starting tree execution: {self.name}")
        
        try:
            # Start from root branch
            if not self.root_branch:
                yield Error(
                    message="No root branch defined",
                    error_type="configuration",
                    recoverable=False
                )
                return
            
            # Execute tree recursively
            async for result in self._execute_branch(
                self.root_branch,
                decision_callback=decision_callback
            ):
                yield result
            
            # Completion
            yield Completed(
                message="Tree execution completed",
                metadata={"tree": self.name}
            )
            
        except Exception as e:
            logger.error(f"Error executing tree: {e}", exc_info=True)
            yield Error(
                message=f"Tree execution failed: {str(e)}",
                error_type="execution",
                recoverable=False,
                metadata={"tree": self.name, "error": str(e)}
            )
    
    async def _execute_branch(
        self,
        branch: Branch,
        decision_callback: Optional[Callable] = None
    ) -> AsyncGenerator[Return, None]:
        """
        Execute a branch recursively.
        
        Args:
            branch: Branch to execute
            decision_callback: Decision callback
            
        Yields:
            Return objects
        """
        # Yield status
        yield Status(branch.status_message)
        
        # Get available options
        available_options = branch.get_all_options()
        
        if not available_options:
            logger.warning(f"Branch {branch.branch_id} has no options")
            return
        
        # Make decision
        decision_node = DecisionNode(
            instruction=branch.instruction,
            available_options=available_options,
            decision_callback=decision_callback
        )
        
        chosen_option = await decision_node.make_decision(self.tree_data)
        logger.info(f"Branch {branch.branch_id} chose: {chosen_option}")
        
        # Execute chosen option
        # Check if it's a tool
        if chosen_option in [tool.name for tool in branch.tools]:
            tool = next(t for t in branch.tools if t.name == chosen_option)
            
            # Check availability
            available, reason = await tool.is_tool_available(self.tree_data)
            if not available:
                yield Error(
                    message=f"Tool {tool.name} not available: {reason}",
                    error_type="availability",
                    recoverable=True
                )
                return
            
            # Check conditional
            if not tool.run_if_true(self.tree_data):
                logger.debug(f"Tool {tool.name} skipped due to run_if_true")
                return
            
            # Execute tool
            async for result in tool(self.tree_data):
                yield result
                
                # Store results in environment
                if hasattr(result, 'data'):
                    self.tree_data.environment.add(
                        f"{tool.name}.result",
                        result.data
                    )
            
            # Check if tool ends execution
            if tool.end:
                logger.info(f"Tool {tool.name} ends execution")
                return
        
        # Check if it's a child branch
        elif chosen_option in [b.branch_id for b in branch.child_branches]:
            child_branch = next(b for b in branch.child_branches if b.branch_id == chosen_option)
            async for result in self._execute_branch(child_branch, decision_callback):
                yield result

