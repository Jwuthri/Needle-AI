# Anomaly Detection Agent

## Overview

The Anomaly Detection Agent is a specialized agent in the Product Review Analysis Workflow that identifies unusual patterns, spikes, and anomalies in review data. It generates high-severity insights for critical issues that require immediate attention.

## Capabilities

### 1. Rating Spike Detection
- Detects sudden increases in low-rating (1-2 star) reviews
- Identifies rating drops (declining average ratings)
- Compares recent periods against historical baseline
- Generates critical alerts for significant spikes (>200% increase)

### 2. Topic Emergence Detection
- Identifies new topics that appear suddenly in recent reviews
- Detects topics with dramatic frequency increases
- Compares recent vs historical review content
- Flags emerging issues that weren't present in historical data

### 3. Source-Specific Anomaly Detection
- Detects platform-specific issues (App Store, Google Play, etc.)
- Identifies sources with significantly worse performance
- Compares rating distributions across sources
- Highlights technical or UX problems specific to platforms

## Key Features

### High-Severity Insights
- Generates insights with severity scores > 0.9 for critical anomalies
- Includes "CRITICAL" or "EMERGING ISSUE" labels in insight text
- Provides recommended actions for each anomaly

### Baseline Calculation
- Establishes baseline patterns from historical data
- Uses statistical thresholds to identify significant deviations
- Adapts to data volume and time spans

### Visualization Support
- Generates line charts showing spikes over time
- Creates bar charts for source comparisons
- Includes annotations marking anomaly points

## Usage Example

```python
from app.core.llm.workflow.agents.anomaly_detection import AnomalyDetectionAgent
from app.models.workflow import ExecutionContext

# Initialize agent
agent = AnomalyDetectionAgent(
    llm_client=llm_client,
    stream_callback=stream_callback
)

# Detect anomalies
insights = await agent.detect_anomalies(
    reviews=reviews,
    context=execution_context,
    db=db_session,
    step_order=1,
    time_window="weekly"  # or "daily"
)

# Process insights
for insight in insights:
    if insight.severity_score > 0.9:
        print(f"CRITICAL: {insight.insight_text}")
        print(f"Action: {insight.metadata.get('recommended_action')}")
```

## Insight Structure

Each anomaly generates an Insight with:

- **source_agent**: "anomaly_detection"
- **insight_text**: Human-readable description of the anomaly
- **severity_score**: 0.7-0.95 (higher for more critical anomalies)
- **confidence_score**: 0.80-0.93
- **supporting_reviews**: Review IDs that evidence the anomaly
- **visualization_hint**: "line_chart" or "bar_chart"
- **visualization_data**: Chart configuration
- **metadata**: Includes:
  - `anomaly_type`: "rating_spike", "topic_emergence", "source_specific", etc.
  - `recommended_action`: Suggested next steps
  - Type-specific fields (baseline, spike_ratio, etc.)

## Anomaly Types

### Rating Spike
```python
{
    "anomaly_type": "rating_spike",
    "baseline": 3.0,
    "spike_value": 12,
    "spike_ratio": 4.0,
    "spike_date": "Week 4, 2025",
    "recommended_action": "Investigate app version released on Oct 9th"
}
```

### Topic Emergence
```python
{
    "anomaly_type": "topic_emergence",
    "topic_name": "Battery Drain",
    "historical_count": 0,
    "recent_count": 8,
    "emergence_ratio": None,  # inf for new topics
    "recommended_action": "Investigate root cause of Battery Drain complaints"
}
```

### Source-Specific
```python
{
    "anomaly_type": "source_specific",
    "source": "google_play",
    "source_low_rating_pct": 65.0,
    "overall_low_rating_pct": 25.0,
    "difference": 40.0,
    "recommended_action": "Investigate google_play-specific issues"
}
```

## Detection Thresholds

- **Rating Spike**: ≥200% increase in low ratings, minimum 3 reviews
- **Rating Decline**: ≥0.5 point drop in average rating
- **Topic Emergence**: ≥3x increase or completely new topic with ≥3 mentions
- **Source Anomaly**: ≥50% more low ratings than overall average, minimum 30% low rating percentage

## Integration with Workflow

The Anomaly Detection Agent:
1. Receives reviews from the Data Retrieval Agent
2. Generates a thought explaining its detection strategy
3. Performs three types of anomaly detection in parallel
4. Returns standardized Insight objects
5. Tracks execution in Chat Message Steps
6. Emits streaming events for real-time updates

## Error Handling

- Gracefully handles insufficient data (returns empty list)
- Uses fallback thought if LLM fails
- Continues with other detection types if one fails
- Logs errors without blocking workflow

## Performance Considerations

- Requires minimum 10 reviews with dates for rating anomalies
- Requires minimum 15 reviews with dates for topic anomalies
- Requires minimum 2 sources with 3+ reviews each for source anomalies
- Groups reviews by time periods (daily/weekly) for efficiency
- Limits LLM analysis to recent samples (10-30 reviews)
