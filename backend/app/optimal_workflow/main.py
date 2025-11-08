"""
Entry point for running the LlamaIndex workflow.
"""

import asyncio
from llama_index.core.workflow import StartEvent

from app import get_logger
from app.workflow.workflow import ProductGapWorkflow

logger = get_logger("llamaindex_workflow.main")


async def run_workflow(query: str, user_id: int = 1, conversation_id: int = None, stream_callback=None):
    """
    Execute the LlamaIndex workflow for a given query.
    
    Args:
        query: User's question
        user_id: User ID for data access
        conversation_id: Conversation ID (creates new if not provided)
        stream_callback: Optional callback function for streaming events
    """
    from app.database.base import SessionLocal
    from app.database.repositories import ConversationRepository
    
    logger.info("=" * 80)
    logger.info(f"🚀 Starting LlamaIndex Workflow")
    logger.info(f"   └─ Query: {query[:100]}{'...' if len(query) > 100 else ''}")
    logger.info("=" * 80)
    
    # Create or use existing conversation
    db_session = SessionLocal()
    try:
        conv_repo = ConversationRepository()
        
        # Create conversation if not provided
        if conversation_id is None:
            conversation = conv_repo.create(
                db=db_session,
                user_id=user_id,
                title=query if len(query) <= 100 else query[:97] + "..."
            )
            conversation_id = conversation.id
            logger.info(f"Created new conversation: {conversation_id}")
        
    finally:
        db_session.close()
    
    # Create workflow instance with conversation_id and stream callback
    workflow = ProductGapWorkflow(
        user_id=user_id,
        conversation_id=conversation_id,
        stream_callback=stream_callback,
        timeout=900,
        verbose=True
    )
    
    # Run workflow
    result = await workflow.run(query=query)
    
    logger.info("=" * 80)
    logger.info("🏁 Workflow Completed")
    logger.info("=" * 80)
    
    return result


async def run_workflow_streaming(query: str, user_id: int = 1, conversation_id: int = None):
    """
    Execute the workflow with streaming support using async generator.
    
    Yields step progress events and final answer chunks.
    """
    import asyncio
    from app.database.base import SessionLocal
    from app.database.repositories import ConversationRepository
    
    logger.info("🚀 Starting LlamaIndex Workflow (Streaming Mode)")
    
    # Create or use existing conversation
    db_session = SessionLocal()
    try:
        conv_repo = ConversationRepository()
        
        # Create conversation if not provided
        if conversation_id is None:
            conversation = conv_repo.create(
                db=db_session,
                user_id=user_id,
                title=query if len(query) <= 100 else query[:97] + "..."
            )
            conversation_id = conversation.id
            logger.info(f"Created new conversation: {conversation_id}")
        
    finally:
        db_session.close()
    
    # Event queue for streaming with immediate notification
    events = asyncio.Queue()
    workflow_done = asyncio.Event()  # Use Event instead of boolean for better signaling
    workflow_error = None
    workflow_result = None
    
    def stream_callback(event):
        """Callback to collect events for streaming."""
        try:
            logger.info(f"Callback received event: {event.get('type', 'unknown')}")  # Debug log
            # Put event in queue - this is thread-safe
            events.put_nowait(event)
        except Exception as e:
            logger.warning(f"Failed to queue event: {e}")
    
    async def run_workflow_async():
        """Run workflow in background and capture result."""
        nonlocal workflow_error, workflow_result
        try:
            workflow = ProductGapWorkflow(
                user_id=user_id,
                conversation_id=conversation_id,
                stream_callback=stream_callback,
                timeout=900,
                verbose=True
            )
            workflow_result = await workflow.run(query=query)
        except Exception as e:
            logger.exception("Error in workflow execution")
            workflow_error = e
        finally:
            workflow_done.set()  # Signal workflow completion
    
    try:
        # Start workflow in background
        workflow_task = asyncio.create_task(run_workflow_async())
        
        # Yield events as they come in with minimal latency
        while not workflow_done.is_set() or not events.empty():
            try:
                # Shorter timeout for faster response (10ms instead of 100ms)
                event = await asyncio.wait_for(events.get(), timeout=0.01)
                logger.info(f"Yielding event: {event.get('type', 'unknown')}")  # Debug log
                yield event
            except asyncio.TimeoutError:
                # No event available, check if workflow is done
                if workflow_done.is_set() and events.empty():
                    break
                # Let other tasks run
                await asyncio.sleep(0)
                continue
        
        # Wait for workflow to complete
        await workflow_task
        
        # Check for errors
        if workflow_error:
            raise workflow_error
        
        # Yield final completion if not already sent
        yield {
            "type": "workflow_complete",
            "conversation_id": conversation_id,
            "result": workflow_result
        }
        
    except Exception as e:
        logger.exception("Error in streaming workflow")
        yield {"type": "error", "error": str(e)}
        raise
    
    logger.info("🏁 Workflow Completed (Streaming)")


if __name__ == "__main__":
    # Test query
    test_query = "What are the main product gaps for Netflix based on customer reviews?"
    result = asyncio.run(run_workflow(test_query))
    print("\n" + "=" * 80)
    print("FINAL RESULT:")
    print("=" * 80)
    print(result)
