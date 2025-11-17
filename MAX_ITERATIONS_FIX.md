# Max Iterations & Missing Content Fix

## Issues Fixed

### 1. Max Iterations Error (20 iterations reached)
**Problem**: Workflow was hitting the 20 iteration limit when SQL queries had errors, causing the LLM to retry multiple times.

**Solutions Implemented**:

#### A. Increased Max Iterations
- Changed from default 20 to 50 iterations
- Location: `backend/app/services/simple_workflow_service.py`
- Allows more retries for complex workflows with SQL error recovery

```python
handler = workflow.run(
    user_msg=request.message,
    initial_state={"user_id": user_id or "default_user"},
    ctx=ctx,
    max_iterations=50  # Increased from default 20
)
```

#### B. SQL Error Retry Limit
- Added counter to prevent infinite SQL error loops
- Location: `backend/app/core/llm/simple_workflow/tools/user_dataset_tool.py`
- Stops after 5 failed SQL attempts with helpful message

**Logic**:
1. Track `sql_error_count` in workflow context
2. Increment on each SQL error
3. Reset to 0 on successful query
4. Stop at 5 errors with message to check schema first

```python
if sql_error_count >= 5:
    return "ERROR: Too many SQL query errors (5). Please check the dataset schema using get_user_datasets tool first."
```

### 2. Missing Content After Page Reload
**Problem**: Streaming content was generated but not visible after page reload - only workflow steps showed up.

**Root Cause**: When workflow hit max iterations error, the accumulated content wasn't being saved to the database.

**Solutions Implemented**:

#### A. Enhanced Error Handling
- Save accumulated content even when workflow errors occur
- Location: `backend/app/services/simple_workflow_service.py`

```python
except Exception as e:
    # Try to save whatever content we have accumulated before the error
    if accumulated_content:
        logger.info(f"Attempting to save accumulated content despite error")
        # Save to database...
```

#### B. Better Logging
- Added detailed logging for content saving
- Track character count of saved content
- Log success/failure of database operations

```python
logger.info(f"Saving final content to database: {len(final_content)} chars")
# ... save operation ...
logger.info(f"Successfully saved assistant message {assistant_message_id}")
```

## Testing

### Test Max Iterations Fix
1. Send a query with intentional SQL errors
2. Verify it stops after 5 SQL attempts
3. Verify workflow doesn't hit 50 iteration limit
4. Check error message suggests using get_user_datasets

### Test Content Saving
1. Send a message that generates streaming content
2. Let it complete (even if it errors)
3. Reload the page
4. Verify the assistant's response is visible
5. Check database logs confirm content was saved

### Test Error Recovery
1. Send SQL query with wrong column name
2. Verify LLM receives error and retries
3. Verify content is saved even if max retries reached
4. Verify error/success badges show correctly

## Benefits

1. **No More Lost Content**: All generated content is saved, even on errors
2. **Prevents Infinite Loops**: SQL error limit stops runaway retries
3. **Better User Experience**: Users see responses even when workflow errors occur
4. **Improved Debugging**: Enhanced logging helps track issues
5. **Graceful Degradation**: System saves partial results on failure

## Configuration

### Adjustable Parameters

**Max Iterations** (`simple_workflow_service.py`):
```python
max_iterations=50  # Increase if needed for complex workflows
```

**SQL Error Limit** (`user_dataset_tool.py`):
```python
if sql_error_count >= 5:  # Adjust threshold as needed
```

## Monitoring

Watch for these log messages:

**Success**:
```
Saving final content to database: 3979 chars
Successfully saved assistant message <id>
```

**Partial Save on Error**:
```
Attempting to save accumulated content despite error: 3979 chars
Successfully saved partial content for message <id>
```

**SQL Error Limit**:
```
ERROR executing SQL query (attempt 5/5): ...
ERROR: Too many SQL query errors (5). Please check the dataset schema...
```

## Future Enhancements

1. Make max_iterations configurable via environment variable
2. Add metrics for SQL error rates
3. Implement exponential backoff for SQL retries
4. Add user notification when hitting retry limits
5. Cache successful SQL queries to avoid re-execution

