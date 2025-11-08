"""
Router Agent Service - Classifies queries and routes to specialist agents.
"""

import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from agno.models.openrouter import OpenRouter

from app.config import get_settings
from app.services.redis_client import RedisClient
from app.utils.logging import get_logger

logger = get_logger("router_agent")


class RouterDecision(BaseModel):
    """Router's classification decision."""
    specialist: str = Field(..., description="Selected specialist: product, research, analytics, or general")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    reasoning: str = Field(..., description="Why this specialist was chosen")
    detected_entities: List[str] = Field(default_factory=list, description="Detected entities like company names, products")
    suggested_tools: List[str] = Field(default_factory=list, description="Tools the specialist might need")


class RouterAgentService:
    """
    Routes user queries to specialized agents using LLM classification.
    
    Fast classification with caching for common patterns.
    """
    
    SPECIALISTS = {
        "product": {
            "description": "Product-specific questions, features, reviews, user feedback, sentiment analysis",
            "keywords": ["review", "feedback", "feature", "product", "customer", "user", "complaint", "praise", "sentiment"],
            "tools": ["rag_retrieval", "database_query", "data_analysis", "nlp_tool", "visualization", "citation"]
        },
        "research": {
            "description": "Market research, competitor analysis, industry trends, external data",
            "keywords": ["competitor", "market", "industry", "trend", "compare", "versus", "vs", "external", "research"],
            "tools": ["web_search", "rag_retrieval", "mcp_api_call", "data_analysis", "citation"]
        },
        "analytics": {
            "description": "Data analysis, statistics, trends, visualizations, aggregations",
            "keywords": ["analyze", "trend", "stat", "graph", "chart", "visualization", "average", "count", "sum", "aggregate"],
            "tools": ["database_query", "data_analysis", "nlp_tool", "visualization", "citation"]
        },
        "general": {
            "description": "General questions, definitions, how-to, platform help",
            "keywords": ["how", "what", "why", "help", "explain", "definition", "guide"],
            "tools": ["web_search", "mcp_api_call", "citation"]
        }
    }
    
    def __init__(self, settings: Any = None):
        self.settings = settings or get_settings()
        self.confidence_threshold = 0.7
        self.cache = RedisClient(self.settings)
        self.cache_ttl = 3600  # 1 hour
        self._model = None
    
    def _get_model(self) -> OpenRouter:
        """Lazy load the router model."""
        if self._model is None:
            api_key = self.settings.get_secret("openrouter_api_key")
            if not api_key:
                raise ValueError("OpenRouter API key not configured")
            
            # Use fast, cheap model for routing
            router_model = getattr(self.settings, "router_model", "openai/gpt-5-nano")
            
            self._model = OpenRouter(
                id=router_model,
                api_key=str(api_key),
                max_tokens=500
            )
        return self._model
    
    async def classify_query(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> RouterDecision:
        """
        Classify query and determine which specialist should handle it.
        
        Args:
            query: User's question
            context: Additional context (company_id, previous messages, etc.)
            
        Returns:
            RouterDecision with specialist choice and reasoning
        """
        context = context or {}
        
        # Check cache first
        cache_key = self._get_cache_key(query)
        cached = await self._get_from_cache(cache_key)
        if cached:
            logger.info(f"Router cache hit for query: {query[:50]}")
            return RouterDecision(**cached)
        
        # # Use keyword heuristics as fallback for speed
        heuristic_result = self._classify_with_heuristics(query, context)
        # if heuristic_result["confidence"] >= 0.9:
        #     logger.info(f"Router using heuristics (high confidence): {heuristic_result['specialist']}")
        #     decision = RouterDecision(**heuristic_result)
        #     await self._save_to_cache(cache_key, decision.model_dump())
        #     return decision
        
        # Use LLM for accurate classification
        try:
            llm_result = await self._classify_with_llm(query, context)
            decision = RouterDecision(**llm_result)
            
            # Cache successful classifications
            if decision.confidence >= 0.6:
                await self._save_to_cache(cache_key, decision.model_dump())
            
            return decision
            
        except Exception as e:
            logger.error(f"LLM classification failed: {e}, falling back to heuristics")
            # Fallback to heuristics
            return RouterDecision(**heuristic_result)
    
    def _classify_with_heuristics(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fast heuristic-based classification."""
        query_lower = query.lower()
        
        # Strong signals
        if context.get("company_id"):
            # If company_id provided, likely product question
            return {
                "specialist": "product",
                "confidence": 0.85,
                "reasoning": "Company ID provided, routing to product specialist",
                "detected_entities": [context.get("company_id")],
                "suggested_tools": ["rag_retrieval", "database_query"]
            }
        
        # Count keyword matches
        scores = {}
        for specialist, config in self.SPECIALISTS.items():
            score = sum(1 for keyword in config["keywords"] if keyword in query_lower)
            scores[specialist] = score
        
        # Get best match
        best_specialist = max(scores, key=scores.get)
        best_score = scores[best_specialist]
        total_keywords = sum(scores.values())
        
        confidence = best_score / (total_keywords + 1) if total_keywords > 0 else 0.5
        
        return {
            "specialist": best_specialist,
            "confidence": confidence,
            "reasoning": f"Heuristic match based on query keywords",
            "detected_entities": [],
            "suggested_tools": self.SPECIALISTS[best_specialist]["tools"][:2]
        }
    
    async def _classify_with_llm(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """LLM-based classification with structured output."""
        
        # Build classification prompt
        prompt = self._build_classification_prompt(query, context)
        
        # Get model
        model = self._get_model()
        
        # Call LLM with structured output request
        messages = [
            {
                "role": "system",
                "content": prompt
            },
            {
                "role": "user",
                "content": f"Query: {query}"
            }
        ]
        
        # Make API call directly (Agno doesn't have structured output yet)
        import httpx
        api_key = self.settings.get_secret("openrouter_api_key")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model.id,
                    "messages": messages,
                    "max_tokens": 300,
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"}
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"OpenRouter API error: {response.status_code}")
            
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            
            # Parse JSON response
            result = json.loads(content)
            
            # Validate and normalize
            specialist = result.get("specialist", "general").lower()
            if specialist not in self.SPECIALISTS:
                specialist = "general"
            
            return {
                "specialist": specialist,
                "confidence": float(result.get("confidence", 0.7)),
                "reasoning": result.get("reasoning", "LLM classification"),
                "detected_entities": result.get("detected_entities", []),
                "suggested_tools": result.get("suggested_tools", self.SPECIALISTS[specialist]["tools"][:2])
            }
    
    def _build_classification_prompt(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> str:
        """Build classification prompt for LLM."""
        
        specialists_desc = "\n".join([
            f"- **{name}**: {config['description']}"
            for name, config in self.SPECIALISTS.items()
        ])
        
        context_str = ""
        if context.get("company_id"):
            context_str = f"\nContext: User is asking about company ID: {context['company_id']}"
        
        return f"""You are a query classifier for Needle AI, a product gap analysis platform.

Classify the user's query into one of these specialists:

{specialists_desc}

{context_str}

Respond in JSON format:
{{
    "specialist": "product|research|analytics|general",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation",
    "detected_entities": ["entity1", "entity2"],
    "suggested_tools": ["tool1", "tool2"]
}}

Be accurate and confident in your classification."""
    
    def _get_cache_key(self, query: str) -> str:
        """Generate cache key for query."""
        import hashlib
        query_hash = hashlib.md5(query.lower().strip().encode()).hexdigest()
        return f"router:classify:{query_hash}"
    
    async def _get_from_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached classification."""
        try:
            cached = await self.cache.get(key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Cache get failed: {e}")
        return None
    
    async def _save_to_cache(self, key: str, data: Dict[str, Any]):
        """Save classification to cache."""
        try:
            await self.cache.set(key, json.dumps(data), ex=self.cache_ttl)
        except Exception as e:
            logger.warning(f"Cache save failed: {e}")
    
    def get_specialist_info(self, specialist: str) -> Dict[str, Any]:
        """Get information about a specialist."""
        return self.SPECIALISTS.get(specialist, self.SPECIALISTS["general"])

