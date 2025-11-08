"""
Retrieval planner agent for creating data retrieval strategies.
"""

from typing import Dict, Any, Optional
from llama_index.core.llms import ChatMessage
from app import get_logger

from .base import get_llm, RetrievalPlan, QueryAnalysis

logger = get_logger(__name__)


async def plan_retrieval(query: str, table_schemas: Dict[str, Any], query_analysis: Optional[QueryAnalysis] = None) -> RetrievalPlan:
    """
    Plan data retrieval strategy.
    """
    llm = get_llm("gpt-5")
    sllm = llm.as_structured_llm(output_cls=RetrievalPlan)
    
    # Handle case where table_schemas is a string (from schema service)
    if isinstance(table_schemas, str):
        schema_info = table_schemas
    else:
        schema_info = "\n".join([
            f"Table: {name}\nSchema: {schema}"
            for name, schema in table_schemas.items()
        ])
    
    # Determine query complexity based on NLP analysis needs
    needs_nlp = query_analysis.needs_nlp_analysis if query_analysis else True
    
    if needs_nlp:
        # Simple queries for NLP analysis - avoid complex patterns
        complexity_guidance = """
**NLP ANALYSIS MODE - KEEP QUERIES EXTREMELY SIMPLE:**
- Generate **ONE simple query per table** maximum - retrieve once per table
- Use **basic WHERE clauses only** - NO LIKE/ILIKE patterns, NO complex conditions
- **ABSOLUTELY NO multiple similar queries** with different keyword patterns
- **FORBIDDEN**: Queries like "text ILIKE '%wish%' OR text ILIKE '%would like%' OR text ILIKE '%please add%'"
- Focus on retrieving **broad, relevant datasets** for downstream NLP processing
- Let NLP analysis handle pattern detection, sentiment analysis, and clustering - not SQL
- Example: `SELECT * FROM user_review_feedback WHERE company_name = 'Netflix' ORDER BY date DESC LIMIT 2000`
- **RETRIEVE ONCE, ANALYZE WITH NLP** - don't pre-filter with keywords"""
    else:
        # More complex queries allowed when no NLP analysis needed
        complexity_guidance = """
**DIRECT QUERY MODE - MODERATE COMPLEXITY ALLOWED:**
- You can use **LIKE patterns** and **multiple conditions** when appropriate
- **Joins and aggregations** are acceptable if they directly answer the query, but avoid as much as possible
- Use **specific filters** to get precise results
- Multiple related queries are acceptable if they serve different purposes"""

    prompt = f"""Create a data retrieval plan for this query:

Query: {query}

Available Tables:
{schema_info}

{complexity_guidance}

General Guidelines:
- If a table includes an **embedding or vector column**, and the user query implies semantic or similarity-based search, 
  use that column with the appropriate vector search operator (`<->` for L2 or `<=>` for cosine similarity).
- Always ensure queries are syntactically valid PostgreSQL.
- Focus on retrieving the most relevant data efficiently.

**EXAMPLE OF WHAT NOT TO DO IN NLP MODE:**
❌ BAD: Multiple similar queries with keyword patterns:
```sql
-- DON'T DO THIS when needs_nlp_analysis=True
SELECT * FROM reviews WHERE text ILIKE '%wish%' OR text ILIKE '%would like%' OR text ILIKE '%please add%';
SELECT * FROM reviews WHERE text ILIKE '%search%' OR text ILIKE '%sort%' OR text ILIKE '%filter%';
SELECT * FROM reviews WHERE text ILIKE '%download%' OR text ILIKE '%offline%';
```

✅ GOOD: One simple query for NLP processing:
```sql
-- DO THIS when needs_nlp_analysis=True
SELECT text, rating, company_name FROM reviews WHERE company_name = 'Netflix' ORDER BY date DESC LIMIT 2000;
```

Return the retrieval plan and the SQL statements needed.
"""

    messages = [
        ChatMessage(role="system", content="You are a data retrieval planner that creates SQL queries."),
        ChatMessage(role="user", content=prompt)
    ]
    
    response = await sllm.achat(messages)
    result = response.raw
    
    logger.info(f"Retrieval plan: {result}")
    return result