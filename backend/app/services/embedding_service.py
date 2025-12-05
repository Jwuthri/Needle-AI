"""
Embedding service for generating vector embeddings using OpenAI.
"""

import logging
from typing import List, Optional
import openai
from openai import AsyncOpenAI

from app.core.config.settings import get_settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating embeddings using OpenAI's text-embedding-3-small model."""
    
    def __init__(self):
        """Initialize the embedding service."""
        self.settings = get_settings()
        self.client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        self.model = "text-embedding-3-small"
        self.dimensions = 1536
    
    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to generate embedding for
            
        Returns:
            List of floats representing the embedding vector, or None if generation fails
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding generation")
            return None
        
        try:
            # Truncate text if too long (OpenAI has 8191 token limit for embeddings)
            # Rough estimate: 1 token ≈ 4 characters
            max_chars = 30000  # Conservative limit
            if len(text) > max_chars:
                text = text[:max_chars]
                logger.info(f"Text truncated to {max_chars} characters for embedding")
            
            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
                encoding_format="float"
            )
            
            embedding = response.data[0].embedding
            logger.debug(f"Generated embedding with {len(embedding)} dimensions")
            
            return embedding
            
        except openai.RateLimitError as e:
            logger.error(f"OpenAI rate limit exceeded: {e}")
            raise
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error generating embedding: {e}")
            raise
    
    async def generate_embeddings_batch(
        self, 
        texts: List[str],
        batch_size: int = 512
    ) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts in batches.
        
        Args:
            texts: List of texts to generate embeddings for
            batch_size: Number of texts to process in each batch
            
        Returns:
            List of embedding vectors (same length as input texts)
        """
        if not texts:
            return []
        
        embeddings = []
        
        # Process in batches to avoid rate limits
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            # Filter out empty texts
            valid_batch = [(idx, text) for idx, text in enumerate(batch) if text and text.strip()]
            
            if not valid_batch:
                embeddings.extend([None] * len(batch))
                continue
            
            try:
                # Truncate texts if needed
                max_chars = 30000
                processed_texts = [
                    text[:max_chars] if len(text) > max_chars else text
                    for _, text in valid_batch
                ]
                
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=processed_texts,
                    encoding_format="float"
                )
                
                # Map embeddings back to original positions
                batch_embeddings = [None] * len(batch)
                for (orig_idx, _), embedding_data in zip(valid_batch, response.data):
                    batch_embeddings[orig_idx] = embedding_data.embedding
                
                embeddings.extend(batch_embeddings)
                
                logger.info(f"Generated {len(valid_batch)} embeddings in batch {i//batch_size + 1}")
                
            except Exception as e:
                logger.error(f"Error generating embeddings for batch {i//batch_size + 1}: {e}")
                # Add None for failed batch
                embeddings.extend([None] * len(batch))
        
        return embeddings
    
    def get_dimensions(self) -> int:
        """Get the dimensions of the embedding model."""
        return self.dimensions


# Singleton instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get or create the embedding service singleton."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service

