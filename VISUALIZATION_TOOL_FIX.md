# Visualization Tool Parameter Fix

## Problem
The LLM was frequently calling `generate_line_chart()` and other visualization functions without the required `data` parameter, causing this error:
```
generate_line_chart() missing 1 required positional argument: 'data'
```

## Root Cause
When functions are wrapped with `FunctionTool.from_defaults()`, the LLM relies on:
1. Parameter order in the function signature
2. Docstring descriptions to understand what's required

The original implementation had `data` as the second parameter (after `ctx`), but the docstring wasn't explicit enough about it being REQUIRED.

## Solution

### 1. Reordered Function Parameters
Moved `data` to the **last position** in all visualization functions:

**Before:**
```python
async def generate_line_chart(
    ctx: Context,
    data: List[Dict[str, Any]],  # 2nd parameter
    title: str,
    x_label: str,
    y_label: str,
    user_id: str
)
```

**After:**
```python
async def generate_line_chart(
    ctx: Context,
    title: str,
    x_label: str,
    y_label: str,
    user_id: str,
    data: List[Dict[str, Any]]  # Last parameter - more prominent
)
```

### 2. Enhanced Docstrings
Made docstrings extremely explicit about required parameters:

```python
"""Generate line chart PNG.

REQUIRED PARAMETERS:
    title (str): Chart title - REQUIRED
    x_label (str): X-axis label - REQUIRED
    y_label (str): Y-axis label - REQUIRED
    user_id (str): User ID for file path - REQUIRED
    data (List[Dict[str, Any]]): List of dicts with x and y keys - REQUIRED
        Example: [{"x": "2024-01", "y": 100}, {"x": "2024-02", "y": 150}]
    
Returns:
    Dict with chart path and metadata
"""
```

### 3. Updated Agent System Prompt
Added explicit instructions in the visualization agent's system prompt:

```python
CRITICAL - ALL PARAMETERS ARE REQUIRED:
When calling ANY chart generation tool, you MUST provide ALL parameters:
- title: Chart title (string)
- user_id: User identifier (string)
- data: List of dictionaries with data points (REQUIRED!)
- x_label, y_label: Axis labels (for bar/line charts)

Example data formats:
- Bar/Line: [{"x": "Jan", "y": 100}, {"x": "Feb", "y": 150}]
- Pie: [{"label": "Positive", "value": 60}, {"label": "Negative", "value": 40}]
- Heatmap: [{"x": "Cat1", "y": "Metric1", "value": 10}]
```

## Files Modified

1. **`backend/app/core/llm/simple_workflow/tools/visualization_tool.py`**
   - Reordered parameters for all 4 functions: `generate_bar_chart`, `generate_line_chart`, `generate_pie_chart`, `generate_heatmap`
   - Enhanced docstrings with explicit "REQUIRED PARAMETERS" sections
   - Added example data formats

2. **`backend/app/core/llm/simple_workflow/agents/visualization_agent.py`**
   - Updated system prompt with "CRITICAL - ALL PARAMETERS ARE REQUIRED" section
   - Added example data formats for each chart type
   - Made parameter requirements crystal clear

## Impact
- LLM will now understand that `data` is a required parameter
- Clear examples help LLM format data correctly
- Reduced errors when generating visualizations
- Better user experience with fewer failed chart generations

## Testing
Test by asking the agent to generate various charts:
- "Show me a line chart of trends over time"
- "Create a bar chart comparing categories"
- "Generate a pie chart of sentiment distribution"

The LLM should now consistently provide the `data` parameter in all cases.

