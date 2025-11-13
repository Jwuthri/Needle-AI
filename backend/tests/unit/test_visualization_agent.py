"""
Unit tests for the Visualization Agent.

Tests visualization generation, chart types, data validation, and metadata tracking.
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from app.core.llm.workflow.agents.visualization import VisualizationAgent
from app.models.workflow import ExecutionContext, VisualizationResult


@pytest.fixture
def visualization_agent(tmp_path):
    """Create a VisualizationAgent instance with temporary output directory."""
    output_dir = tmp_path / "visualizations"
    return VisualizationAgent(output_dir=str(output_dir))


@pytest.fixture
def mock_context():
    """Create a mock ExecutionContext."""
    return ExecutionContext(
        user_id="test_user_123",
        session_id="session_456",
        message_id="msg_789",
        query="Test query"
    )


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return AsyncMock()


class TestVisualizationAgentInitialization:
    """Test VisualizationAgent initialization."""
    
    def test_initialization_creates_output_directory(self, tmp_path):
        """Test that initialization creates the output directory."""
        output_dir = tmp_path / "test_viz"
        agent = VisualizationAgent(output_dir=str(output_dir))
        
        assert agent.output_dir.exists()
        assert agent.output_dir.is_dir()
    
    def test_initialization_with_stream_callback(self, tmp_path):
        """Test initialization with stream callback."""
        callback = AsyncMock()
        agent = VisualizationAgent(
            output_dir=str(tmp_path),
            stream_callback=callback
        )
        
        assert agent.stream_callback == callback


class TestBarChartGeneration:
    """Test bar chart generation."""
    
    @pytest.mark.asyncio
    async def test_generate_bar_chart_success(self, visualization_agent, mock_context, mock_db):
        """Test successful bar chart generation."""
        data = {
            "x": ["Category A", "Category B", "Category C"],
            "y": [10, 25, 15],
            "name": "Test Data"
        }
        
        with patch("plotly.graph_objects.Figure.write_image"):
            result = await visualization_agent.generate_visualization(
                data=data,
                chart_type="bar",
                title="Test Bar Chart",
                labels={"x": "Categories", "y": "Values"},
                context=mock_context,
                db=mock_db,
                step_order=1
            )
        
        assert isinstance(result, VisualizationResult)
        assert result.chart_type == "bar"
        assert result.title == "Test Bar Chart"
        assert "/static/visualizations/" in result.filepath
        assert result.metadata["data_points"] == 3
    
    @pytest.mark.asyncio
    async def test_generate_bar_chart_with_custom_color(self, visualization_agent):
        """Test bar chart generation with custom color."""
        data = {
            "x": ["A", "B"],
            "y": [5, 10],
            "color": "#FF5733"
        }
        
        with patch("plotly.graph_objects.Figure.write_image"):
            result = await visualization_agent.generate_visualization(
                data=data,
                chart_type="bar",
                title="Custom Color Bar Chart"
            )
        
        assert result.chart_type == "bar"


class TestLineChartGeneration:
    """Test line chart generation."""
    
    @pytest.mark.asyncio
    async def test_generate_line_chart_success(self, visualization_agent):
        """Test successful line chart generation."""
        data = {
            "x": ["Jan", "Feb", "Mar", "Apr"],
            "y": [10, 15, 13, 20],
            "name": "Monthly Trend"
        }
        
        with patch("plotly.graph_objects.Figure.write_image"):
            result = await visualization_agent.generate_visualization(
                data=data,
                chart_type="line",
                title="Trend Over Time",
                labels={"x": "Month", "y": "Value"}
            )
        
        assert result.chart_type == "line"
        assert result.title == "Trend Over Time"
        assert result.metadata["data_points"] == 4


class TestPieChartGeneration:
    """Test pie chart generation."""
    
    @pytest.mark.asyncio
    async def test_generate_pie_chart_success(self, visualization_agent):
        """Test successful pie chart generation."""
        data = {
            "labels": ["Positive", "Neutral", "Negative"],
            "values": [60, 25, 15]
        }
        
        with patch("plotly.graph_objects.Figure.write_image"):
            result = await visualization_agent.generate_visualization(
                data=data,
                chart_type="pie",
                title="Sentiment Distribution"
            )
        
        assert result.chart_type == "pie"
        assert result.title == "Sentiment Distribution"
        assert result.metadata["data_points"] == 3
    
    @pytest.mark.asyncio
    async def test_generate_pie_chart_with_custom_colors(self, visualization_agent):
        """Test pie chart with custom colors."""
        data = {
            "labels": ["A", "B"],
            "values": [70, 30],
            "colors": ["#FF6B6B", "#4ECDC4"]
        }
        
        with patch("plotly.graph_objects.Figure.write_image"):
            result = await visualization_agent.generate_visualization(
                data=data,
                chart_type="pie",
                title="Custom Colors Pie"
            )
        
        assert result.chart_type == "pie"


class TestScatterChartGeneration:
    """Test scatter plot generation."""
    
    @pytest.mark.asyncio
    async def test_generate_scatter_chart_success(self, visualization_agent):
        """Test successful scatter plot generation."""
        data = {
            "x": [1, 2, 3, 4, 5],
            "y": [2, 4, 3, 5, 6],
            "size": 12
        }
        
        with patch("plotly.graph_objects.Figure.write_image"):
            result = await visualization_agent.generate_visualization(
                data=data,
                chart_type="scatter",
                title="Correlation Plot",
                labels={"x": "Variable X", "y": "Variable Y"}
            )
        
        assert result.chart_type == "scatter"
        assert result.title == "Correlation Plot"


class TestHeatmapGeneration:
    """Test heatmap generation."""
    
    @pytest.mark.asyncio
    async def test_generate_heatmap_success(self, visualization_agent):
        """Test successful heatmap generation."""
        data = {
            "z": [[1, 2, 3], [4, 5, 6], [7, 8, 9]],
            "x": ["A", "B", "C"],
            "y": ["Row 1", "Row 2", "Row 3"],
            "colorscale": "Viridis"
        }
        
        with patch("plotly.graph_objects.Figure.write_image"):
            result = await visualization_agent.generate_visualization(
                data=data,
                chart_type="heatmap",
                title="Correlation Heatmap",
                labels={"x": "Features", "y": "Samples"}
            )
        
        assert result.chart_type == "heatmap"
        assert result.title == "Correlation Heatmap"
        assert result.metadata["data_points"] == 3


class TestDataValidation:
    """Test data validation."""
    
    @pytest.mark.asyncio
    async def test_invalid_chart_type(self, visualization_agent):
        """Test that invalid chart type raises ValueError."""
        data = {"x": [1, 2], "y": [3, 4]}
        
        with pytest.raises(ValueError, match="Unsupported chart type"):
            await visualization_agent.generate_visualization(
                data=data,
                chart_type="invalid_type",
                title="Test"
            )
    
    @pytest.mark.asyncio
    async def test_missing_x_data_for_bar_chart(self, visualization_agent):
        """Test that missing x data raises ValueError."""
        data = {"y": [1, 2, 3]}
        
        with pytest.raises(ValueError, match="requires 'x' and 'y' data"):
            await visualization_agent.generate_visualization(
                data=data,
                chart_type="bar",
                title="Test"
            )
    
    @pytest.mark.asyncio
    async def test_mismatched_x_y_lengths(self, visualization_agent):
        """Test that mismatched x and y lengths raise ValueError."""
        data = {"x": [1, 2], "y": [3, 4, 5]}
        
        with pytest.raises(ValueError, match="must have same length"):
            await visualization_agent.generate_visualization(
                data=data,
                chart_type="bar",
                title="Test"
            )
    
    @pytest.mark.asyncio
    async def test_empty_data(self, visualization_agent):
        """Test that empty data raises ValueError."""
        data = {"x": [], "y": []}
        
        with pytest.raises(ValueError, match="requires at least one data point"):
            await visualization_agent.generate_visualization(
                data=data,
                chart_type="bar",
                title="Test"
            )
    
    @pytest.mark.asyncio
    async def test_pie_chart_missing_labels(self, visualization_agent):
        """Test that pie chart without labels raises ValueError."""
        data = {"values": [1, 2, 3]}
        
        with pytest.raises(ValueError, match="requires 'labels' and 'values'"):
            await visualization_agent.generate_visualization(
                data=data,
                chart_type="pie",
                title="Test"
            )
    
    @pytest.mark.asyncio
    async def test_heatmap_missing_z_data(self, visualization_agent):
        """Test that heatmap without z data raises ValueError."""
        data = {"x": [1, 2], "y": [3, 4]}
        
        with pytest.raises(ValueError, match="requires 'z' data"):
            await visualization_agent.generate_visualization(
                data=data,
                chart_type="heatmap",
                title="Test"
            )


class TestFilePathGeneration:
    """Test file path generation."""
    
    @pytest.mark.asyncio
    async def test_unique_filenames(self, visualization_agent):
        """Test that each visualization gets a unique filename."""
        data = {"x": [1, 2], "y": [3, 4]}
        
        with patch("plotly.graph_objects.Figure.write_image"):
            result1 = await visualization_agent.generate_visualization(
                data=data,
                chart_type="bar",
                title="Chart 1"
            )
            
            result2 = await visualization_agent.generate_visualization(
                data=data,
                chart_type="bar",
                title="Chart 2"
            )
        
        assert result1.filepath != result2.filepath
        assert result1.metadata["viz_id"] != result2.metadata["viz_id"]
    
    @pytest.mark.asyncio
    async def test_user_specific_subdirectory(self, visualization_agent, mock_context):
        """Test that visualizations are saved in user-specific subdirectories."""
        data = {"x": [1, 2], "y": [3, 4]}
        
        with patch("plotly.graph_objects.Figure.write_image"):
            result = await visualization_agent.generate_visualization(
                data=data,
                chart_type="bar",
                title="User Chart",
                context=mock_context
            )
        
        assert f"user_{mock_context.user_id}" in result.filepath
    
    @pytest.mark.asyncio
    async def test_safe_filename_from_title(self, visualization_agent):
        """Test that special characters in title are handled safely."""
        data = {"x": [1, 2], "y": [3, 4]}
        
        with patch("plotly.graph_objects.Figure.write_image"):
            result = await visualization_agent.generate_visualization(
                data=data,
                chart_type="bar",
                title="Chart with Special!@#$%^&*() Characters"
            )
        
        # Filename should not contain special characters
        assert "!" not in result.metadata["filename"]
        assert "@" not in result.metadata["filename"]


class TestMetadataTracking:
    """Test metadata tracking in Chat Message Steps."""
    
    @pytest.mark.asyncio
    async def test_metadata_tracked_in_chat_message_steps(self, visualization_agent, mock_context, mock_db):
        """Test that visualization metadata is tracked in Chat Message Steps."""
        data = {"x": [1, 2], "y": [3, 4]}
        
        with patch("plotly.graph_objects.Figure.write_image"), \
             patch("app.database.repositories.chat_message_step.ChatMessageStepRepository.create") as mock_create:
            
            await visualization_agent.generate_visualization(
                data=data,
                chart_type="bar",
                title="Tracked Chart",
                context=mock_context,
                db=mock_db,
                step_order=5
            )
            
            # Verify ChatMessageStepRepository.create was called
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args.kwargs
            
            assert call_kwargs["message_id"] == mock_context.message_id
            assert call_kwargs["agent_name"] == "visualization"
            assert call_kwargs["step_order"] == 5
            assert "Generated bar chart" in call_kwargs["thought"]
            assert call_kwargs["structured_output"]["chart_type"] == "bar"
            assert call_kwargs["structured_output"]["title"] == "Tracked Chart"
    
    @pytest.mark.asyncio
    async def test_error_tracked_in_chat_message_steps(self, visualization_agent, mock_context, mock_db):
        """Test that visualization errors are tracked in Chat Message Steps."""
        data = {"x": [1, 2], "y": [3, 4]}
        
        with patch("plotly.graph_objects.Figure.write_image", side_effect=Exception("Write error")), \
             patch("app.database.repositories.chat_message_step.ChatMessageStepRepository.create") as mock_create:
            
            with pytest.raises(Exception, match="Write error"):
                await visualization_agent.generate_visualization(
                    data=data,
                    chart_type="bar",
                    title="Error Chart",
                    context=mock_context,
                    db=mock_db,
                    step_order=3
                )
            
            # Verify error was tracked
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args.kwargs
            
            assert "Failed to generate" in call_kwargs["thought"]


class TestStreamingEvents:
    """Test streaming event emission."""
    
    @pytest.mark.asyncio
    async def test_emits_step_start_event(self, tmp_path):
        """Test that step start event is emitted."""
        callback = AsyncMock()
        agent = VisualizationAgent(
            output_dir=str(tmp_path),
            stream_callback=callback
        )
        
        data = {"x": [1, 2], "y": [3, 4]}
        
        with patch("plotly.graph_objects.Figure.write_image"):
            await agent.generate_visualization(
                data=data,
                chart_type="bar",
                title="Test Chart"
            )
        
        # Check that step_start event was emitted
        calls = callback.call_args_list
        start_event = calls[0][0][0]
        
        assert start_event["event_type"] == "agent_step_start"
        assert start_event["data"]["agent_name"] == "visualization"
        assert start_event["data"]["chart_type"] == "bar"
    
    @pytest.mark.asyncio
    async def test_emits_step_complete_event(self, tmp_path):
        """Test that step complete event is emitted."""
        callback = AsyncMock()
        agent = VisualizationAgent(
            output_dir=str(tmp_path),
            stream_callback=callback
        )
        
        data = {"x": [1, 2], "y": [3, 4]}
        
        with patch("plotly.graph_objects.Figure.write_image"):
            await agent.generate_visualization(
                data=data,
                chart_type="line",
                title="Test Chart"
            )
        
        # Check that step_complete event was emitted
        calls = callback.call_args_list
        complete_event = calls[1][0][0]
        
        assert complete_event["event_type"] == "agent_step_complete"
        assert complete_event["data"]["success"] is True
        assert complete_event["data"]["chart_type"] == "line"
    
    @pytest.mark.asyncio
    async def test_emits_error_event_on_failure(self, tmp_path):
        """Test that error event is emitted on failure."""
        callback = AsyncMock()
        agent = VisualizationAgent(
            output_dir=str(tmp_path),
            stream_callback=callback
        )
        
        data = {"x": [1, 2], "y": [3, 4]}
        
        with patch("plotly.graph_objects.Figure.write_image", side_effect=Exception("Test error")):
            with pytest.raises(Exception):
                await agent.generate_visualization(
                    data=data,
                    chart_type="bar",
                    title="Error Chart"
                )
        
        # Check that error event was emitted
        calls = callback.call_args_list
        error_event = calls[1][0][0]
        
        assert error_event["event_type"] == "agent_step_error"
        assert "Test error" in error_event["data"]["error"]


class TestVisualizationResult:
    """Test VisualizationResult structure."""
    
    @pytest.mark.asyncio
    async def test_result_contains_all_required_fields(self, visualization_agent):
        """Test that result contains all required fields."""
        data = {"x": [1, 2, 3], "y": [4, 5, 6]}
        
        with patch("plotly.graph_objects.Figure.write_image"):
            result = await visualization_agent.generate_visualization(
                data=data,
                chart_type="bar",
                title="Complete Result Test"
            )
        
        assert hasattr(result, "filepath")
        assert hasattr(result, "chart_type")
        assert hasattr(result, "title")
        assert hasattr(result, "metadata")
        
        assert result.filepath.startswith("/static/visualizations/")
        assert result.chart_type == "bar"
        assert result.title == "Complete Result Test"
        assert "filename" in result.metadata
        assert "viz_id" in result.metadata
        assert "data_points" in result.metadata
        assert result.metadata["data_points"] == 3
