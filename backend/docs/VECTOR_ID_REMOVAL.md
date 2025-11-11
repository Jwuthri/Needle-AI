# Vector ID Removal - Migration 010

## What Changed

Removed the redundant `vector_id` column from the `reviews` table.

## Why?

The `vector_id` column was used to store Pinecone vector IDs, but this is **completely redundant** because:

1. **You can use `review.id` directly** as the Pinecone vector ID
2. No need for a separate column to track external IDs
3. Simplifies the schema
4. One less column to maintain

## Example: Using Review ID with Pinecone

If you ever want to use Pinecone, just use the review's primary key:

```python
# Store in Pinecone using review.id
import pinecone

# Upsert to Pinecone
pinecone_index.upsert(
    vectors=[
        {
            "id": review.id,  # ← Use the review ID directly!
            "values": embedding,
            "metadata": {
                "company_id": review.company_id,
                "content": review.content[:1000],
            }
        }
    ]
)

# Query Pinecone
results = pinecone_index.query(
    vector=query_embedding,
    top_k=10,
    include_metadata=True
)

# Get reviews from database using the IDs from Pinecone
review_ids = [match.id for match in results.matches]
reviews = await ReviewRepository.get_by_ids(db, review_ids)
```

## What's Better Now

### Before (with vector_id)
```python
# Had to maintain two IDs
review.id = "abc-123"
review.vector_id = "pinecone-xyz-456"  # Separate ID, extra tracking

# Had to lookup by vector_id
review = await ReviewRepository.get_by_vector_id(db, pinecone_result.id)
```

### After (without vector_id)
```python
# Just one ID to track
review.id = "abc-123"  # Use this for everything

# Direct lookup
review = await ReviewRepository.get_by_id(db, pinecone_result.id)
```

## Migration Applied

```bash
alembic upgrade head  # Applied migration 010
```

**Result:**
- ✅ `vector_id` column removed
- ✅ `idx_reviews_vector` index removed
- ✅ Cleaner schema
- ✅ No functionality lost

## For PostgreSQL pgvector

You don't need external IDs at all - the `embedding` column stores everything:

```python
# Store embedding directly in PostgreSQL
review.embedding = embedding_vector

# Query using SQL
results = await ReviewRepository.similarity_search(db, query_embedding)
```

Much cleaner! 🎯

