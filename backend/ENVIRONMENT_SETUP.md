# Environment Setup Checklist

## 📋 Quick Setup (5 minutes)

### 1. Copy Environment Template

```bash
cd backend
cp .env.template .env
```

### 2. Add Required API Keys

Open `.env` and add your keys:

```bash
# Minimum for basic functionality
OPENROUTER_API_KEY=sk-or-v1-...           # For chat & embeddings
PINECONE_API_KEY=...                       # For vector search
DATABASE_URL=postgresql://user:pass@host/db  # Your database

# For full functionality  
APIFY_API_TOKEN=...                        # For web scraping
STRIPE_SECRET_KEY=sk_test_...              # For payments
STRIPE_WEBHOOK_SECRET=whsec_...            # For payment webhooks
```

### 3. Install Dependencies

```bash
uv pip install pinecone-client stripe apify-client pandas
```

### 4. Run Database Migration

```bash
uv run alembic upgrade head
```

### 5. Start the Server

```bash
uvicorn app.main:app --reload
```

## 🔑 Where to Get API Keys

### OpenRouter (Required)
1. Visit: https://openrouter.ai
2. Sign up/login
3. Go to "Keys" section
4. Create new key
5. Copy to `OPENROUTER_API_KEY`

### Pinecone (Required for RAG)
1. Visit: https://pinecone.io
2. Sign up for free tier
3. Go to "API Keys"
4. Copy API key to `PINECONE_API_KEY`
5. Note your environment (usually `gcp-starter`)

### Apify (Optional - for scraping)
1. Visit: https://apify.com
2. Sign up for free tier
3. Go to "Settings" → "Integrations"
4. Copy personal API token to `APIFY_API_TOKEN`

### Stripe (Optional - for payments)
1. Visit: https://stripe.com
2. Sign up/login
3. Go to "Developers" → "API keys"
4. Use test keys for development:
   - Copy "Secret key" to `STRIPE_SECRET_KEY`
   - Copy "Publishable key" to `STRIPE_PUBLISHABLE_KEY`
5. For webhooks:
   - Install Stripe CLI: `brew install stripe/stripe-cli/stripe`
   - Run: `stripe listen --forward-to localhost:8000/api/v1/payments/webhook`
   - Copy webhook secret to `STRIPE_WEBHOOK_SECRET`

## 📝 Environment Variables Reference

### Core Settings
```bash
APP_NAME="NeedleAi"
ENVIRONMENT=development    # development | production
DEBUG=true                 # true | false
HOST=0.0.0.0
PORT=8000
```

### Database
```bash
# PostgreSQL (recommended)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/needleai

# SQLite (testing only)
DATABASE_URL=sqlite:///./needleai.db
```

### Redis (Required for Celery)
```bash
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

### LLM Provider
```bash
LLM_PROVIDER=openrouter   # openrouter | openai | anthropic
OPENROUTER_API_KEY=your-key-here
DEFAULT_MODEL=gpt-4
MAX_TOKENS=1000
TEMPERATURE=0.7
```

### Vector Database
```bash
VECTOR_DATABASE=pinecone   # pinecone | weaviate | qdrant | chromadb
PINECONE_API_KEY=your-key-here
PINECONE_ENVIRONMENT=gcp-starter
PINECONE_INDEX_NAME=product-reviews
```

### Memory Configuration
```bash
MEMORY_TYPE=chat           # chat | vector | hybrid
MEMORY_BACKEND=redis       # redis | in_memory
```

### Web Scraping
```bash
APIFY_API_TOKEN=your-token-here
APIFY_REDDIT_ACTOR_ID=trudax/reddit-scraper
APIFY_TWITTER_ACTOR_ID=apidojo/tweet-scraper

# Cost per review (in credits, 1 USD = 100 credits)
REDDIT_REVIEW_COST=0.01    # $1 per 100 reviews
TWITTER_REVIEW_COST=0.01   # $1 per 100 reviews
CSV_REVIEW_COST=0.00       # Free for CSV imports
```

### Payments
```bash
STRIPE_SECRET_KEY=sk_test_your-key
STRIPE_PUBLISHABLE_KEY=pk_test_your-key
STRIPE_WEBHOOK_SECRET=whsec_your-secret
STRIPE_CURRENCY=usd
```

### RAG Configuration
```bash
RAG_TOP_K_RESULTS=5              # Number of reviews to retrieve
RAG_SIMILARITY_THRESHOLD=0.7     # Minimum similarity (0.0-1.0)
```

### Security (Clerk Auth)
```bash
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
CLERK_JWT_KEY=your-jwt-key
```

### CORS
```bash
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### Rate Limiting
```bash
RATE_LIMIT_REQUESTS=100    # Requests per window
RATE_LIMIT_WINDOW=60       # Window in seconds
```

### File Uploads
```bash
MAX_UPLOAD_SIZE=10485760   # 10MB in bytes
ALLOWED_UPLOAD_TYPES=.txt,.pdf,.doc,.docx,.json,.csv,.xlsx
UPLOAD_DIR=data/uploads
```

### Monitoring (Optional)
```bash
ENABLE_METRICS=false
ENABLE_TRACING=false
TRACING_EXPORTER=console   # console | jaeger | zipkin | otlp
```

## 🚀 Quick Test

After setup, test the platform:

```bash
# 1. Health check
curl http://localhost:8000/api/v1/health

# 2. View API docs
open http://localhost:8000/docs

# 3. Test with example request
curl -X POST http://localhost:8000/api/v1/companies \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Company", "domain": "example.com"}'
```

## 🔧 Troubleshooting

### Database Connection Error
```bash
# Check if PostgreSQL is running
pg_isready

# Or use Docker
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres
```

### Redis Connection Error
```bash
# Check if Redis is running
redis-cli ping

# Or use Docker
docker run -d -p 6379:6379 redis
```

### Import Errors
```bash
# Reinstall dependencies
uv pip install -r requirements.txt
```

### Migration Errors
```bash
# Reset database (WARNING: Deletes all data)
uv run alembic downgrade base
uv run alembic upgrade head
```

## 📚 Next Steps

1. ✅ Setup environment → You are here
2. Read `START_HERE.md` for quick start guide
3. Read `FINAL_SUMMARY.md` for complete overview
4. Read `TESTING_GUIDE.md` for testing examples
5. Check `ASYNC_MIGRATION_COMPLETE.md` for async status

## 💡 Pro Tips

1. **Development**: Use SQLite for quick testing
   ```bash
   DATABASE_URL=sqlite:///./test.db
   ```

2. **Production**: Use PostgreSQL with connection pooling
   ```bash
   DATABASE_URL=postgresql://user:pass@host/db?pool_size=20
   ```

3. **Testing**: Set `CELERY_TASK_ALWAYS_EAGER=true` to run tasks synchronously

4. **Debugging**: Set `LOG_LEVEL=DEBUG` for verbose logging

5. **Free Tier**: All services offer free tiers for development!

