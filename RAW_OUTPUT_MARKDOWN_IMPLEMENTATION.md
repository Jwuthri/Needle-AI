# Raw Output with Markdown Rendering Implementation

## Summary

Updated the agent step display to use `raw_output` field with markdown rendering instead of structured output for better readability.

## Changes Made

### 1. Database Model (`chat_message_step.py`)
Added `raw_output` column to store unprocessed agent output:
```python
raw_output = Column(Text, nullable=True)  # For raw unprocessed output from agents
```

### 2. Repository (`chat_message_step.py`)
- Added `raw_output` parameter to `create()` method
- Added new `update_with_result()` method to update steps with tool results including raw_output
- Updated `bulk_create()` to support raw_output

### 3. Migration (017)
Created migration to add `raw_output` column to `chat_message_steps` table.

### 4. Frontend Component (`experimental-chat-view.tsx`)
Updated `formatToolContent()` function to:
- Accept `rawOutput` parameter
- Render `raw_output` using `StreamingMarkdown` component for proper markdown display
- Fall back to structured output or plain text if raw_output is not available

```tsx
{rawOutput ? (
  <StreamingMarkdown content={rawOutput} />
) : typeof output === 'object' ? (
  <pre className="text-white/70 whitespace-pre-wrap break-words font-mono">
    {JSON.stringify(output, null, 2)}
  </pre>
) : (
  <div className="text-white/70 whitespace-pre-wrap break-words">
    {String(output)}
  </div>
)}
```

### 5. TypeScript Types (`chat.ts`)
Added `raw_output` field to `AgentStep` interface:
```typescript
export interface AgentStep {
  // ... existing fields
  raw_output?: string; // Raw unprocessed output from agent
}
```

## Usage

When creating or updating agent steps, you can now include `raw_output`:

```python
# Create step with raw output
step = await ChatMessageStepRepository.create(
    db=db,
    message_id=message_id,
    agent_name="data_discovery",
    step_order=0,
    tool_call={"tool_name": "analyze_data"},
    raw_output="## Analysis Results\n\n- Finding 1\n- Finding 2"
)

# Update step with result
await ChatMessageStepRepository.update_with_result(
    db=db,
    step_id=step_id,
    status="success",
    raw_output="## Final Report\n\nThe analysis shows..."
)
```

## Benefits

1. **Better Readability**: Markdown rendering makes agent outputs more readable
2. **Flexible Display**: Supports headings, lists, code blocks, etc.
3. **Backward Compatible**: Falls back to structured output if raw_output is not available
4. **Consistent Formatting**: Uses the same `StreamingMarkdown` component as chat messages

## Status

✅ Database migration applied
✅ Backend models updated
✅ Frontend rendering updated
✅ TypeScript types updated

**Ready to use!** Just restart your backend server to pick up the model changes.

