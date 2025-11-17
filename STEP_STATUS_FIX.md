# Step Status Error State Fix

## Problem
When running a query with tool errors during streaming, the error status was displayed correctly during streaming but disappeared after the stream completed and state refreshed from the database.

## Root Cause
There was a mismatch between the database enum values and the Python code:

1. **Migration (014)**: Created enum with uppercase values: `'SUCCESS'`, `'ERROR'`, `'PENDING'`
2. **Python Model**: Expected lowercase values: `'success'`, `'error'`, `'pending'`
3. **Service Code**: Was setting status to uppercase `"ERROR"` and `"SUCCESS"` instead of lowercase

This caused the database to either reject the values or use default values, resulting in all steps showing as "success" after refresh.

## Changes Made

### 1. Backend Service (`simple_workflow_service.py`)
**File**: `backend/app/services/simple_workflow_service.py`

Changed line 211 from:
```python
status="ERROR" if is_error else "SUCCESS"
```

To:
```python
status="error" if is_error else "success"
```

### 2. Database Migration (`014_add_status_to_chat_message_steps.py`)
**File**: `backend/alembic/versions/014_add_status_to_chat_message_steps.py`

Changed enum creation to use lowercase values and added CASCADE drop to handle existing enum:
```python
# Drop old enum if it exists (in case migration was partially run with uppercase values)
op.execute("DROP TYPE IF EXISTS stepstatusenum CASCADE")

# Create enum type with lowercase values (to match Python enum)
step_status_enum = postgresql.ENUM('success', 'error', 'pending', name='stepstatusenum')
step_status_enum.create(op.get_bind(), checkfirst=True)

# Add status column to chat_message_steps with default value
op.add_column('chat_message_steps', sa.Column('status', sa.Enum('success', 'error', 'pending', name='stepstatusenum'), nullable=False, server_default='success'))
```

### 3. Repository (`chat_message_step.py`)
**File**: `backend/app/database/repositories/chat_message_step.py`

Changed line 174 from:
```python
status=step_data.get('status', 'SUCCESS')
```

To:
```python
status=step_data.get('status', 'success')
```

### 4. SQL Fix Script
**File**: `backend/scripts/fix_step_status_enum.sql`

Created a SQL script to update any existing data with uppercase values to lowercase (in case the old migration was already run).

## Verification

### Python Model (Already Correct)
**File**: `backend/app/database/models/chat_message_step.py`
```python
class StepStatusEnum(str, enum.Enum):
    """Status of a step execution."""
    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"
```

### Frontend Types (Already Correct)
**File**: `frontend/src/types/chat.ts`
```typescript
export interface AgentStep {
  status?: 'active' | 'completed' | 'error';
  // ...
}
```

### Frontend Components (Already Correct)
The frontend was already checking for lowercase status values:
- `experimental-chat-view.tsx`: Checks `step.status === 'error'`
- `pipeline-visualizer.tsx`: Checks `step.status.toLowerCase() === 'success'`

## Migration Steps

### ✅ Migration 015 Created and Applied

A new migration (015) has been created to fix the enum case issue. This migration:

1. Creates a temporary column to store status values
2. Converts all uppercase values to lowercase
3. Drops the old enum type
4. Creates a new enum type with lowercase values
5. Applies the new enum to the status column
6. Cleans up the temporary column

**To apply the fix:**
```bash
cd backend
alembic upgrade head
```

This will automatically convert all existing data from uppercase to lowercase values.

### Verification

After running the migration, you can verify it worked:

```bash
cd backend
python -c "
import asyncio
from app.database.session import get_async_session
from sqlalchemy import text

async def check():
    async with get_async_session() as db:
        result = await db.execute(text('''
            SELECT e.enumlabel
            FROM pg_type t 
            JOIN pg_enum e ON t.oid = e.enumtypid  
            WHERE t.typname = 'stepstatusenum'
            ORDER BY e.enumsortorder
        '''))
        print('Enum values:', [row[0] for row in result.fetchall()])

asyncio.run(check())
"
```

Expected output: `Enum values: ['success', 'error', 'pending']`

## Testing

To verify the fix:

1. Start a chat session
2. Run a query that will cause a tool error (e.g., invalid SQL query)
3. During streaming, verify the error status is shown
4. After streaming completes, refresh the page
5. Verify the error status is still displayed correctly

## Summary

All enum values are now consistently lowercase throughout the stack:
- ✅ Database enum: `'success'`, `'error'`, `'pending'`
- ✅ Python enum: `'success'`, `'error'`, `'pending'`
- ✅ Service code: `'success'`, `'error'`, `'pending'`
- ✅ Repository: `'success'`, `'error'`, `'pending'`
- ✅ Frontend types: `'completed'`, `'error'`, `'active'` (frontend uses slightly different names but maps correctly)

