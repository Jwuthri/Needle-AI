"""
LLM-based EDA generation for database tables.

This module uses LlamaIndex to analyze table statistics and generate comprehensive
field metadata including descriptions, data types, and value distributions.
"""

from typing import Any, Dict, List, Optional

from llama_index.core.llms import ChatMessage
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.logging import get_logger
from app.optimal_workflow.agents.base import get_llm
from app.database.models.llm_call import LLMCallTypeEnum
from app.utils.llm_call_logger import log_llm_call, complete_llm_call, fail_llm_call

logger = get_logger(__name__)


class FieldMetadata(BaseModel):
    """Metadata for a single field."""

    field_name: str = Field(description="Name of the field")
    data_type: str = Field(description="Data type (int, text, timestamp, float, boolean)")
    description: str = Field(description="Detailed description of what this field represents and its purpose")
    unique_value_count: int | None = Field(default=None, description="Number of unique values")
    top_values: List[str] | None = Field(default=None, description="Top 5-10 most common values with counts")


class VectorStoreColumns(BaseModel):
    """Metadata for vector store columns."""

    main_column: str = Field(description="Primary column to use for text embedding")
    alternative_columns: List[str] = Field(description="Alternative columns that could be concatenated with main column for richer semantic search")
    description: str = Field(description="Explanation of why these columns are suitable for vector search")


class TableEDAResponse(BaseModel):
    """LLM response for table EDA."""

    summary: str = Field(description="A comprehensive summary describing what the table contains (keep it under 100 words), its purpose, relationships between fields, data structure, and any notable patterns or characteristics (MUST BE IN MARKDOWN FORMAT, with emot and add color around the column name object)")
    field_metadata: List[FieldMetadata] = Field(description="Detailed metadata for each field including description and purpose")
    vector_store_columns: Optional[VectorStoreColumns] = Field(default=None, description="Columns suitable for vector store indexing (if applicable)")


class EDAGenerator:
    """Service for generating table EDA using LLM."""

    def _log_prefix(self, table_name: str = None) -> str:
        """Generate log prefix following team standards."""
        return f"[EDAGenerator] | [table={table_name or 'None'}]"

    async def generate_table_eda(
        self,
        table_name: str,
        column_stats: Dict[str, Dict[str, Any]],
        row_count: int,
        sample_data: List[Dict[str, Any]],
        model: str = None,
        db: Optional[AsyncSession] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Use LLM to generate summary and field metadata from column statistics.

        Args:
            table_name: Name of the table
            column_stats: Column statistics
            row_count: Total row count
            sample_data: First 5 rows of the table
            model: Optional model name override
            db: Database session for logging
            user_id: User ID for logging

        Returns:
            Dict with summary, field_metadata, column_stats, sample_data, and vector_store_columns
        """
        logger.info(f"{self._log_prefix(table_name)} | Generating LLM insights")

        # Format stats for LLM
        stats_summary = f"Table: {table_name}\nTotal Rows: {row_count}\n\nColumn Statistics:\n"
        for col_name, stats in column_stats.items():
            stats_summary += f"\n{col_name} ({stats.get('dtype', 'unknown')}):\n"
            for key, value in stats.items():
                if key == 'top_values':
                    # Format top values nicely
                    top_str = ", ".join([f"{k}({v})" for k, v in list(value.items())[:5]])
                    stats_summary += f"  - {key}: {top_str}\n"
                elif key == 'sample_values':
                    stats_summary += f"  - {key}: {', '.join(map(str, value))}\n"
                elif key != 'dtype':
                    stats_summary += f"  - {key}: {value}\n"

        # Format sample data for LLM
        sample_str = "\n\nSample Data (first 5 rows):\n"
        for i, row in enumerate(sample_data[:5], 1):
            sample_str += f"\nRow {i}: {row}\n"

        prompt = f"""Analyze this database table and provide:

1. A comprehensive summary (3-5 sentences) describing:
   - What this table contains and its purpose
   - The context (e.g., e-commerce, customer service, analytics)
   - Relationships between fields and how they work together
   - The data structure (e.g., list of JSON objects, relational records)
   - Any notable patterns, characteristics, or data quality observations
   
   IMPORTANT for summary formatting:
   - Use markdown formatting (bold, italic, code blocks)
   - Wrap column/field names in backticks like `column_name` for green highlighting
   - Use **bold** for important concepts
   - Use emojis sparingly for visual interest (e.g., 📊 for data, ⚠️ for warnings)
   - DO NOT use HTML tags or <object> tags - use markdown only
   - Never mention the table name in the summary

2. For EACH field, provide:
   - field_name: The exact column name
   - data_type: Simplified type (int, text, timestamp, float, boolean)
   - description: A detailed description (1-2 sentences) explaining what this field represents, its purpose, and any important patterns or characteristics
   - unique_value_count: Number of unique values (if available)
   - top_values: List of top 5-10 most common values formatted as "value(count)" (if applicable)

3. Identify columns suitable for vector store indexing:
   - main_column: The primary text column that would benefit most from semantic search (e.g., message content, descriptions, reviews)
   - alternative_columns: Other text columns that could be concatenated for richer search (e.g., subject, title, tags)
   - description: Explain why these columns are good candidates for vector search
   - If no text columns are suitable for vector search, set vector_store_columns to null

Table: {table_name}

Total Rows: {row_count}

{stats_summary}

{sample_str}

Be specific and actionable. Focus on helping someone understand what each field means, how fields relate to each other, and how to use the data effectively."""

        # Get LLM instance and create structured LLM
        llm = get_llm(model=model)
        structured_llm = llm.as_structured_llm(output_cls=TableEDAResponse)

        # Create messages
        messages = [
            ChatMessage(
                role="system",
                content="You are an expert data analyst that generates comprehensive table metadata and field descriptions."
            ),
            ChatMessage(role="user", content=prompt)
        ]

        # Log LLM call
        log_id = None
        if db:
            try:
                log_id = await log_llm_call(
                    llm=llm,
                    messages=messages,
                    call_type=LLMCallTypeEnum.SYSTEM,
                    db=db,
                    user_id=user_id,
                    extra_metadata={'table_name': table_name, 'row_count': row_count}
                )
            except Exception as e:
                logger.warning(f"{self._log_prefix(table_name)} | Failed to log LLM call: {e}")

        try:
            # Get structured response
            response = await structured_llm.achat(messages)
            eda_response: TableEDAResponse = response.raw

            # Complete logging
            if log_id and db:
                try:
                    await complete_llm_call(log_id, response, db)
                except Exception as e:
                    logger.warning(f"{self._log_prefix(table_name)} | Failed to complete LLM call log: {e}")

            logger.info(f"{self._log_prefix(table_name)} | Generated metadata for {len(eda_response.field_metadata)} fields")
            
            # Build complete response with all fields
            complete_response = {
                "summary": eda_response.summary,
                "field_metadata": [field.model_dump() for field in eda_response.field_metadata],
                "column_stats": column_stats,
                "sample_data": sample_data[:5],  # Ensure only 5 rows
                "vector_store_columns": eda_response.vector_store_columns.model_dump() if eda_response.vector_store_columns else None
            }
            
            return complete_response
        except Exception as e:
            # Log failure
            if log_id and db:
                try:
                    await fail_llm_call(log_id, e, db)
                except Exception as log_error:
                    logger.warning(f"{self._log_prefix(table_name)} | Failed to log LLM call error: {log_error}")
            raise

