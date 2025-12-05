# Agent Loop Prevention Guide

## The Problem
Agents were getting stuck in infinite loops because they were told to work in "COMPLETE SILENCE" and "STOP immediately" after calling tools. However, in LangGraph, **agents MUST return some response** to signal completion and trigger supervisor routing.

## The Solution Pattern
Every agent that calls tools must follow this exact pattern:

```
1. Call tool (tool does the work, returns comprehensive output)
2. Say "Done." or similar (1-2 words MAX)
3. STOP - Supervisor sees response → Routes to next agent
```

## Updated Agents

### ✅ DataLibrarian
**Pattern:** Call tool → Say "Done." or "Dataset info retrieved." (4 words max)

```python
1. Call list_datasets or get_dataset_info
2. Say "Done."
3. Supervisor routes to Reporter
```

**Why:** Tool returns complete dataset list or schema. No need to summarize.

---

### ✅ DataAnalyst
**Pattern:** Call tool → Say "Done." or "Analysis complete." (2 words max)

```python
1. Call sentiment_analysis/clustering/tfidf/etc.
2. Say "Done."
3. Supervisor routes to Reporter
```

**Why:** Analysis tools return full markdown reports with stats, insights, tables. Agent just confirms completion.

---

### ✅ Visualizer
**Pattern:** Call tool → Say "Done." (1 word)

```python
1. Call generate_plot
2. Say "Done."
3. Supervisor routes to Reporter
```

**Why:** generate_plot returns complete visualization report with chart path, stats, insights. Agent is invisible.

---

### ✅ Researcher
**Pattern:** Call tool → Say "Done." or "Search complete." (2 words max)

```python
1. Call web_search_tool/get_current_time/get_user_location
2. Say "Done."
3. Supervisor routes to Reporter
```

**Why:** Search tools return formatted results. No need to rewrite.

---

### ✅ Reporter
**Pattern:** No tools - synthesizes from conversation history

```python
1. Read full conversation history
2. Extract tool outputs and agent findings
3. Create comprehensive final report
4. Deliver to user
```

**Why:** Reporter is the ONLY agent that writes detailed responses for the user. All other agents are silent executors.

---

### ✅ Supervisor
**Pattern:** Routes agents + has loop prevention

```python
1. Analyze conversation and decide next agent
2. LOOP PREVENTION: If same agent called 2+ times consecutively
   → Force route to Reporter
3. Return routing decision
```

**Why:** Prevents infinite loops by detecting repeated agent calls.

## Key Principles

### 1. Tools Do the Heavy Lifting
All tools (sentiment_analysis, generate_plot, web_search, etc.) return **complete, comprehensive markdown reports**. They include:
- Statistics and analysis
- Formatted tables
- Insights and findings
- File paths (for visualizations)
- Recommendations

**Agents should NEVER summarize or duplicate tool output.**

### 2. Agents Are Silent Executors
Worker agents (Librarian, Analyst, Visualizer, Researcher) are:
- Tool callers, not writers
- Invisible to the user
- Confirming completion with 1-2 words

### 3. Reporter Is The Voice
Only the Reporter:
- Writes detailed prose
- Synthesizes findings
- Communicates directly with user
- Formats final output

### 4. Response = Route Trigger
In LangGraph, an agent's response signals it's done. Without a response, the graph doesn't know the agent finished, causing loops.

## Testing Checklist

Use this checklist to verify agents don't loop:

### ✅ DataLibrarian Test
```
User: "What datasets do we have?"
Expected:
1. DataLibrarian calls list_datasets
2. DataLibrarian says "Done."
3. Supervisor routes to Reporter
4. Reporter shows dataset list to user

🚫 Should NOT see:
- DataLibrarian calling list_datasets multiple times
- DataLibrarian writing summaries
- DataLibrarian stuck "Processing..."
```

### ✅ DataAnalyst Test
```
User: "What's the sentiment of our reviews?"
Expected:
1. DataAnalyst calls sentiment_analysis
2. DataAnalyst says "Done."
3. Supervisor routes to Reporter
4. Reporter shows sentiment analysis report

🚫 Should NOT see:
- DataAnalyst calling sentiment_analysis multiple times
- DataAnalyst writing analysis paragraphs
- DataAnalyst stuck "Analyzing..."
```

### ✅ Visualizer Test
```
User: "Show sentiment as pie chart"
Expected:
1. Visualizer calls generate_plot
2. Visualizer says "Done."
3. Supervisor routes to Reporter
4. Reporter shows chart with markdown image

🚫 Should NOT see:
- Visualizer calling generate_plot multiple times
- Visualizer explaining the chart
- Visualizer stuck "Creating chart..."
```

### ✅ Researcher Test
```
User: "What's the latest news about X?"
Expected:
1. Researcher calls web_search_tool
2. Researcher says "Search complete."
3. Supervisor routes to Reporter
4. Reporter shows search results

🚫 Should NOT see:
- Researcher searching multiple times
- Researcher rewriting search results
- Researcher stuck "Searching..."
```

## Common Mistakes to Avoid

### ❌ Telling Agents to Work in "COMPLETE SILENCE"
**Problem:** Agent doesn't know it needs to respond
**Result:** Loops trying to figure out what to say

**Fix:** Tell agent to say "Done." after calling tool

### ❌ Saying "STOP immediately" or "DO NOT respond"
**Problem:** Agent tries to obey by not responding
**Result:** Graph doesn't receive completion signal → loops

**Fix:** Say "After tool returns, say 'Done.' then STOP"

### ❌ Letting Agents Summarize Tool Output
**Problem:** Agent writes paragraphs duplicating tool output
**Result:** Wastes tokens, confuses conversation flow

**Fix:** "Tools return complete reports. You just say 'Done.'"

### ❌ Not Explaining the Loop Prevention Pattern
**Problem:** Future updates might break the pattern
**Result:** Loops return

**Fix:** Document clearly: "Call tool → Say 'Done.' → STOP"

## Debugging Loops

If you see an agent looping:

### 1. Check the Agent Prompt
Look for:
- ✅ "After tool returns, say 'Done.'"
- ❌ "STOP immediately"
- ❌ "Work in SILENCE"
- ❌ "DO NOT respond"

### 2. Check Tool Returns
Verify tool returns complete output:
```python
# Good
return "# Analysis Report\n\n**Statistics:** ..."

# Bad
return ""  # Empty string
```

### 3. Check Supervisor Routing
Verify supervisor routes to Reporter after agent completion:
```python
# Supervisor should route to Reporter after:
- DataLibrarian → Reporter
- DataAnalyst → Reporter
- Visualizer → Reporter
- Researcher → Reporter
```

### 4. Check Loop Prevention Logic
Supervisor has built-in loop prevention:
```python
# If same agent called 2+ times consecutively
# → Force route to Reporter
if all(agent == recent_agents[0] for agent in recent_agents):
    return {"next": "Reporter"}
```

## Summary

**The Golden Rule:**
> Agents call tools. Tools return complete reports. Agents say "Done." Supervisor routes to Reporter. Reporter communicates with user.

**Remember:**
- Tools are comprehensive (they generate full markdown reports)
- Agents are silent executors (1-2 word responses max)
- Reporter is the communicator (synthesizes and delivers to user)
- Response triggers routing (without response = loop)

**Pattern for ALL agents:**
```
1. Call tool
2. Say "Done."
3. STOP
```

This prevents loops and creates a clean, efficient workflow.

