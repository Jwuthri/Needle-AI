# LG Workflow History Fix Summary

## Problem
The lg_workflow was not using conversation history correctly. When users asked follow-up questions like:
1. "What is the sentiment of reviews?" 
2. "Can you display as a pie chart please?"
3. "Please regenerate the graph"

The system would lose context and not understand what the user was referring to.

## Root Causes

### 1. Conversation History Not Passed to Workflow
**File:** `backend/app/api/v1/chat_experimental.py`

The conversation history was being fetched from the database but never passed to the LangGraph workflow. The workflow was initialized with only the current message, losing all context from previous exchanges.

### 2. Supervisor Routing Logic
**File:** `backend/app/core/llm/lg_workflow/agents/supervisor.py`

The supervisor didn't have explicit rules for handling follow-up visualization requests like "regenerate the graph" or "update the chart."

### 3. Visualizer Not Context-Aware
**File:** `backend/app/core/llm/lg_workflow/agents/visualizer.py`

The Visualizer agent's prompt didn't emphasize reading conversation history to understand follow-up requests.

### 4. Pie Chart Aggregation Issue
**File:** `backend/app/core/llm/lg_workflow/tools/viz.py`

The pie chart tool required pre-aggregated data (labels + values), but sentiment analysis returns individual rows with categorical labels. The tool needed to auto-aggregate categorical columns.

### 5. DataAnalyst Column Communication
**File:** `backend/app/core/llm/lg_workflow/agents/analyst.py`

The DataAnalyst didn't explicitly communicate what columns it created, making it harder for the Visualizer to know what's available.

## Fixes Applied

### 1. Pass Conversation History to Workflow ✅
**Change:** Modified `chat_experimental.py` to convert conversation history to LangChain message format and include it in the workflow initialization.

```python
# Convert history to LangChain messages
history_messages = []
for msg in conversation_history:
    if msg["role"] == "user":
        history_messages.append(HumanMessage(content=msg["content"]))
    elif msg["role"] == "assistant":
        history_messages.append(AIMessage(content=msg["content"]))

# Add current message
history_messages.append(HumanMessage(content=request.message))

inputs = {
    "messages": history_messages  # Now includes full history!
}
```

### 2. Enhanced Supervisor Routing ✅
**Change:** Added explicit rule #8 to handle follow-up visualization requests:

```python
"8. CRITICAL - VISUALIZATION FOLLOW-UPS: If the user asks to 'regenerate', 'redo', 
    'remake', 'update', or 'change' a graph/plot/chart mentioned in previous messages, 
    route to Visualizer. Review the conversation history to understand what visualization 
    they're referring to."
```

### 3. Context-Aware Visualizer ✅
**Change:** Updated Visualizer prompt to emphasize context awareness:

- Added "Context Awareness" as step 1 in the workflow
- Added "FOLLOW-UP REQUEST HANDLING" section with explicit examples
- Emphasized reading conversation history to infer visualization parameters
- Added Example Flow #3 for "regenerate" requests

### 4. Auto-Aggregate Pie Charts ✅
**Change:** Modified `generate_plot_tool` to support auto-aggregation for categorical data:

```python
elif plot_type in ["pie", "piechart"]:
    if y_column:
        # Pre-aggregated data with explicit values
        fig = go.Figure(data=[go.Pie(labels=plot_df[x_column], values=plot_df[y_column])])
    else:
        # Auto-aggregate: count occurrences of categorical column
        value_counts = plot_df[x_column].value_counts()
        fig = go.Figure(data=[go.Pie(labels=value_counts.index, values=value_counts.values)])
```

Now users can create sentiment pie charts with:
```python
generate_plot(table_name="reviews", x_column="sentiment_label", y_column="", plot_type="pie")
```

### 5. Explicit Column Communication ✅
**Change:** Updated DataAnalyst prompt to explicitly mention created columns:

```python
"When you add columns (e.g., sentiment_label), explicitly mention them in your response"
"Example: 'I've added a 'sentiment_label' column with Positive/Neutral/Negative categories.'"
```

## Testing the Fix

### Test Scenario 1: Sentiment Analysis + Visualization
```
User: "What is the overall sentiment of our reviews?"
→ DataAnalyst analyzes, mentions "sentiment_label" column
→ Reporter presents findings

User: "Can you display as a graph/plot pie please"
→ Supervisor recognizes visualization request
→ Visualizer reads history, finds sentiment_label column
→ Creates pie chart with auto-aggregation
→ Reporter presents chart

✅ WORKS: Visualizer has context from previous exchange
```

### Test Scenario 2: Regenerate Request
```
User: "Please regenerate the graph"
→ Supervisor recognizes "regenerate" + "graph" as follow-up
→ Visualizer reads history, finds previous pie chart request
→ Uses same parameters to create new chart
→ Reporter presents updated chart

✅ WORKS: System understands "the graph" refers to previous visualization
```

### Test Scenario 3: Multi-Turn Follow-Ups
```
User: "What's the sentiment?"
→ Sentiment analysis performed

User: "Show as pie chart"
→ Pie chart created

User: "Now show as bar chart"
→ Bar chart created (understands context)

User: "Go back to the pie chart"
→ Pie chart recreated

✅ WORKS: Full conversation history maintained throughout
```

## Files Modified

1. **backend/app/api/v1/chat_experimental.py**
   - Pass conversation history to workflow initialization

2. **backend/app/core/llm/lg_workflow/agents/supervisor.py**
   - Add follow-up visualization routing rule

3. **backend/app/core/llm/lg_workflow/agents/visualizer.py**
   - Emphasize context awareness
   - Add follow-up request handling examples
   - Update pie chart documentation

4. **backend/app/core/llm/lg_workflow/agents/analyst.py**
   - Add explicit column creation communication
   - Document columns each tool creates

5. **backend/app/core/llm/lg_workflow/tools/viz.py**
   - Add auto-aggregation for categorical pie charts

## Impact

✅ **Improved Context Retention:** Agents now have full conversation history  
✅ **Better Follow-Up Handling:** System understands references to previous analyses  
✅ **Smarter Visualizations:** Pie charts auto-aggregate categorical data  
✅ **Clearer Communication:** Agents explicitly state what columns they create  
✅ **Enhanced User Experience:** Natural multi-turn conversations work seamlessly  

## Next Steps (Optional Improvements)

1. **Memory Persistence:** Consider saving visualization parameters to a shared state for even faster follow-ups
2. **Chart Comparison:** Add ability to compare multiple visualizations side-by-side
3. **Chart Export:** Add download links directly in the UI
4. **Smart Defaults:** Auto-suggest visualizations based on data analysis results

