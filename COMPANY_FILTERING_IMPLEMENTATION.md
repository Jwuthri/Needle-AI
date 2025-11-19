# Company Filtering Implementation

## Overview
When a company is selected in the frontend, the company name is prepended to the user's message so the LLM agents know which company to focus their analysis on.

## Implementation

### Frontend → Backend Flow
The company selection from the frontend is sent via the `ChatRequest.company_id` field:

```typescript
// frontend/src/components/chat/chat-view.tsx
await sendStreamMessage(
  {
    message,
    session_id: currentSessionId,
    company_id: companyId || undefined,
  },
  token
)
```

### Backend: Prepend Company Context to Message

**File**: `backend/app/services/simple_workflow_service.py`

When processing a message, if a `company_id` is provided, the company name is fetched from the database and prepended to the user's message:

```python
# Prepend company context to the user message if company is selected
user_message = request.message
if request.company_id:
    # Fetch company name from database
    from app.database.repositories.company import CompanyRepository
    from app.database.session import get_async_session
    async with get_async_session() as company_db:
        company = await CompanyRepository.get_by_id(company_db, request.company_id)
        if company:
            company_name = company.name
            user_message = f"[Analyzing data for company: {company_name}]\n\nQuery: {request.message}"
            logger.info(f"Added company context to message: {company_name}")

# Start workflow execution
handler = workflow.run(
    user_msg=user_message,
    initial_state={"user_id": user_id or "default_user"},
    ctx=ctx,
    max_iterations=50
)
```

## How It Works

1. **User selects company** in the frontend dropdown (bottom right)
2. **Frontend sends** `company_id` with each chat message
3. **Backend fetches** company name from database using the company_id
4. **Backend prepends** company name to the message: `[Analyzing data for company: Spotify]`
5. **Agents see** the company name in the message and filter their queries accordingly

## Example

**User selects**: Spotify (company_id: "abc123")  
**User asks**: "analyze sentiment"  
**Backend fetches**: Company name = "Spotify"  
**Message sent to LLM**: 
```
[Analyzing data for company: Spotify]

Query: analyze sentiment
```

The agents will naturally focus on Spotify data when writing SQL queries.

## Benefits

- ✅ **Simple**: Just prepends text to the message
- ✅ **Flexible**: Works with any data structure
- ✅ **Natural**: Agents understand context naturally
- ✅ **No SQL injection**: No automatic query modification

## Files Modified

- `backend/app/services/simple_workflow_service.py`

