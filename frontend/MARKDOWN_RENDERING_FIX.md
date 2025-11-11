# Markdown Rendering Fix

## Problem
The chat interface was breaking when messages contained markdown headers (like `##`, `###`). This happened because:

1. The `highlightKeywords()` function was applying JSX span elements to text
2. This was breaking markdown syntax by mixing JSX with markdown
3. The `formatAssistantContent()` function didn't recognize markdown headers (`##`)
4. Lines with keywords near markdown headers were being incorrectly formatted

## Changes Made

### 1. Added Markdown Header Support
Now properly detects and renders markdown headers:
```typescript
// Before: Only detected lines ending with ":"
if (line.trim().endsWith(':') && line.trim().length > 3)

// After: Also detects markdown headers
if (trimmedLine.startsWith('#')) {
  const headerMatch = trimmedLine.match(/^(#{1,6})\s+(.+)/)
  // Renders as proper h1-h6 based on # count
}
```

### 2. Fixed Keyword Highlighting
- Removed keyword highlighting from user message titles (line 225)
- Removed keyword highlighting from summary lines (line 271)
- Only apply highlighting to regular text content, not headers

### 3. Better Header Detection
- Added check to exclude URLs from header detection: `!trimmedLine.includes('http')`
- Prevents URLs ending with `:` from being treated as headers

### 4. Added Support for:
- ✅ Markdown headers: `#`, `##`, `###`, `####`, `#####`, `######`
- ✅ Bullet points: `-`, `•`, `*`
- ✅ Code blocks: ``` ` ` ` ```
- ✅ Regular paragraphs
- ✅ Headers ending with `:`

## Result
- Markdown headers now render properly with correct sizing
- No more broken formatting when keywords appear near `##` lines
- Better visual hierarchy with different header sizes:
  - `#` → text-2xl
  - `##` → text-xl
  - `###` → text-lg

## Example

**Before** (broken):
```
Great question. I calculate ## What you'll get
```

**After** (fixed):
```
Great question. I calculate

## What you'll get
(Rendered as proper xl header with green dot indicator)
```

## Files Changed
- `frontend/src/components/chat/enhanced-message.tsx`
  - Updated `formatAssistantContent()` function (lines 78-189)
  - Fixed summary rendering (lines 264-274)
  - Fixed user message rendering (line 225)

