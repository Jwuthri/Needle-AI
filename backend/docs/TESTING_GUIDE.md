# Testing Guide

This document outlines the testing strategy for the Product Review Analysis Platform.

## Test Structure

```
tests/
├── unit/                      # Isolated component tests
│   ├── test_scrapers.py      # Scraper logic (mocked external APIs)
│   ├── test_vector_service.py # Pinecone/embedding tests
│   ├── test_payment_service.py # Stripe integration tests
│   ├── test_rag_chat.py      # RAG service tests
│   └── test_analytics.py     # Analytics service tests
│
├── integration/               # End-to-end workflow tests
│   ├── test_scraping_flow.py # Complete scraping workflow
│   ├── test_chat_with_rag.py # RAG query flow
│   └── test_payment_flow.py  # Credit purchase & usage
│
└── performance/               # Load and performance tests
    └── test_concurrent_scraping.py
```

## Unit Test Examples

### Testing Scrapers (Mocked)

```python
# tests/unit/test_scrapers.py
import pytest
from unittest.mock import AsyncMock, patch
from app.services.scrapers import RedditScraper, TwitterScraper, CSVImporter

@pytest.mark.asyncio
async def test_reddit_scraper_with_mock():
    """Test Reddit scraper with mocked Apify response."""
    with patch('aiohttp.ClientSession') as mock_session:
        # Mock Apify API responses
        mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value.json.return_value = {
            "data": {"id": "run_123"}
        }
        
        scraper = RedditScraper(settings)
        reviews = await scraper.scrape("gorgias", limit=10)
        
        assert len(reviews) > 0
        assert reviews[0].content is not None

@pytest.mark.asyncio
async def test_csv_importer():
    """Test CSV import with sample file."""
    csv_content = "content,author,date\nGreat product!,John,2024-01-01"
    
    # Create temp CSV
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(csv_content)
        temp_path = f.name
    
    try:
        importer = CSVImporter(settings)
        reviews = await importer.scrape(temp_path, limit=10)
        
        assert len(reviews) == 1
        assert reviews[0].content == "Great product!"
        assert reviews[0].author == "John"
    finally:
        os.unlink(temp_path)
```

### Testing Vector Service

```python
# tests/unit/test_vector_service.py
@pytest.mark.asyncio
async def test_vector_search():
    """Test similarity search with mock Pinecone."""
    with patch('pinecone.Index') as mock_index:
        mock_index.return_value.query.return_value = Mock(
            matches=[
                Mock(id="rev_1", score=0.95, metadata={"content": "Test review"})
            ]
        )
        
        vector_service = VectorService()
        await vector_service.initialize()
        
        results = await vector_service.search_similar_reviews(
            query="product feedback",
            company_id="comp_123",
            top_k=10
        )
        
        assert len(results) > 0
        assert results[0]['relevance_score'] >= 0.7
```

### Testing Payment Service

```python
# tests/unit/test_payment_service.py
@pytest.mark.asyncio
async def test_checkout_session_creation():
    """Test Stripe checkout session creation."""
    with patch('stripe.checkout.Session.create') as mock_create:
        mock_create.return_value = Mock(
            id="cs_test_123",
            url="https://checkout.stripe.com/test"
        )
        
        payment_service = PaymentService()
        result = await payment_service.create_checkout_session(
            user_id="user_123",
            package_name="starter",
            success_url="http://localhost/success",
            cancel_url="http://localhost/cancel"
        )
        
        assert result['session_id'] == "cs_test_123"
        assert "checkout.stripe.com" in result['checkout_url']
```

## Integration Tests

### Complete Scraping Workflow

```python
# tests/integration/test_scraping_flow.py
@pytest.mark.asyncio
@pytest.mark.integration
async def test_complete_scraping_workflow():
    """Test entire scraping workflow."""
    async with get_async_session() as db:
        # 1. Create company
        company = await CompanyRepository.create(
            db, name="Test Corp", created_by="user_123"
        )
        
        # 2. Check credits
        credit_account = await UserCreditRepository.get_or_create(
            db, "user_123"
        )
        await UserCreditRepository.add_credits(db, "user_123", 10.0)
        
        # 3. Create scraping job
        job = await ScrapingJobRepository.create(
            db,
            company_id=company.id,
            source_id="source_reddit",
            user_id="user_123",
            total_reviews_target=10,
            cost=0.1
        )
        
        # 4. Run scraping (with mocked Apify)
        # ... test scraping logic
        
        # 5. Verify results
        reviews = await ReviewRepository.list_company_reviews(
            db, company.id
        )
        assert len(reviews) > 0
        
        # 6. Check credits deducted
        updated_account = await UserCreditRepository.get_by_user_id(
            db, "user_123"
        )
        assert updated_account.credits_available < 10.0
```

### RAG Chat Flow

```python
# tests/integration/test_chat_with_rag.py
@pytest.mark.asyncio
@pytest.mark.integration
async def test_rag_chat_with_reviews():
    """Test RAG chat with actual reviews."""
    # Setup: Create company and reviews
    async with get_async_session() as db:
        company = await CompanyRepository.create(
            db, name="Test", created_by="user_123"
        )
        
        # Add test reviews
        for i in range(5):
            await ReviewRepository.create(
                db,
                company_id=company.id,
                source_id="source_test",
                content=f"Test review {i}",
                sentiment_score=0.5
            )
        
        await db.commit()
    
    # Test RAG chat
    rag_service = RAGChatService()
    await rag_service.initialize()
    
    request = ChatRequest(
        message="What do customers think?",
        session_id="test_session"
    )
    
    response = await rag_service.process_message(
        request,
        user_id="user_123",
        company_ids=[company.id]
    )
    
    # Verify response structure
    assert response.message is not None
    assert response.metadata is not None
    assert 'pipeline_steps' in response.metadata
    assert 'sources' in response.metadata
    assert len(response.metadata['sources']) > 0
```

## Running Tests

```bash
# Install test dependencies
uv pip install pytest pytest-asyncio pytest-cov

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test categories
pytest tests/unit/
pytest tests/integration/ -m integration
pytest tests/performance/

# Run specific test file
pytest tests/unit/test_scrapers.py -v

# Run tests with specific marker
pytest -m "not integration"  # Skip integration tests
```

## Test Configuration

```ini
# pytest.ini
[pytest]
asyncio_mode = auto
markers =
    integration: Integration tests (require database)
    unit: Unit tests (mocked dependencies)
    performance: Performance/load tests
    slow: Slow-running tests

testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

## Mock Data Fixtures

```python
# tests/conftest.py
import pytest
from app.database.session import get_async_session

@pytest.fixture
async def db_session():
    """Provide test database session."""
    async with get_async_session() as session:
        yield session
        await session.rollback()

@pytest.fixture
def sample_company():
    """Sample company data."""
    return {
        "name": "Test Company",
        "domain": "test.com",
        "industry": "Software"
    }

@pytest.fixture
def sample_reviews():
    """Sample review data."""
    return [
        {
            "content": "Great product!",
            "author": "user1",
            "sentiment_score": 0.8
        },
        {
            "content": "Needs improvement",
            "author": "user2",
            "sentiment_score": -0.3
        }
    ]
```

## CI/CD Integration

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install uv
          uv pip install -r requirements.txt
          uv pip install pytest pytest-asyncio pytest-cov
      
      - name: Run tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test
          REDIS_URL: redis://localhost:6379
        run: |
          pytest --cov=app --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Test Coverage Goals

- **Unit Tests**: >80% coverage
- **Integration Tests**: All critical paths
- **Performance Tests**: Key endpoints under load

## Next Steps

1. Implement unit tests for each scraper with mocked APIs
2. Add integration tests for complete workflows
3. Set up CI/CD pipeline with automated testing
4. Add performance benchmarks
5. Create test data generation utilities

## Notes

- Use `pytest.mark.asyncio` for async tests
- Mock external APIs (Apify, Stripe, Pinecone) in unit tests
- Use test database for integration tests
- Clean up test data after each test
- Use fixtures for common test data

