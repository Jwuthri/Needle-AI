# SQL Error Handling & Step Status Implementation

## Overview
This implementation improves error handling for SQL queries in the LLM workflow and adds visual status indicators for execution steps in the frontend.

## Changes Made

### 1. Backend - Error Handling

#### Tool Error Handling (`backend/app/core/llm/simple_workflow/tools/user_dataset_tool.py`)
- **Changed**: `get_dataset_data_from_sql` now returns error messages to the LLM instead of raising exceptions
- **Benefit**: Allows the LLM to see SQL errors and generate corrected queries
- **Example**: When a column doesn't exist, the LLM receives:
  ```
  ERROR executing SQL query:
  column "company_name" does not exist
  
  Please analyze the error and generate a corrected SQL query.
  ```

### 2. Backend - Step Status Tracking

#### Database Model (`backend/app/database/models/chat_message_step.py`)
- **Added**: `StepStatusEnum` with values: `SUCCESS`, `ERROR`, `PENDING`
- **Added**: `status` column to `ChatMessageStep` model
- **Migration**: Created migration `014_add_status_to_chat_message_steps.py`

#### Repository (`backend/app/database/repositories/chat_message_step.py`)
- **Added**: `update_status()` method to update step status
- **Modified**: `bulk_create()` to accept status parameter

#### Workflow Service (`backend/app/services/simple_workflow_service.py`)
- **Added**: Error detection in tool results
- **Logic**: Checks if tool output starts with "ERROR" or contains "error" in first 100 chars
- **Action**: Updates step status to ERROR in database when detected
- **Streaming**: Includes `is_error` flag in tool_result events

### 3. Frontend - Status Display

#### Type Definitions (`frontend/src/types/chat.ts`)
- **Modified**: `AgentStep` interface to include `'error'` status option
- **Before**: `status?: 'active' | 'completed'`
- **After**: `status?: 'active' | 'completed' | 'error'`

#### Chat View (`frontend/src/components/chat/experimental-chat-view.tsx`)
- **Added**: Visual status indicators for completed steps
  - ✓ Green badge for successful steps
  - ✕ Red badge for error steps
- **Added**: Red border for error step cards
- **Added**: Status badges in step headers

#### Streaming Hook (`frontend/src/hooks/use-experimental-chat-stream.ts`)
- **Modified**: `tool_result` handler to process `is_error` flag
- **Logic**: Updates last step's status based on error detection
- **Benefit**: Real-time error indication during streaming

## Visual Changes

### Completed Steps (Collapsed View)
```
┌─────────────────────────────────────┐
│ 🔢 Workflow Execution Steps         │
│ [Success] [Error] status badges     │
└─────────────────────────────────────┘
```

### Expanded Steps
```
┌─────────────────────────────────────┐
│ Step 1: data_discovery_agent        │
│                      [Success ✓]    │
│ Tool: get_dataset_data_from_sql     │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ Step 2: data_discovery_agent        │
│                      [Error ✕]      │
│ ERROR: column "company_name" ...    │
└─────────────────────────────────────┘
```

### Streaming Steps
- Active: Spinning loader icon
- Success: Green checkmark (✓)
- Error: Red X (✕) with error badge

## Database Migration

Run the migration to add the status column:
```bash
cd backend
alembic upgrade head
```

## Testing

1. **Test SQL Error Handling**:
   - Send a query that references a non-existent column
   - Verify the LLM receives the error message
   - Verify the LLM attempts to correct the query

2. **Test Status Display**:
   - Open the experimental chat view
   - Send a message that triggers SQL queries
   - Expand the workflow steps
   - Verify success/error badges appear correctly

3. **Test Real-time Updates**:
   - Watch steps during streaming
   - Verify status updates from active → success/error
   - Verify visual indicators change accordingly

## Benefits

1. **Self-Healing Queries**: LLM can see and fix SQL errors automatically
2. **Better Debugging**: Visual indicators make it easy to spot failed steps
3. **User Transparency**: Users can see exactly which steps succeeded/failed
4. **Improved UX**: Clear visual feedback during long-running workflows

## Future Enhancements

1. Add retry logic for failed steps
2. Show detailed error messages in tooltips
3. Add filtering to show only error steps
4. Export error logs for debugging
5. Add error rate metrics to dashboard

