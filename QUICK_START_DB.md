# Quick Start: Database Setup

## TL;DR

```bash
# Setup database and run migrations
cd backend
./scripts/setup-db.sh
```

## What Was Fixed

✅ Changed `metadata` → `extra_metadata` in all database tables to avoid SQLAlchemy conflicts
✅ Updated 3 migration scripts (001, 002, 003)
✅ Created database setup scripts
✅ All 8 affected tables now use `extra_metadata`

## Database Commands

### Shell Script (Easy)
```bash
cd backend

# Setup everything
./scripts/setup-db.sh
```

### Python Script (More Control)
```bash
cd backend

# Full setup
python scripts/db_manager.py setup

# Or step by step
python scripts/db_manager.py create    # Create DB
python scripts/db_manager.py migrate   # Run migrations
python scripts/db_manager.py status    # Check status

# Reset (drop + create + migrate)
python scripts/db_manager.py reset
```

## Tables with `extra_metadata` Column

1. `users` - User account metadata
2. `chat_sessions` - Session configuration
3. `chat_messages` - Message context
4. `api_keys` - API key info
5. `task_results` - Background task data
6. `reviews` - Review platform data (upvotes, etc.)
7. `llm_calls` - LLM debugging info

## Migration Order

```
001_initial_migration.py (users, sessions, messages, etc.)
  ↓
002_product_review_platform.py (companies, reviews, credits)
  ↓
003_add_llm_call_logging.py (llm_calls table)
```

## Troubleshooting

**"Database already exists"**
→ This is fine! Script will skip creation and run migrations.

**"Cannot connect to PostgreSQL"**
→ Start PostgreSQL: `docker-compose up -d db`

**"Alembic not found"**
→ Install: `pip install alembic psycopg2-binary`

**Need to start fresh?**
```bash
python scripts/db_manager.py reset
```

## Documentation

- Full guide: `backend/scripts/DATABASE_SCRIPTS.md`
- Fix summary: `METADATA_FIX_SUMMARY.md`

