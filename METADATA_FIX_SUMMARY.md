# Database Schema Metadata Fix Summary

## Issue Fixed

The database models and migration scripts had a naming conflict where the column name `metadata` was used instead of `extra_metadata`. This caused conflicts with SQLAlchemy's internal `metadata` attribute.

## Changes Made

### 1. Migration Scripts Updated

#### `001_initial_migration.py`
Updated 6 tables to use `extra_metadata` instead of `metadata`:
- ✅ `users` table (line 32)
- ✅ `chat_sessions` table (line 54)
- ✅ `chat_messages` table (line 71)
- ✅ `completions` table (line 100)
- ✅ `api_keys` table (line 124)
- ✅ `task_results` table (line 146)

#### `002_product_review_platform.py`
- ✅ `reviews` table (line 153)

#### `003_add_llm_call_logging.py`
- ✅ `llm_calls` table (line 55)

### 2. Model Files (Already Correct)

All model files already used `extra_metadata`:
- ✅ `app/database/models/user.py`
- ✅ `app/database/models/chat_session.py`
- ✅ `app/database/models/chat_message.py`
- ✅ `app/database/models/api_key.py`
- ✅ `app/database/models/task_result.py`
- ✅ `app/database/models/review.py`
- ✅ `app/database/models/llm_call.py`

### 3. Database Management Scripts Created

#### Shell Script: `scripts/setup-db.sh`
A comprehensive bash script for database setup and migrations:
```bash
./scripts/setup-db.sh
```

Features:
- Validates PostgreSQL connection
- Creates database if it doesn't exist
- Runs Alembic migrations
- Provides troubleshooting tips
- Color-coded output

#### Python Script: `scripts/db_manager.py`
A Python-based database manager with programmatic API:
```bash
# Full setup
python scripts/db_manager.py setup

# Individual operations
python scripts/db_manager.py create
python scripts/db_manager.py migrate
python scripts/db_manager.py status
python scripts/db_manager.py drop
python scripts/db_manager.py reset
```

Features:
- Full database lifecycle management
- Can be imported as a Python module
- Supports custom DATABASE_URL
- Migration history and status checking
- Confirmation prompts for destructive operations

#### Documentation: `scripts/DATABASE_SCRIPTS.md`
Complete guide for using the database management scripts with:
- Quick start instructions
- Usage examples
- Troubleshooting guide
- Best practices
- CI/CD integration examples

## Migration Strategy

### For New Installations
Simply run:
```bash
./scripts/setup-db.sh
```
or
```bash
python scripts/db_manager.py setup
```

### For Existing Databases

If you have an existing database with the old `metadata` column names, you need to either:

1. **Start fresh** (recommended for development):
   ```bash
   python scripts/db_manager.py reset
   ```

2. **Manual migration** (if you have important data):
   ```sql
   -- For each affected table
   ALTER TABLE users RENAME COLUMN metadata TO extra_metadata;
   ALTER TABLE chat_sessions RENAME COLUMN metadata TO extra_metadata;
   ALTER TABLE chat_messages RENAME COLUMN metadata TO extra_metadata;
   ALTER TABLE api_keys RENAME COLUMN metadata TO extra_metadata;
   ALTER TABLE task_results RENAME COLUMN metadata TO extra_metadata;
   ALTER TABLE reviews RENAME COLUMN metadata TO extra_metadata;
   ALTER TABLE llm_calls RENAME COLUMN metadata TO extra_metadata;
   ```

## Verification

To verify the schema is correct:

```bash
# Check current migration status
python scripts/db_manager.py status

# Or using alembic directly
cd backend
alembic current

# Inspect database schema
psql -d needleai -c "\d users"
psql -d needleai -c "\d reviews"
psql -d needleai -c "\d llm_calls"
```

## Why This Fix Was Needed

In SQLAlchemy, `metadata` is a reserved attribute used internally by the declarative base to manage the database schema. Using `metadata` as a column name can cause:
- Naming conflicts with SQLAlchemy internals
- Confusion between the column and the schema metadata
- Potential runtime errors in complex queries

Using `extra_metadata` clearly indicates this is application-level metadata, not SQLAlchemy's schema metadata.

## Related Files

- Migration scripts: `backend/alembic/versions/*.py`
- Model files: `backend/app/database/models/*.py`
- Database scripts: `backend/scripts/setup-db.sh` and `backend/scripts/db_manager.py`
- Documentation: `backend/scripts/DATABASE_SCRIPTS.md`

## Testing

After applying these changes:

1. **Test database creation**:
   ```bash
   python scripts/db_manager.py drop --force
   python scripts/db_manager.py create
   ```

2. **Test migrations**:
   ```bash
   python scripts/db_manager.py migrate
   ```

3. **Verify schema**:
   ```bash
   python scripts/db_manager.py status
   ```

4. **Run application tests**:
   ```bash
   cd backend
   pytest
   ```

## Status

✅ All migration scripts updated
✅ All model files verified
✅ Database management scripts created
✅ Documentation completed
✅ Ready for deployment

