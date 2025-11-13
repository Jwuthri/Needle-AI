"""
Tests for Chat Message Step tracking across workflows.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from app.optimal_workflow.product_review_workflow import ProductReviewAnalysisWorkflow
from app.optimal_workflow.simple_workflow import run_simple_workflow
from app.optimal_workflow.medium_workflow import run_medium_workflow


class TestChatMessageStepTracking:
    """Test suite for Chat Message Step tracking functionality."""
    
    @pytest.mark.asyncio
    async def test_track_step_in_db_with_thought(self):
        """Test that _track_step_in_db correctly saves thought and structured output."""
        workflow = ProductReviewAnalysisWorkflow(
            user_id="test_user",
            session_id="test_session",
            assistant_message_id="test_message_123"
        )
        
        with patch('app.optimal_workflow.product_review_workflow.get_async_session') as mock_session:
            mock_db = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db
            
            with patch('app.optimal_workflow.product_review_workflow.ChatMessageStepRepository') as mock_repo:
                mock_repo.create = AsyncMock(return_value=MagicMock(id="step_123"))
                
                # Track a step with thought and structured output
                await workflow._track_step_in_db(
                    agent_name="TestAgent",
                    step_order=1,
                    content={"test": "data"},
                    is_structured=True,
                    thought="This is my reasoning"
                )
                
                # Verify create was called with correct parameters
                mock_repo.create.assert_called_once()
                call_kwargs = mock_repo.create.call_args.kwargs
                
                assert call_kwargs["message_id"] == "test_message_123"
                assert call_kwargs["agent_name"] == "TestAgent"
                assert call_kwargs["step_order"] == 1
                assert call_kwargs["thought"] == "This is my reasoning"
                assert call_kwargs["structured_output"] == {"test": "data"}
                assert "tool_call" not in call_kwargs or call_kwargs["tool_call"] is None
    
    @pytest.mark.asyncio
    async def test_track_tool_call(self):
        """Test that _track_tool_call correctly saves tool call information."""
        workflow = ProductReviewAnalysisWorkflow(
            user_id="test_user",
            session_id="test_session",
            assistant_message_id="test_message_123"
        )
        
        with patch('app.optimal_workflow.product_review_workflow.get_async_session') as mock_session:
            mock_db = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db
            
            with patch('app.optimal_workflow.product_review_workflow.ChatMessageStepRepository') as mock_repo:
                mock_repo.create = AsyncMock(return_value=MagicMock(id="step_123"))
                
                # Track a tool call
                await workflow._track_tool_call(
                    agent_name="DataRetrieval",
                    tool_name="query_reviews",
                    parameters={"rating_filter": "<=2"},
                    result={"review_count": 45},
                    thought="Querying negative reviews"
                )
                
                # Verify create was called with tool_call
                mock_repo.create.assert_called_once()
                call_kwargs = mock_repo.create.call_args.kwargs
                
                assert call_kwargs["agent_name"] == "DataRetrieval"
                assert call_kwargs["thought"] == "Querying negative reviews"
                assert "tool_call" in call_kwargs
                assert call_kwargs["tool_call"]["tool_name"] == "query_reviews"
                assert call_kwargs["tool_call"]["parameters"] == {"rating_filter": "<=2"}
                assert call_kwargs["tool_call"]["result"] == {"review_count": 45}
    
    @pytest.mark.asyncio
    async def test_track_step_without_assistant_message_id(self):
        """Test that tracking gracefully handles missing assistant_message_id."""
        workflow = ProductReviewAnalysisWorkflow(
            user_id="test_user",
            session_id="test_session",
            assistant_message_id=None  # No message ID
        )
        
        # Should return None without attempting database operation
        result = await workflow._track_step_in_db(
            agent_name="TestAgent",
            step_order=1,
            content={"test": "data"},
            is_structured=True
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_simple_workflow_tracks_steps(self):
        """Test that simple workflow tracks start and completion steps."""
        with patch('app.optimal_workflow.simple_workflow.get_async_session') as mock_session, \
             patch('app.optimal_workflow.simple_workflow.ChatMessageStepRepository') as mock_step_repo, \
             patch('app.optimal_workflow.simple_workflow.ChatMessageRepository') as mock_msg_repo, \
             patch('app.optimal_workflow.simple_workflow.OpenAI') as mock_llm:
            
            mock_db = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db
            mock_step_repo.create = AsyncMock()
            mock_msg_repo.update = AsyncMock()
            
            # Mock LLM response
            mock_response = AsyncMock()
            mock_response.__aiter__.return_value = iter([
                MagicMock(delta="Hello"),
                MagicMock(delta=" there!")
            ])
            mock_llm.return_value.astream_chat.return_value = mock_response
            
            # Run simple workflow
            await run_simple_workflow(
                query="Hello",
                user_id="test_user",
                session_id="test_session",
                assistant_message_id="msg_123"
            )
            
            # Verify two steps were tracked (start and completion)
            assert mock_step_repo.create.call_count == 2
            
            # Check first call (workflow start)
            first_call = mock_step_repo.create.call_args_list[0].kwargs
            assert first_call["agent_name"] == "SimpleWorkflow"
            assert first_call["step_order"] == 0
            assert "thought" in first_call
            assert "gpt-5-nano" in first_call["thought"]
            
            # Check second call (completion)
            second_call = mock_step_repo.create.call_args_list[1].kwargs
            assert second_call["agent_name"] == "SimpleWorkflow"
            assert second_call["step_order"] == 1
            assert "prediction" in second_call
    
    @pytest.mark.asyncio
    async def test_medium_workflow_tracks_steps(self):
        """Test that medium workflow tracks start and completion steps with history."""
        conversation_history = [
            {"role": "user", "content": "What are product gaps?"},
            {"role": "assistant", "content": "Product gaps are..."}
        ]
        
        with patch('app.optimal_workflow.medium_workflow.get_async_session') as mock_session, \
             patch('app.optimal_workflow.medium_workflow.ChatMessageStepRepository') as mock_step_repo, \
             patch('app.optimal_workflow.medium_workflow.ChatMessageRepository') as mock_msg_repo, \
             patch('app.optimal_workflow.medium_workflow.OpenAI') as mock_llm:
            
            mock_db = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db
            mock_step_repo.create = AsyncMock()
            mock_msg_repo.update = AsyncMock()
            
            # Mock LLM response
            mock_response = AsyncMock()
            mock_response.__aiter__.return_value = iter([
                MagicMock(delta="Based"),
                MagicMock(delta=" on our previous discussion...")
            ])
            mock_llm.return_value.astream_chat.return_value = mock_response
            
            # Run medium workflow
            await run_medium_workflow(
                query="Tell me more",
                conversation_history=conversation_history,
                user_id="test_user",
                session_id="test_session",
                assistant_message_id="msg_123"
            )
            
            # Verify two steps were tracked
            assert mock_step_repo.create.call_count == 2
            
            # Check first call includes history count
            first_call = mock_step_repo.create.call_args_list[0].kwargs
            assert first_call["agent_name"] == "MediumWorkflow"
            assert first_call["structured_output"]["history_messages"] == 2
            
            # Check second call includes history usage
            second_call = mock_step_repo.create.call_args_list[1].kwargs
            assert second_call["structured_output"]["history_used"] == 2
    
    @pytest.mark.asyncio
    async def test_step_ordering_is_sequential(self):
        """Test that step_order is maintained sequentially."""
        workflow = ProductReviewAnalysisWorkflow(
            user_id="test_user",
            session_id="test_session",
            assistant_message_id="test_message_123"
        )
        
        # Get multiple step orders
        order1 = workflow._get_next_step_order()
        order2 = workflow._get_next_step_order()
        order3 = workflow._get_next_step_order()
        
        # Verify sequential ordering
        assert order1 == 1
        assert order2 == 2
        assert order3 == 3
    
    @pytest.mark.asyncio
    async def test_track_step_handles_pydantic_models(self):
        """Test that _track_step_in_db handles Pydantic models correctly."""
        from pydantic import BaseModel
        
        class TestModel(BaseModel):
            field1: str
            field2: int
        
        workflow = ProductReviewAnalysisWorkflow(
            user_id="test_user",
            session_id="test_session",
            assistant_message_id="test_message_123"
        )
        
        with patch('app.optimal_workflow.product_review_workflow.get_async_session') as mock_session:
            mock_db = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db
            
            with patch('app.optimal_workflow.product_review_workflow.ChatMessageStepRepository') as mock_repo:
                mock_repo.create = AsyncMock(return_value=MagicMock(id="step_123"))
                
                # Track a step with Pydantic model
                model = TestModel(field1="test", field2=42)
                await workflow._track_step_in_db(
                    agent_name="TestAgent",
                    step_order=1,
                    content=model,
                    is_structured=True
                )
                
                # Verify model was converted to dict
                call_kwargs = mock_repo.create.call_args.kwargs
                assert call_kwargs["structured_output"] == {"field1": "test", "field2": 42}
    
    @pytest.mark.asyncio
    async def test_track_step_handles_errors_gracefully(self):
        """Test that _track_step_in_db handles database errors gracefully."""
        workflow = ProductReviewAnalysisWorkflow(
            user_id="test_user",
            session_id="test_session",
            assistant_message_id="test_message_123"
        )
        
        with patch('app.optimal_workflow.product_review_workflow.get_async_session') as mock_session:
            mock_db = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db
            
            with patch('app.optimal_workflow.product_review_workflow.ChatMessageStepRepository') as mock_repo:
                # Simulate database error
                mock_repo.create = AsyncMock(side_effect=Exception("Database error"))
                
                # Should not raise exception, just return None
                result = await workflow._track_step_in_db(
                    agent_name="TestAgent",
                    step_order=1,
                    content={"test": "data"},
                    is_structured=True
                )
                
                assert result is None
