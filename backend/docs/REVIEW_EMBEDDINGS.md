# Review Embeddings System

This document explains how to use the review embeddings system powered by PostgreSQL pgvector and OpenAI's text-embedding-3-small model.

## Overview

The review embeddings system allows you to:
- Store vector embeddings of review content directly in PostgreSQL
- Perform semantic similarity searches across reviews
- Find related reviews based on meaning, not just keywords
- Enable advanced analytics and clustering

## Database Setup

### 1. Install pgvector Extension

The migration `009_add_review_embeddings.py` will automatically install the pgvector extension when you run:

```bash
cd backend
alembic upgrade head
```

This migration:
- Enables the pgvector extension in PostgreSQL
- Adds an `embedding` column (1536 dimensions) to the reviews table
- Creates an IVFFlat index for fast similarity searches

### 2. Install Dependencies

Update your Python environment:

```bash
cd backend
uv sync  # or pip install -r requirements.txt
```

## Generating Embeddings

### Using Celery Tasks (Recommended for Production)

#### Generate Embeddings for a Single Review

```python
from app.tasks.embedding_tasks import generate_review_embedding

# Queue task
result = generate_review_embedding.delay(review_id="review-123")

# Get result
status = result.get()
# Returns: {"status": "success", "review_id": "review-123"}
```

#### Generate Embeddings in Batch

```python
from app.tasks.embedding_tasks import generate_embeddings_batch

# Process 100 reviews at a time
result = generate_embeddings_batch.delay(
    company_id="company-123",  # Optional: filter by company
    batch_size=100
)

status = result.get()
# Returns: {
#     "status": "completed",
#     "processed": 95,
#     "failed": 5,
#     "total_found": 100
# }
```

#### Generate All Missing Embeddings

```python
from app.tasks.embedding_tasks import generate_all_embeddings

# Process all reviews without embeddings
result = generate_all_embeddings.delay(
    company_id="company-123",  # Optional
    batch_size=100
)

status = result.get()
# Returns: {
#     "status": "processing",
#     "total_reviews": 1500,
#     "batches_created": 15,
#     "task_group_id": "group-id-123"
# }
```

### Using the Embedding Service Directly

For scripts or one-off operations:

```python
import asyncio
from app.services.embedding_service import get_embedding_service
from app.database.session import get_async_session
from app.database.repositories.review import ReviewRepository

async def generate_single_embedding():
    embedding_service = get_embedding_service()
    
    # Generate embedding for text
    text = "This product is amazing! Best purchase ever."
    embedding = await embedding_service.generate_embedding(text)
    
    # Update review
    async with get_async_session() as db:
        await ReviewRepository.update_embedding(
            db, 
            review_id="review-123",
            embedding=embedding
        )
        await db.commit()

asyncio.run(generate_single_embedding())
```

## Performing Similarity Searches

### Basic Similarity Search

```python
import asyncio
from app.services.embedding_service import get_embedding_service
from app.database.session import get_async_session
from app.database.repositories.review import ReviewRepository

async def find_similar_reviews():
    embedding_service = get_embedding_service()
    
    # Generate embedding for search query
    query = "problems with customer service"
    query_embedding = await embedding_service.generate_embedding(query)
    
    # Search for similar reviews
    async with get_async_session() as db:
        results = await ReviewRepository.similarity_search(
            db,
            query_embedding=query_embedding,
            company_id="company-123",  # Optional
            limit=10,
            similarity_threshold=0.7  # 0-1, higher = more similar
        )
        
        # results is a list of (Review, similarity_score) tuples
        for review, score in results:
            print(f"Similarity: {score:.2f}")
            print(f"Content: {review.content[:100]}...")
            print("---")

asyncio.run(find_similar_reviews())
```

### Find Reviews Without Embeddings

```python
async def find_unprocessed_reviews():
    async with get_async_session() as db:
        reviews = await ReviewRepository.get_reviews_without_embeddings(
            db,
            limit=100,
            company_id="company-123"  # Optional
        )
        print(f"Found {len(reviews)} reviews without embeddings")

asyncio.run(find_unprocessed_reviews())
```

## API Integration Example

Here's how you might add an API endpoint for semantic search:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database.session import get_async_db_session
from app.services.embedding_service import get_embedding_service
from app.database.repositories.review import ReviewRepository
from app.models.review import ReviewResponse

router = APIRouter()

@router.get("/reviews/search-semantic")
async def search_reviews_semantic(
    query: str,
    company_id: str,
    limit: int = 10,
    threshold: float = 0.7,
    db: AsyncSession = Depends(get_async_db_session)
):
    """Search reviews using semantic similarity."""
    
    # Generate query embedding
    embedding_service = get_embedding_service()
    query_embedding = await embedding_service.generate_embedding(query)
    
    if not query_embedding:
        return {"error": "Failed to generate query embedding"}
    
    # Search for similar reviews
    results = await ReviewRepository.similarity_search(
        db,
        query_embedding=query_embedding,
        company_id=company_id,
        limit=limit,
        similarity_threshold=threshold
    )
    
    # Format response
    return {
        "query": query,
        "results": [
            {
                "review": ReviewResponse.from_orm(review),
                "similarity": score
            }
            for review, score in results
        ]
    }
```

## Background Processing

Add to your Celery worker startup to automatically process new reviews:

```python
# In app/tasks/embedding_tasks.py or a separate scheduler

from celery.schedules import crontab
from app.core.celery_app import celery_app

# Add to your Celery beat schedule
celery_app.conf.beat_schedule = {
    'generate-embeddings-hourly': {
        'task': 'app.tasks.embedding_tasks.generate_embeddings_batch',
        'schedule': crontab(minute=0),  # Run every hour
        'kwargs': {'batch_size': 100}
    },
}
```

## Configuration

Add these to your `.env` file:

```bash
# OpenAI API Key (required for embeddings)
OPENAI_API_KEY=sk-your-key-here

# Optional: Adjust embedding batch size
EMBEDDING_BATCH_SIZE=100
```

## Performance Considerations

### Indexing Strategy

The migration creates an IVFFlat index with 100 lists. For optimal performance:

- **< 10,000 reviews**: Keep default (100 lists)
- **10,000 - 100,000 reviews**: Use 1,000 lists
- **> 100,000 reviews**: Use 10,000 lists

To rebuild the index:

```sql
-- Drop old index
DROP INDEX idx_reviews_embedding;

-- Create new index with more lists
CREATE INDEX idx_reviews_embedding ON reviews 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 1000);
```

### Batch Processing

- Process embeddings in batches of 50-100 for optimal throughput
- OpenAI rate limits: ~3,000 requests/min on tier 2
- Each batch request counts as 1 request

### Cost Estimation

OpenAI text-embedding-3-small pricing (as of 2024):
- $0.02 per 1M tokens
- Average review ~100 tokens
- 1,000 reviews ≈ 100,000 tokens ≈ $0.002

## Troubleshooting

### Embeddings Not Generating

1. Check OpenAI API key: `echo $OPENAI_API_KEY`
2. Check Celery worker is running: `celery -A app.core.celery_app worker --loglevel=info`
3. Check task status in Celery logs

### Slow Similarity Searches

1. Verify index exists: `SELECT indexname FROM pg_indexes WHERE tablename = 'reviews';`
2. Run VACUUM ANALYZE: `VACUUM ANALYZE reviews;`
3. Consider increasing `lists` parameter in index

### Out of Memory Errors

- Reduce batch_size in `generate_embeddings_batch`
- Process one company at a time
- Increase Celery worker memory limit

## Additional Resources

- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [OpenAI Embeddings Guide](https://platform.openai.com/docs/guides/embeddings)
- [PostgreSQL Vector Operations](https://github.com/pgvector/pgvector#querying)

