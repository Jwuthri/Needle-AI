# Product Review Analysis Platform - Backend Implementation

## Phase 1: Cleanup Cookiecutter Demo Code

Remove demo/example business logic while preserving core infrastructure:

**Remove:**

- `/app/agents/` - example agent files
- `/app/api/v1/completions.py` - generic completion endpoints
- `/app/api/v1/team_chat.py` - team chat example (if exists)
- `/app/services/completion_service.py` - generic completion logic
- Example code from `/examples/` directory

**Keep:**

- All middleware (`/app/middleware/`)
- Logging, monitoring, tracing (`/app/core/monitoring.py`, `/app/core/tracing.py`)
- CQRS infrastructure (`/app/core/cqrs/`)
- Security (Clerk auth, rate limiting, input sanitization)
- Database layer (repositories, transaction management)
- Background tasks infrastructure (Celery setup)
- Configuration management
- Existing Agno chat service (will adapt for RAG)

## Phase 2: Database Models

Create new domain models in `/app/database/models/`:

**company.py** - Target company/product being analyzed

```python
- id, name, domain, industry, created_by (user_id)
- created_at, updated_at
```

**review_source.py** - Configurable review sources (Reddit, Twitter, etc.)

```python
- id, name, source_type (reddit/twitter/custom)
- config (JSON), is_active, cost_per_review
```

**scraping_job.py** - Background scraping tasks

```python
- id, company_id, source_id, status, progress_percentage
- total_reviews_target, reviews_fetched, cost, user_id
- started_at, completed_at, error_message
```

**review.py** - Collected reviews/feedback

```python
- id, company_id, source_id, scraping_job_id
- content, author, sentiment_score, url, metadata (JSON)
- scraped_at, processed_at
```

**user_credit.py** - Stripe payment credits

```python
- id, user_id, credits_available, total_purchased
- stripe_customer_id, last_purchase_at
```

**data_import.py** - User-uploaded data (CSV, etc.)

```python
- id, company_id, user_id, file_path, import_type (csv/json)
- status, rows_imported, created_at
```

Update existing models:

- Keep `User`, `ChatSession`, `ChatMessage` (adapt metadata)
- Remove `Completion`, update `TaskResult` for scraping jobs

## Phase 3: Pinecone RAG Integration

**Create `/app/services/vector_service.py`:**

- Initialize Pinecone index for reviews
- Embed review content using OpenAI embeddings (via Agno)
- Index reviews with metadata (company_id, source, sentiment, date)
- Query interface for RAG retrieval

**Update `/app/services/agno_chat_service.py`:**

- Configure Agno agent with Pinecone vector memory
- Add retrieval instructions for product analysis
- Context-aware responses with source attribution
- Track sources used in each response

## Phase 4: Review Scraping Architecture

**Create `/app/services/scrapers/base.py`:**

```python
class BaseReviewScraper(ABC):
    @abstractmethod
    async def scrape(company_name: str, limit: int) -> List[Review]
    @abstractmethod
    async def estimate_cost(limit: int) -> float
```

**Create pluggable scrapers:**

- `/app/services/scrapers/reddit_scraper.py` - Apify Reddit integration
- `/app/services/scrapers/twitter_scraper.py` - Apify Twitter integration
- `/app/services/scrapers/csv_importer.py` - CSV file parser

**Create `/app/services/scraper_factory.py`:**

- Registry of available scrapers
- Cost calculation per source
- Scraper selection and orchestration

## Phase 5: Background Jobs (Async Worker-Ready)

**Architecture Note:** All services use async/await for future queue-based worker distribution. Tasks can run on separate worker processes without blocking main API server.

**Create `/app/tasks/scraping_tasks.py`:**

```python
@celery_app.task(bind=True)
def scrape_reviews_task(self, job_id, company_id, source_id, limit):
    # Celery wrapper calls async function
    return asyncio.run(scrape_reviews_async(self, job_id, company_id, source_id, limit))

async def scrape_reviews_async(task, job_id, company_id, source_id, limit):
    # All operations async: database, Apify, Pinecone
    # Update progress percentage throughout
    # Scrape from source via Apify (async HTTP)
    # Process sentiment analysis (async LLM calls)
    # Index to Pinecone (async batch operations)
    # Deduct user credits (async DB transaction)
    # Update job status (async DB update)
```

**Create `/app/tasks/sentiment_tasks.py`:**

```python
@celery_app.task
def analyze_sentiment_batch(review_ids):
    return asyncio.run(analyze_sentiment_batch_async(review_ids))

async def analyze_sentiment_batch_async(review_ids):
    # Batch process reviews concurrently
    # Use asyncio.gather for parallel LLM calls
    # Async database updates
```

**Create `/app/tasks/indexing_tasks.py`:**

```python
@celery_app.task
def index_reviews_to_vector_db(review_ids):
    return asyncio.run(index_reviews_async(review_ids))

async def index_reviews_async(review_ids):
    # Async Pinecone batch indexing
    # Async embedding generation
```

## Phase 6: Stripe Payment Integration

**Create `/app/services/payment_service.py`:**

- Create Stripe customer
- Handle credit purchases
- Webhook for payment confirmation
- Credit deduction tracking

**Create `/app/api/v1/payments.py`:**

```python
POST /api/v1/payments/checkout - Create checkout session
POST /api/v1/payments/webhook - Stripe webhook handler
GET /api/v1/payments/credits - Get user credit balance
```

## Phase 7: Core API Endpoints

**Create `/app/api/v1/companies.py`:**

```python
POST /companies - Create new company analysis
GET /companies - List user's companies
GET /companies/{id} - Get company details
DELETE /companies/{id} - Delete company
```

**Create `/app/api/v1/scraping.py`:**

```python
POST /scraping/jobs - Start new scraping job
GET /scraping/jobs/{id} - Get job status & progress
GET /scraping/jobs/{id}/reviews - Get scraped reviews
GET /scraping/sources - List available sources & costs
POST /scraping/estimate - Estimate cost before scraping
```

**Create `/app/api/v1/data_imports.py`:**

```python
POST /data-imports/csv - Upload CSV file
GET /data-imports/{id}/status - Check import progress
GET /data-imports - List imports
```

**Update `/app/api/v1/chat.py`:**

```python
POST /chat - Enhanced with query visualization metadata
  Response includes:
  - message (AI response)
  - sources (list of reviews used)
  - query_type (classification of user question)
  - related_questions (suggested follow-ups)
  - pipeline_steps (for visualization like Weaviate)
  
POST /chat/attach-data - Attach specific data sources to session
GET /chat/sources/{message_id} - Get detailed sources
POST /chat/feedback - Like/dislike/copy tracking
```

## Phase 8: Analytics & Dashboard

**Create `/app/api/v1/analytics.py`:**

```python
GET /analytics/{company_id}/overview
  - Total reviews, by source
  - Sentiment distribution (pos/neg/neutral percentages)
  - Date range stats
  
GET /analytics/{company_id}/insights
  - Common themes/product gaps (LLM-generated)
  - Main competitors mentioned
  - Top feature requests
  - Comparison with competitors
  
GET /analytics/{company_id}/reviews
  - Paginated reviews with filters
  - Filter by source, sentiment, date
  - Search reviews
```

**Create `/app/services/analytics_service.py`:**

- Aggregate review statistics
- Use LLM to generate insights on-demand
- Cache common queries

## Phase 9: Enhanced Chat Features (Weaviate-style)

**Update Chat Response Model (`/app/models/chat.py`):**

```python
class QueryPipelineStep(BaseModel):
    name: str  # "Query preprocessing", "Vector search", "LLM generation"
    duration_ms: int
    status: str
    metadata: Dict[str, Any]

class ReviewSource(BaseModel):
    review_id: str
    content: str
    author: str
    source: str  # reddit/twitter
    sentiment: float
    url: Optional[str]
    relevance_score: float

class EnhancedChatResponse(ChatResponse):
    query_type: str  # "product_gap", "competitor", "sentiment"
    pipeline_steps: List[QueryPipelineStep]
    sources: List[ReviewSource]
    related_questions: List[str]
    attached_companies: List[str]  # company IDs in context
```

**Implement Pipeline Visualization:**

- Track timing for each step (query → retrieval → generation)
- Classify query intent
- Generate related questions using LLM
- Format markdown responses with proper code blocks, lists, etc.

## Phase 10: Configuration

**Update `/app/core/config/settings.py`:**

```python
# Apify
apify_api_token: str
apify_reddit_actor_id: str
apify_twitter_actor_id: str

# Pinecone
pinecone_api_key: str
pinecone_environment: str
pinecone_index_name: str = "product-reviews"

# Stripe
stripe_secret_key: str
stripe_webhook_secret: str
stripe_publishable_key: str

# Review costs (per review)
reddit_review_cost: float = 0.01
twitter_review_cost: float = 0.01
csv_review_cost: float = 0.00
```

**Update `/app/dependencies.py`:**

- Add scraper factory dependency
- Add payment service dependency
- Add vector service dependency

## Testing Strategy

Create tests in `/tests/unit/`:

- `test_scrapers.py` - Mock Apify responses
- `test_sentiment_analysis.py` - LLM sentiment scoring
- `test_payment_service.py` - Mock Stripe
- `test_vector_service.py` - Mock Pinecone
- `test_analytics.py` - Dashboard calculations

Update `/tests/integration/`:

- `test_scraping_flow.py` - End-to-end scraping
- `test_chat_with_rag.py` - RAG query flow

## Migration

Create Alembic migration in `/alembic/versions/`:

- `002_product_review_platform.py`
- Drop unused tables (completions)
- Create new tables (companies, reviews, scraping_jobs, etc.)
- Migrate existing chat tables if needed