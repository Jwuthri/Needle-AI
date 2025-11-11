"""
Service for managing user-uploaded datasets with CSV processing and EDA generation.
"""

import io
import re
from typing import Any, Dict, Optional

from app.config import get_settings
from app.utils.logging import get_logger
import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from llama_index.core.llms import ChatMessage

from app.core.llm.eda_generator import EDAGenerator, TableEDAResponse
from app.database.repositories.user_dataset import UserDatasetRepository
from app.database.models.llm_call import LLMCallTypeEnum
from app.optimal_workflow.agents.base import get_llm
from app.utils.llm_call_logger import log_llm_call, complete_llm_call, fail_llm_call
from app.utils.dynamic_tables import (
    create_dynamic_table,
    drop_dynamic_table,
    generate_dynamic_table_name,
    insert_dataframe_to_table,
)

logger = get_logger(__name__)


class UserDatasetService:
    """Service for managing user datasets."""

    def __init__(self, db: AsyncSession):
        """Initialize user dataset service."""
        self.db = db
        self.repository = UserDatasetRepository()
        self.eda_generator = EDAGenerator()

    def _log_prefix(self, user_id: Optional[str] = None, table_name: Optional[str] = None) -> str:
        """Generate log prefix."""
        parts = ["[UserDatasetService]"]
        if user_id:
            parts.append(f"[user={user_id}]")
        if table_name:
            parts.append(f"[table={table_name}]")
        return " | ".join(parts)

    def _get_llm_model_name(self) -> Optional[str]:
        """Get configured LLM model name for EDA generation."""
        settings = get_settings()
        return settings.default_model

    async def generate_dataset_name(
        self,
        user_id: str,
        filename: str,
        column_names: list[str],
        sample_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a dataset name using LLM based on filename and column names.
        
        Args:
            user_id: User ID
            filename: Original filename
            column_names: List of column names from the CSV
            sample_data: Optional sample data row for context
            
        Returns:
            Generated dataset name
        """
        logger.info(f"{self._log_prefix(user_id)} | Generating dataset name using LLM")
        
        # Get existing table names for this user
        existing_names = await UserDatasetRepository.get_all_table_names(self.db, user_id)
        existing_names_str = ", ".join(existing_names) if existing_names else "none"
        
        # Prepare context
        columns_str = ", ".join(column_names[:20])  # Limit to first 20 columns
        if len(column_names) > 20:
            columns_str += f" (and {len(column_names) - 20} more columns)"
        
        sample_context = ""
        if sample_data:
            # Show a few sample values
            sample_items = list(sample_data.items())[:5]
            sample_context = "\nSample data:\n"
            for key, value in sample_items:
                sample_context += f"  - {key}: {str(value)[:50]}\n"
        
        prompt = f"""Generate a short, descriptive name for this dataset. The name should:
- Be lowercase with underscores (e.g., "customer_orders", "sales_data_2024")
- Be 2-4 words maximum
- Accurately describe what the data contains
- NOT be one of these existing names: {existing_names_str}
- Be suitable as a database table name (alphanumeric and underscores only)

Filename: {filename}
Columns: {columns_str}
{sample_context}

Generate ONLY the name, nothing else. No quotes, no explanation, just the name."""

        try:
            llm = get_llm(model=self._get_llm_model_name())
            messages = [
                ChatMessage(
                    role="system",
                    content="You are a helpful assistant that generates concise, descriptive dataset names. Always respond with only the name, no additional text."
                ),
                ChatMessage(role="user", content=prompt)
            ]
            
            # Log LLM call
            log_id = None
            try:
                log_id = await log_llm_call(
                    llm=llm,
                    messages=messages,
                    call_type=LLMCallTypeEnum.SYSTEM,
                    db=self.db,
                    user_id=user_id,
                    extra_metadata={'filename': filename, 'purpose': 'dataset_name_generation'}
                )
            except Exception as e:
                logger.warning(f"{self._log_prefix(user_id)} | Failed to log LLM call: {e}")
            
            try:
                response = await llm.achat(messages)
                generated_name = response.message.content.strip()
                
                # Complete logging
                if log_id:
                    try:
                        await complete_llm_call(log_id, response, self.db)
                    except Exception as e:
                        logger.warning(f"{self._log_prefix(user_id)} | Failed to complete LLM call log: {e}")
                
                # Clean up the response (remove quotes, extra whitespace)
                generated_name = re.sub(r'^["\']|["\']$', '', generated_name)
                generated_name = generated_name.strip()
                
                # Sanitize to ensure it's valid
                generated_name = re.sub(r'[^a-zA-Z0-9_]', '_', generated_name)
                generated_name = generated_name.strip('_')
                
                # Ensure it's not empty and not too long
                if not generated_name:
                    # Fallback to filename-based name
                    generated_name = re.sub(r'[^a-zA-Z0-9_]', '_', filename.replace('.csv', '').lower())
                    generated_name = generated_name.strip('_')[:50]
                
                if len(generated_name) > 50:
                    generated_name = generated_name[:50]
                
                # Check if generated name conflicts with existing names
                if generated_name.lower() in [name.lower() for name in existing_names]:
                    # Add a suffix if conflict
                    counter = 1
                    base_name = generated_name
                    while generated_name.lower() in [name.lower() for name in existing_names]:
                        generated_name = f"{base_name}_{counter}"
                        counter += 1
                        if counter > 100:  # Safety limit
                            break
                
                logger.info(f"{self._log_prefix(user_id)} | Generated dataset name: {generated_name}")
                return generated_name
            except Exception as e:
                # Log failure
                if log_id:
                    try:
                        await fail_llm_call(log_id, e, self.db)
                    except Exception as log_error:
                        logger.warning(f"{self._log_prefix(user_id)} | Failed to log LLM call error: {log_error}")
                raise
            
        except Exception as e:
            logger.error(f"{self._log_prefix(user_id)} | Failed to generate dataset name: {e}", exc_info=True)
            # Fallback to filename-based name
            fallback_name = re.sub(r'[^a-zA-Z0-9_]', '_', filename.replace('.csv', '').lower())
            fallback_name = fallback_name.strip('_')[:50]
            if not fallback_name:
                fallback_name = "dataset"
            
            # Ensure no conflict
            existing_names_lower = [name.lower() for name in existing_names]
            if fallback_name.lower() in existing_names_lower:
                counter = 1
                base_name = fallback_name
                while fallback_name.lower() in existing_names_lower:
                    fallback_name = f"{base_name}_{counter}"
                    counter += 1
            
            return fallback_name

    def compute_column_stats(self, df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """
        Compute column-level statistics from a DataFrame.

        Args:
            df: Pandas DataFrame

        Returns:
            Dict mapping column names to their statistics
        """
        stats = {}

        for col_name in df.columns:
            col_stats = {
                "non_null_count": int(df[col_name].notna().sum()),
                "null_count": int(df[col_name].isna().sum()),
                "dtype": str(df[col_name].dtype)
            }

            # Get non-null values
            non_null = df[col_name].dropna()

            if len(non_null) == 0:
                stats[col_name] = col_stats
                continue

            # Numeric columns
            if pd.api.types.is_numeric_dtype(df[col_name]):
                col_stats["min"] = float(non_null.min())
                col_stats["max"] = float(non_null.max())
                col_stats["mean"] = float(non_null.mean())
                col_stats["median"] = float(non_null.median())
                col_stats["distinct_count"] = int(non_null.nunique())

            # String columns
            elif pd.api.types.is_string_dtype(df[col_name]) or df[col_name].dtype == 'object':
                try:
                    col_stats["distinct_count"] = int(non_null.nunique())
                    # Get top 10 most common values
                    top_values = non_null.value_counts().head(10).to_dict()
                    col_stats["top_values"] = {str(k): int(v) for k, v in top_values.items()}
                    # Sample values (first 5 unique)
                    col_stats["sample_values"] = [str(v) for v in non_null.unique()[:5]]
                except (TypeError, ValueError):
                    # Handle unhashable types (e.g., JSON/dict columns)
                    col_stats["data_type"] = "JSON"
                    col_stats["sample_values"] = [str(v)[:100] for v in non_null.head(3)]

            # Boolean columns
            elif pd.api.types.is_bool_dtype(df[col_name]):
                col_stats["true_count"] = int((non_null == True).sum())
                col_stats["false_count"] = int((non_null == False).sum())

            # Datetime columns
            elif pd.api.types.is_datetime64_any_dtype(df[col_name]):
                col_stats["min"] = str(non_null.min())
                col_stats["max"] = str(non_null.max())
                col_stats["distinct_count"] = int(non_null.nunique())

            stats[col_name] = col_stats

        return stats

    async def upload_csv(
        self,
        user_id: str,
        file_content: bytes,
        table_name: str,
        filename: str,
        max_rows: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Upload and process a CSV file.

        Args:
            user_id: User ID
            file_content: CSV file content as bytes
            table_name: User-provided table name
            filename: Original filename
            max_rows: Optional maximum rows to process

        Returns:
            Dict with dataset metadata

        Raises:
            ValueError: If CSV parsing fails or table already exists
        """
        logger.info(f"{self._log_prefix(user_id, table_name)} | Starting CSV upload")

        dynamic_table_name = None

        try:
            # Parse CSV
            try:
                # Try different encodings
                encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
                df = None
                for encoding in encodings:
                    try:
                        df = pd.read_csv(
                            io.BytesIO(file_content),
                            encoding=encoding,
                            nrows=max_rows
                        )
                        logger.info(f"{self._log_prefix(user_id, table_name)} | Parsed CSV with encoding: {encoding}")
                        break
                    except UnicodeDecodeError:
                        continue

                if df is None:
                    raise ValueError("Could not parse CSV with any supported encoding")

            except Exception as e:
                logger.error(f"{self._log_prefix(user_id, table_name)} | CSV parsing failed: {e}")
                raise ValueError(f"Failed to parse CSV: {str(e)}")

            if df.empty:
                raise ValueError("CSV file is empty")

            # Filter out 'embedding' columns (case-insensitive)
            embedding_cols = [col for col in df.columns if col.lower() == 'embedding']
            if embedding_cols:
                logger.info(f"{self._log_prefix(user_id, table_name)} | Removing {len(embedding_cols)} embedding column(s): {embedding_cols}")
                df = df.drop(columns=embedding_cols)

            if df.empty or len(df.columns) == 0:
                raise ValueError("CSV file has no valid columns after filtering")

            row_count = len(df)
            logger.info(f"{self._log_prefix(user_id, table_name)} | Parsed {row_count} rows, {len(df.columns)} columns")

            # Generate table name if not provided
            if not table_name or not table_name.strip():
                # Get sample data for context
                sample_data = None
                if not df.empty:
                    sample_data = df.iloc[0].to_dict()
                
                table_name = await self.generate_dataset_name(
                    user_id=user_id,
                    filename=filename,
                    column_names=list(df.columns),
                    sample_data=sample_data
                )
                logger.info(f"{self._log_prefix(user_id, table_name)} | Generated table name: {table_name}")
            else:
                table_name = table_name.strip()

            # Check if table name already exists for this user
            existing = await UserDatasetRepository.get_by_table_name(self.db, user_id, table_name)
            if existing:
                raise ValueError(f"Dataset name '{table_name}' already exists. Please choose a different name.")

            # Generate dynamic table name
            dynamic_table_name = generate_dynamic_table_name(user_id, table_name)
            logger.info(f"{self._log_prefix(user_id, table_name)} | Dynamic table name: {dynamic_table_name}")

            # Create dynamic table
            await create_dynamic_table(self.db, dynamic_table_name, df, if_exists='fail')
            await self.db.commit()

            # Insert data
            rows_inserted = await insert_dataframe_to_table(
                self.db,
                dynamic_table_name,
                df,
                if_exists='append'
            )
            await self.db.commit()

            logger.info(f"{self._log_prefix(user_id, table_name)} | Inserted {rows_inserted} rows")

            # Compute column statistics
            column_stats = self.compute_column_stats(df)
            logger.info(f"{self._log_prefix(user_id, table_name)} | Computed stats for {len(column_stats)} columns")

            # Generate EDA using LLM
            model_name = self._get_llm_model_name()
            eda_response = await self.eda_generator.generate_table_eda(
                table_name=dynamic_table_name,
                column_stats=column_stats,
                row_count=row_count,
                model=model_name
            )

            # Convert field metadata to dict for storage
            field_metadata_dict = [fm.model_dump() for fm in eda_response.field_metadata]

            # Create user dataset record
            user_dataset = await self.repository.create(
                db=self.db,
                user_id=user_id,
                origin=filename,
                table_name=table_name,
                row_count=row_count,
                description=eda_response.summary,
                meta={"field_metadata": field_metadata_dict}
            )
            await self.db.commit()

            logger.info(f"{self._log_prefix(user_id, table_name)} | Created user dataset record: {user_dataset.id}")

            return {
                "success": True,
                "dataset_id": user_dataset.id,
                "table_name": table_name,
                "dynamic_table_name": dynamic_table_name,
                "row_count": row_count,
                "column_count": len(df.columns),
                "description": eda_response.summary,
                "field_metadata": field_metadata_dict
            }

        except Exception as e:
            logger.error(f"{self._log_prefix(user_id, table_name)} | Upload failed: {e}", exc_info=True)
            
            # Cleanup: drop dynamic table if it was created
            # Note: We rollback first, then try to drop in a new transaction if needed
            await self.db.rollback()
            
            if dynamic_table_name:
                try:
                    # Try to drop the table in a new transaction
                    # Since we rolled back, we need to check if table was actually created
                    # (it might not have been if error happened early)
                    result = await self.db.execute(
                        text("""
                            SELECT EXISTS (
                                SELECT FROM information_schema.tables 
                                WHERE table_schema = 'public' 
                                AND table_name = :table_name
                            )
                        """),
                        {"table_name": dynamic_table_name}
                    )
                    if result.scalar():
                        await drop_dynamic_table(self.db, dynamic_table_name)
                        await self.db.commit()
                except Exception as cleanup_error:
                    logger.error(f"Failed to cleanup table {dynamic_table_name}: {cleanup_error}")
                    await self.db.rollback()
            
            raise

    async def get_dataset(self, dataset_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get dataset by ID (with user verification).

        Args:
            dataset_id: Dataset ID
            user_id: User ID for verification

        Returns:
            Dataset dict or None
        """
        dataset = await self.repository.get_by_id(self.db, dataset_id)
        if not dataset or dataset.user_id != user_id:
            return None

        dynamic_table_name = generate_dynamic_table_name(user_id, dataset.table_name)

        return {
            "id": dataset.id,
            "user_id": dataset.user_id,
            "origin": dataset.origin,
            "table_name": dataset.table_name,
            "dynamic_table_name": dynamic_table_name,
            "description": dataset.description,
            "row_count": dataset.row_count,
            "meta": dataset.meta,
            "created_at": dataset.created_at.isoformat() if dataset.created_at else None,
            "updated_at": dataset.updated_at.isoformat() if dataset.updated_at else None,
        }

    async def get_dataset_data(
        self,
        dataset_id: str,
        user_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get data from a dataset's dynamic table.
        
        Args:
            dataset_id: Dataset ID
            user_id: User ID for verification
            limit: Maximum number of rows to return
            offset: Number of rows to skip
            
        Returns:
            Dict with data rows and pagination info
        """
        dataset = await self.repository.get_by_id(self.db, dataset_id)
        if not dataset or dataset.user_id != user_id:
            return None
        
        dynamic_table_name = generate_dynamic_table_name(user_id, dataset.table_name)
        
        # Query data from dynamic table
        from sqlalchemy import text
        from sqlalchemy.exc import ProgrammingError
        
        try:
            # Get total count
            count_query = text(f'SELECT COUNT(*) FROM "{dynamic_table_name}"')
            count_result = await self.db.execute(count_query)
            total_rows = count_result.scalar()
            
            # Get paginated data
            data_query = text(f'SELECT * FROM "{dynamic_table_name}" LIMIT :limit OFFSET :offset')
            data_result = await self.db.execute(
                data_query,
                {"limit": limit, "offset": offset}
            )
        except ProgrammingError as e:
            # Table might not exist (e.g., if it was created before the fix)
            error_msg = str(e)
            if "does not exist" in error_msg.lower():
                logger.error(f"Table {dynamic_table_name} does not exist. Dataset may have been created with old naming convention.")
                raise ValueError(f"Table for dataset '{dataset.table_name}' does not exist. Please re-upload the dataset.")
            raise
        
        # Convert rows to dicts
        rows = []
        columns = data_result.keys()
        for row in data_result.fetchall():
            row_dict = {}
            for i, col in enumerate(columns):
                value = row[i]
                # Handle JSONB columns - parse if it's a string
                if isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                    try:
                        import json
                        value = json.loads(value)
                    except (json.JSONDecodeError, ValueError):
                        pass
                row_dict[col] = value
            rows.append(row_dict)
        
        return {
            "data": rows,
            "columns": list(columns),
            "total_rows": total_rows,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total_rows
        }

    async def list_datasets(self, user_id: str, limit: int = 50, offset: int = 0) -> list[Dict[str, Any]]:
        """
        List user's datasets.

        Args:
            user_id: User ID
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of dataset dicts
        """
        datasets = await self.repository.list_user_datasets(self.db, user_id, limit, offset)

        return [
            {
                "id": ds.id,
                "user_id": ds.user_id,
                "origin": ds.origin,
                "table_name": ds.table_name,
                "dynamic_table_name": generate_dynamic_table_name(ds.user_id, ds.table_name),
                "description": ds.description,
                "row_count": ds.row_count,
                "meta": ds.meta,
                "created_at": ds.created_at.isoformat() if ds.created_at else None,
                "updated_at": ds.updated_at.isoformat() if ds.updated_at else None,
            }
            for ds in datasets
        ]

