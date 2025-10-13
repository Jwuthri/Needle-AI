"""
Tree-based agentic architecture for LLM orchestration.

This module implements a tree-based decision system inspired by Elysia,
where agents navigate a tree of decision nodes and tools.
"""

from app.agents.tree.base import Tree, DecisionNode, Branch
from app.agents.tree.environment import Environment, TreeData, CollectionData
from app.agents.tree.tool import TreeTool, tool
from app.agents.tree.returns import (
    Return,
    Text,
    Response,
    Update,
    Status,
    Warning,
    Completed,
    Result,
    Retrieval,
    Error as TreeError,
)
from app.agents.tree.executors.agno_executor import AgnoTreeExecutor

__all__ = [
    # Core classes
    "Tree",
    "DecisionNode",
    "Branch",
    
    # Environment & state
    "Environment",
    "TreeData",
    "CollectionData",
    
    # Tools
    "TreeTool",
    "tool",
    
    # Return types
    "Return",
    "Text",
    "Response",
    "Update",
    "Status",
    "Warning",
    "Completed",
    "Result",
    "Retrieval",
    "TreeError",
    
    # Executors
    "AgnoTreeExecutor",
]

