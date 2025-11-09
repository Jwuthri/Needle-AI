"""
Simple workflow for handling general queries that don't require data retrieval.
Uses gpt-5-nano for fast, cost-effective responses.
"""

from typing import Optional, Callable
from llama_index.llms.openai import OpenAI
from datetime import datetime

from app.core.config.settings import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def run_simple_workflow(
    query: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    stream_callback: Optional[Callable] = None,
    assistant_message_id: Optional[int] = None
) -> str:
    """
    Execute simple workflow for general queries.
    
    Uses gpt-5-nano to directly answer without any data retrieval.
    Suitable for greetings, general knowledge, casual conversation.
    
    Args:
        query: User's query
        user_id: User ID
        session_id: Session ID
        stream_callback: Optional callback for streaming events
        assistant_message_id: ID of assistant message to update in database
        
    Returns:
        Markdown-formatted response
    """
    logger.info(f"🚀 Starting Simple Workflow (gpt-5-nano) for query: {query[:100]}")
    
    if stream_callback:
        stream_callback({
            "type": "step_start",
            "step": "simple_response",
            "title": "Generating Response",
            "session_id": session_id
        })
    
    settings = get_settings()
    api_key = str(settings.get_secret("openai_api_key"))
    
    # Use gpt-5-nano for simple queries
    llm = OpenAI(
        model="gpt-5-nano",
        api_key=api_key,
        temperature=0.7,  # Slightly higher for conversational tone
        max_tokens=1024
    )
    t0 = datetime.now()
    logger.info(f"🚀 Starting Simple Workflow (gpt-5-nano) at {t0}")
    system_prompt = """You are a helpful AI assistant. Provide clear, concise, and friendly responses.
    
    For greetings and casual conversation, be warm and engaging.
    For general knowledge questions, provide accurate information in a conversational tone.
    Format your response in markdown for better readability.
    Make your answer as long as possible."""
    
    from llama_index.core.llms import ChatMessage
    
    messages = [
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(role="user", content=query)
    ]
    
    try:
        # Stream response from LLM
        accumulated_answer = ""
        
        # Get streaming response generator (don't await here!)
        response = await llm.astream_chat(messages)
        t1 = datetime.now()
        logger.info(f"🚀 Simple Workflow (gpt-5-nano) starting response in {t1 - t0}")
        
        async for chunk in response:
            # Extract delta content from chunk
            token = chunk.delta if hasattr(chunk, 'delta') else str(chunk)
            
            if not token:
                continue
            
            accumulated_answer += token
            
            # Stream each token to frontend
            if stream_callback:
                stream_callback({
                    "type": "content",
                    "data": {"content": token},
                    "session_id": session_id
                })
        
        t2 = datetime.now()

        logger.info(f"✅ Simple workflow completed: {len(accumulated_answer)} chars in {t2 - t1}")
        
        # Save to database if assistant_message_id provided
        if assistant_message_id:
            try:
                from app.database.session import get_async_session
                from app.database.repositories.chat_message import ChatMessageRepository
                
                async with get_async_session() as db:
                    await ChatMessageRepository.update(
                        db=db,
                        message_id=assistant_message_id,
                        content=accumulated_answer,
                        completed_at=datetime.utcnow()
                    )
                    await db.commit()
                    logger.info(f"💾 Saved simple workflow response to DB (message_id={assistant_message_id})")
            except Exception as db_error:
                logger.error(f"Failed to save to database: {db_error}", exc_info=True)
        
        if stream_callback:
            # Emit step complete
            stream_callback({
                "type": "step_complete",
                "step": "simple_response",
                "title": "Response Generated",
                "session_id": session_id,
                "result": {"status": "success"}
            })
            
            # Emit final complete event with full response
            stream_callback({
                "type": "complete",
                "data": {
                    "message_id": str(assistant_message_id) if assistant_message_id else session_id,
                    "message": accumulated_answer,
                    "session_id": session_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "metadata": {
                        "model": "gpt-5-nano",
                        "workflow": "simple",
                        "provider": "openai"
                    }
                }
            })
        
        return accumulated_answer
        
    except Exception as e:
        logger.error(f"Error in simple workflow: {e}", exc_info=True)
        
        if stream_callback:
            stream_callback({
                "type": "step_error",
                "step": "simple_response",
                "error": str(e),
                "session_id": session_id
            })
        
        return "I apologize, but I encountered an error processing your request. Please try again."

