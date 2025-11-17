# Raw Output Column Addition

## Overview
Added a new `raw_output` column to the `chat_message_steps` table to store the raw unprocessed output from agents, separate from the `structured_output` field.

## Changes Made

### 1. Database Migration (`017_add_raw_output_to_chat_message_steps.py`)
- **File**: `backend/alembic/versions/017_add_raw_output_to_chat_message_steps.py`
- **Action**: Added new `raw_output` TEXT column to `chat_message_steps` table
- **Nullable**: Yes (existing records will have NULL)
- **Type**: TEXT (for storing large unprocessed output strings)

### 2. Database Model (`chat_message_step.py`)
- **File**: `backend/app/database/models/chat_message_step.py`
- **Change**: Added `raw_output = Column(Text, nullable=True)` field
- **Purpose**: Store raw unprocessed output from agents before any parsing or structuring

### 3. Repository Layer (`chat_message_step.py`)
- **File**: `backend/app/database/repositories/chat_message_step.py`
- **Changes**:
  - Updated `create()` method to accept `raw_output` parameter
  - Updated `update_with_result()` method to accept and update `raw_output`
  - Updated `bulk_create()` method to handle `raw_output` in step data

### 4. Service Layer (`simple_workflow_service.py`)
- **File**: `backend/app/services/simple_workflow_service.py`
- **Changes**:
  - Store raw output string: `raw_output = output_str`
  - Pass `raw_output` to `ChatMessageStepRepository.update_with_result()`
  - Store full raw output in agent_steps: `agent_steps[-1]["raw_output"] = raw_output`

### 5. Frontend Types (`chat.ts`)
- **File**: `frontend/src/types/chat.ts`
- **Change**: Added `raw_output?: string` to `AgentStep` interface
- **Purpose**: Type support for displaying raw output in frontend

## Data Storage Strategy

### Before (Current Behavior)
```python
# Everything was stored in structured_output or prediction
structured_output = tool_output.model_dump()  # Parsed/structured
prediction = str(tool_output)  # Text output
```

### After (New Behavior)
```python
# Raw output stored separately
raw_output = str(tool_output)  # Full raw unprocessed output
structured_output = tool_output.model_dump()  # Parsed/structured (if applicable)
prediction = str(tool_output)  # Text output (if not structured)
```

## Use Cases

1. **Debugging**: View the exact raw output from agents before any processing
2. **Audit Trail**: Complete record of what agents actually returned
3. **Error Analysis**: Understand failures by seeing raw error messages
4. **Data Recovery**: Reprocess raw output if parsing logic changes

## Database Schema

```sql
ALTER TABLE chat_message_steps 
ADD COLUMN raw_output TEXT NULL;
```

### Table Structure
```
chat_message_steps
├── id (String, PK)
├── message_id (String, FK)
├── agent_name (String)
├── step_order (Integer)
├── status (String)
├── tool_call (JSON)
├── structured_output (JSON)  -- Parsed/structured data
├── prediction (Text)          -- Text output
├── raw_output (Text)          -- NEW: Raw unprocessed output
└── created_at (DateTime)
```

## Migration Instructions

### Apply Migration
```bash
cd backend
alembic upgrade head
```

### Rollback (if needed)
```bash
alembic downgrade -1
```

## API Changes

### No Breaking Changes
- All new fields are optional
- Existing code continues to work
- New `raw_output` field is populated automatically for new steps
- Existing steps will have `NULL` for `raw_output`

## Example Usage

### Backend - Creating a Step with Raw Output
```python
step = await ChatMessageStepRepository.create(
    db=db,
    message_id="msg_123",
    agent_name="gap_analysis",
    step_order=1,
    structured_output={"gaps": [...]},
    raw_output="Raw output: Found 3 gaps in the data..."  # NEW
)
```

### Backend - Updating with Raw Output
```python
await ChatMessageStepRepository.update_with_result(
    db=db,
    step_id="step_123",
    status="success",
    structured_output={"result": "..."},
    prediction="Analysis complete",
    raw_output="Full raw agent output here..."  # NEW
)
```

### Frontend - Accessing Raw Output
```typescript
interface AgentStep {
  step_id: string;
  agent_name: string;
  content: any;
  raw_output?: string;  // NEW: Access raw output
  // ... other fields
}

// Display raw output in debug view
{step.raw_output && (
  <pre className="text-xs">
    {step.raw_output}
  </pre>
)}
```

## Testing

### Verify Migration
```bash
# Check column exists
psql -d needleai -c "\d chat_message_steps"

# Should show raw_output column
```

### Test Data Flow
1. Send a chat message through the workflow
2. Check database: `SELECT raw_output FROM chat_message_steps WHERE message_id = 'xxx'`
3. Verify raw_output is populated with full agent output

## Benefits

1. **Complete Data Capture**: Never lose the original output
2. **Debugging**: Easier to debug issues with raw data
3. **Flexibility**: Can reprocess data without re-running agents
4. **Audit Trail**: Full record of agent behavior
5. **No Breaking Changes**: Backward compatible with existing code

