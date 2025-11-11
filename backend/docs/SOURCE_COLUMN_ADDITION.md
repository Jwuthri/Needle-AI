# Source Column Addition - Migration 011

## What Changed

Added a simple `source` column to store the review source platform directly as a string.

## The Problem

**Before:** Had to use complex foreign key relationship
```python
source_id = Column(String, ForeignKey("review_sources.id"), nullable=False)  # Required!

# Requires separate review_sources table with:
# - id, name, source_type (enum), config, cost_per_review, is_active, etc.
```

**Mock data is simple:**
```python
{"source": "app_store", "date": "2025-10-15", "author": "user123"}
{"source": "reddit"}
{"source": "trustpilot"}
```

## The Solution

**Now:** Simple string column + optional foreign key
```python
source = Column(String(100), nullable=True)  # Simple! "app_store", "reddit", etc.
source_id = Column(String, ForeignKey(...), nullable=True)  # Optional for complex tracking
```

### Benefits:
1. ✅ **Simpler** - Just store the platform name
2. ✅ **Flexible** - No need for pre-defined sources
3. ✅ **Optional FK** - Use `source_id` only if you need complex source tracking
4. ✅ **Direct from data** - Maps directly to mock data structure

## What Gets Stored Now

```python
review = Review(
    content="Great product!",
    source="app_store",  # ← Simple string from mock data
    source_id=None,  # Optional - only if using review_sources table
    author="user123",
    review_date=datetime(2025, 10, 15)  # ← Also added: actual review date
)
```

## Mock Data Mapping

```python
# Mock data
{
    "text": "Great product!",
    "source": "app_store",
    "date": "2025-10-15",
    "author": "user123",
    "rating": 5
}

# Becomes
Review(
    content="Great product!",          # text → content
    source="app_store",                 # source → source (new!)
    author="user123",                   # author → author
    review_date=datetime(2025, 10, 15), # date → review_date (now used!)
    sentiment_score=1.0,                # rating (5) → sentiment (+1.0)
    extra_metadata={                    # Original data preserved
        "rating": 5,
        "category": "review"
    }
)
```

## Query Examples

### Filter by source
```python
# Simple filtering
app_store_reviews = await db.execute(
    select(Review).filter(Review.source == "app_store")
)

reddit_reviews = await db.execute(
    select(Review).filter(Review.source == "reddit")
)
```

### Filter by date range
```python
# Reviews from last month
from datetime import datetime, timedelta

last_month = datetime.now() - timedelta(days=30)
recent_reviews = await db.execute(
    select(Review)
    .filter(Review.review_date >= last_month)
    .order_by(Review.review_date.desc())
)
```

### Aggregate by source
```python
# Count reviews per source
from sqlalchemy import func

source_counts = await db.execute(
    select(Review.source, func.count(Review.id))
    .group_by(Review.source)
)
```

## When to Use `source_id`?

Use the optional `source_id` foreign key if you need:
- Complex source configuration
- Cost tracking per source
- Source-specific scraping rules
- Historical source management

Most cases: just use the simple `source` column! 🎯

## Migration Applied

```bash
alembic upgrade head  # Applied migration 011
```

**Database changes:**
- ✅ Added `source` column (VARCHAR(100))
- ✅ Made `source_id` nullable (was required)
- ✅ Added index on `source` for performance

