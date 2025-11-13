# Synthesis Agent

## Overview

The Synthesis Agent is responsible for combining insights from multiple analysis agents into coherent, well-structured narrative responses. It acts as the final step in the workflow, taking standardized `Insight` objects and weaving them into comprehensive markdown reports with embedded visualizations and source citations.

## Key Responsibilities

1. **Generate Synthesis Plan**: Create a structured plan (thought) before generating the response
2. **Prioritize Insights**: Sort insights by severity and confidence scores
3. **Group by Theme**: Organize insights into logical categories
4. **Embed Visualizations**: Call Visualization Agent and embed charts in markdown
5. **Add Citations**: Include supporting evidence with review references
6. **Track Execution**: Save reasoning and outputs to Chat Message Steps

## Architecture

### Input

The Synthesis Agent accepts:
- **Query**: Original user query string
- **Insights**: List of `Insight` objects from analysis agents
- **Context**: `ExecutionContext` with session and user information
- **Database Session**: For tracking execution steps
- **Step Order**: Position in the workflow execution

### Output

Returns a markdown-formatted string containing:
- Introduction with query restatement
- Key findings section (top 3-5 insights)
- Detailed analysis sections by theme
- Embedded visualizations with explanations
- Recommendations based on high-severity insights
- Supporting evidence with review citations

## Data Models

### SynthesisThought

```python
class SynthesisThought(BaseModel):
    outline: List[str]  # Section headings in order
    key_insights: List[str]  # Insight IDs to highlight
    visualization_placements: Dict[str, int]  # Insight ID -> section index
    narrative_strategy: str  # "severity-based", "chronological", "thematic"
    reasoning: str  # Why this structure was chosen
```

### Insight (Input)

```python
class Insight(BaseModel):
    source_agent: str  # "sentiment", "topic_modeling", etc.
    insight_text: str  # Human-readable finding
    severity_score: float  # 0.0 to 1.0
    confidence_score: float  # 0.0 to 1.0
    supporting_reviews: List[str]  # Review IDs
    visualization_hint: Optional[str]  # "bar_chart", "line_chart", etc.
    visualization_data: Optional[Dict]  # Data for chart generation
    metadata: Dict[str, Any]  # Additional context
```

## Core Methods

### synthesize_response()

Main entry point that orchestrates the synthesis process.

**Flow**:
1. Generate synthesis plan (thought)
2. Save thought to Chat Message Steps
3. Prioritize insights by severity × confidence
4. Group insights by theme (source agent)
5. Generate markdown sections:
   - Introduction
   - Key findings
   - Theme sections with visualizations
   - Recommendations
   - Citations
6. Save output to Chat Message Steps
7. Return markdown string

### generate_synthesis_plan()

Creates a structured plan using LLM before generating the response.

**Process**:
1. Summarize insights for LLM context
2. Prompt LLM to create outline and strategy
3. Parse JSON response
4. Map insight indices to IDs
5. Determine visualization placements
6. Return `SynthesisThought` object

**Fallback**: Returns default plan if LLM fails

### _prioritize_insights()

Sorts insights by combined score (severity × confidence) in descending order.

**Purpose**: Ensures most important findings are highlighted first.

### _group_insights_by_theme()

Groups insights by source agent and maps to user-friendly theme names.

**Theme Mapping**:
- `sentiment` → "Sentiment Analysis"
- `topic_modeling` → "Common Themes"
- `anomaly_detection` → "Critical Issues"
- `summary` → "Overview"

**Sorting**: Groups are sorted by highest severity within each group.

### _generate_markdown_response()

Orchestrates the creation of all markdown sections.

**Sections**:
1. Introduction (query + summary)
2. Key Findings (top 3-5 insights)
3. Theme Sections (one per group)
4. Recommendations (actionable items)
5. Citations (supporting evidence)

### _embed_visualization()

Calls Visualization Agent to generate charts and returns markdown with embedded images.

**Process**:
1. Extract visualization parameters from insight
2. Call `visualization_agent.generate_visualization()`
3. Get file path from result
4. Create markdown with image reference
5. Add explanatory text if available

**Error Handling**: Returns `None` if visualization fails (synthesis continues)

## Integration with Workflow

### Chat Message Steps

The Synthesis Agent creates multiple Chat Message Steps:

1. **Thought Step**: Contains synthesis plan reasoning
   - `thought`: Reasoning text
   - `structured_output`: Full `SynthesisThought` object

2. **Output Step**: Contains synthesis results
   - `prediction`: First 1000 chars of response
   - `structured_output`: Metadata (insights used, sections created, etc.)

3. **Error Step** (if applicable): Contains error information
   - `thought`: Error description

### Streaming Events

Emits events for real-time updates:
- `agent_step_start`: When synthesis begins
- `agent_step_complete`: When synthesis succeeds
- `agent_step_error`: When synthesis fails

## Usage Example

```python
from app.core.llm.workflow.agents.synthesis import SynthesisAgent
from app.core.llm.base import BaseLLMClient
from app.models.workflow import ExecutionContext, Insight

# Initialize agent
llm_client = BaseLLMClient()
visualization_agent = VisualizationAgent()
synthesis_agent = SynthesisAgent(
    llm_client=llm_client,
    visualization_agent=visualization_agent,
    stream_callback=my_callback
)

# Prepare insights from other agents
insights = [
    Insight(
        source_agent="sentiment",
        insight_text="Performance has 78% negative sentiment",
        severity_score=0.78,
        confidence_score=0.92,
        supporting_reviews=["rev_1", "rev_2"],
        visualization_hint="bar_chart",
        visualization_data={...},
        metadata={}
    ),
    # ... more insights
]

# Synthesize response
response = await synthesis_agent.synthesize_response(
    query="What are my main product gaps?",
    insights=insights,
    context=execution_context,
    db=db_session,
    step_order=10
)

print(response)  # Markdown formatted report
```

## Response Structure

### Example Output

```markdown
# Analysis Results

**Query:** What are my main product gaps?

I've analyzed your review data and identified **4 key insights** across 4 categories. Here's what I found:

## 🔑 Key Findings

1. 🔴 **CRITICAL: 1-star reviews spiked 400% on Oct 10th**
   - Confidence: 93%
   - Source: Anomaly Detection

2. 🔴 **'UI Slowness' is the most frequent complaint, appearing in 18 reviews**
   - Confidence: 90%
   - Source: Common Themes

3. 🔴 **Performance aspect has 78% negative sentiment across 35 reviews**
   - Confidence: 92%
   - Source: Sentiment Analysis

## Critical Issues

### 🔴 CRITICAL: 1-star reviews spiked 400% on Oct 10th

**1-Star Review Spike**

![1-Star Review Spike](/static/visualizations/abc123.png)

*Based on 3 reviews*

## Common Themes

### 🔴 'UI Slowness' is the most frequent complaint, appearing in 18 reviews

**Top Complaint Topics**

![Top Complaint Topics](/static/visualizations/def456.png)

*Based on 6 reviews*

## 💡 Recommendations

Based on the analysis, here are the top priority actions:

1. Investigate app version released on Oct 9th
2. Address UI performance issues
3. Improve app stability

## 📚 Supporting Evidence

This analysis is based on **11 reviews**. Here are some representative examples:

1. Review `rev_1`
   - Related to: CRITICAL: 1-star reviews spiked 400% on Oct 10th...

2. Review `rev_2`
   - Related to: Performance aspect has 78% negative sentiment...
```

## Error Handling

### Fallback Response

If synthesis fails, the agent generates a simple fallback response:
- Lists insights with severity indicators
- Includes basic formatting
- Omits visualizations and detailed structure

### Graceful Degradation

- **LLM Failure**: Uses default synthesis plan
- **Visualization Failure**: Continues without charts
- **Database Failure**: Logs error but returns response

## Performance Considerations

### Optimization Strategies

1. **Insight Limiting**: Only top 20 insights sent to LLM for planning
2. **Parallel Processing**: Could parallelize section generation (future)
3. **Caching**: Synthesis plans could be cached for similar queries
4. **Streaming**: Sections could be streamed as generated (future)

### Resource Usage

- **LLM Calls**: 1-2 per synthesis (plan + optional key points)
- **Database Writes**: 2-3 Chat Message Steps
- **Visualization Calls**: 0-N depending on insights

## Testing

Comprehensive test suite in `tests/unit/test_synthesis_agent.py`:

- ✅ Initialization
- ✅ Synthesis plan generation
- ✅ Insight prioritization
- ✅ Theme grouping
- ✅ Section generation (intro, findings, citations, recommendations)
- ✅ Fallback responses
- ✅ Error handling
- ✅ Event emission
- ✅ End-to-end synthesis

Run tests:
```bash
pytest tests/unit/test_synthesis_agent.py -v
```

## Future Enhancements

### Potential Improvements

1. **Multi-Format Output**: Support HTML, PDF, JSON formats
2. **Interactive Elements**: Add collapsible sections, tabs
3. **Customizable Templates**: User-defined report structures
4. **Streaming Synthesis**: Stream sections as they're generated
5. **A/B Testing**: Test different narrative strategies
6. **Personalization**: Adapt style to user preferences
7. **Multi-Language**: Support synthesis in different languages

### Integration Points

- **Feedback Loop**: Use user ratings to improve synthesis quality
- **Template Library**: Pre-built templates for common query types
- **Export Options**: PDF, Word, PowerPoint generation
- **Collaboration**: Share and comment on synthesized reports

## Dependencies

- `app.core.llm.base.BaseLLMClient`: For LLM completions
- `app.database.repositories.chat_message_step.ChatMessageStepRepository`: For tracking
- `app.models.workflow`: Data models (Insight, SynthesisThought, ExecutionContext)
- `app.utils.logging`: Structured logging
- Visualization Agent (optional): For chart generation

## Related Components

- **Analysis Agents**: Provide input insights
  - Sentiment Analysis Agent
  - Topic Modeling Agent
  - Anomaly Detection Agent
  - Summary Agent
- **Visualization Agent**: Generates charts
- **Workflow Orchestrator**: Coordinates agent execution
- **Chat Message Steps**: Tracks execution history
