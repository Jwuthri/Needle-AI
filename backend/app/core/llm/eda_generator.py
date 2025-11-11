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


class TableEDAResponse(BaseModel):
    """LLM response for table EDA."""

    summary: str = Field(description="A concise summary of the table data (2-3 sentences)")
    field_metadata: List[FieldMetadata] = Field(description="Detailed metadata for each field including description and purpose")


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
        model: str = None,
        db: Optional[AsyncSession] = None,
        user_id: Optional[str] = None
    ) -> TableEDAResponse:
        """
        Use LLM to generate summary and field metadata from column statistics.

        Args:
            table_name: Name of the table
            column_stats: Column statistics
            row_count: Total row count
            model: Optional model name override

        Returns:
            TableEDAResponse with summary and field metadata
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

        prompt = f"""Analyze this database table and provide:

1. A concise summary (2-3 sentences) describing what this table contains and its purpose

2. For EACH field, provide:

   - field_name: The exact column name

   - data_type: Simplified type (int, text, timestamp, float, boolean)

   - description: A detailed description (1-2 sentences) explaining what this field represents, its purpose, and any important patterns or characteristics

   - unique_value_count: Number of unique values (if available)

   - top_values: List of top 5-10 most common values formatted as "value(count)" (if applicable)

Table: {table_name}

Total Rows: {row_count}

{stats_summary}

Be specific and actionable. Focus on helping someone understand what each field means and how to use it in queries.

For example, if a field is "conversation_id", explain that it's a UUID that groups messages in the same conversation thread."""

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
            return eda_response
        except Exception as e:
            # Log failure
            if log_id and db:
                try:
                    await fail_llm_call(log_id, e, db)
                except Exception as log_error:
                    logger.warning(f"{self._log_prefix(table_name)} | Failed to log LLM call error: {log_error}")
            raise

