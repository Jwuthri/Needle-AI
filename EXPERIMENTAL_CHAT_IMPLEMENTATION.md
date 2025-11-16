# Experimental Chat Implementation Summary

## Overview
Successfully implemented an experimental chat interface using the `simple_workflow` multi-agent system with real-time streaming of agent execution details including tool calls, tool results, agent transitions, and response content.

## Backend Changes

### 1. Simple Workflow Service (`backend/app/services/simple_workflow_service.py`)
- Created service to manage workflow execution with streaming
- Initializes OpenAI LLM with OpenRouter as backend
- Creates product review workflow with specialized agents
- Streams all workflow events:
  - `ToolCall` events → tool_call SSE events
  - `ToolCallResult` events → tool_result SSE events  
  - Agent transitions → agent SSE events
  - Content deltas → content SSE events
- Saves agent steps to database using `ChatMessageStepRepository`
- Tracks step order and agent names for UI visualization

### 2. Experimental Chat Router (`backend/app/api/v1/chat_experimental.py`)
- New endpoint: `POST /api/v1/chat-experimental/stream`
- Reuses existing database tables (chat_sessions, chat_messages, chat_message_steps)
- Direct integration with simple_workflow (bypasses orchestrator)
- Returns Server-Sent Events (SSE) with event types:
  - `status`: Status updates
  - `agent`: Agent transitions
  - `tool_call`: Tool execution started
  - `tool_result`: Tool execution completed
  - `content`: Streaming response text
  - `complete`: Final response with metadata
  - `error`: Error messages

### 3. Router Registration (`backend/app/api/v1/router.py`)
- Registered experimental chat router under `/chat-experimental` prefix
- Tagged as "chat-experimental" for API documentation

## Frontend Changes

### 1. Sidebar Menu (`frontend/src/components/layout/sidebar.tsx`)
- Added "Chat (Experimental)" menu item below regular Chat
- Displays "NEW" badge to indicate experimental status
- Routes to `/chat-experimental`
- Badge styling uses purple theme to match experimental workflow colors

### 2. Experimental Chat Page (`frontend/src/app/chat-experimental/page.tsx`)
- New page at `/chat-experimental`
- Uses authentication check (Clerk)
- Renders `ExperimentalChatView` component
- Shares session management with regular chat via context

### 3. Experimental Streaming Hook (`frontend/src/hooks/use-experimental-chat-stream.ts`)
- Custom hook for experimental workflow streaming
- Tracks additional state:
  - `toolExecutions`: Array of tool calls and their status
  - `agentSteps`: Formatted agent execution steps
  - `currentAgent`: Currently active agent name
- Parses SSE events:
  - `agent`: Agent transition events
  - `tool_call`: Tool execution start
  - `tool_result`: Tool execution completion
  - `content`: Response streaming
  - `status`: Status updates
- Formats steps with tool execution details for UI

### 4. Experimental Chat View (`frontend/src/components/chat/experimental-chat-view.tsx`)
- Enhanced chat interface with workflow visibility
- Features:
  - Purple header badge indicating experimental mode
  - Live workflow execution panel showing:
    - Agent steps in real-time
    - Tool calls with arguments
    - Tool results with output preview
    - Step numbering and status indicators
  - Expandable/collapsible execution pipeline
  - Tool execution formatting with icons and badges
  - Color-coded status (purple for active, green for completed)
  - Real-time streaming of agent actions
- Uses purple/blue gradient theme to distinguish from regular chat

### 5. API Client Update (`frontend/src/lib/api.ts`)
- Added `sendMessageExperimental()` method
- Routes to `/chat-experimental/` endpoint
- Maintains same interface as regular chat for easy integration

## Key Features

### Real-Time Visibility
- See each agent's actions as they happen
- View tool calls with their arguments
- See tool results as they complete
- Track agent transitions throughout workflow

### Tool Execution Display
- Tool name and type (call vs result)
- Arguments passed to tools (formatted JSON)
- Output from tools (truncated for readability)
- Status indicators (running, completed)
- Color-coded visual feedback

### Workflow Pipeline
- Step-by-step execution visualization
- Numbered steps showing execution order
- Active step highlighting
- Completion status tracking
- Collapsible panel for space efficiency

### Shared Infrastructure
- Same database tables as regular chat
- Sessions viewable from either interface
- Same authentication and rate limiting
- Consistent message storage and retrieval

## Testing

The implementation includes:
- Proper error handling for streaming failures
- Database transaction management
- Type-safe TypeScript interfaces
- Linting compliance for all files
- SSE connection management with abort controllers

## Usage

1. Navigate to "Chat (Experimental)" in the sidebar
2. Send a message as usual
3. Watch the workflow execute in real-time:
   - See which agent is working
   - View tool calls as they happen
   - See results as they complete
4. Expand "Workflow Execution" to see full details
5. Final response streams after workflow completes

## Technical Notes

- Uses `llama_index` AgentWorkflow for multi-agent coordination
- OpenRouter API provides LLM backend (OpenAI-compatible)
- Server-Sent Events (SSE) for real-time streaming
- React hooks manage streaming state
- Database persistence ensures conversation history
- Purple/blue color scheme differentiates from regular chat

## Future Enhancements

Potential improvements:
- Add workflow configuration options
- Enable agent selection/customization
- Provide detailed tool output inspection
- Add performance metrics (execution time, token usage)
- Export workflow execution traces
- Add workflow debugging tools

