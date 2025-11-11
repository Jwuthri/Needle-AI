# NeedleAI CLI - Review Management Commands

This CLI provides commands for managing reviews, including ingestion and embedding generation.

## Installation

Make sure you're in the backend directory and have installed dependencies:

```bash
cd backend
uv sync  # or pip install -e .
```

## Running the Migration

Before ingesting reviews, run the database migration to add the embedding column:

```bash
alembic upgrade head
```

## Commands

### 1. Ingest Mock Reviews

Ingest reviews from `data/mock_reviews.py` into the database:

```bash
# Basic usage - ingests all reviews with embeddings
python -m app.cli_commands.main reviews ingest-mock

# Or use the script shortcut
python scripts/ingest_mock_reviews.py

# Skip embeddings for faster testing
python -m app.cli_commands.main reviews ingest-mock --skip-embeddings

# Use custom file path
python -m app.cli_commands.main reviews ingest-mock --file path/to/reviews.py

# Adjust batch size for embedding generation
python -m app.cli_commands.main reviews ingest-mock --batch-size 25
```

**What it does:**
- Creates companies (Spotify, Notion, Slack, Netflix) if they don't exist
- Creates a "Mock Data Import" review source
- Inserts all 190 reviews into the database
- Generates embeddings using OpenAI text-embedding-3-small
- Converts ratings (1-5) to sentiment scores (-1 to 1)

**Options:**
- `--file, -f`: Path to mock reviews file (default: `data/mock_reviews.py`)
- `--skip-embeddings`: Skip embedding generation (faster for testing)
- `--batch-size, -b`: Batch size for embedding generation (default: 50)

**Example output:**
```
🚀 Starting Mock Review Ingestion

📂 Loading mock reviews from: data/mock_reviews.py
✓ Loaded 190 reviews for 4 companies

📋 Setting up review source...
✓ Review source ready: Mock Data Import

🤖 Embedding service initialized

  ✓ Spotify: 80 reviews with embeddings
  ✓ Notion: 60 reviews with embeddings
  ✓ Slack: 30 reviews with embeddings
  ✓ Netflix: 20 reviews with embeddings

🎉 Ingestion Complete!

Summary:
  • Companies: 4
  • Total Reviews: 190
  • Embeddings: Generated
```

### 2. Generate Embeddings

Generate embeddings for reviews that don't have them:

```bash
# Generate for all reviews
python -m app.cli_commands.main reviews generate-embeddings

# Generate only for a specific company
python -m app.cli_commands.main reviews generate-embeddings --company Spotify

# Limit the number of reviews to process
python -m app.cli_commands.main reviews generate-embeddings --limit 100

# Adjust batch size
python -m app.cli_commands.main reviews generate-embeddings --batch-size 50
```

**Options:**
- `--company, -c`: Company name to filter reviews
- `--batch-size, -b`: Batch size for processing (default: 100)
- `--limit, -l`: Limit number of reviews to process

### 3. Show Statistics

Display statistics about reviews in the database:

```bash
# Overall statistics
python -m app.cli_commands.main reviews stats

# Statistics for a specific company
python -m app.cli_commands.main reviews stats --company Spotify
```

**Example output:**
```
📊 Review Statistics

Overall Statistics
  Companies: 4
  Total Reviews: 190
  With Embeddings: 190
  Missing Embeddings: 0
```

## Environment Setup

Make sure you have your OpenAI API key set in your `.env` file:

```bash
OPENAI_API_KEY=sk-your-key-here
```

## Troubleshooting

### Import Errors

If you get import errors, make sure you're running from the backend directory:

```bash
cd backend
python -m app.cli_commands.main reviews ingest-mock
```

### Database Connection Errors

Check your database connection in `.env`:

```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/needleai
```

Make sure PostgreSQL is running:

```bash
# Check if running
pg_isready

# Start if needed (macOS)
brew services start postgresql

# Start if needed (Linux)
sudo systemctl start postgresql
```

### OpenAI API Errors

If embeddings fail:
1. Check your API key is valid
2. Check you have available credits
3. Try reducing batch size: `--batch-size 10`

### Missing Dependencies

Install missing dependencies:

```bash
uv sync
# or
pip install -e .
```

## Advanced Usage

### Custom Review Format

To ingest your own reviews, create a Python file with this format:

```python
MOCK_REVIEWS = {
    "CompanyName": [
        {
            "id": 1,
            "category": "review",
            "rating": 5,
            "text": "Great product!",
            "source": "app_store",
            "date": "2025-10-15",
            "author": "user123"
        },
        # ... more reviews
    ],
    # ... more companies
}
```

Then ingest:

```bash
python -m app.cli_commands.main reviews ingest-mock --file your_reviews.py
```

### Batch Processing Script

For processing large datasets, create a script:

```python
import asyncio
from app.cli_commands.review_commands import _ingest_mock_reviews

async def main():
    # Process without embeddings first (fast)
    await _ingest_mock_reviews("data/mock_reviews.py", skip_embeddings=True, batch_size=50)
    
    # Then generate embeddings in background
    # (or use Celery task from embedding_tasks.py)

asyncio.run(main())
```

## Integration with Celery

For production, use Celery tasks instead:

```python
from app.tasks.embedding_tasks import generate_all_embeddings

# Queue embedding generation
result = generate_all_embeddings.delay(batch_size=100)
```

See `docs/REVIEW_EMBEDDINGS.md` for more details.

## Next Steps

After ingesting reviews:

1. **Try semantic search:**
   ```python
   from app.database.repositories.review import ReviewRepository
   # See docs/REVIEW_EMBEDDINGS.md for examples
   ```

2. **Build analytics dashboards**
3. **Set up automated embedding generation for new reviews**
4. **Create API endpoints for semantic search**

## Help

For more information about any command:

```bash
python -m app.cli_commands.main --help
python -m app.cli_commands.main reviews --help
python -m app.cli_commands.main reviews ingest-mock --help
```

