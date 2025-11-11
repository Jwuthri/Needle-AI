# Review Embeddings System - Implementation Summary

## What Was Added

### 1. Database Changes

**Migration: `009_add_review_embeddings.py`**
- Enabled `pgvector` extension in PostgreSQL
- Added `embedding` column to `reviews` table (1536 dimensions)
- Created IVFFlat index for fast similarity searches using cosine distance

### 2. Services

**`app/services/embedding_service.py`**
- OpenAI text-embedding-3-small integration
- Batch processing support (up to 100 texts per batch)
- Automatic text truncation for long content
- Error handling and rate limit management

### 3. Repository Methods

**`app/database/repositories/review.py`**
- `update_embedding()` - Update single review embedding
- `bulk_update_embeddings()` - Batch update multiple reviews
- `get_reviews_without_embeddings()` - Find unprocessed reviews
- `similarity_search()` - Semantic search using cosine similarity

### 4. Background Tasks

**`app/tasks/embedding_tasks.py`**
- `generate_review_embedding` - Single review processing
- `generate_embeddings_batch` - Batch processing (100 at a time)
- `generate_all_embeddings` - Orchestrate full processing
- `regenerate_review_embedding` - Force regeneration

### 5. CLI Commands

**`app/cli_commands/review_commands.py`**
- `reviews ingest-mock` - Import mock reviews with embeddings
- `reviews generate-embeddings` - Generate missing embeddings
- `reviews stats` - Show database statistics

### 6. Dependencies

**Added to `pyproject.toml`:**
- `pgvector>=0.2.4` - PostgreSQL vector extension
- Already had: `openai>=1.3.7`, `numpy>=1.24.0`

## Quick Usage

### Ingest Mock Reviews
```bash
cd backend
alembic upgrade head
python -m app.cli_commands.main reviews ingest-mock
```

### Semantic Search
```python
from app.services.embedding_service import get_embedding_service
from app.database.repositories.review import ReviewRepository

# Generate query embedding
query = "mobile app crashes frequently"
embedding_service = get_embedding_service()
query_embedding = await embedding_service.generate_embedding(query)

# Search similar reviews
results = await ReviewRepository.similarity_search(
    db,
    query_embedding=query_embedding,
    company_id="company-123",  # Optional
    limit=10,
    similarity_threshold=0.7
)
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│             CLI / API / Background Tasks        │
└───────────────────┬─────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────┐
│         Embedding Service (OpenAI)              │
│  • Text → 1536-dimensional vectors              │
│  • Batch processing                             │
└───────────────────┬─────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────┐
│         Review Repository                        │
│  • CRUD operations                               │
│  • Similarity search                             │
└───────────────────┬─────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────┐
│      PostgreSQL + pgvector                       │
│  • Vector storage (1536 dims)                    │
│  • IVFFlat indexing                              │
│  • Cosine similarity (<=> operator)              │
└─────────────────────────────────────────────────┘
```

## Files Created/Modified

### New Files
- `backend/alembic/versions/009_add_review_embeddings.py` - Migration
- `backend/app/services/embedding_service.py` - Embedding generation
- `backend/app/tasks/embedding_tasks.py` - Celery tasks
- `backend/app/cli_commands/__init__.py` - CLI package
- `backend/app/cli_commands/main.py` - CLI entry point
- `backend/app/cli_commands/review_commands.py` - Review commands
- `backend/scripts/ingest_mock_reviews.py` - Quick run script
- `backend/docs/REVIEW_EMBEDDINGS.md` - Full documentation
- `backend/docs/CLI_USAGE.md` - CLI guide
- `backend/QUICKSTART_REVIEWS.md` - Quick start guide

### Modified Files
- `backend/app/database/models/review.py` - Added embedding column
- `backend/app/database/repositories/review.py` - Added embedding methods
- `backend/pyproject.toml` - Added pgvector dependency, updated CLI entry
- `backend/app/cli.py` - Updated import path

## Configuration

Add to `.env`:
```bash
OPENAI_API_KEY=sk-your-key-here
```

## Performance

### Indexing
- **IVFFlat** with 100 lists (default)
- Adjust for dataset size:
  - < 10K reviews: 100 lists
  - 10K-100K: 1,000 lists
  - > 100K: 10,000 lists

### Costs
- OpenAI text-embedding-3-small: $0.02 per 1M tokens
- Average review ~100 tokens
- 1,000 reviews ≈ $0.002

### Speed
- Embedding generation: ~50-100 reviews/minute
- Similarity search: < 100ms for 100K reviews (with index)

## Next Steps

1. **Run the migration**: `alembic upgrade head`
2. **Install dependencies**: `pip install pgvector`
3. **Ingest mock data**: `python -m app.cli_commands.main reviews ingest-mock`
4. **Test similarity search**: See examples in `docs/REVIEW_EMBEDDINGS.md`
5. **Build API endpoints**: Add semantic search to your API
6. **Set up automation**: Use Celery tasks for new reviews

## Documentation

- **Quick Start**: `QUICKSTART_REVIEWS.md`
- **CLI Commands**: `docs/CLI_USAGE.md`
- **Full Guide**: `docs/REVIEW_EMBEDDINGS.md`
- **Migration Details**: `alembic/versions/009_add_review_embeddings.py`

## Testing

Test the CLI:
```bash
cd backend
python -m app.cli_commands.main reviews --help
python -m app.cli_commands.main reviews ingest-mock --help
```

Test similarity search (after ingestion):
```bash
python -m app.cli_commands.main reviews stats
```

## Support

For issues:
1. Check PostgreSQL is running with pgvector installed
2. Verify OpenAI API key is set
3. Check database connection in `.env`
4. Review logs for specific errors

## Credits

Built using:
- PostgreSQL pgvector for vector storage
- OpenAI text-embedding-3-small for embeddings
- SQLAlchemy for ORM
- Celery for background tasks
- Click for CLI

