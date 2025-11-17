# Agent Routing Information Fix

## Problem
The LLM was exposing internal routing information to users, such as "Route: Visualization → Report Writer" in the chat responses. This was confusing and unprofessional.

## Root Cause
Multiple agent system prompts explicitly instructed agents to mention routing:
- "After analysis, route to Visualization → Report Writer"
- "Generate chart, then route to Report Writer"
- "Loading dataset..." then route

The LLM was following these instructions literally and outputting the routing information in user-facing responses.

## Solution
Updated all agent system prompts to:
1. Remove explicit routing instructions
2. Add rule: "NEVER mention routing, agents, or internal workflow"
3. Emphasize working silently and efficiently
4. Focus on delivering results without explaining internal processes

## Files Modified

### 1. `backend/app/core/llm/simple_workflow/agents/coordinator_agent.py`
- Removed routing language
- Changed "Route queries" to "Work efficiently"
- Added explicit rule against mentioning internal workflow

### 2. `backend/app/core/llm/simple_workflow/agents/data_discovery_agent.py`
- Removed routing instructions
- Changed "route to analysts" to "Proceed with analysis"
- Emphasized silent background work

### 3. `backend/app/core/llm/simple_workflow/agents/gap_analysis_agent.py`
- Removed "route to Visualization → Report Writer"
- Added "NEVER mention routing, agents, or internal workflow"

### 4. `backend/app/core/llm/simple_workflow/agents/sentiment_analysis_agent.py`
- Removed "route to Visualization → Report Writer"
- Added explicit no-routing rule

### 5. `backend/app/core/llm/simple_workflow/agents/trend_analysis_agent.py`
- Removed "route to Visualization → Report Writer"
- Added explicit no-routing rule

### 6. `backend/app/core/llm/simple_workflow/agents/clustering_agent.py`
- Removed "route to Visualization → Report Writer"
- Added explicit no-routing rule

### 7. `backend/app/core/llm/simple_workflow/agents/visualization_agent.py`
- Removed "Generate chart, then route to Report Writer"
- Changed to "Stay completely silent - let your charts speak"
- Emphasized silent chart generation

### 8. `backend/app/core/llm/simple_workflow/agents/general_assistant_agent.py`
- Added explicit no-routing rule for consistency
- Emphasized natural, direct answers

### 9. `backend/app/core/llm/simple_workflow/agents/report_writer_agent.py`
- Removed "You are the FINAL agent" language
- Added explicit no-routing rule
- Changed to "Deliver the complete report naturally"

## Testing
After these changes, agents will:
- Work silently in the background
- Never mention "routing", "agents", or internal workflow details
- Deliver results directly to users
- Maintain brevity without exposing implementation details

## Impact
- **User Experience**: Cleaner, more professional responses
- **Agent Behavior**: No functional changes, only prompt improvements
- **Backward Compatibility**: Fully compatible with existing workflow

