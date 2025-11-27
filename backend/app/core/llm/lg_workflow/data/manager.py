import pandas as pd
from typing import Optional, Dict, Any
from app.services.user_dataset_service import UserDatasetService
from app.database.repositories.user_dataset import UserDatasetRepository
from app.database.session import get_async_session
from app.utils.logging import get_logger

logger = get_logger(__name__)

class DataManager:
    """
    Manages access to user datasets stored in the database.
    Uses table_name as the primary identifier for datasets.
    """
    _instances: Dict[str, 'DataManager'] = {}
    
    def __new__(cls, session_id: str = "default"):
        if session_id not in cls._instances:
            instance = super(DataManager, cls).__new__(cls)
            instance._local_cache = {}
            instance.session_id = session_id
            cls._instances[session_id] = instance
        return cls._instances[session_id]

    @classmethod
    def get_instance(cls, session_id: str = "default") -> 'DataManager':
        return cls(session_id)

    async def list_datasets(self, user_id: str) -> str:
        """Lists available datasets for the user."""
        async with get_async_session() as db:
            service = UserDatasetService(db)
            datasets = await service.list_datasets(user_id)
            
            if not datasets:
                return "No datasets found."
            
            # Format as a list for the LLM - emphasize table_name as the key identifier
            output = ["Available Datasets:"]
            for ds in datasets:
                table_name = ds['table_name']
                # Check if we have a local modified version
                status = " (Modified in session)" if table_name in self._local_cache else ""
                output.append(f"- Table: {table_name}, Rows: {ds['row_count']}, Description: {ds['description']}{status}")
            
            # Also list cached-only datasets (artifacts)
            for table_name, item in self._local_cache.items():
                # Handle both old (df only) and new (df, desc) formats
                if isinstance(item, tuple):
                    df, desc = item
                else:
                    df = item
                    desc = "Intermediate result"
                
                # If it's not in the main list (i.e. purely local artifact)
                if not any(d['table_name'] == table_name for d in datasets):
                     output.append(f"- Table: {table_name}, Rows: {len(df)}, Description: {desc} (Session Artifact)")

            return "\n".join(output)

    async def get_dataset(self, table_name: str, user_id: str) -> pd.DataFrame:
        """Retrieves a dataframe by table_name, checking local cache first."""
        # Check local cache first
        if table_name in self._local_cache:
            item = self._local_cache[table_name]
            # Handle tuple format
            if isinstance(item, tuple):
                df, _ = item
            else:
                df = item
                
            logger.info(f"DataManager[{self.session_id}]: Returning cached dataset {table_name}")
            return df

        async with get_async_session() as db:
            # Get dataset by table_name
            dataset = await UserDatasetRepository.get_by_table_name(db, table_name, user_id)
            if not dataset:
                return pd.DataFrame()  # Return empty DataFrame if dataset not found
            
            service = UserDatasetService(db)
            data_result = await service.get_dataset_data(str(dataset.id), user_id, limit=100_000)
            if not data_result or not data_result.get("data"):
                return pd.DataFrame()
                
            df = pd.DataFrame(data_result["data"])
            return df

    async def get_metadata(self, table_name: str, user_id: str) -> Dict[str, Any]:
        """Retrieves metadata for a dataset by table_name."""
        # Check local cache first for basic metadata
        local_meta = {}
        if table_name in self._local_cache:
            item = self._local_cache[table_name]
            if isinstance(item, tuple):
                df, desc = item
            else:
                df = item
                desc = "Intermediate result"
                
            local_meta = {
                "table_name": table_name,
                "row_count": len(df),
                "description": f"{desc} [Modified in current session]",
                "field_metadata": [{"column_name": col, "data_type": str(dtype), "description": ""} for col, dtype in df.dtypes.items()]
            }

        async with get_async_session() as db:
            dataset = await UserDatasetRepository.get_by_table_name(db, table_name, user_id)
            
            if not dataset:
                # If not in DB but in cache, return local meta
                if local_meta:
                    return local_meta
                return {}
            
            metadata = {
                "id": dataset.id,
                "table_name": dataset.table_name,
                "description": dataset.description,
                "row_count": dataset.row_count,
                "field_metadata": dataset.field_metadata,
                "column_stats": dataset.column_stats,
                "sample_data": dataset.sample_data,
            }
            
            # If in DB and in cache, merge
            if local_meta:
                metadata['row_count'] = local_meta['row_count']
                metadata['description'] = local_meta['description']
                
            return metadata

    async def semantic_search(self, table_name: str, query: str, user_id: str, top_n: int = 5) -> pd.DataFrame:
        """
        Performs semantic search on a dataset by table_name.
        WARNING: This currently only works on the DB version of the dataset.
        """
        async with get_async_session() as db:
            # Verify the table exists for this user
            dataset = await UserDatasetRepository.get_by_table_name(db, table_name, user_id)
            if not dataset:
                return pd.DataFrame()
            
            service = UserDatasetService(db)
            try:
                results = await service.get_dataset_data_from_semantic_search(query, table_name, top_n)
                return results
            except AttributeError:
                logger.error(f"Semantic search method not found on service.")
                return pd.DataFrame()

    async def update_dataset(self, table_name: str, df: pd.DataFrame, user_id: str) -> bool:
        """
        Updates an existing dataset in the local cache ONLY by table_name.
        Does NOT persist to database.
        """
        try:
            # Preserve description if it exists
            desc = "Updated dataset"
            if table_name in self._local_cache:
                item = self._local_cache[table_name]
                if isinstance(item, tuple):
                    _, desc = item
            
            self._local_cache[table_name] = (df, desc)
            logger.info(f"DataManager[{self.session_id}]: Updated dataset {table_name} in local cache. Rows: {len(df)}")
            return True
        except Exception as e:
            logger.error(f"DataManager[{self.session_id}]: Failed to update local cache: {e}")
            return False

    async def save_artifact(self, data: Any, artifact_name: str, description: str, user_id: str) -> str:
        """
        Saves an intermediate result to the local cache with a custom name.
        Returns the artifact name (table_name).
        """
        if isinstance(data, pd.DataFrame):
            # Use the provided artifact_name or generate one
            if not artifact_name:
                import uuid
                artifact_name = f"artifact_{uuid.uuid4().hex[:8]}"
            
            # Store tuple of (dataframe, description)
            self._local_cache[artifact_name] = (data, description)
            logger.info(f"DataManager[{self.session_id}]: Saved artifact {artifact_name} to local cache. Desc: {description}")
            return artifact_name
        
        return "ERR_UNSUPPORTED_TYPE"
