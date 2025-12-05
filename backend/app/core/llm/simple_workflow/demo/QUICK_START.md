# Quick Start Guide - Gap & Trend Analysis Tools

## ✅ What Was Built

Two powerful analysis tools integrated into the simple_workflow system:

1. **Gap Analysis Tool** - Identifies underrepresented clusters and market opportunities
2. **Trend Analysis Tool** - Detects temporal patterns using Python/pandas

## 🚀 Quick Test

### 1. Activate Virtual Environment
```bash
cd backend
source .venv/bin/activate
```

### 2. Test Imports
```bash
python -c "
from app.core.llm.simple_workflow.tools.gap_analysis_tool import detect_gaps_from_clusters
from app.core.llm.simple_workflow.tools.trend_analysis_tool import analyze_temporal_trends
print('✅ All imports successful!')
"
```

### 3. Run Demo Script
```bash
python -m app.core.llm.simple_workflow.demo_gap_trend_analysis
```

## 📁 Files Created/Modified

### New Files
```
tools/
  ├── gap_analysis_tool.py          # Gap analysis implementation
  └── trend_analysis_tool.py        # Trend analysis implementation

agents/
  ├── gap_analysis_agent.py         # Updated to use new tool
  └── trend_analysis_agent.py       # Updated to use new tool

demo_gap_trend_analysis.py          # Demo script
README_GAP_TREND_ANALYSIS.md        # Comprehensive docs
IMPLEMENTATION_SUMMARY.md           # Implementation details
QUICK_START.md                      # This file
```

## 🎯 Usage Examples

### Gap Analysis (Auto-triggers clustering)
```python
from llama_index.core.workflow import Context
from app.core.llm.simple_workflow.tools.gap_analysis_tool import detect_gaps_from_clusters

# In a workflow step
gap_report = await detect_gaps_from_clusters(
    ctx,
    dataset_name="customer_reviews",
    min_cluster_size=5
)
print(gap_report)  # Markdown report with gap insights
```

### Trend Analysis
```python
from app.core.llm.simple_workflow.tools.trend_analysis_tool import analyze_temporal_trends

# In a workflow step
trend_report = await analyze_temporal_trends(
    ctx,
    dataset_name="sales_data",
    time_column="order_date",
    value_columns=None,  # Auto-detect numeric columns
    aggregation="sum",
    time_grouping="month"
)
print(trend_report)  # Markdown report with trend insights
```

## 🔍 What Each Tool Does

### Gap Analysis
- ✅ Auto-triggers clustering if not done
- ✅ Identifies underrepresented clusters (< 50% avg size)
- ✅ Analyzes outliers and noise points
- ✅ Calculates cluster concentration
- ✅ Provides actionable recommendations

**Output**: Markdown report with:
- Cluster statistics
- Underrepresented clusters with samples
- Outlier analysis
- Distribution table
- Key insights

### Trend Analysis
- ✅ Auto-detects numeric columns
- ✅ Smart time grouping (auto/day/week/month/quarter/year)
- ✅ Multiple aggregations (mean/sum/count/median)
- ✅ Linear regression for trends
- ✅ Volatility detection

**Output**: Markdown report with:
- Trend direction (📈/📉/📊)
- Summary statistics
- Recent values table
- Overall trend summary

## 🏗️ Architecture

```
User/Agent Request
      ↓
   Tool Function (async)
      ↓
   Context (shared state)
      ↓
   Analysis & Storage
      ↓
   Markdown Report
```

### Context State Structure
```python
ctx.state = {
    "dataset_data": {
        "dataset_name": pd.DataFrame,
        "clustering": {
            "dataset_name": pd.DataFrame  # With __cluster_id__
        }
    },
    "gap_analysis": {
        "dataset_name": {...}  # Gap results
    },
    "trend_analysis": {
        "dataset_name": {...}  # Trend results
    }
}
```

## 🧪 Testing

### Manual Test
```bash
# Activate venv
source .venv/bin/activate

# Run demo
python -m app.core.llm.simple_workflow.demo_gap_trend_analysis
```

### Expected Output
```
🚀 Starting Gap & Trend Analysis Demo
📦 Step 1: Initializing workflow context...
✅ Context initialized successfully!

📊 Step 2: Fetching available datasets...
✅ Found X datasets!

🔍 Step 3: Loading dataset...
✅ Dataset loaded successfully!

🔎 Step 4: Running Gap Analysis...
✅ Gap analysis completed!

# Gap Analysis Report for 'dataset_name'
...

📈 Step 5: Running Trend Analysis...
✅ Trend analysis completed!

# Trend Analysis Report for 'dataset_name'
...

🎉 Gap & Trend Analysis Demo Completed!
```

## 📊 Integration with Workflow

Both agents are already integrated into the workflow:

```python
# In workflow.py
from app.core.llm.simple_workflow.agents import (
    create_gap_analysis_agent,
    create_trend_analysis_agent,
    ...
)

# Agents are created and added to workflow
gap_analysis_agent = create_gap_analysis_agent(llm, user_id)
trend_analysis_agent = create_trend_analysis_agent(llm, user_id)

workflow = AgentWorkflow(
    agents=[
        ...,
        gap_analysis_agent,
        trend_analysis_agent,
        ...
    ],
    root_agent="coordinator",
    timeout=300,
)
```

## 🎓 Key Concepts

### 1. Auto-Clustering
Gap analysis automatically triggers clustering if needed:
```python
# No need to cluster first!
gap_report = await detect_gaps_from_clusters(ctx, dataset_name)
# Tool checks for clustering, runs it if needed, then analyzes
```

### 2. Auto-Detection
Trend analysis auto-detects columns:
```python
# Don't know which columns? Let it auto-detect!
trend_report = await analyze_temporal_trends(
    ctx, 
    dataset_name, 
    time_column="date",
    value_columns=None  # Auto-detects numeric columns
)
```

### 3. Context Persistence
Results are stored in context for downstream use:
```python
# Run analysis
await detect_gaps_from_clusters(ctx, dataset_name)

# Later, access results
ctx_state = await ctx.store.get("state", {})
gap_results = ctx_state["gap_analysis"][dataset_name]
```

## 🔧 Troubleshooting

### Import Errors
```bash
# Make sure you're in the venv
source .venv/bin/activate

# Check Python version (should be 3.11+)
python --version

# Test imports
python -c "import umap; import hdbscan; print('✅ Dependencies OK')"
```

### Module Not Found
```bash
# Install dependencies
cd backend
uv pip install -e .
```

### Dataset Not Found
```bash
# Make sure dataset is loaded in context first
await get_dataset_data_from_sql(ctx, query, dataset_name)
# Then run analysis
await detect_gaps_from_clusters(ctx, dataset_name)
```

## 📚 Documentation

- **Comprehensive Guide**: `README_GAP_TREND_ANALYSIS.md`
- **Implementation Details**: `IMPLEMENTATION_SUMMARY.md`
- **Demo Script**: `demo_gap_trend_analysis.py`
- **Tool Code**: `tools/gap_analysis_tool.py`, `tools/trend_analysis_tool.py`
- **Agent Code**: `agents/gap_analysis_agent.py`, `agents/trend_analysis_agent.py`

## 🎉 Summary

You now have two powerful analysis tools:

1. **Gap Analysis** - Find market opportunities in clustered data
2. **Trend Analysis** - Detect temporal patterns and trends

Both tools:
- ✅ Work seamlessly with existing workflow
- ✅ Auto-detect and auto-configure when possible
- ✅ Store results in context for downstream use
- ✅ Return LLM-friendly markdown reports
- ✅ Include comprehensive error handling

**Next Steps**:
1. Run the demo script
2. Read the comprehensive documentation
3. Integrate into your workflows
4. Build amazing data-driven insights!

