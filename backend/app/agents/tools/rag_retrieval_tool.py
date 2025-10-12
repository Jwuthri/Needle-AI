"""
RAG Retrieval Tool - Searches vector database for relevant reviews.
"""

from typing import Any, Dict, List, Optional

from app.agents.tools.base_tool import BaseTool, ToolResult
from app.config import get_settings
from app.services.vector_service import VectorService
from app.utils.logging import get_logger

logger = get_logger("rag_retrieval_tool")


class RAGRetrievalTool(BaseTool):
    """
    Retrieves relevant documents from the vector database (Pinecone).
    
    Searches product reviews based on semantic similarity to the query.
    Returns the most relevant reviews with metadata and relevance scores.
    """
    
    def __init__(self):
        super().__init__()
        self.settings = get_settings()
        self.vector_service: Optional[VectorService] = None
        self._initialized = False
    
    @property
    def name(self) -> str:
        return "rag_retrieval"
    
    @property
    def description(self) -> str:
        return """Search the vector database for relevant product reviews and customer feedback.

Use this tool when:
- User asks about product reviews, customer feedback, or user opinions
- Query mentions specific companies or products
- Analysis requires data from stored reviews

Parameters:
- query: The search query (user's question)
- company_id: Optional company ID to filter results
- website: Optional website filter (e.g., "g2", "capterra", "trustpilot")
- sentiment: Optional sentiment filter ("positive", "negative", "neutral")
- top_k: Number of results to return (default 15)
- min_score: Minimum relevance score 0-1 (default 0.7)

Returns relevant reviews with content, metadata, and relevance scores.
"""
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query to find relevant reviews"
                },
                "company_id": {
                    "type": "string",
                    "description": "Optional company ID to filter results"
                },
                "website": {
                    "type": "string",
                    "description": "Optional website to filter by (e.g., 'g2', 'capterra', 'trustpilot')"
                },
                "sentiment": {
                    "type": "string",
                    "enum": ["positive", "negative", "neutral"],
                    "description": "Optional sentiment filter"
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return",
                    "default": 15
                },
                "min_score": {
                    "type": "number",
                    "description": "Minimum relevance score (0-1)",
                    "default": 0.7
                }
            },
            "required": ["query"]
        }
    
    async def _ensure_initialized(self):
        """Ensure vector service is initialized."""
        if not self._initialized:
            self.vector_service = VectorService(self.settings)
            await self.vector_service.initialize()
            self._initialized = True
    
    async def execute(
        self,
        query: str,
        company_id: Optional[str] = None,
        website: Optional[str] = None,
        sentiment: Optional[str] = None,
        top_k: int = 15,
        min_score: float = 0.7,
        **kwargs
    ) -> ToolResult:
        """
        Search vector database for relevant reviews.
        
        Args:
            query: Search query
            company_id: Optional company ID to filter
            website: Optional website to filter by
            sentiment: Optional sentiment filter (positive/negative/neutral)
            top_k: Number of results to return
            min_score: Minimum relevance score
            
        Returns:
            ToolResult with retrieved reviews and metadata
        """
        try:
            await self._ensure_initialized()
            
            if not self.vector_service:
                return ToolResult(
                    success=False,
                    summary="Vector service not available",
                    error="Vector service failed to initialize"
                )
            
            # Search for relevant reviews
            all_reviews = await self.vector_service.search_similar_reviews(
                query=query,
                company_id=company_id,
                top_k=top_k * 2,  # Get more initially for filtering
                min_score=min_score
            )
            
            # Apply additional filters
            filtered_reviews = []
            for review in all_reviews:
                # Filter by website
                if website:
                    review_website = review.get("source", "").lower()
                    if website.lower() not in review_website:
                        continue
                
                # Filter by sentiment
                if sentiment:
                    review_sentiment = self._classify_sentiment(review.get("sentiment_score", 0))
                    if review_sentiment != sentiment.lower():
                        continue
                
                filtered_reviews.append(review)
            
            # Deduplicate and sort by relevance
            seen_ids = set()
            unique_reviews = []
            for review in sorted(filtered_reviews, key=lambda x: x.get("relevance_score", 0), reverse=True):
                review_id = review.get("review_id")
                if review_id and review_id not in seen_ids:
                    seen_ids.add(review_id)
                    unique_reviews.append(review)
            
            # Limit to top_k
            unique_reviews = unique_reviews[:top_k]
            
            # Prepare structured output
            result_data = {
                "reviews": unique_reviews,
                "count": len(unique_reviews),
                "avg_relevance": (
                    sum(r.get("relevance_score", 0) for r in unique_reviews) / len(unique_reviews)
                    if unique_reviews else 0
                ),
                "company_id": company_id,
                "website": website,
                "sentiment": sentiment,
                "query": query
            }
            
            # Build summary
            summary = f"Found {len(unique_reviews)} relevant reviews"
            if company_id:
                summary += f" for company {company_id}"
            if website:
                summary += f" from {website}"
            if sentiment:
                summary += f" with {sentiment} sentiment"
            if unique_reviews:
                avg_score = result_data["avg_relevance"]
                summary += f" (avg relevance: {avg_score:.2f})"
            
            return ToolResult(
                success=True,
                data=result_data,
                summary=summary,
                metadata={
                    "top_k": top_k,
                    "min_score": min_score,
                    "query_length": len(query),
                    "filters_applied": {
                        "company_id": company_id is not None,
                        "website": website is not None,
                        "sentiment": sentiment is not None
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"RAG retrieval failed: {e}", exc_info=True)
            return ToolResult(
                success=False,
                summary=f"Failed to retrieve reviews: {str(e)}",
                error=str(e)
            )
    
    def _classify_sentiment(self, sentiment_score: float) -> str:
        """Classify sentiment score into positive/negative/neutral."""
        if sentiment_score > 0.33:
            return "positive"
        elif sentiment_score < -0.33:
            return "negative"
        else:
            return "neutral"
    
    async def cleanup(self):
        """Cleanup vector service resources."""
        if self.vector_service:
            await self.vector_service.cleanup()
            self._initialized = False

