"""
Conversational Context Manager for Product Review Analysis Workflow.

This module implements context persistence and retrieval for multi-turn conversations,
enabling follow-up queries to leverage previous results and maintain conversational state.
"""

import json
from typing import Any, Dict, List, Optional
from datetime import datetime

from app.models.workflow import ExecutionContext, Insight
from app.services.redis_client import RedisClient
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ConversationalContextManager:
    """
    Manages conversational context across multiple query turns.
    
    This class handles:
    - Saving execution results (insights, agent outputs) to Redis
    - Loading previous context for follow-up queries
    - Detecting follow-up queries that reference previous results
    - Enabling context-aware planning for efficient follow-ups
    """
    
    def __init__(self, redis_client: RedisClient):
        """
        Initialize the conversational context manager.
        
        Args:
            redis_client: Redis client for context storage
        """
        self.redis_client = redis_client
        self.context_ttl = 86400  # 24 hours
        logger.info("Initialized ConversationalContextManager")
    
    async def save_context(
        self,
        session_id: str,
        query: str,
        insights: List[Insight],
        agent_outputs: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Save execution context to Redis for future reference.
        
        This method stores:
        - The original query
        - Generated insights from all agents
        - Agent outputs for potential reuse
        - Metadata (timestamps, execution stats, etc.)
        
        The context is associated with the session_id and can be retrieved
        for follow-up queries in the same session.
        
        Args:
            session_id: Session identifier
            query: The original query text
            insights: List of insights generated during execution
            agent_outputs: Dictionary of agent outputs (step_id -> output)
            metadata: Optional additional metadata
            
        Returns:
            True if context was saved successfully, False otherwise
            
        Requirements: 12.1, 12.2
        """
        try:
            # Build context data structure
            context_data = {
                "query": query,
                "insights": [self._serialize_insight(insight) for insight in insights],
                "agent_outputs": agent_outputs,
                "metadata": metadata or {},
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            # Generate Redis key for this context
            context_key = f"conversation_context:{session_id}"
            
            # Get existing context history
            existing_context = await self.redis_client.get(context_key)
            
            if existing_context:
                # Append to existing history
                if isinstance(existing_context, dict) and "history" in existing_context:
                    history = existing_context["history"]
                else:
                    # Legacy format - convert to new format
                    history = [existing_context] if existing_context else []
                
                history.append(context_data)
                
                # Keep only last 10 turns to prevent unbounded growth
                if len(history) > 10:
                    history = history[-10:]
                
                full_context = {
                    "session_id": session_id,
                    "history": history,
                    "last_updated": datetime.utcnow().isoformat()
                }
            else:
                # Create new context
                full_context = {
                    "session_id": session_id,
                    "history": [context_data],
                    "last_updated": datetime.utcnow().isoformat()
                }
            
            # Save to Redis with TTL
            success = await self.redis_client.set(
                context_key,
                full_context,
                expire=self.context_ttl
            )
            
            if success:
                logger.info(
                    f"Saved context for session {session_id}: "
                    f"{len(insights)} insights, {len(agent_outputs)} agent outputs"
                )
            else:
                logger.warning(f"Failed to save context for session {session_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error saving context for session {session_id}: {e}", exc_info=True)
            return False
    
    async def load_context(
        self,
        session_id: str
    ) -> Optional[ExecutionContext]:
        """
        Load previous context from Redis and reconstruct ExecutionContext.
        
        This method retrieves the conversation history for a session and
        reconstructs an ExecutionContext object that can be used for
        follow-up queries.
        
        The reconstructed context includes:
        - Conversation history (previous queries and results)
        - Cached results from previous executions
        - Last visualization data for "show me more" queries
        
        Args:
            session_id: Session identifier
            
        Returns:
            ExecutionContext with previous conversation state, or None if not found
            
        Requirements: 12.6
        """
        try:
            # Get context from Redis
            context_key = f"conversation_context:{session_id}"
            stored_context = await self.redis_client.get(context_key)
            
            if not stored_context:
                logger.debug(f"No context found for session {session_id}")
                return None
            
            # Extract history
            if isinstance(stored_context, dict) and "history" in stored_context:
                history = stored_context["history"]
            else:
                # Legacy format
                history = [stored_context] if stored_context else []
            
            if not history:
                logger.debug(f"Empty history for session {session_id}")
                return None
            
            # Get the most recent context
            latest_context = history[-1]
            
            # Reconstruct ExecutionContext
            # Note: We create a minimal context with conversational state
            # The actual execution fields will be populated during workflow execution
            context = ExecutionContext(
                user_id="",  # Will be set by workflow
                session_id=session_id,
                message_id="",  # Will be set by workflow
                query="",  # Will be set by workflow
                conversation_history=history,
                cached_results=self._extract_cached_results(history),
                last_visualization_data=self._extract_last_visualization(latest_context)
            )
            
            logger.info(
                f"Loaded context for session {session_id}: "
                f"{len(history)} previous turns"
            )
            
            return context
            
        except Exception as e:
            logger.error(f"Error loading context for session {session_id}: {e}", exc_info=True)
            return None
    
    async def is_follow_up_query(
        self,
        query: str,
        previous_context: Optional[ExecutionContext],
        llm_client: Optional[Any] = None
    ) -> bool:
        """
        Detect if a query references previous results.
        
        This method uses multiple strategies to detect follow-up queries:
        1. Keyword detection (e.g., "that", "the biggest", "compare", "show me more")
        2. Pronoun references (e.g., "it", "them", "those")
        3. LLM-based detection (if llm_client is provided)
        
        Args:
            query: The current query text
            previous_context: Previous execution context (if available)
            llm_client: Optional LLM client for advanced detection
            
        Returns:
            True if query appears to be a follow-up, False otherwise
            
        Requirements: 12.6
        """
        try:
            # If no previous context, it can't be a follow-up
            if not previous_context or not previous_context.conversation_history:
                return False
            
            # Normalize query for analysis
            query_lower = query.lower().strip()
            
            # Strategy 1: Keyword detection
            # Keywords that indicate reference to previous results
            follow_up_keywords = [
                "that", "the biggest", "the largest", "the most",
                "compare", "comparison", "versus", "vs",
                "show me more", "tell me more", "what about",
                "how about", "also", "additionally",
                "the same", "similar", "like that",
                "those", "these", "them"
            ]
            
            # Check for keywords (excluding common words that might appear in new queries)
            if any(keyword in query_lower for keyword in follow_up_keywords):
                logger.info(f"Follow-up detected via keywords: {query}")
                return True
            
            # Check for "and" only at the start (to avoid false positives)
            if query_lower.startswith("and "):
                logger.info(f"Follow-up detected via 'and' starter: {query}")
                return True
            
            # Strategy 2: Pronoun detection at start of query
            pronoun_starters = ["it ", "they ", "them ", "those ", "these ", "that "]
            if any(query_lower.startswith(pronoun) for pronoun in pronoun_starters):
                logger.info(f"Follow-up detected via pronoun: {query}")
                return True
            
            # Strategy 3: Short queries (likely follow-ups)
            # Queries with < 5 words are often follow-ups like "what about positive feedback?"
            word_count = len(query.split())
            if word_count < 5 and previous_context.conversation_history:
                logger.info(f"Follow-up detected via short query: {query}")
                return True
            
            # Strategy 4: LLM-based detection (if available)
            if llm_client:
                is_follow_up = await self._llm_detect_follow_up(
                    query,
                    previous_context,
                    llm_client
                )
                if is_follow_up:
                    logger.info(f"Follow-up detected via LLM: {query}")
                    return True
            
            logger.debug(f"Query does not appear to be a follow-up: {query}")
            return False
            
        except Exception as e:
            logger.error(f"Error detecting follow-up query: {e}", exc_info=True)
            # Default to False on error
            return False
    
    async def get_context_for_planning(
        self,
        session_id: str,
        current_query: str
    ) -> Dict[str, Any]:
        """
        Get context-aware planning information for the Planner Agent.
        
        This method prepares context information that helps the Planner Agent:
        - Reuse cached results from previous queries
        - Generate simpler plans for follow-up queries
        - Reference previous insights and visualizations
        
        Args:
            session_id: Session identifier
            current_query: The current query being planned
            
        Returns:
            Dictionary with planning context including:
            - previous_queries: List of previous query texts
            - available_insights: Insights from previous executions
            - cached_data: Data that can be reused
            - suggested_shortcuts: Hints for simpler execution
            
        Requirements: 12.6
        """
        try:
            # Load previous context
            context = await self.load_context(session_id)
            
            if not context or not context.conversation_history:
                return {
                    "previous_queries": [],
                    "available_insights": [],
                    "cached_data": {},
                    "suggested_shortcuts": []
                }
            
            # Extract previous queries
            previous_queries = [
                turn.get("query", "") for turn in context.conversation_history
            ]
            
            # Extract all insights from previous turns
            available_insights = []
            for turn in context.conversation_history:
                insights = turn.get("insights", [])
                for insight_data in insights:
                    available_insights.append(insight_data)
            
            # Prepare cached data
            cached_data = context.cached_results
            
            # Generate suggested shortcuts based on query patterns
            suggested_shortcuts = self._generate_shortcuts(
                current_query,
                previous_queries,
                available_insights
            )
            
            return {
                "previous_queries": previous_queries,
                "available_insights": available_insights,
                "cached_data": cached_data,
                "suggested_shortcuts": suggested_shortcuts,
                "last_visualization": context.last_visualization_data
            }
            
        except Exception as e:
            logger.error(f"Error getting context for planning: {e}", exc_info=True)
            return {
                "previous_queries": [],
                "available_insights": [],
                "cached_data": {},
                "suggested_shortcuts": []
            }
    
    def _serialize_insight(self, insight: Insight) -> Dict[str, Any]:
        """
        Serialize an Insight object to a dictionary for storage.
        
        Args:
            insight: Insight object to serialize
            
        Returns:
            Dictionary representation of the insight
        """
        if isinstance(insight, Insight):
            return insight.model_dump()
        elif isinstance(insight, dict):
            return insight
        else:
            # Fallback for unexpected types
            return {"raw": str(insight)}
    
    def _extract_cached_results(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract reusable results from conversation history.
        
        Args:
            history: List of previous conversation turns
            
        Returns:
            Dictionary of cached results that can be reused
        """
        cached = {}
        
        for idx, turn in enumerate(history):
            turn_key = f"turn_{idx}"
            
            # Cache agent outputs
            if "agent_outputs" in turn:
                cached[f"{turn_key}_outputs"] = turn["agent_outputs"]
            
            # Cache insights
            if "insights" in turn:
                cached[f"{turn_key}_insights"] = turn["insights"]
            
            # Cache query for reference
            if "query" in turn:
                cached[f"{turn_key}_query"] = turn["query"]
        
        return cached
    
    def _extract_last_visualization(
        self,
        latest_context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Extract visualization data from the most recent context.
        
        Args:
            latest_context: The most recent conversation turn
            
        Returns:
            Visualization data if available, None otherwise
        """
        # Look for visualization data in insights
        insights = latest_context.get("insights", [])
        
        for insight in reversed(insights):  # Start with most recent
            if isinstance(insight, dict):
                viz_data = insight.get("visualization_data")
                if viz_data:
                    return viz_data
        
        return None
    
    def _generate_shortcuts(
        self,
        current_query: str,
        previous_queries: List[str],
        available_insights: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Generate suggested shortcuts for the Planner Agent.
        
        Analyzes the current query against previous queries and insights
        to suggest optimizations.
        
        Args:
            current_query: The current query text
            previous_queries: List of previous query texts
            available_insights: List of available insights
            
        Returns:
            List of shortcut suggestions
        """
        shortcuts = []
        query_lower = current_query.lower()
        
        # Check if asking about specific insights
        if "biggest" in query_lower or "largest" in query_lower or "most" in query_lower:
            if available_insights:
                shortcuts.append("reuse_top_insight")
        
        # Check if asking for comparison
        if "compare" in query_lower or "versus" in query_lower:
            shortcuts.append("reuse_previous_data")
        
        # Check if asking for more details
        if "more" in query_lower or "details" in query_lower or "tell me about" in query_lower:
            shortcuts.append("expand_previous_insight")
        
        # Check if asking about different aspect of same data
        if previous_queries:
            last_query = previous_queries[-1].lower()
            # If both queries mention similar topics, suggest data reuse
            common_words = set(query_lower.split()) & set(last_query.split())
            if len(common_words) > 2:
                shortcuts.append("reuse_dataset")
        
        return shortcuts
    
    async def _llm_detect_follow_up(
        self,
        query: str,
        previous_context: ExecutionContext,
        llm_client: Any
    ) -> bool:
        """
        Use LLM to detect if query is a follow-up.
        
        This is a more sophisticated detection method that uses the LLM
        to understand query intent and context references.
        
        Args:
            query: Current query text
            previous_context: Previous execution context
            llm_client: LLM client for inference
            
        Returns:
            True if LLM determines this is a follow-up query
        """
        try:
            # Get last query from history
            if not previous_context.conversation_history:
                return False
            
            last_turn = previous_context.conversation_history[-1]
            last_query = last_turn.get("query", "")
            
            # Create prompt for LLM
            prompt = f"""Analyze if the current query is a follow-up to the previous query.

Previous query: "{last_query}"
Current query: "{query}"

A follow-up query typically:
- References results from the previous query (e.g., "that", "the biggest one")
- Asks for more details about previous results
- Compares or contrasts with previous results
- Uses pronouns referring to previous context

Answer with just "yes" or "no".
"""
            
            # Call LLM (simplified - actual implementation would use proper LLM client)
            # For now, return False as this is optional enhancement
            # TODO: Implement actual LLM call when LLM client is available
            
            return False
            
        except Exception as e:
            logger.error(f"Error in LLM follow-up detection: {e}", exc_info=True)
            return False
