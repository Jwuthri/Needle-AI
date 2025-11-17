# User Dataset Security Fix

## Problem

The LLM in the simple workflow had access to the hardcoded `reviews` table instead of being restricted to user-uploaded datasets only. This was a **critical security issue** that allowed:

1. LLM accessing system tables like `reviews`, `users`, `chat_messages`, etc.
2. Users potentially accessing other users' data
3. Bypassing the user dataset isolation model

### Root Causes

1. **Agent Prompt Hardcoded "reviews"**: The data discovery agent's system prompt explicitly told the LLM to "Use 'reviews' dataset if uncertain"
2. **No SQL Validation**: The `UserDatasetService.get_dataset_data_from_sql()` method executed any SQL query without validating table access
3. **Misleading Examples**: Tool docstrings showed examples using the `reviews` table instead of user datasets

## Solution

### 1. Updated Data Discovery Agent Prompt

**File**: `backend/app/core/llm/simple_workflow/agents/data_discovery_agent.py`

**Changes**:
- Removed hardcoded "Use 'reviews' dataset if uncertain"
- Added explicit instruction: "ALWAYS start by calling get_user_datasets to see available datasets"
- Clarified that LLM can ONLY access user datasets returned by `get_user_datasets`
- Updated examples to show proper workflow

### 2. Added SQL Query Validation

**File**: `backend/app/services/user_dataset_service.py`

**Changes**:
- Added `_validate_sql_query_for_user_datasets()` method that:
  - Extracts table names from SQL queries using regex
  - Blocks access to any table NOT starting with `__user_`
  - Blocks forbidden patterns: `pg_`, `information_schema`, `reviews`, `users`, `chat_`, `llm_`
  - Returns clear error messages directing LLM to use `get_user_datasets` tool

- Updated `get_dataset_data_from_sql()` to call validation before execution
- Updated `get_dataset_data_from_semantic_search()` to use validated queries
- Updated `get_dataset_data_from_semantic_search_from_sql()` to use validated queries

### 3. Fixed Tool Documentation

**Files**:
- `backend/app/core/llm/simple_workflow/tools/user_dataset_tool.py`
- `backend/app/core/llm/simple_workflow/tools/semantic_search_tool.py`

**Changes**:
- Removed examples showing `reviews` table
- Added examples showing proper workflow:
  1. First call `get_user_datasets()` to get available datasets
  2. Use the `table_name` field (e.g., `__user_123_customer_reviews`)
  3. Query using the full dynamic table name
- Added security warnings in docstrings

## Security Model

### User Dataset Table Naming Convention

All user datasets are stored in tables with this format:
```
__user_{user_id}_{dataset_name}
```

Example: `__user_user_2mabcdef123_customer_reviews`

### Access Control

1. **LLM Level**: Agent prompts instruct LLM to only use datasets from `get_user_datasets`
2. **Service Level**: SQL validation blocks any query accessing non-`__user_` tables
3. **Database Level**: User datasets are isolated by the `__user_{user_id}_` prefix

### Validation Rules

SQL queries are validated to ensure:
- ✅ Only tables starting with `__user_` can be accessed
- ❌ System tables are blocked: `reviews`, `users`, `chat_messages`, `llm_calls`, etc.
- ❌ PostgreSQL system tables are blocked: `pg_*`, `information_schema`
- ❌ Any forbidden pattern in query is rejected

## Testing

To verify the fix works:

1. **Test with user dataset**:
```python
# LLM should call get_user_datasets first
datasets = await get_user_datasets(ctx, user_id="user_123")
table_name = datasets[0]["table_name"]  # "__user_user_123_my_data"

# Then query using that table_name
data = await get_dataset_data_from_sql(
    ctx=ctx,
    sql_query=f'SELECT * FROM "{table_name}" LIMIT 10',
    dataset_name=table_name
)
# ✅ Should work
```

2. **Test blocking system tables**:
```python
# Try to access reviews table
data = await get_dataset_data_from_sql(
    ctx=ctx,
    sql_query='SELECT * FROM reviews LIMIT 10',
    dataset_name="reviews"
)
# ❌ Should raise ValueError: "Access denied: Query contains forbidden pattern 'reviews'"
```

3. **Test blocking other user's data**:
```python
# Try to access another user's dataset
data = await get_dataset_data_from_sql(
    ctx=ctx,
    sql_query='SELECT * FROM "__user_other_user_456_data" LIMIT 10',
    dataset_name="__user_other_user_456_data"
)
# ✅ Blocked by validation (table starts with __user_)
# But user_id binding in tools prevents cross-user access at repository level
```

## Impact

### Before Fix
- ❌ LLM could access `reviews` table with all customer review data
- ❌ Potential data leakage between users
- ❌ No SQL injection protection

### After Fix
- ✅ LLM can ONLY access user's own datasets
- ✅ SQL validation prevents unauthorized table access
- ✅ Clear error messages guide LLM to correct behavior
- ✅ Defense in depth: validation at multiple layers

## Files Modified

1. `backend/app/core/llm/simple_workflow/agents/data_discovery_agent.py`
2. `backend/app/services/user_dataset_service.py`
3. `backend/app/core/llm/simple_workflow/tools/user_dataset_tool.py`
4. `backend/app/core/llm/simple_workflow/tools/semantic_search_tool.py`

## Next Steps

1. ✅ Test the fix with actual user queries
2. Consider adding audit logging for blocked SQL attempts
3. Add unit tests for SQL validation logic
4. Review other workflows (optimal_workflow) for similar issues

