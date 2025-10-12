# Clerk User Database Sync Implementation

## Summary

Implemented automatic synchronization of Clerk users to the PostgreSQL database. When users authenticate with Clerk, they are automatically created or updated in the local database.

## What Was Added

### 1. User Sync Service
**File**: `backend/app/services/user_sync_service.py`

A service that handles synchronization between Clerk and the database:
- **Creates** new users on first login
- **Updates** existing users (email, name, username, last_login_at)
- **Syncs metadata** from Clerk to `extra_metadata` field
- Uses Clerk ID as the primary key

### 2. New Authentication Functions
**File**: `backend/app/core/security/clerk_auth.py`

Added two new authentication dependency functions:

#### `get_current_db_user()`
- Optional authentication with database sync
- Returns `(ClerkUser, User)` tuple or `None`
- Gracefully handles DB sync failures
- Use for optional auth endpoints

#### `require_current_db_user()`
- Required authentication with database sync
- Returns `(ClerkUser, User)` tuple
- Raises HTTPException if auth or sync fails
- Use for protected endpoints that need user data

### 3. Database Helper
**File**: `backend/app/core/security/clerk_auth.py`

Added `_get_db_session()` helper for dependency injection.

### 4. Documentation
**File**: `backend/docs/CLERK_USER_SYNC.md`

Comprehensive guide covering:
- How the sync works
- Usage examples for different scenarios
- Database schema details
- Migration guide
- Testing approaches
- Troubleshooting

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                     User Authentication Flow                 │
└─────────────────────────────────────────────────────────────┘

1. User sends request with JWT token
   ↓
2. Verify JWT with Clerk (clerk_auth.py)
   ↓
3. Extract ClerkUser from token
   ↓
4. Check if user exists in database
   ├─ Exists: Update last_login_at + sync changed fields
   └─ New: Create user record with Clerk ID
   ↓
5. Return (ClerkUser, DatabaseUser) to endpoint
```

## Key Design Decisions

### 1. Clerk ID as Primary Key
```python
id = Column(String, primary_key=True)  # Uses Clerk user ID
```
**Why**: Ensures 1:1 mapping, prevents duplicates, simplifies lookups.

### 2. Non-Breaking Changes
- Kept existing `get_current_user()` and `require_current_user()`
- Added NEW functions for database sync
- Existing endpoints work without changes

### 3. Graceful Degradation
```python
# Optional auth - DB sync failure doesn't break auth
try:
    db_user = await sync_user(...)
except Exception:
    db_user = None  # Still return Clerk user
return (clerk_user, db_user)
```

### 4. Automatic Sync on Every Auth
- Updates `last_login_at` on every request
- Syncs any changed Clerk data (email, name, etc.)
- Minimal performance impact

## Usage Examples

### Basic Protected Endpoint

```python
from app.core.security.clerk_auth import require_current_db_user

@router.get("/me")
async def get_current_user(
    user_data: tuple = Depends(require_current_db_user)
):
    clerk_user, db_user = user_data
    
    return {
        "email": clerk_user.email,
        "last_login": db_user.last_login_at,
        "total_requests": db_user.total_requests
    }
```

### Optional Authentication

```python
from app.core.security.clerk_auth import get_current_db_user

@router.get("/content")
async def get_content(
    user_data: tuple | None = Depends(get_current_db_user)
):
    if user_data:
        clerk_user, db_user = user_data
        return {"message": f"Hello {clerk_user.email}"}
    return {"message": "Hello guest"}
```

### Using Database Relationships

```python
@router.get("/my-companies")
async def get_companies(
    user_data: tuple = Depends(require_current_db_user)
):
    clerk_user, db_user = user_data
    
    # Access user's companies via relationship
    return {
        "companies": [
            {"id": c.id, "name": c.name}
            for c in db_user.companies
        ]
    }
```

## Database Schema

The `users` table stores:

| Column | Type | Description |
|--------|------|-------------|
| `id` | String | Clerk user ID (primary key) |
| `email` | String | User's email |
| `username` | String | Username |
| `full_name` | String | Full name |
| `status` | Enum | active/inactive/suspended |
| `last_login_at` | DateTime | Updated on every auth |
| `extra_metadata` | JSON | Clerk metadata |
| `preferences` | JSON | User preferences |
| `total_requests` | Integer | Usage tracking |
| `total_tokens_used` | Integer | Usage tracking |

## Migration Path

### For New Endpoints
```python
# Use the new functions
user_data: tuple = Depends(require_current_db_user)
```

### For Existing Endpoints
No changes needed! Existing code continues to work:
```python
# This still works
current_user: ClerkUser = Depends(get_current_user)
```

### When to Update
Update to database sync when you need:
- User relationships (companies, sessions, etc.)
- Usage tracking
- User preferences
- Last login tracking
- Any database queries involving users

## Files Modified

1. ✅ `backend/app/services/user_sync_service.py` - New service
2. ✅ `backend/app/core/security/clerk_auth.py` - Added sync functions
3. ✅ `backend/app/database/models/user.py` - Comment about Clerk IDs
4. ✅ `backend/docs/CLERK_USER_SYNC.md` - Documentation

## Testing

### Run Tests
```bash
cd backend
pytest tests/unit/test_auth.py -v
```

### Manual Testing
```bash
# 1. Start backend
./scripts/start.sh

# 2. Test authentication
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_CLERK_TOKEN"

# 3. Check database
psql -d needleai -c "SELECT id, email, last_login_at FROM users;"
```

## Benefits

✅ **Single Source of Truth**: User data in one database  
✅ **Relationship Support**: Link users to other entities  
✅ **Usage Tracking**: Automatic request/token counting  
✅ **Last Login Tracking**: Always up to date  
✅ **Offline Queries**: No need to hit Clerk API  
✅ **Backwards Compatible**: Existing code works unchanged  
✅ **Graceful Degradation**: DB failures don't break auth  

## Next Steps

To use in your endpoints:

1. **Import the function**:
   ```python
   from app.core.security.clerk_auth import require_current_db_user
   ```

2. **Add dependency**:
   ```python
   user_data: tuple = Depends(require_current_db_user)
   ```

3. **Unpack the tuple**:
   ```python
   clerk_user, db_user = user_data
   ```

4. **Use the database user**:
   ```python
   companies = db_user.companies
   last_login = db_user.last_login_at
   ```

## References

- Full documentation: `backend/docs/CLERK_USER_SYNC.md`
- User model: `backend/app/database/models/user.py`
- User repository: `backend/app/database/repositories/user.py`
- Sync service: `backend/app/services/user_sync_service.py`

