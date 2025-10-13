# n8n Multi-Agent Orchestrator Workflow

This n8n workflow replicates the Python orchestrator service using a visual workflow approach.

## Architecture

The workflow implements a 4-agent pipeline similar to the Python version:

```
User Query
    ↓
🧠 Query Planner Agent
    ↓
Route Based on Needs
    ├── 📚 RAG Retrieval (if needs_rag)
    └── 🌐 Web Search (if needs_web)
    ↓
Merge Data Sources
    ↓
📊 Analysis Agent (if needs_analysis)
    ↓
✨ Synthesis Agent
    ↓
Final Response
```

## Features

✅ **Structured Outputs**: Each agent returns strict JSON schemas
✅ **Conditional Routing**: Only executes agents when needed
✅ **Parallel Execution**: RAG and Web Search run in parallel when both needed
✅ **Type-Safe**: Uses Pydantic-like schemas for all agent outputs
✅ **Comprehensive**: Includes citations, confidence levels, and recommendations

## Installation

### 1. Import the Workflow

1. Open your n8n instance
2. Go to **Workflows** → **Import from File**
3. Upload `n8n-workflow-orchestrator.json`
4. The workflow will be created with all nodes connected

### 2. Configure OpenAI Credentials

1. Go to **Settings** → **Credentials** → **Add Credential**
2. Select **OpenAI API**
3. Enter your OpenAI API key
4. Save as "OpenAI API"

### 3. Activate the Workflow

1. Click the **Active** toggle in the top-right
2. Copy the webhook URL (it will look like: `https://your-n8n.com/webhook/chat`)

## Usage

### Making Requests

Send a POST request to the webhook URL:

```bash
curl -X POST https://your-n8n.com/webhook/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the main complaints about our mobile app?",
    "session_id": "user-123",
    "user_id": "user_abc"
  }'
```

### Response Format

```json
{
  "message": "Based on analysis of customer feedback...",
  "session_id": "user-123",
  "message_id": "1697123456789-a1b2c3d4e",
  "timestamp": "2025-10-12T12:34:56.789Z",
  "metadata": {
    "model": "gpt-4o",
    "provider": "n8n_team",
    "confidence": "high",
    "citations": [
      {
        "source": "G2 Review",
        "title": "Mobile App Experience",
        "url": "https://..."
      }
    ],
    "recommendations": [
      "Improve app loading speed",
      "Fix login issues on iOS"
    ]
  }
}
```

## Agent Schemas

### Query Planner Output
```json
{
  "intent": "summarization|aggregation|filtering|ranking|trend_analysis|gap_analysis|competitive_analysis|general_inquiry",
  "required_data_sources": ["rag", "web", "database"],
  "requires_analysis": true,
  "requires_visualization": false,
  "output_format": "text|visualization|cited_summary|detailed_report",
  "key_topics": ["mobile app", "performance", "user experience"]
}
```

### Data Retrieval Output
```json
{
  "summary": "Found 15 reviews mentioning mobile app issues",
  "total_sources": 15,
  "rag_results": [
    {
      "title": "Review Title",
      "content": "Review content...",
      "relevance": 0.95
    }
  ],
  "web_results": [
    {
      "title": "Article Title",
      "url": "https://...",
      "snippet": "Article snippet..."
    }
  ]
}
```

### Analysis Output
```json
{
  "summary": "Analysis reveals 3 key issues with the mobile app",
  "key_findings": [
    "67% of complaints mention slow loading",
    "Login failures increased 23% in Q3"
  ],
  "statistical_insights": {
    "avg_rating": 3.2,
    "complaint_rate": 0.34
  },
  "nlp_insights": {
    "sentiment": "negative",
    "themes": ["performance", "reliability", "user experience"]
  },
  "visualizations": [
    {
      "type": "bar",
      "data": {"complaint_types": {...}}
    }
  ]
}
```

### Synthesis Output
```json
{
  "response": "# Mobile App Feedback Analysis\n\nBased on customer feedback...",
  "confidence_level": "high",
  "citations": [...],
  "recommendations": [...]
}
```

## Customization

### Modify Agent Instructions

Each agent node has a system prompt that defines its behavior. To customize:

1. Click on the agent node (e.g., "🧠 Query Planner Agent")
2. Edit the **System Message** in the messages section
3. Adjust the JSON schema requirements
4. Save and test

### Add New Agents

To add new agents (e.g., "Visualization Agent"):

1. Add a new **OpenAI Chat Model** node
2. Define the system prompt and output schema
3. Connect it in the appropriate position
4. Update the **Merge** nodes to include the new data

### Change Models

To use different models:

1. Click on any agent node
2. Change the **Model** parameter
3. Options: `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, etc.
4. Adjust temperature and max tokens as needed

### Add Error Handling

Add an **Error Trigger** node:

1. Add **Error Trigger** node
2. Connect to a **Send Email** or **Slack** node
3. Configure to notify on failures

## Workflow Nodes Explained

| Node | Purpose |
|------|---------|
| **Webhook - Chat Input** | Receives POST requests with user queries |
| **Extract Input** | Parses request body and extracts fields |
| **Query Planner Agent** | Analyzes intent and determines execution plan |
| **Parse Query Plan** | Extracts routing flags (needs_rag, needs_web) |
| **Route Data Needs** | Conditionally executes RAG/Web based on flags |
| **RAG Retrieval Agent** | Searches vector database for reviews |
| **Web Search Agent** | Searches web for external information |
| **Merge Data Sources** | Combines RAG and Web results |
| **Needs Analysis?** | Checks if analysis is required |
| **Analysis Agent** | Performs statistical and NLP analysis |
| **Merge Analysis** | Combines data with analysis results |
| **Synthesis Agent** | Generates final user-facing response |
| **Format Final Response** | Structures the output JSON |
| **Webhook Response** | Returns result to caller |

## Performance

- **Average Execution Time**: 10-20 seconds
- **Parallel Execution**: RAG + Web run simultaneously
- **Token Usage**: ~3,000-8,000 tokens per request
- **Cost per Request**: $0.02-$0.10 (depending on models)

## Monitoring

### View Execution History

1. Go to **Executions** in n8n
2. Filter by workflow name
3. Click any execution to see:
   - Node outputs
   - Execution time
   - Errors

### Track Costs

Add a **Spreadsheet** node to log:
- Timestamp
- User ID
- Tokens used
- Cost
- Execution time

## Comparison: n8n vs Python

| Feature | n8n Workflow | Python Orchestrator |
|---------|--------------|---------------------|
| **Ease of Setup** | ⭐⭐⭐⭐⭐ Visual, no code | ⭐⭐⭐ Requires coding |
| **Performance** | ⭐⭐⭐⭐ Fast (parallel) | ⭐⭐⭐⭐⭐ Optimized |
| **Flexibility** | ⭐⭐⭐⭐ Easy to modify | ⭐⭐⭐⭐⭐ Full control |
| **Debugging** | ⭐⭐⭐⭐⭐ Visual logs | ⭐⭐⭐ Text logs |
| **Scaling** | ⭐⭐⭐ n8n limits | ⭐⭐⭐⭐⭐ Unlimited |
| **Cost** | n8n hosting + LLM | Hosting + LLM |

## Troubleshooting

### Agent Not Returning JSON

**Problem**: Agent returns text instead of JSON

**Solution**: 
1. Emphasize "ONLY return JSON" in system prompt
2. Add `"jsonOutput": true` to agent parameters
3. Use stricter temperature (0.2-0.4)

### Workflow Times Out

**Problem**: Execution exceeds timeout

**Solution**:
1. Increase workflow timeout in Settings
2. Use faster models (gpt-4o-mini)
3. Reduce max tokens
4. Simplify agent instructions

### Missing Data in Merge

**Problem**: Merge node missing expected data

**Solution**:
1. Check conditional routing logic
2. Ensure all paths lead to merge
3. Add default values for optional branches

## Advanced Features

### Add Streaming

For real-time responses, replace the webhook with:
1. **WebSocket** node for bidirectional communication
2. Stream agent outputs as they complete
3. Use **Send Message** nodes after each agent

### Add Caching

Add **Redis** or **Memory** nodes to cache:
- Query plans for similar queries
- Retrieved data (TTL: 1 hour)
- Analysis results

### Add Database Persistence

1. Add **Postgres** node after "Format Final Response"
2. Save: message, response, metadata, agent steps
3. Query history for context

## Next Steps

1. ✅ Import the workflow
2. ✅ Configure OpenAI credentials
3. ✅ Test with sample queries
4. 🔧 Customize agent prompts
5. 📊 Add monitoring/logging
6. 🚀 Deploy to production

## Support

For issues or questions:
- Check n8n docs: https://docs.n8n.io
- Review execution logs in n8n
- Compare with Python implementation

---

**Created**: October 2025  
**Version**: 1.0  
**Compatible with**: n8n v1.0+

