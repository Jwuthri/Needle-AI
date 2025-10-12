"""
Execution tree tracker for multi-agent orchestration.
Tracks all steps (agent calls, tool invocations, decisions) in a hierarchical structure
for UI visualization similar to Langfuse/LangSmith trace views.
"""

import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Types of execution nodes."""
    AGENT = "agent"
    TOOL = "tool"
    DECISION = "decision"
    SYNTHESIS = "synthesis"


class NodeStatus(str, Enum):
    """Execution status of a node."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ExecutionNode(BaseModel):
    """A single node in the execution tree."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Human-readable name of this step")
    type: NodeType = Field(..., description="Type of execution node")
    status: NodeStatus = Field(default=NodeStatus.PENDING)
    
    # Timing
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_ms: Optional[int] = None
    
    # Data
    input_data: Optional[Dict[str, Any]] = Field(default=None, description="Input to this step")
    output_data: Optional[Dict[str, Any]] = Field(default=None, description="Output from this step")
    input_summary: Optional[str] = Field(default=None, description="Human-readable input summary")
    output_summary: Optional[str] = Field(default=None, description="Human-readable output summary")
    
    # Hierarchy
    parent_id: Optional[str] = None
    children: List["ExecutionNode"] = Field(default_factory=list)
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    
    class Config:
        use_enum_values = True


class ExecutionTree:
    """
    Tracks the full execution flow of a chat request through the orchestrator.
    
    Usage:
        tree = ExecutionTree(query="What are the main product gaps?")
        
        # Start a tool
        node_id = tree.start_node("RAG Retrieval", NodeType.TOOL, input_data={...})
        # ... execute tool ...
        tree.complete_node(node_id, output_data={...}, output_summary="Found 15 reviews")
        
        # Export for API response
        tree_dict = tree.to_dict()
    """
    
    def __init__(self, query: str, session_id: Optional[str] = None):
        """Initialize execution tree with root query node."""
        self.query = query
        self.session_id = session_id
        self.tree_id = str(uuid.uuid4())
        self.created_at = datetime.utcnow()
        
        # Root node represents the entire query
        self.root = ExecutionNode(
            id="root",
            name="Query Orchestration",
            type=NodeType.AGENT,
            status=NodeStatus.RUNNING,
            start_time=self.created_at,
            input_data={"query": query},
            input_summary=query[:100],
            metadata={"session_id": session_id}
        )
        
        # Index for fast node lookup
        self._nodes: Dict[str, ExecutionNode] = {"root": self.root}
        self._current_parent: Optional[str] = "root"
    
    def start_node(
        self,
        name: str,
        node_type: NodeType,
        input_data: Optional[Dict[str, Any]] = None,
        input_summary: Optional[str] = None,
        parent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start a new execution node.
        
        Args:
            name: Human-readable step name
            node_type: Type of node (agent, tool, decision)
            input_data: Full input data
            input_summary: Brief summary of input
            parent_id: Parent node ID (defaults to current parent or root)
            metadata: Additional metadata
            
        Returns:
            Node ID for later reference
        """
        parent_id = parent_id or self._current_parent or "root"
        parent = self._nodes.get(parent_id)
        
        if not parent:
            raise ValueError(f"Parent node {parent_id} not found")
        
        node = ExecutionNode(
            name=name,
            type=node_type,
            status=NodeStatus.RUNNING,
            start_time=datetime.utcnow(),
            input_data=input_data,
            input_summary=input_summary,
            parent_id=parent_id,
            metadata=metadata or {}
        )
        
        # Add to parent's children
        parent.children.append(node)
        
        # Index the node
        self._nodes[node.id] = node
        
        # Update current parent for nested calls
        self._current_parent = node.id
        
        return node.id
    
    def complete_node(
        self,
        node_id: str,
        output_data: Optional[Dict[str, Any]] = None,
        output_summary: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Mark a node as completed with its output."""
        node = self._nodes.get(node_id)
        if not node:
            raise ValueError(f"Node {node_id} not found")
        
        node.status = NodeStatus.COMPLETED
        node.end_time = datetime.utcnow()
        node.output_data = output_data
        node.output_summary = output_summary
        
        if node.start_time:
            duration = (node.end_time - node.start_time).total_seconds()
            node.duration_ms = int(duration * 1000)
        
        if metadata:
            node.metadata.update(metadata)
        
        # Reset current parent to this node's parent
        if node.parent_id:
            self._current_parent = node.parent_id
    
    def fail_node(
        self,
        node_id: str,
        error: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Mark a node as failed with error details."""
        node = self._nodes.get(node_id)
        if not node:
            raise ValueError(f"Node {node_id} not found")
        
        node.status = NodeStatus.FAILED
        node.end_time = datetime.utcnow()
        node.error = error
        
        if node.start_time:
            duration = (node.end_time - node.start_time).total_seconds()
            node.duration_ms = int(duration * 1000)
        
        if metadata:
            node.metadata.update(metadata)
        
        # Reset current parent
        if node.parent_id:
            self._current_parent = node.parent_id
    
    def skip_node(self, node_id: str, reason: str):
        """Mark a node as skipped."""
        node = self._nodes.get(node_id)
        if not node:
            raise ValueError(f"Node {node_id} not found")
        
        node.status = NodeStatus.SKIPPED
        node.metadata["skip_reason"] = reason
        
        if node.parent_id:
            self._current_parent = node.parent_id
    
    def complete_tree(self, final_output: Optional[str] = None):
        """Mark the entire tree as completed."""
        self.root.status = NodeStatus.COMPLETED
        self.root.end_time = datetime.utcnow()
        
        if final_output:
            self.root.output_summary = final_output
        
        if self.root.start_time:
            duration = (self.root.end_time - self.root.start_time).total_seconds()
            self.root.duration_ms = int(duration * 1000)
    
    def fail_tree(self, error: str):
        """Mark the entire tree as failed."""
        self.root.status = NodeStatus.FAILED
        self.root.end_time = datetime.utcnow()
        self.root.error = error
        
        if self.root.start_time:
            duration = (self.root.end_time - self.root.start_time).total_seconds()
            self.root.duration_ms = int(duration * 1000)
    
    def get_node(self, node_id: str) -> Optional[ExecutionNode]:
        """Get a node by ID."""
        return self._nodes.get(node_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert tree to dictionary for API response.
        
        Returns a clean, serializable representation suitable for frontend rendering.
        """
        def node_to_dict(node: ExecutionNode) -> Dict[str, Any]:
            return {
                "id": node.id,
                "name": node.name,
                "type": node.type,
                "status": node.status,
                "start_time": node.start_time.isoformat() if node.start_time else None,
                "end_time": node.end_time.isoformat() if node.end_time else None,
                "duration_ms": node.duration_ms,
                "input_summary": node.input_summary,
                "output_summary": node.output_summary,
                "error": node.error,
                "metadata": node.metadata,
                "children": [node_to_dict(child) for child in node.children]
            }
        
        return {
            "tree_id": self.tree_id,
            "query": self.query,
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "root": node_to_dict(self.root)
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        stats = {
            "total_nodes": len(self._nodes),
            "completed": 0,
            "failed": 0,
            "running": 0,
            "pending": 0,
            "skipped": 0,
            "total_duration_ms": self.root.duration_ms or 0
        }
        
        for node in self._nodes.values():
            if node.status == NodeStatus.COMPLETED:
                stats["completed"] += 1
            elif node.status == NodeStatus.FAILED:
                stats["failed"] += 1
            elif node.status == NodeStatus.RUNNING:
                stats["running"] += 1
            elif node.status == NodeStatus.PENDING:
                stats["pending"] += 1
            elif node.status == NodeStatus.SKIPPED:
                stats["skipped"] += 1
        
        return stats

