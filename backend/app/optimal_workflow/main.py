"""
Entry point for running the LlamaIndex workflow with intelligent routing.

Routes queries to appropriate workflow based on complexity:
- Simple: gpt-5-nano for general queries, greetings, non-data questions
- Medium: gpt-5-mini for follow-up questions using conversation history  
- Complex: Full workflow for queries requiring data retrieval and analysis
"""

import asyncio
from datetime import datetime
import time
from typing import Optional, List, Dict, Any, Callable
from llama_index.core.workflow import StartEvent

from app.utils.logging import get_logger
from app.optimal_workflow.query_classifier import classify_query, QueryComplexity
from app.optimal_workflow.simple_workflow import run_simple_workflow
from app.optimal_workflow.medium_workflow import run_medium_workflow
from app.optimal_workflow.workflow import ProductGapWorkflow

logger = get_logger("llamaindex_workflow.main")


async def run_workflow(
    query: str,
    user_id: str = None,
    session_id: str = None,
    stream_callback: Optional[Callable] = None,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
    assistant_message_id: Optional[int] = None
):
    """
    Execute the appropriate workflow for a given query based on complexity.
    
    Automatically routes to:
    - Simple workflow (gpt-5-nano): General queries, greetings, casual conversation
    - Medium workflow (gpt-5-mini): Follow-up questions using conversation history
    - Complex workflow (full): Queries requiring data retrieval and deep analysis
    
    Args:
        query: User's question
        user_id: User ID (string from Clerk or other auth provider)
        session_id: Session ID (passed from chat API)
        stream_callback: Optional callback function for streaming events
        conversation_history: Recent conversation messages for context
        assistant_message_id: ID of assistant message to update in database
    """
    logger.info("=" * 80)
    logger.info(f"🚀 Starting Workflow Router")
    logger.info(f"   └─ Query: {query[:100]}{'...' if len(query) > 100 else ''}")
    logger.info("=" * 80)
    
    try:
        # Classify query to determine workflow
        classification = await classify_query(
            query=query,
            conversation_history=conversation_history,
            user_id=user_id
        )
        
        logger.info(f"📊 Query classified as: {classification.complexity.upper()}")
        
        # Emit classification event
        if stream_callback:
            stream_callback({
                "type": "workflow_routed",
                "complexity": classification.complexity,
                "session_id": session_id
            })
        
        # Route to appropriate workflow
        if classification.complexity == QueryComplexity.SIMPLE:
            logger.info("🎯 Routing to SIMPLE workflow (gpt-5-nano)")
            result = await run_simple_workflow(
                query=query,
                user_id=user_id,
                session_id=session_id,
                stream_callback=stream_callback,
                assistant_message_id=assistant_message_id
            )
            
        elif classification.complexity == QueryComplexity.MEDIUM:
            logger.info("🎯 Routing to MEDIUM workflow (gpt-5-mini)")
            result = await run_medium_workflow(
                query=query,
                conversation_history=conversation_history,
                user_id=user_id,
                session_id=session_id,
                stream_callback=stream_callback,
                assistant_message_id=assistant_message_id
            )
            
        else:  # COMPLEX
            logger.info("🎯 Routing to COMPLEX workflow (full pipeline)")
            workflow = ProductGapWorkflow(
                user_id=user_id,
                session_id=session_id,
                stream_callback=stream_callback,
                timeout=900,
                verbose=True
            )
            result = await workflow.run(query=query)
        
        logger.info("=" * 80)
        logger.info("🏁 Workflow Completed")
        logger.info("=" * 80)
        
        return result
        
    except Exception as e:
        logger.error(f"Error in workflow routing: {e}", exc_info=True)
        
        if stream_callback:
            stream_callback({
                "type": "workflow_error",
                "error": str(e),
                "session_id": session_id
            })
        
        raise


async def run_workflow_streaming(
    query: str,
    user_id: str = None,
    session_id: str = None,
    assistant_message_id: int = None,
    conversation_history: Optional[List[Dict[str, Any]]] = None
):
    """
    Execute the workflow with streaming support using async generator.
    
    Automatically routes to appropriate workflow based on query complexity.
    Yields step progress events and final answer chunks.
    
    Args:
        query: User query
        user_id: User ID
        session_id: Session ID
        assistant_message_id: ID of assistant message for saving steps to DB
        conversation_history: Recent conversation messages for context
    """
    import asyncio
    
    logger.info("🚀 Starting Workflow Router (Streaming Mode)")
    
    # Event queue for streaming with immediate notification
    events = asyncio.Queue()
    workflow_done = asyncio.Event()
    workflow_error = None
    workflow_result = None
    
    def stream_callback(event):
        """Callback to collect events for streaming."""
        try:
            # logger.info(f"Callback received event: {event.get('type', 'unknown')}")
            events.put_nowait(event)
        except Exception as e:
            logger.warning(f"Failed to queue event: {e}")
    
    async def run_workflow_async():
        """Run workflow in background and capture result."""
        nonlocal workflow_error, workflow_result
        try:
            # Classify query
            classification = await classify_query(
                query=query,
                conversation_history=conversation_history,
                user_id=user_id
            )
            
            logger.info(f"📊 Query classified as: {classification.complexity.upper()}")
            
            # Emit classification event
            stream_callback({
                "type": "workflow_routed",
                "complexity": classification.complexity,
                "session_id": session_id
            })
            
            # Route to appropriate workflow
            from datetime import datetime as dt
            now = dt.now()
            logger.info(f"🎯 Routing workflow now at {now}")
            if classification.complexity == QueryComplexity.SIMPLE:
                logger.info(f"🎯 Routing to SIMPLE workflow (gpt-5-nano)")
                workflow_result = await run_simple_workflow(
                    query=query,
                    user_id=user_id,
                    session_id=session_id,
                    stream_callback=stream_callback,
                    assistant_message_id=assistant_message_id
                )
                
            elif classification.complexity == QueryComplexity.MEDIUM:
                logger.info("🎯 Routing to MEDIUM workflow (gpt-5-mini)")
                workflow_result = await run_medium_workflow(
                    query=query,
                    conversation_history=conversation_history,
                    user_id=user_id,
                    session_id=session_id,
                    stream_callback=stream_callback,
                    assistant_message_id=assistant_message_id
                )
                
            else:  # COMPLEX
                logger.info("🎯 Routing to COMPLEX workflow (full pipeline)")
                workflow = ProductGapWorkflow(
                    user_id=user_id,
                    session_id=session_id,
                    assistant_message_id=assistant_message_id,
                    stream_callback=stream_callback,
                    timeout=900,
                    verbose=True
                )
                workflow_result = await workflow.run(query=query)
                
        except Exception as e:
            logger.exception("Error in workflow execution")
            workflow_error = e
        finally:
            workflow_done.set()
    
    try:
        # Start workflow in background
        workflow_task = asyncio.create_task(run_workflow_async())
        
        # Yield events as they come in with immediate response
        while True:
            # Check if there are events in queue (non-blocking)
            while not events.empty():
                try:
                    event = events.get_nowait()
                    logger.info(f"Yielding event: {event.get('type', 'unknown')}")
                    yield event
                except asyncio.QueueEmpty:
                    break
            
            # Check if workflow is done
            if workflow_done.is_set() and events.empty():
                break
            
            # Give control back to event loop
            await asyncio.sleep(0)
        
        # Wait for workflow to complete
        await workflow_task
        
        # Check for errors
        if workflow_error:
            raise workflow_error
        
        # Yield final completion if not already sent
        yield {
            "type": "workflow_complete",
            "session_id": session_id,
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
