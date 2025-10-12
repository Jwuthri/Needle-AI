"""
RAG-enabled chat service for product review analysis.
Integrates Pinecone vector search with Agno agents.
"""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from agno import Agent
    AGNO_AVAILABLE = True
except ImportError:
    AGNO_AVAILABLE = False

from app.config import get_settings
from app.exceptions import ConfigurationError, ExternalServiceError
from app.models.chat import ChatRequest, ChatResponse
from app.services.vector_service import VectorService
from app.utils.logging import get_logger

logger = get_logger("rag_chat_service")


class RAGChatService:
    """
    RAG-enabled chat service for analyzing product reviews.
    
    Features:
    - Vector similarity search for relevant reviews
    - Context-aware responses with source attribution
    - Query classification and intent detection
    - Pipeline step tracking for visualization
    - Related question generation
    """

    def __init__(self, settings: Any = None):
        if not AGNO_AVAILABLE:
            raise ConfigurationError("Agno package not installed")

        self.settings = settings or get_settings()
        self.agent: Optional[Agent] = None
        self.vector_service: Optional[VectorService] = None
        self._initialized = False

    async def initialize(self):
        """Initialize RAG chat service with Agno and Pinecone."""
        if self._initialized:
            return

        try:
            # Initialize vector service
            self.vector_service = VectorService(self.settings)
            await self.vector_service.initialize()

            # Create Agno agent for product analysis
            api_key = self.settings.get_secret("openrouter_api_key")
            if not api_key:
                raise ConfigurationError("OpenRouter API key not configured")

            self.agent = Agent(
                model=self.settings.default_model,
                provider="openrouter",
                api_key=api_key,
                
                instructions=self._get_agent_instructions(),
                
                # Agent configuration
                temperature=0.7,
                max_tokens=self.settings.max_tokens,
                structured_outputs=False,
                debug=self.settings.debug,
                
                # Performance
                max_retries=3,
            )

            self._initialized = True
            logger.info("RAG chat service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize RAG chat service: {e}")
            raise ConfigurationError(f"RAG chat service initialization failed: {e}")

    async def cleanup(self):
        """Cleanup resources."""
        if self.vector_service:
            await self.vector_service.cleanup()
        self._initialized = False
        logger.debug("RAG chat service cleaned up")

    def _get_agent_instructions(self) -> str:
        """Get specialized instructions for product review analysis."""
        return """
You are an expert product analyst specializing in customer feedback analysis.

Your role is to analyze customer reviews and feedback to provide insights about:
- Product strengths and weaknesses (product gaps)
- Customer sentiment and satisfaction
- Feature requests and user needs
- Competitive positioning
- Common issues and pain points

When answering questions:
1. **Base your responses on the provided review context**
2. **Cite specific reviews when making claims**
3. **Provide balanced analysis** (both positive and negative aspects)
4. **Quantify insights when possible** (e.g., "30% of reviews mention...")
5. **Be specific and actionable** in your recommendations

Response formatting:
- Use clear, professional language
- Structure responses with headings and bullet points
- Include relevant quotes from reviews
- Highlight key takeaways

If the context doesn't contain enough information, acknowledge this limitation.
"""

    async def process_message(
        self,
        request: ChatRequest,
        user_id: Optional[str] = None,
        company_ids: Optional[List[str]] = None
    ) -> ChatResponse:
        """
        Process a chat message with RAG retrieval.
        
        Args:
            request: Chat request with message
            user_id: User ID for personalization
            company_ids: List of company IDs to query (filter context)
            
        Returns:
            Enhanced chat response with sources and pipeline info
        """
        if not self._initialized:
            await self.initialize()

        pipeline_steps = []
        start_time = time.time()

        try:
            # Step 1: Query preprocessing
            step_start = time.time()
            query = request.message
            query_type = await self._classify_query(query)
            pipeline_steps.append({
                "name": "Query Preprocessing",
                "duration_ms": int((time.time() - step_start) * 1000),
                "status": "completed",
                "metadata": {"query_type": query_type}
            })

            # Step 2: Vector search for relevant reviews
            step_start = time.time()
            relevant_reviews = []
            for company_id in (company_ids or []):
                company_reviews = await self.vector_service.search_similar_reviews(
                    query=query,
                    company_id=company_id,
                    top_k=15,  # Get top 15 most relevant reviews
                    min_score=0.7
                )
                relevant_reviews.extend(company_reviews)

            # Deduplicate and sort by relevance
            seen_ids = set()
            unique_reviews = []
            for review in sorted(relevant_reviews, key=lambda x: x["relevance_score"], reverse=True):
                if review["review_id"] not in seen_ids:
                    seen_ids.add(review["review_id"])
                    unique_reviews.append(review)

            pipeline_steps.append({
                "name": "Vector Search",
                "duration_ms": int((time.time() - step_start) * 1000),
                "status": "completed",
                "metadata": {
                    "reviews_found": len(unique_reviews),
                    "companies_searched": len(company_ids or [])
                }
            })

            # Step 3: Build context from retrieved reviews
            step_start = time.time()
            context = self._build_context(unique_reviews[:10])  # Use top 10 for context
            pipeline_steps.append({
                "name": "Context Building",
                "duration_ms": int((time.time() - step_start) * 1000),
                "status": "completed",
                "metadata": {"reviews_used": len(unique_reviews[:10])}
            })

            # Step 4: Generate response with Agno
            step_start = time.time()
            prompt = self._build_prompt(query, context, query_type)
            
            response = await self.agent.run(
                message=prompt,
                session_id=request.session_id or "default"
            )

            # Extract response content
            if isinstance(response, str):
                response_content = response
            elif hasattr(response, 'content'):
                response_content = response.content
            else:
                response_content = str(response)

            pipeline_steps.append({
                "name": "LLM Generation",
                "duration_ms": int((time.time() - step_start) * 1000),
                "status": "completed",
                "metadata": {"model": self.settings.default_model}
            })

            # Step 5: Generate related questions
            step_start = time.time()
            related_questions = await self._generate_related_questions(query, query_type)
            pipeline_steps.append({
                "name": "Related Questions",
                "duration_ms": int((time.time() - step_start) * 1000),
                "status": "completed",
                "metadata": {"questions_generated": len(related_questions)}
            })

            # Format sources for response
            sources = self._format_sources(unique_reviews[:10])

            # Create enhanced response
            chat_response = ChatResponse(
                message=response_content,
                session_id=request.session_id or "default",
                metadata={
                    "query_type": query_type,
                    "pipeline_steps": pipeline_steps,
                    "sources": sources,
                    "related_questions": related_questions,
                    "attached_companies": company_ids or [],
                    "total_duration_ms": int((time.time() - start_time) * 1000),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

            logger.debug(f"Processed RAG message for session {request.session_id}")
            return chat_response

        except Exception as e:
            logger.error(f"Error processing RAG message: {e}")
            
            # Add error to pipeline
            pipeline_steps.append({
                "name": "Error",
                "duration_ms": int((time.time() - start_time) * 1000),
                "status": "failed",
                "metadata": {"error": str(e)}
            })

            raise ExternalServiceError(f"RAG chat processing failed: {e}", service="rag_chat")

    async def _classify_query(self, query: str) -> str:
        """
        Classify the query intent.
        
        Types: product_gap, competitor, sentiment, feature_request, general
        """
        query_lower = query.lower()

        if any(word in query_lower for word in ["competitor", "comparison", "vs", "versus", "alternative"]):
            return "competitor"
        elif any(word in query_lower for word in ["gap", "missing", "lack", "need", "improve"]):
            return "product_gap"
        elif any(word in query_lower for word in ["sentiment", "feeling", "opinion", "satisfaction"]):
            return "sentiment"
        elif any(word in query_lower for word in ["feature", "request", "want", "wish", "should"]):
            return "feature_request"
        else:
            return "general"

    def _build_context(self, reviews: List[Dict[str, Any]]) -> str:
        """Build context string from retrieved reviews."""
        if not reviews:
            return "No relevant reviews found in the database."

        context_parts = ["Here are relevant customer reviews:\n"]
        
        for i, review in enumerate(reviews, 1):
            sentiment = review.get("sentiment_score", 0)
            sentiment_label = "Positive" if sentiment > 0.33 else "Negative" if sentiment < -0.33 else "Neutral"
            
            context_parts.append(f"\nReview {i} [{sentiment_label} - {review.get('source', 'unknown')}]:")
            context_parts.append(f"{review.get('content', '')}")
            
            if review.get("author"):
                context_parts.append(f"Author: {review['author']}")

        return "\n".join(context_parts)

    def _build_prompt(self, query: str, context: str, query_type: str) -> str:
        """Build the full prompt with context."""
        type_instructions = {
            "product_gap": "Focus on identifying gaps, missing features, and areas for improvement.",
            "competitor": "Compare with competitors and analyze competitive positioning.",
            "sentiment": "Analyze overall sentiment and customer satisfaction levels.",
            "feature_request": "Identify and prioritize feature requests from customers.",
            "general": "Provide a comprehensive analysis based on the reviews."
        }

        instruction = type_instructions.get(query_type, type_instructions["general"])

        return f"""
{instruction}

{context}

User Question: {query}

Provide a detailed, well-structured response based on the reviews above. Include specific examples and quotes when relevant.
"""

    async def _generate_related_questions(self, query: str, query_type: str) -> List[str]:
        """Generate related follow-up questions."""
        # Simple rule-based generation (can be enhanced with LLM)
        base_questions = {
            "product_gap": [
                "What are the most frequently mentioned missing features?",
                "How do customers describe their workarounds?",
                "What improvements would have the highest impact?"
            ],
            "competitor": [
                "Which competitors are mentioned most often?",
                "What do competitors do better according to reviews?",
                "What are our competitive advantages?"
            ],
            "sentiment": [
                "What are the main drivers of negative sentiment?",
                "Which features receive the most positive feedback?",
                "How has sentiment changed over time?"
            ],
            "feature_request": [
                "What are the most requested features?",
                "Which user segments are requesting these features?",
                "Are there common themes in feature requests?"
            ],
            "general": [
                "What are the main product strengths?",
                "What are the biggest customer pain points?",
                "How satisfied are customers overall?"
            ]
        }

        return base_questions.get(query_type, base_questions["general"])

    def _format_sources(self, reviews: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format review sources for response."""
        sources = []
        for review in reviews:
            sources.append({
                "review_id": review.get("review_id"),
                "content": review.get("content", "")[:200] + "...",  # Truncate
                "author": review.get("author"),
                "source": review.get("source"),
                "sentiment": review.get("sentiment_score"),
                "url": review.get("url"),
                "relevance_score": review.get("relevance_score")
            })
        return sources

    async def health_check(self) -> bool:
        """Check if RAG chat service is healthy."""
        try:
            if not self._initialized:
                await self.initialize()

            # Check vector service
            vector_healthy = await self.vector_service.health_check()
            
            return vector_healthy

        except Exception as e:
            logger.error(f"RAG chat service health check failed: {e}")
            return False

