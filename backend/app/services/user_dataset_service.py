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

from app.core.llm.eda_generator import EDAGenerator
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
        Uses normalized column names (same as the database table).

        Args:
            df: Pandas DataFrame with normalized column names

        Returns:
            Dict mapping normalized column names to their statistics
        """
        from app.utils.dynamic_tables import sanitize_column_name
        
        stats = {}

        for col_name in df.columns:
            # Use normalized column name for stats
            normalized_col_name = sanitize_column_name(col_name)
            
            col_stats = {
                "non_null_count": int(df[col_name].notna().sum()),
                "null_count": int(df[col_name].isna().sum()),
                "dtype": str(df[col_name].dtype)
            }

            # Get non-null values
            non_null = df[col_name].dropna()

            if len(non_null) == 0:
                stats[normalized_col_name] = col_stats
                continue

            # Try to detect and convert date strings to datetime
            if pd.api.types.is_string_dtype(df[col_name]) or df[col_name].dtype == 'object':
                # Sample a few values to check if they're dates
                sample_values = non_null.head(10)
                date_like_count = 0
                
                for val in sample_values:
                    val_str = str(val).strip()
                    # Check for common date patterns
                    if re.match(r'\d{4}-\d{2}-\d{2}', val_str) or \
                       re.match(r'\d{2}/\d{2}/\d{4}', val_str) or \
                       re.match(r'\d{2}-\d{2}-\d{4}', val_str) or \
                       re.match(r'\d{4}/\d{2}/\d{2}', val_str):
                        date_like_count += 1
                
                # If majority look like dates, try to convert
                if date_like_count >= len(sample_values) * 0.7:
                    try:
                        converted = pd.to_datetime(non_null, errors='coerce')
                        # If most values converted successfully, use datetime stats
                        if converted.notna().sum() >= len(non_null) * 0.7:
                            non_null = converted.dropna()
                            col_stats["dtype"] = "datetime64[ns]"
                            col_stats["min"] = str(non_null.min())
                            col_stats["max"] = str(non_null.max())
                            col_stats["distinct_count"] = int(non_null.nunique())
                            stats[normalized_col_name] = col_stats
                            continue
                    except Exception:
                        pass  # Fall through to string handling

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

            stats[normalized_col_name] = col_stats

        return stats

    async def _add_embeddings_to_table(
        self,
        df: pd.DataFrame,
        dynamic_table_name: str,
        vector_store_columns: Dict[str, Any],
        user_id: str
    ) -> None:
        """
        Add __embedding__ column to the dynamic table with generated embeddings.

        Args:
            df: Original DataFrame with the data
            dynamic_table_name: Name of the dynamic table
            vector_store_columns: Dict with main_column and alternative_columns
            user_id: User ID for logging
        """
        from app.services.embedding_service import get_embedding_service
        
        main_column = vector_store_columns.get("main_column")
        alternative_columns = vector_store_columns.get("alternative_columns", [])
        
        if not main_column:
            logger.warning(f"{self._log_prefix(user_id, dynamic_table_name)} | No main_column specified for embeddings")
            return
        
        logger.info(f"{self._log_prefix(user_id, dynamic_table_name)} | Generating embeddings from main_column: {main_column}, alternatives: {alternative_columns}")
        
        # Build text for embedding from main column and alternatives
        texts_to_embed = []
        for _, row in df.iterrows():
            text_parts = []
            
            # Add main column
            if main_column in row and pd.notna(row[main_column]):
                text_parts.append(str(row[main_column]))
            
            # Add alternative columns
            for alt_col in alternative_columns:
                if alt_col in row and pd.notna(row[alt_col]):
                    text_parts.append(str(row[alt_col]))
            
            # Combine all parts
            combined_text = " | ".join(text_parts) if text_parts else ""
            texts_to_embed.append(combined_text)
        
        # Generate embeddings in batches
        embedding_service = get_embedding_service()
        embeddings = await embedding_service.generate_embeddings_batch(texts_to_embed, batch_size=2000)
        
        logger.info(f"{self._log_prefix(user_id, dynamic_table_name)} | Generated {len(embeddings)} embeddings")
        
        # Add __embedding__ column to the table
        # First, check if column exists and add it if not
        try:
            # Check if __embedding__ column exists
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = :table_name 
                AND column_name = '__embedding__'
            """)
            result = await self.db.execute(check_query, {"table_name": dynamic_table_name})
            column_exists = result.fetchone() is not None
            
            if not column_exists:
                # Add the vector column
                embedding_dim = embedding_service.get_dimensions()
                alter_query = text(f'ALTER TABLE "{dynamic_table_name}" ADD COLUMN __embedding__ vector({embedding_dim})')
                await self.db.execute(alter_query)
                await self.db.commit()
                logger.info(f"{self._log_prefix(user_id, dynamic_table_name)} | Added __embedding__ column")
            
            # Update each row with its embedding
            # Get the primary key or row identifier
            # First, get all rows with their IDs
            select_query = text(f'SELECT * FROM "{dynamic_table_name}"')
            result = await self.db.execute(select_query)
            rows = result.fetchall()
            columns = list(result.keys())
            
            # Find a unique identifier column (prefer 'id', otherwise use first column)
            id_column = None
            if 'id' in columns:
                id_column = 'id'
            else:
                # Use the first column as identifier
                id_column = columns[0]
            
            logger.info(f"{self._log_prefix(user_id, dynamic_table_name)} | Using '{id_column}' as identifier for embedding updates")
            
            # Update embeddings for each row
            id_idx = columns.index(id_column)
            for i, (row, embedding) in enumerate(zip(rows, embeddings)):
                if embedding is None:
                    logger.warning(f"{self._log_prefix(user_id, dynamic_table_name)} | Skipping row {i} - no embedding generated")
                    continue
                
                # Get the identifier value
                id_value = row[id_idx]
                
                # Convert embedding to PostgreSQL vector format
                embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
                
                # Update the row - use direct string formatting for asyncpg compatibility
                update_query = text(
                    f'UPDATE "{dynamic_table_name}" '
                    f'SET __embedding__ = \'{embedding_str}\'::vector '
                    f'WHERE "{id_column}" = :id_value'
                )
                await self.db.execute(update_query, {"id_value": id_value})
            
            await self.db.commit()
            logger.info(f"{self._log_prefix(user_id, dynamic_table_name)} | Successfully updated {len([e for e in embeddings if e is not None])} embeddings")
            
        except Exception as e:
            logger.error(f"{self._log_prefix(user_id, dynamic_table_name)} | Failed to add embeddings: {e}", exc_info=True)
            await self.db.rollback()
            raise

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

            # Normalize column names BEFORE any processing
            from app.utils.dynamic_tables import sanitize_column_name
            original_columns = list(df.columns)
            normalized_columns = [sanitize_column_name(col) for col in df.columns]
            
            # Create mapping for logging
            column_mapping = {orig: norm for orig, norm in zip(original_columns, normalized_columns) if orig != norm}
            if column_mapping:
                logger.info(f"{self._log_prefix(user_id, table_name)} | Normalized {len(column_mapping)} column names: {column_mapping}")
            
            # Rename columns in DataFrame
            df.columns = normalized_columns

            # Generate table name if not provided
            if not table_name or not table_name.strip():
                # Get sample data for context (using original column names for context)
                sample_data = None
                if not df.empty:
                    sample_data = df.iloc[0].to_dict()
                
                table_name = await self.generate_dataset_name(
                    user_id=user_id,
                    filename=filename,
                    column_names=original_columns,  # Use original names for better context
                    sample_data=sample_data
                )
                logger.info(f"{self._log_prefix(user_id, table_name)} | Generated table name: {table_name}")
            else:
                table_name = table_name.strip()

            # Generate dynamic table name
            dynamic_table_name = generate_dynamic_table_name(user_id, table_name)
            logger.info(f"{self._log_prefix(user_id, table_name)} | Dynamic table name: {dynamic_table_name}")

            # Check if table name already exists for this user
            existing = await UserDatasetRepository.get_by_table_name(self.db, dynamic_table_name, user_id)
            if existing:
                raise ValueError(f"Dataset name '{table_name}' already exists. Please choose a different name.")

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

            logger.info(f"{self._log_prefix(user_id, dynamic_table_name)} | Inserted {rows_inserted} rows")

            # Compute column statistics
            column_stats = self.compute_column_stats(df)
            logger.info(f"{self._log_prefix(user_id, dynamic_table_name)} | Computed stats for {len(column_stats)} columns")

            # Prepare sample data (first 5 rows)
            sample_data = df.head(5).to_dict(orient='records')

            # Generate EDA using LLM
            model_name = self._get_llm_model_name()
            eda_response = await self.eda_generator.generate_table_eda(
                table_name=dynamic_table_name,
                column_stats=column_stats,
                row_count=row_count,
                sample_data=sample_data,
                model=model_name,
                db=self.db,
                user_id=user_id
            )

            # Generate embeddings if vector_store_columns are identified
            embeddings_generated = False
            vector_store_columns = eda_response.get("vector_store_columns", {})
            if vector_store_columns and vector_store_columns.get("main_column"):
                logger.info(f"{self._log_prefix(user_id, dynamic_table_name)} | Generating embeddings for vector store")
                await self._add_embeddings_to_table(
                    df=df,
                    dynamic_table_name=dynamic_table_name,
                    vector_store_columns=vector_store_columns,
                    user_id=user_id
                )
                await self.db.commit()
                embeddings_generated = True
                logger.info(f"{self._log_prefix(user_id, dynamic_table_name)} | Embeddings generated and stored")

            # Create user dataset record with all EDA data - store dynamic_table_name as table_name
            user_dataset = await self.repository.create(
                db=self.db,
                user_id=user_id,
                origin=filename,
                table_name=dynamic_table_name,  # Store the full dynamic table name
                row_count=row_count,
                description=eda_response["summary"],
                field_metadata=eda_response["field_metadata"],
                column_stats=eda_response["column_stats"],
                sample_data=eda_response["sample_data"],
                vector_store_columns=eda_response["vector_store_columns"],
                meta={}
            )
            await self.db.commit()

            logger.info(f"{self._log_prefix(user_id, dynamic_table_name)} | Created user dataset record: {user_dataset.id}")

            return {
                "success": True,
                "dataset_id": user_dataset.id,
                "table_name": dynamic_table_name,
                "row_count": row_count,
                "column_count": len(df.columns),
                "description": eda_response["summary"],
                "field_metadata": eda_response["field_metadata"],
                "column_stats": eda_response["column_stats"],
                "sample_data": eda_response["sample_data"],
                "vector_store_columns": eda_response["vector_store_columns"],
                "embeddings_generated": embeddings_generated
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

        return {
            "id": dataset.id,
            "user_id": dataset.user_id,
            "origin": dataset.origin,
            "table_name": dataset.table_name,
            "description": dataset.description,
            "row_count": dataset.row_count,
            "field_metadata": dataset.field_metadata,
            "column_stats": dataset.column_stats,
            "sample_data": dataset.sample_data,
            "vector_store_columns": dataset.vector_store_columns,
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
        
        table_name = dataset.table_name
        
        # Query data from table
        from sqlalchemy import text
        from sqlalchemy.exc import ProgrammingError
        
        try:
            # Get total count
            count_query = text(f'SELECT COUNT(*) FROM "{table_name}"')
            count_result = await self.db.execute(count_query)
            total_rows = count_result.scalar()
            
            # Get paginated data
            data_query = text(f'SELECT * FROM "{table_name}" LIMIT :limit OFFSET :offset')
            data_result = await self.db.execute(
                data_query,
                {"limit": limit, "offset": offset}
            )
        except ProgrammingError as e:
            # Table might not exist
            error_msg = str(e)
            if "does not exist" in error_msg.lower():
                logger.error(f"Table {table_name} does not exist.")
                raise ValueError(f"Table '{table_name}' does not exist. Please re-upload the dataset.")
            raise
        
        # Convert rows to dicts, filtering out __embedding__ column
        rows = []
        columns = [col for col in data_result.keys() if col != '__embedding__']
        all_columns = list(data_result.keys())
        
        for row in data_result.fetchall():
            row_dict = {}
            for i, col in enumerate(all_columns):
                # Skip __embedding__ column
                if col == '__embedding__':
                    continue
                    
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
            "columns": columns,
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
                "description": ds.description,
                "row_count": ds.row_count,
                "field_metadata": ds.field_metadata,
                "column_stats": ds.column_stats,
                "sample_data": ds.sample_data,
                "vector_store_columns": ds.vector_store_columns,
                "meta": ds.meta,
                "created_at": ds.created_at.isoformat() if ds.created_at else None,
                "updated_at": ds.updated_at.isoformat() if ds.updated_at else None,
            }
            for ds in datasets
        ]

    async def get_dataset_data_from_sql(self, sql_query: str) -> pd.DataFrame:
        """
        Execute a SQL query and return the results as a pandas DataFrame.
        Filters out __embedding__ column from results.
        
        Args:
            sql_query: SQL query to execute
            
        Returns:
            Pandas DataFrame with query results (without __embedding__ column)
            
        Raises:
            ValueError: If query execution fails
        """
        logger.info(f"{self._log_prefix()} | Executing SQL query")
        
        try:
            # Execute query using async SQLAlchemy
            result = await self.db.execute(text(sql_query))
            rows = result.fetchall()
            
            # Convert to DataFrame
            if rows:
                df = pd.DataFrame(rows, columns=result.keys())
                # Drop __embedding__ column if it exists
                if '__embedding__' in df.columns:
                    df = df.drop(columns=['__embedding__'])
            else:
                df = pd.DataFrame()
            
            logger.info(f"{self._log_prefix()} | Query returned {len(df)} rows")
            return df
        except Exception as e:
            logger.error(f"{self._log_prefix()} | SQL query failed: {e}", exc_info=True)
            raise ValueError(f"Failed to execute SQL query: {str(e)}")

    async def get_dataset_data_from_semantic_search(self, query: str, dataset_name: str, top_n: int = -1) -> pd.DataFrame:
        """
        Perform semantic search on a dataset and return the results as a pandas DataFrame.
        
        Args:
            query: Search query text
            dataset_name: Name of the dataset to search on
            top_n: Maximum number of results to return (default: -1 for all results)
            
        Returns:
            Pandas DataFrame with search results
        """
        try:
            from app.services.embedding_service import get_embedding_service
            # Generate embedding for the query
            embedding_service = get_embedding_service()
            embedding_vector = await embedding_service.generate_embedding(query)
            
            # Convert embedding to string format for PostgreSQL
            embedding_str = "[" + ",".join(str(x) for x in embedding_vector) + "]"
            top_n_str = "" if top_n == -1 else f"LIMIT {top_n};"
            sql_query = f"""
            SELECT
                *,
                1 - (__embedding__ <=> '{embedding_str}'::vector) AS __similarity_score__
            FROM {dataset_name}
            ORDER BY __similarity_score__
            {top_n_str}
            """
            return await self.get_dataset_data_from_sql(sql_query)
        except Exception as e:
            logger.error(f"Failed to get dataset data from semantic search: {e}", exc_info=True)
            raise ValueError(f"Failed to get dataset data from semantic search: {str(e)}")
    
    async def get_dataset_data_from_semantic_search_from_sql(self, sql_query: str, query: str, dataset_name: str, top_n: int = -1) -> pd.DataFrame:
        """
        Perform semantic search on a dataset using a SQL query and return the results as a pandas DataFrame.
        
        Args:
            sql_query: SQL query to execute (set the embedding vector as [PLACEHOLDER_QUERY_VECTOR])
            query: Search query text
            dataset_name: Name of the dataset to search on
            top_n: Maximum number of results to return (default: -1 for all results)
            
        Returns:
            Pandas DataFrame with search results
        """
        try:
            from app.services.embedding_service import get_embedding_service
            # Generate embedding for the query
            embedding_service = get_embedding_service()
            embedding_vector = await embedding_service.generate_embedding(query)
            
            # Convert embedding to string format for PostgreSQL
            embedding_str = "[" + ",".join(str(x) for x in embedding_vector) + "]"
            sql_query = sql_query.replace("[PLACEHOLDER_QUERY_VECTOR]", embedding_str)
            return await self.get_dataset_data_from_sql(sql_query)
        except Exception as e:
            logger.error(f"Failed to get dataset data from semantic search: {e}", exc_info=True)
            raise ValueError(f"Failed to get dataset data from semantic search: {str(e)}")

    async def delete_dataset(self, dataset_id: str, user_id: str) -> bool:
        """
        Delete a user dataset and its associated dynamic table.
        
        Args:
            dataset_id: ID of the dataset to delete
            user_id: ID of the user who owns the dataset
            
        Returns:
            True if deletion was successful
            
        Raises:
            ValueError: If dataset not found or user doesn't have permission
        """
        logger.info(f"{self._log_prefix(user_id)} | Deleting dataset {dataset_id}")
        
        # Get the dataset to verify ownership and get table name
        dataset = await self.repository.get_by_id(self.db, dataset_id)
        
        if not dataset:
            logger.warning(f"{self._log_prefix(user_id)} | Dataset {dataset_id} not found")
            raise ValueError("Dataset not found")
        
        if dataset.user_id != user_id:
            logger.warning(f"{self._log_prefix(user_id)} | User does not own dataset {dataset_id}")
            raise ValueError("You do not have permission to delete this dataset")
        
        table_name = dataset.table_name
        
        try:
            # Drop the dynamic table first
            logger.info(f"{self._log_prefix(user_id)} | Dropping dynamic table {table_name}")
            await drop_dynamic_table(self.db, table_name)
            
            # Delete the database record
            logger.info(f"{self._log_prefix(user_id)} | Deleting dataset record {dataset_id}")
            await self.repository.delete(self.db, dataset_id)
            
            # Commit the transaction
            await self.db.commit()
            
            logger.info(f"{self._log_prefix(user_id)} | Successfully deleted dataset {dataset_id} and table {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"{self._log_prefix(user_id)} | Failed to delete dataset {dataset_id}: {e}", exc_info=True)
            await self.db.rollback()
            raise ValueError(f"Failed to delete dataset: {str(e)}")
