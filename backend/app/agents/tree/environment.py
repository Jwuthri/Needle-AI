"""
Environment and state management for tree execution.

Provides centralized storage for:
- Tool results
- Conversation history
- Collection metadata
- Execution context
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class CollectionData(BaseModel):
    """Metadata about available data collections."""
    
    name: str = Field(..., description="Collection name")
    description: Optional[str] = Field(None, description="Collection description")
    schema_info: Dict[str, Any] = Field(default_factory=dict, description="Collection schema")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class Environment:
    """
    Persistent storage for tool results and intermediate data.
    
    Acts as a shared memory accessible by all agents and tools in the tree.
    Results are stored with keys like "tool_name.result_name" for easy retrieval.
    """
    
    def __init__(self):
        self._storage: Dict[str, Any] = {}
        self._history: List[Dict[str, Any]] = []  # Track all additions for debugging
    
    def add(self, key: str, value: Any, metadata: Optional[Dict[str, Any]] = None):
        """
        Add a value to the environment.
        
        Args:
            key: Storage key (e.g., "query.results")
            value: Value to store
            metadata: Optional metadata about this entry
        """
        self._storage[key] = value
        self._history.append({
            "action": "add",
            "key": key,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        })
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from the environment.
        
        Args:
            key: Storage key
            default: Default value if key not found
            
        Returns:
            Stored value or default
        """
        return self._storage.get(key, default)
    
    def remove(self, key: str) -> bool:
        """
        Remove a value from the environment.
        
        Args:
            key: Storage key
            
        Returns:
            True if removed, False if key didn't exist
        """
        if key in self._storage:
            del self._storage[key]
            self._history.append({
                "action": "remove",
                "key": key,
                "timestamp": datetime.utcnow().isoformat()
            })
            return True
        return False
    
    def find(self, pattern: str) -> Dict[str, Any]:
        """
        Find all keys matching a pattern.
        
        Args:
            pattern: Key pattern (e.g., "query.*")
            
        Returns:
            Dict of matching key-value pairs
        """
        import re
        regex = re.compile(pattern.replace("*", ".*"))
        return {k: v for k, v in self._storage.items() if regex.match(k)}
    
    def replace(self, key: str, value: Any):
        """
        Replace a value in the environment.
        
        Args:
            key: Storage key
            value: New value
        """
        self._storage[key] = value
        self._history.append({
            "action": "replace",
            "key": key,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def clear(self):
        """Clear all stored values."""
        self._storage.clear()
        self._history.append({
            "action": "clear",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def keys(self) -> List[str]:
        """Get all stored keys."""
        return list(self._storage.keys())
    
    def items(self) -> List[tuple]:
        """Get all key-value pairs."""
        return list(self._storage.items())
    
    def to_dict(self) -> Dict[str, Any]:
        """Export environment as dictionary."""
        return self._storage.copy()


class TreeData:
    """
    Central object holding the entire state of the tree execution.
    
    This is passed to all tools and decision nodes, providing them with:
    - Environment (persistent storage)
    - Conversation history
    - Collection metadata
    - Task tracking
    - Configuration
    """
    
    def __init__(
        self,
        user_prompt: str,
        collections: Optional[List[CollectionData]] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        environment: Optional[Environment] = None,
        tasks_completed: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize tree data.
        
        Args:
            user_prompt: User's query/prompt
            collections: Available data collections
            conversation_history: Previous conversation messages
            environment: Persistent environment storage
            tasks_completed: List of completed tasks
            metadata: Additional metadata
        """
        self.user_prompt = user_prompt
        self.collections = collections or []
        self.conversation_history = conversation_history or []
        self.environment = environment or Environment()
        self.tasks_completed = tasks_completed or []
        self.metadata = metadata or {}
        
        # Execution tracking
        self.errors: List[Dict[str, Any]] = []
        self.recursion_depth = 0
        self.max_recursion_depth = 10
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Add a message to conversation history.
        
        Args:
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Optional metadata
        """
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        })
    
    def add_task(self, task_name: str, result: Any, metadata: Optional[Dict[str, Any]] = None):
        """
        Record a completed task.
        
        Args:
            task_name: Name of the task
            result: Task result
            metadata: Optional metadata
        """
        self.tasks_completed.append({
            "task": task_name,
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        })
    
    def add_error(self, error: str, context: Optional[Dict[str, Any]] = None):
        """
        Record an error.
        
        Args:
            error: Error message
            context: Optional error context
        """
        self.errors.append({
            "error": error,
            "timestamp": datetime.utcnow().isoformat(),
            "context": context or {}
        })
    
    def get_collection(self, name: str) -> Optional[CollectionData]:
        """
        Get collection metadata by name.
        
        Args:
            name: Collection name
            
        Returns:
            CollectionData or None
        """
        for collection in self.collections:
            if collection.name == name:
                return collection
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Export tree data as dictionary."""
        return {
            "user_prompt": self.user_prompt,
            "collections": [c.dict() for c in self.collections],
            "conversation_history": self.conversation_history,
            "environment": self.environment.to_dict(),
            "tasks_completed": self.tasks_completed,
            "errors": self.errors,
            "metadata": self.metadata
        }

