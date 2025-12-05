import asyncio
import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import pandas as pd
import numpy as np
from app.core.llm.lg_workflow.data.manager import DataManager
from app.core.llm.lg_workflow.tools.data_access import list_datasets_tool, get_dataset_data_tool, semantic_search_tool
from app.core.llm.lg_workflow.tools.analytics import clustering_tool, tfidf_tool, describe_tool
from app.core.llm.lg_workflow.tools.ml import trend_analysis_tool, product_gap_detection_tool

class TestDataTools(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Reset DataManager instances
        DataManager._instances = {}
        self.dm = DataManager.get_instance("default")
        
    @patch('app.core.llm.lg_workflow.data.manager.get_async_session')
    @patch('app.core.llm.lg_workflow.data.manager.UserDatasetService')
    async def test_list_datasets(self, mock_service_cls, mock_get_session):
        # Setup mock
        mock_db = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_db
        
        mock_service = mock_service_cls.return_value
        mock_service.list_datasets = AsyncMock(return_value=[
            {
                "id": "123",
                "table_name": "test_dataset",
                "row_count": 100,
                "description": "Test Description"
            }
        ])
        
        # Test DataManager
        result = await self.dm.list_datasets("user1")
        self.assertIn("test_dataset", result)
        
        # Test Tool (uses default session)
        tool_result = await list_datasets_tool.ainvoke({"user_id": "user1"})
        self.assertIn("test_dataset", tool_result)

    # ... (other tests similar updates if needed) ...

    async def test_save_artifact(self):
        # Test save_artifact directly
        df = pd.DataFrame({"col": [1, 2, 3]})
        artifact_name = await self.dm.save_artifact(df, "test_artifact", "Test Artifact Description", "user1")
        self.assertNotEqual(artifact_name, "ERR_UNSUPPORTED_TYPE")
        
        # Verify it's in local cache with description
        self.assertIn(artifact_name, self.dm._local_cache)
        cached_item = self.dm._local_cache[artifact_name]
        self.assertIsInstance(cached_item, tuple)
        self.assertEqual(cached_item[1], "Test Artifact Description")
        
        # Test get_dataset retrieves it
        retrieved_df = await self.dm.get_dataset(artifact_name, "user1")
        self.assertEqual(len(retrieved_df), 3)
        
        # Test get_metadata retrieves description
        meta = await self.dm.get_metadata(artifact_name, "user1")
        self.assertIn("Test Artifact Description", meta["description"])

    @patch('app.core.llm.lg_workflow.data.manager.UserDatasetRepository')
    @patch('app.core.llm.lg_workflow.data.manager.get_async_session')
    @patch('app.core.llm.lg_workflow.data.manager.UserDatasetService')
    async def test_ml_tools(self, mock_service_cls, mock_get_session, mock_repo_cls):
        # Setup mock
        mock_db = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_db
        
        # Mock the repository
        mock_dataset = MagicMock()
        mock_dataset.id = "123"
        mock_dataset.table_name = "test_table"
        mock_repo_cls.get_by_table_name = AsyncMock(return_value=mock_dataset)
        
        mock_service = mock_service_cls.return_value
        
        # Mock data for ML tools
        dates = pd.date_range(start='2023-01-01', periods=10, freq='D')
        df = pd.DataFrame({
            "date": dates,
            "value": np.arange(10),  # Perfect linear trend
            "text": ["foo"] * 10
        })
        mock_service.get_dataset_data = AsyncMock(return_value={"data": df.to_dict(orient="records")})
        
        # Test Trend Analysis
        trend_result = await trend_analysis_tool.ainvoke({
            "table_name": "test_table", 
            "date_column": "date", 
            "value_column": "value", 
            "user_id": "user1",
            "period": "D"
        })
        self.assertIn("increasing", trend_result)
        self.assertIn("slope", trend_result)
        
        # Test Product Gap Detection (requires __embedding__)
        # Create product-like data with embeddings
        product_df = pd.DataFrame({
            "name": ["Product A", "Product B", "Product C", "Product D", "Product E", "Product F"],
            "price": [10, 12, 15, 100, 110, 115],
            "category": ["A", "A", "A", "B", "B", "B"],
            "__embedding__": [
                [0.1, 0.2, 0.1], [0.11, 0.21, 0.09], [0.12, 0.19, 0.11],  # Cluster 1
                [0.8, 0.9, 0.85], [0.81, 0.88, 0.87], [0.79, 0.91, 0.83]  # Cluster 2
            ]
        })
        mock_service.get_dataset_data = AsyncMock(return_value={"data": product_df.to_dict(orient="records")})
        
        gap_result = await product_gap_detection_tool.ainvoke({
            "table_name": "test_table",
            "user_id": "user1",
            "min_cluster_size": 2,
            "eps": 0.3
        })
        self.assertIn("Product Gap Analysis", gap_result)
        self.assertIn("Clustered Products", gap_result)

    @patch('app.core.llm.lg_workflow.data.manager.UserDatasetRepository')
    @patch('app.core.llm.lg_workflow.data.manager.get_async_session')
    @patch('app.core.llm.lg_workflow.data.manager.UserDatasetService')
    async def test_analytics_tools(self, mock_service_cls, mock_get_session, mock_repo_cls):
        # Setup mock
        mock_db = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_db
        
        # Mock the repository
        mock_dataset = MagicMock()
        mock_dataset.id = "123"
        mock_dataset.table_name = "test_table"
        mock_dataset.description = "Test Description"
        mock_dataset.row_count = 100
        mock_dataset.field_metadata = [{"column_name": "col1", "data_type": "int", "description": "Column 1"}]
        mock_dataset.column_stats = {"col1": {"mean": 10}}
        mock_dataset.sample_data = [{"col1": 1}, {"col1": 2}]
        mock_repo_cls.get_by_table_name = AsyncMock(return_value=mock_dataset)
        
        mock_service = mock_service_cls.return_value
        df = pd.DataFrame({
            "val": [1, 2, 3, 4, 5, 1, 2, 3, 4, 5],
            "text": ["foo", "bar", "baz", "foo", "bar"] * 2
        })
        mock_service.get_dataset_data = AsyncMock(return_value={"data": df.to_dict(orient="records")})
        
        # Test Describe Tool - need to add table_name to mock dataset
        desc_result = await describe_tool.ainvoke({"table_name": "test_table", "user_id": "user1"})
        self.assertIn("Test Description", desc_result)
        
        # Test Clustering Tool
        # Mock update_dataset (DataManager method)
        # Since tools use DataManager.get_instance("default"), and we reset it in setUp,
        # we are testing against the same instance.
        
        cluster_result = await clustering_tool.ainvoke({"table_name": "test_table", "target_column": "val", "user_id": "user1"})
        self.assertIn("updated", cluster_result)
        
        # Verify it's in local cache of the default instance
        dm = DataManager.get_instance("default")
        self.assertIn("test_table", dm._local_cache)
        cached_item = dm._local_cache["test_table"]
        # Extract df from tuple
        if isinstance(cached_item, tuple):
            df, _ = cached_item
        else:
            df = cached_item
        self.assertIn("cluster", df.columns)

if __name__ == '__main__':
    unittest.main()
