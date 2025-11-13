# Summary Agent

## Overview

The Summary Agent is a specialized component of the Product Review Analysis Workflow that creates concise summaries from large volumes of product reviews. It generates overview insights that capture key points and themes, supporting both extractive and abstractive summarization approaches.

## Purpose

The Summary Agent serves to:
1. Create concise summaries from large review datasets
2. Extract key points and themes from reviews
3. Support both extractive (selecting key sentences) and abstractive (generating new text) summarization
4. Generate standardized Insight objects with summary information
5. Track reasoning and execution in Chat Message Steps

## Architecture

### Class Structure

```python
class SummaryAgent:
    def __init__(
        self,
        llm_client: BaseLLMClient,
        stream_callback: Optional[Callable] = None
    )
    
    async def summarize_reviews(
        self,
        reviews: List[Dict[str, Any]],
        context: ExecutionContext,
        db: AsyncSession,
        step_order: int,
        summary_type: str = "extractive",
        max_length: int = 500
    ) -> List[Insight]
    
    async def generate_thought(
        self,
        reviews: List[Dict[str, Any]],
        context: ExecutionContext,
        summary_type: str = "extractive"
    ) -> str
```

## Summarization Types

### 1. Extractive Summarization

Extractive summarization identifies and extracts the most important sentences from the original reviews without generating new text.

**Process:**
1. Analyze review texts to identify key sentences
2. Select 3-5 representative sentences covering main themes
3. Include both positive and negative feedback
4. Combine selected sentences into a cohesive summary

**Use Cases:**
- When accuracy and attribution are critical
- When preserving original user language is important
- For legal or compliance purposes

**Example Output:**
```
"Users praise the features and content quality but consistently criticize app performance. 
The app crashes frequently and has a laggy interface. Customer support responsiveness is 
also a concern."
```

### 2. Abstractive Summarization

Abstractive summarization creates a new summary that captures the essence of the reviews in generated language.

**Process:**
1. Analyze overall themes and sentiments
2. Generate new text that synthesizes key points
3. Organize by theme (e.g., "Users praise X but criticize Y")
4. Create a cohesive narrative

**Use Cases:**
- When a polished, professional summary is needed
- When combining multiple perspectives
- For executive summaries and reports

**Example Output:**
```
"Overall, users appreciate the app's features and content but are frustrated by persistent 
performance issues. The app frequently crashes and has a laggy interface, which significantly 
impacts user experience. Additionally, customer support responsiveness needs improvement."
```

## Insight Generation

The Summary Agent generates standardized Insight objects:

```python
Insight(
    source_agent="summary",
    insight_text="Overall: [summary text]",
    severity_score=0.60,  # Based on average rating
    confidence_score=0.85,  # Based on review coverage
    supporting_reviews=["rev_1", "rev_2", ...],
    visualization_hint=None,  # Summaries typically don't need visualizations
    visualization_data=None,
    metadata={
        "summary_type": "extractive" | "abstractive",
        "full_summary": "Complete summary text",
        "key_points": ["Point 1", "Point 2", "Point 3"],
        "total_reviews_summarized": 45,
        "avg_rating": 2.8
    }
)
```

## Key Features

### 1. Thought Generation

Before performing summarization, the agent generates a reasoning trace explaining:
- The summarization approach (extractive vs abstractive)
- Key points to extract
- How to organize the summary

This thought is saved to Chat Message Steps for transparency.

### 2. Key Point Extraction

The agent automatically extracts 3-5 key points from the summary:
- Each point is a clear, standalone sentence
- Points cover main themes and sentiments
- Stored in metadata for easy access

### 3. Confidence Scoring

Confidence scores are calculated based on:
- Number of reviews summarized (more reviews = higher confidence)
- Coverage of the dataset
- Quality of the summary

Formula:
```python
confidence_score = min(0.90, 0.70 + (len(reviews) / 100) * 0.2)
```

### 4. Severity Scoring

Severity scores reflect the overall sentiment:
- Based on average rating of reviews
- Higher severity for more negative feedback
- Used for prioritization in synthesis

Formula:
```python
severity_score = max(0.3, 1.0 - (avg_rating / 5.0))
```

## Integration with Workflow

### 1. Execution Flow

```
1. Planner Agent determines summary is needed
2. Summary Agent receives reviews and context
3. Agent generates thought explaining approach
4. Agent performs summarization (extractive or abstractive)
5. Agent extracts key points from summary
6. Agent creates Insight object with metadata
7. Insight is added to ExecutionContext
8. Synthesis Agent uses summary in final response
```

### 2. Chat Message Step Tracking

The Summary Agent creates two Chat Message Steps:

**Step 1: Thought**
```python
{
    "agent_name": "summary",
    "step_order": 1,
    "thought": "I will create an extractive summary of 45 reviews..."
}
```

**Step 2: Structured Output**
```python
{
    "agent_name": "summary",
    "step_order": 2,
    "structured_output": {
        "insights_generated": 1,
        "summary_type": "extractive",
        "reviews_summarized": 45
    }
}
```

### 3. Streaming Events

The agent emits streaming events for real-time updates:

```python
# Start event
{
    "event_type": "agent_step_start",
    "data": {
        "agent_name": "summary",
        "action": "summarize_reviews",
        "review_count": 45,
        "summary_type": "extractive"
    }
}

# Complete event
{
    "event_type": "agent_step_complete",
    "data": {
        "agent_name": "summary",
        "action": "summarize_reviews",
        "success": True,
        "insights_generated": 1
    }
}
```

## Usage Examples

### Example 1: Extractive Summary

```python
agent = SummaryAgent(llm_client=llm_client)

insights = await agent.summarize_reviews(
    reviews=reviews,
    context=context,
    db=db,
    step_order=1,
    summary_type="extractive",
    max_length=500
)

# Result: One insight with extractive summary
print(insights[0].metadata["full_summary"])
print(insights[0].metadata["key_points"])
```

### Example 2: Abstractive Summary

```python
agent = SummaryAgent(llm_client=llm_client)

insights = await agent.summarize_reviews(
    reviews=reviews,
    context=context,
    db=db,
    step_order=1,
    summary_type="abstractive",
    max_length=500
)

# Result: One insight with abstractive summary
print(insights[0].insight_text)
```

### Example 3: With Streaming

```python
async def stream_callback(event):
    print(f"Event: {event['event_type']}")
    print(f"Data: {event['data']}")

agent = SummaryAgent(
    llm_client=llm_client,
    stream_callback=stream_callback
)

insights = await agent.summarize_reviews(
    reviews=reviews,
    context=context,
    db=db,
    step_order=1
)
```

## Error Handling

The Summary Agent handles errors gracefully:

1. **LLM API Errors**: Falls back to empty insights, logs error
2. **Empty Reviews**: Returns empty insights or minimal insight
3. **JSON Parsing Errors**: Falls back to sentence splitting for key points
4. **Database Errors**: Logs error but continues execution

All errors are tracked in Chat Message Steps for debugging.

## Performance Considerations

### 1. Review Limiting

The agent limits the number of reviews sent to the LLM:
- Maximum 50 reviews for context
- Each review text truncated to 300 characters
- Prevents token limit issues

### 2. Caching

Summary results can be cached in ExecutionContext:
```python
context.cached_results["summary"] = insights[0]
```

### 3. Parallel Execution

Summary Agent can run in parallel with other analysis agents:
- Independent of sentiment analysis
- Independent of topic modeling
- Can be executed concurrently for efficiency

## Testing

The Summary Agent includes comprehensive unit tests:

```bash
pytest tests/unit/test_summary_agent.py -v
```

Test coverage includes:
- Agent initialization
- Thought generation
- Extractive summarization
- Abstractive summarization
- Streaming events
- Error handling
- Context integration
- Confidence score calculation

## Future Enhancements

Potential improvements for the Summary Agent:

1. **Multi-document Summarization**: Summarize across multiple datasets
2. **Aspect-focused Summaries**: Create summaries for specific aspects
3. **Hierarchical Summaries**: Generate summaries at multiple levels of detail
4. **Summary Evaluation**: Automatic quality assessment of summaries
5. **Customizable Templates**: User-defined summary formats
6. **Language Support**: Multi-language summarization

## Related Components

- **Synthesis Agent**: Uses summary insights in final response
- **Planner Agent**: Determines when summarization is needed
- **Sentiment Analysis Agent**: Provides complementary sentiment insights
- **Topic Modeling Agent**: Provides complementary topic insights

## References

- Design Document: `.kiro/specs/product-review-analysis-workflow/design.md`
- Requirements: `.kiro/specs/product-review-analysis-workflow/requirements.md`
- Implementation: `backend/app/core/llm/workflow/agents/summary.py`
- Tests: `backend/tests/unit/test_summary_agent.py`
