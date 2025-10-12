# Clerk User Synchronization

This document explains how Clerk users are automatically synchronized to the database.

## Overview

When a user authenticates with Clerk, they are automatically created or updated in the local PostgreSQL database. This provides:

- **Single Source of User Data**: All user records in one place for queries and relationships
- **User Tracking**: Track last login, usage statistics, preferences
- **Database Relationships**: Link users to chat sessions, companies, credits, etc.
- **Offline Queries**: Query user data without hitting Clerk API

## How It Works

### User ID Strategy

- **Clerk ID as Primary Key**: We use the Clerk user ID as the database primary key
- This ensures 1:1 mapping between Clerk users and database users
- No risk of duplicate users or ID conflicts

### Sync Behavior

On every successful authentication:
1. Verify JWT token with Clerk
2. Check if user exists in database (by Clerk ID)
3. **If new user**: Create record with Clerk data
4. **If existing user**: Update `last_login_at` and sync any changed fields (email, name, etc.)

### What Gets Synced

From Clerk to Database:
- `id` - Clerk user ID (primary key)
- `email` - User's email address
- `username` - Username (or derived from email)
- `full_name` - Full name from Clerk
- `last_login_at` - Updated on every auth
- `extra_metadata` - Clerk metadata including:
  - `clerk_id` - Original Clerk ID
  - `image_url` - Profile image URL
  - `clerk_metadata` - Public metadata from Clerk
  - `created_from_clerk` - Flag indicating Clerk-created user

## Usage

### Option 1: Database User Required (Recommended)

Use `require_current_db_user` when you need both Clerk auth AND database user:

```python
from app.core.security.clerk_auth import require_current_db_user
from app.database.models.user import User
from fastapi import APIRouter, Depends

router = APIRouter()

@router.get("/me")
async def get_current_user_info(
    user_data: tuple = Depends(require_current_db_user)
):
    """Get current user information."""
    clerk_user, db_user = user_data
    
    return {
        "clerk_id": clerk_user.id,
        "email": clerk_user.email,
        "full_name": clerk_user.full_name,
        "database_id": db_user.id,
        "last_login": db_user.last_login_at,
        "total_requests": db_user.total_requests
    }
```

### Option 2: Optional Database User

Use `get_current_db_user` for optional authentication:

```python
from app.core.security.clerk_auth import get_current_db_user
from typing import Optional

@router.get("/public-or-private")
async def flexible_endpoint(
    user_data: Optional[tuple] = Depends(get_current_db_user)
):
    """Endpoint that works with or without auth."""
    if user_data is None:
        return {"message": "Public content"}
    
    clerk_user, db_user = user_data
    return {
        "message": "Private content",
        "user": clerk_user.email
    }
```

### Option 3: Clerk Only (No Database Sync)

For backwards compatibility, use existing functions:

```python
from app.core.security.clerk_auth import get_current_user, ClerkUser
from typing import Optional

@router.get("/clerk-only")
async def clerk_only_endpoint(
    current_user: Optional[ClerkUser] = Depends(get_current_user)
):
    """Only verify with Clerk, don't sync to database."""
    if not current_user:
        return {"message": "Not authenticated"}
    
    return {"clerk_id": current_user.id}
```

## Working with Database Users

### Accessing Relationships

```python
@router.get("/my-companies")
async def get_user_companies(
    user_data: tuple = Depends(require_current_db_user),
    db: AsyncSession = Depends(get_db)
):
    """Get companies created by the user."""
    clerk_user, db_user = user_data
    
    # Access relationships
    companies = db_user.companies
    
    return {
        "count": len(companies),
        "companies": [
            {
                "id": c.id,
                "name": c.name,
                "created_at": c.created_at
            }
            for c in companies
        ]
    }
```

### Updating User Data

```python
from app.database.repositories.user import UserRepository

@router.patch("/me/preferences")
async def update_preferences(
    preferences: dict,
    user_data: tuple = Depends(require_current_db_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user preferences."""
    clerk_user, db_user = user_data
    
    # Update preferences
    updated_user = await UserRepository.update(
        db, 
        db_user.id, 
        preferences=preferences
    )
    
    await db.commit()
    
    return {
        "message": "Preferences updated",
        "preferences": updated_user.preferences
    }
```

### Tracking Usage

```python
@router.post("/api-call")
async def tracked_api_call(
    user_data: tuple = Depends(require_current_db_user),
    db: AsyncSession = Depends(get_db)
):
    """API call with automatic usage tracking."""
    clerk_user, db_user = user_data
    
    # Do something...
    tokens_used = 150
    
    # Track usage
    await UserRepository.increment_usage(
        db, 
        db_user.id, 
        requests=1,
        tokens=tokens_used
    )
    await db.commit()
    
    return {"status": "success"}
```

## Service Integration

### In Background Tasks

```python
from celery import shared_task
from app.database.session import get_db_session
from app.database.repositories.user import UserRepository

@shared_task
def process_user_data(user_id: str):
    """Background task that works with database user."""
    with get_db_session() as db:
        user = UserRepository.get_by_id(db, user_id)
        
        if user:
            # Process user data
            pass
```

### In Services

```python
class MyService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def do_something_for_user(self, user_id: str):
        """Service method that needs user data."""
        user = await UserRepository.get_by_id(self.db, user_id)
        
        if user:
            # Work with user
            user.total_requests += 1
            await self.db.flush()
```

## Migration Guide

### Updating Existing Endpoints

**Before** (Clerk only):
```python
@router.get("/data")
async def get_data(
    current_user: ClerkUser = Depends(require_current_user)
):
    return {"user_id": current_user.id}
```

**After** (With database sync):
```python
@router.get("/data")
async def get_data(
    user_data: tuple = Depends(require_current_db_user)
):
    clerk_user, db_user = user_data
    
    return {
        "user_id": clerk_user.id,
        "last_login": db_user.last_login_at
    }
```

## Database Schema

The `users` table stores:

```sql
CREATE TABLE users (
    id VARCHAR PRIMARY KEY,              -- Clerk user ID
    email VARCHAR(255) UNIQUE,
    username VARCHAR(100) UNIQUE,
    full_name VARCHAR(255),
    status VARCHAR,                      -- active, inactive, suspended
    last_login_at TIMESTAMP,             -- Updated on every auth
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    extra_metadata JSONB,                -- Clerk data
    preferences JSONB,                   -- User preferences
    total_requests INTEGER DEFAULT 0,    -- Usage tracking
    total_tokens_used INTEGER DEFAULT 0
);
```

## Error Handling

### Graceful Degradation

The sync process is designed to not break authentication:

```python
# In get_current_db_user (optional auth)
try:
    db_user = await UserSyncService.sync_clerk_user(db, clerk_user)
except Exception as e:
    logger.error(f"DB sync failed: {e}")
    # Still returns Clerk user, db_user will be None
```

### Required Sync

When using `require_current_db_user`, database sync failures will return 500:

```python
# In require_current_db_user
try:
    db_user = await UserSyncService.sync_clerk_user(db, clerk_user)
except Exception as e:
    logger.error(f"DB sync failed: {e}")
    raise HTTPException(status_code=500, detail="Failed to sync user")
```

## Testing

### Testing with Database Sync

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_authenticated_endpoint(client: AsyncClient, db_session, clerk_token):
    """Test endpoint with user sync."""
    headers = {"Authorization": f"Bearer {clerk_token}"}
    
    response = await client.get("/api/v1/me", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "email" in data
    assert "database_id" in data
```

### Mocking User Sync

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_with_mocked_sync():
    """Test with mocked database sync."""
    with patch("app.services.user_sync_service.UserSyncService.sync_clerk_user") as mock_sync:
        mock_sync.return_value = AsyncMock(
            id="user_123",
            email="test@example.com"
        )
        
        # Test your endpoint
        pass
```

## Performance Considerations

### Database Queries

Each authenticated request performs:
1. JWT verification (Clerk API or cached keys)
2. Database query (SELECT by user ID)
3. Potential INSERT or UPDATE (first login or changed data)

**Optimization**: The sync is lightweight - most requests only update `last_login_at`.

### Caching

Consider caching user lookups for high-traffic endpoints:

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_cached_user(user_id: str):
    # Cache user data for a short time
    pass
```

## Troubleshooting

### User Not Syncing

Check logs for sync errors:
```bash
grep "Failed to sync user" backend/logs/app.log
```

### Duplicate Users

Won't happen - Clerk ID is used as primary key.

### Database Connection Issues

If database is down, `get_current_db_user` returns (ClerkUser, None).
`require_current_db_user` will return 500 error.

## Summary

✅ **Automatic**: Users sync on every auth  
✅ **Seamless**: No code changes needed in most cases  
✅ **Reliable**: Clerk ID as primary key prevents duplicates  
✅ **Flexible**: Use sync or non-sync auth as needed  
✅ **Tracked**: Last login and usage automatically updated  

Use `require_current_db_user` for new endpoints that need database access.
Use `get_current_user` for backward compatibility or when database is not needed.

