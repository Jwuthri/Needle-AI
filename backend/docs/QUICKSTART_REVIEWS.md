# Quick Start: Ingesting Mock Reviews

This guide will help you quickly ingest the mock reviews into your database with embeddings.

## Prerequisites

1. **PostgreSQL with pgvector** running
2. **OpenAI API key** set in `.env`:
   ```bash
   OPENAI_API_KEY=sk-your-key-here
   ```
3. **Dependencies installed**:
   ```bash
   cd backend
   pip install pgvector  # or: uv add pgvector
   ```

## Step 1: Run the Migration

```bash
cd backend
alembic upgrade head
```

This adds the `embedding` column to the `reviews` table with pgvector support.

## Step 2: Ingest Mock Reviews

### Option A: Full Ingestion (with embeddings)

```bash
cd backend
python -m app.cli_commands.main reviews ingest-mock
```

This will:
- ✅ Create 4 companies (Spotify, Notion, Slack, Netflix)
- ✅ Insert 190 reviews
- ✅ Generate embeddings for all reviews (~2-3 minutes)

### Option B: Quick Test (no embeddings)

```bash
cd backend
python -m app.cli_commands.main reviews ingest-mock --skip-embeddings
```

This completes in seconds, then generate embeddings later:

```bash
python -m app.cli_commands.main reviews generate-embeddings
```

## Step 3: Verify

```bash
python -m app.cli_commands.main reviews stats
```

Expected output:
```
📊 Review Statistics

Overall Statistics
  Companies: 4
  Total Reviews: 190
  With Embeddings: 190
  Missing Embeddings: 0
```

## What Gets Created

### Companies
- **Spotify**: 80 reviews
- **Notion**: 60 reviews  
- **Slack**: 30 reviews
- **Netflix**: 50 reviews

### Review Source
- Name: "Mock Data Import"
- Type: CUSTOM_CSV
- Cost: $0.00 per review

### Data Fields
Each review includes:
- `content`: The review text
- `author`: Username
- `sentiment_score`: -1.0 to 1.0 (derived from rating)
- `embedding`: 1536-dimensional vector (OpenAI text-embedding-3-small)
- `extra_metadata`: Original rating, source platform, category

## Next Steps

### 1. Try Semantic Search

```python
from app.database.session import get_db_session
from app.database.repositories.review import ReviewRepository
from app.services.embedding_service import get_embedding_service
import asyncio

async def search():
    embedding_service = get_embedding_service()
    query_embedding = await embedding_service.generate_embedding(
        "problems with mobile app performance"
    )
    
    async with get_db_session() as db:
        results = await ReviewRepository.similarity_search(
            db,
            query_embedding=query_embedding,
            limit=5,
            similarity_threshold=0.7
        )
        
        for review, score in results:
            print(f"Similarity: {score:.2f}")
            print(f"Company: {review.company.name}")
            print(f"Review: {review.content[:100]}...")
            print("---")

asyncio.run(search())
```

### 2. Build API Endpoint

See `docs/REVIEW_EMBEDDINGS.md` for example API endpoints.

### 3. Set Up Background Processing

Use Celery tasks for production:

```python
from app.tasks.embedding_tasks import generate_all_embeddings

# Queue all embeddings
generate_all_embeddings.delay()
```

## Troubleshooting

### "No module named 'pgvector'"
```bash
pip install pgvector
```

### "No module named 'click'" or "No module named 'rich'"
```bash
pip install click rich
```

### Database connection error
Check `.env`:
```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/needleai
```

### OpenAI rate limit
Reduce batch size:
```bash
python -m app.cli_commands.main reviews ingest-mock --batch-size 10
```

## Cost Estimate

OpenAI text-embedding-3-small pricing:
- $0.02 per 1M tokens
- 190 reviews × ~100 tokens = ~19,000 tokens
- Cost: ~$0.0004 (less than a cent)

## Commands Reference

```bash
# Ingest all reviews
python -m app.cli_commands.main reviews ingest-mock

# Ingest without embeddings (fast)
python -m app.cli_commands.main reviews ingest-mock --skip-embeddings

# Generate embeddings later
python -m app.cli_commands.main reviews generate-embeddings

# Generate for specific company
python -m app.cli_commands.main reviews generate-embeddings --company Spotify

# Show stats
python -m app.cli_commands.main reviews stats
python -m app.cli_commands.main reviews stats --company Notion

# Get help
python -m app.cli_commands.main reviews --help
```

## Full Documentation

- **CLI Usage**: `docs/CLI_USAGE.md`
- **Embeddings Guide**: `docs/REVIEW_EMBEDDINGS.md`

