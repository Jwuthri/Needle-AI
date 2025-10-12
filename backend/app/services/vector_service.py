"""
Vector service for Pinecone integration and RAG functionality.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from pinecone import Pinecone, ServerlessSpec
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from app.config import get_settings
from app.exceptions import ConfigurationError, ExternalServiceError
from app.utils.logging import get_logger

logger = get_logger("vector_service")


class VectorService:
    """
    Service for managing vector embeddings and similarity search using Pinecone.
    
    Handles:
    - Review embedding generation
    - Vector indexing with metadata
    - Similarity search for RAG
    - Index management
    """

    def __init__(self, settings: Any = None):
        if not PINECONE_AVAILABLE:
            raise ConfigurationError("Pinecone package not installed. Install with: pip install pinecone-client")
        
        if not OPENAI_AVAILABLE:
            raise ConfigurationError("OpenAI package not installed. Install with: pip install openai")
        
        self.settings = settings or get_settings()
        self.pinecone_client: Optional[Pinecone] = None
        self.index = None
        self.openai_client = None
        self._initialized = False

    async def initialize(self):
        """Initialize Pinecone client and index."""
        if self._initialized:
            return

        try:
            # Get API keys
            pinecone_api_key = self.settings.get_secret("pinecone_api_key")
            if not pinecone_api_key:
                raise ConfigurationError("Pinecone API key not configured")

            openrouter_api_key = self.settings.get_secret("openrouter_api_key")
            if not openrouter_api_key:
                raise ConfigurationError("OpenRouter API key not configured for embeddings")

            # Initialize Pinecone
            self.pinecone_client = Pinecone(api_key=pinecone_api_key)
            
            # Initialize OpenAI client for embeddings (via OpenRouter)
            self.openai_client = openai.AsyncOpenAI(
                api_key=openrouter_api_key,
                base_url="https://openrouter.ai/api/v1"
            )

            # Get or create index
            index_name = self.settings.pinecone_index_name
            
            # Check if index exists
            existing_indexes = self.pinecone_client.list_indexes()
            index_exists = any(idx['name'] == index_name for idx in existing_indexes)

            if not index_exists:
                # Create index with serverless spec
                logger.info(f"Creating Pinecone index: {index_name}")
                self.pinecone_client.create_index(
                    name=index_name,
                    dimension=1536,  # OpenAI text-embedding-3-small dimension
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud='aws',
                        region='us-east-1'  # Default, can be configured
                    )
                )

            # Connect to index
            self.index = self.pinecone_client.Index(index_name)
            
            self._initialized = True
            logger.info(f"Vector service initialized with index: {index_name}")

        except Exception as e:
            logger.error(f"Failed to initialize vector service: {e}")
            raise ConfigurationError(f"Vector service initialization failed: {e}")

    async def cleanup(self):
        """Cleanup resources."""
        self._initialized = False
        logger.debug("Vector service cleaned up")

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text using OpenAI embeddings via OpenRouter.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Use text-embedding-3-small model (cost-effective)
            response = await self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            
            embedding = response.data[0].embedding
            return embedding

        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise ExternalServiceError(f"Failed to generate embedding: {e}", service="openai_embeddings")

    async def index_review(
        self,
        review_id: str,
        content: str,
        company_id: str,
        source: str,
        sentiment_score: Optional[float] = None,
        author: Optional[str] = None,
        url: Optional[str] = None,
        review_date: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Index a single review into Pinecone.
        
        Args:
            review_id: Unique review ID
            content: Review text content
            company_id: Company ID
            source: Review source (reddit, twitter, etc.)
            sentiment_score: Sentiment score (-1 to 1)
            author: Review author
            url: Original review URL
            review_date: Original review timestamp
            metadata: Additional metadata
            
        Returns:
            Vector ID in Pinecone
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Generate embedding
            embedding = await self.generate_embedding(content)

            # Prepare metadata
            vector_metadata = {
                "review_id": review_id,
                "company_id": company_id,
                "source": source,
                "content": content[:1000],  # Store truncated content for retrieval
                "indexed_at": datetime.utcnow().isoformat(),
            }

            if sentiment_score is not None:
                vector_metadata["sentiment_score"] = sentiment_score

            if author:
                vector_metadata["author"] = author

            if url:
                vector_metadata["url"] = url

            if review_date:
                vector_metadata["review_date"] = review_date.isoformat()

            if metadata:
                vector_metadata.update(metadata)

            # Upsert to Pinecone
            vector_id = f"review_{review_id}"
            self.index.upsert(
                vectors=[{
                    "id": vector_id,
                    "values": embedding,
                    "metadata": vector_metadata
                }]
            )

            logger.debug(f"Indexed review {review_id} as vector {vector_id}")
            return vector_id

        except Exception as e:
            logger.error(f"Error indexing review {review_id}: {e}")
            raise ExternalServiceError(f"Failed to index review: {e}", service="pinecone")

    async def index_reviews_batch(
        self,
        reviews: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> List[str]:
        """
        Index multiple reviews in batches.
        
        Args:
            reviews: List of review dictionaries
            batch_size: Number of reviews per batch
            
        Returns:
            List of vector IDs
        """
        if not self._initialized:
            await self.initialize()

        vector_ids = []
        
        try:
            # Process in batches
            for i in range(0, len(reviews), batch_size):
                batch = reviews[i:i + batch_size]
                
                # Generate embeddings concurrently
                embedding_tasks = [
                    self.generate_embedding(review["content"])
                    for review in batch
                ]
                embeddings = await asyncio.gather(*embedding_tasks)

                # Prepare vectors for upsert
                vectors = []
                for review, embedding in zip(batch, embeddings):
                    review_id = review["review_id"]
                    vector_id = f"review_{review_id}"
                    
                    vector_metadata = {
                        "review_id": review_id,
                        "company_id": review["company_id"],
                        "source": review["source"],
                        "content": review["content"][:1000],
                        "indexed_at": datetime.utcnow().isoformat(),
                    }
                    
                    # Add optional fields
                    for field in ["sentiment_score", "author", "url", "review_date"]:
                        if field in review and review[field]:
                            value = review[field]
                            if field == "review_date" and isinstance(value, datetime):
                                value = value.isoformat()
                            vector_metadata[field] = value

                    vectors.append({
                        "id": vector_id,
                        "values": embedding,
                        "metadata": vector_metadata
                    })
                    
                    vector_ids.append(vector_id)

                # Upsert batch
                self.index.upsert(vectors=vectors)
                logger.info(f"Indexed batch of {len(vectors)} reviews")

            return vector_ids

        except Exception as e:
            logger.error(f"Error in batch indexing: {e}")
            raise ExternalServiceError(f"Failed to batch index reviews: {e}", service="pinecone")

    async def search_similar_reviews(
        self,
        query: str,
        company_id: Optional[str] = None,
        source: Optional[str] = None,
        top_k: int = 10,
        min_score: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search for similar reviews using semantic similarity.
        
        Args:
            query: Search query text
            company_id: Filter by company ID
            source: Filter by source
            top_k: Number of results to return
            min_score: Minimum similarity score
            
        Returns:
            List of similar reviews with scores and metadata
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Generate query embedding
            query_embedding = await self.generate_embedding(query)

            # Prepare filter
            filter_dict = {}
            if company_id:
                filter_dict["company_id"] = company_id
            if source:
                filter_dict["source"] = source

            # Query Pinecone
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                filter=filter_dict if filter_dict else None
            )

            # Format results
            similar_reviews = []
            for match in results.matches:
                if match.score >= min_score:
                    similar_reviews.append({
                        "review_id": match.metadata.get("review_id"),
                        "content": match.metadata.get("content"),
                        "company_id": match.metadata.get("company_id"),
                        "source": match.metadata.get("source"),
                        "sentiment_score": match.metadata.get("sentiment_score"),
                        "author": match.metadata.get("author"),
                        "url": match.metadata.get("url"),
                        "relevance_score": match.score,
                        "vector_id": match.id
                    })

            logger.debug(f"Found {len(similar_reviews)} similar reviews for query")
            return similar_reviews

        except Exception as e:
            logger.error(f"Error searching similar reviews: {e}")
            raise ExternalServiceError(f"Failed to search reviews: {e}", service="pinecone")

    async def delete_review(self, vector_id: str) -> bool:
        """Delete a review from the index."""
        if not self._initialized:
            await self.initialize()

        try:
            self.index.delete(ids=[vector_id])
            logger.debug(f"Deleted vector: {vector_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting vector {vector_id}: {e}")
            return False

    async def delete_company_reviews(self, company_id: str) -> bool:
        """Delete all reviews for a company."""
        if not self._initialized:
            await self.initialize()

        try:
            self.index.delete(filter={"company_id": company_id})
            logger.info(f"Deleted all reviews for company: {company_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting company reviews: {e}")
            return False

    async def get_index_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        if not self._initialized:
            await self.initialize()

        try:
            stats = self.index.describe_index_stats()
            return {
                "total_vectors": stats.total_vector_count,
                "dimension": stats.dimension,
                "index_fullness": stats.index_fullness,
                "namespaces": stats.namespaces
            }

        except Exception as e:
            logger.error(f"Error getting index stats: {e}")
            return {}

    async def health_check(self) -> bool:
        """Check if vector service is healthy."""
        try:
            if not self._initialized:
                await self.initialize()

            # Try to get index stats
            await self.get_index_stats()
            return True

        except Exception as e:
            logger.error(f"Vector service health check failed: {e}")
            return False

