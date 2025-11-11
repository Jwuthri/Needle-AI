"""
Medium complexity workflow for handling follow-up queries using conversation history.
Uses gpt-5-mini for context-aware responses.
"""

from typing import Optional, Callable, List, Dict, Any
from llama_index.llms.openai import OpenAI

from app.core.config.settings import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def run_medium_workflow(
    query: str,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    stream_callback: Optional[Callable] = None,
    assistant_message_id: Optional[int] = None
) -> str:
    """
    Execute medium complexity workflow for queries that can be answered with conversation history.
    
    Uses gpt-5-mini to answer using context from previous messages.
    Suitable for follow-up questions, clarifications, elaborations.
    
    Args:
        query: User's query
        conversation_history: Previous messages in the conversation
        user_id: User ID
        session_id: Session ID
        stream_callback: Optional callback for streaming events
        assistant_message_id: ID of assistant message to update in database
        
    Returns:
        Markdown-formatted response
    """
    logger.info(f"🚀 Starting Medium Workflow (gpt-5-mini) for query: {query[:100]}")
    
    if stream_callback:
        stream_callback({
            "type": "step_start",
            "step": "context_response",
            "title": "Analyzing Conversation History",
            "session_id": session_id
        })
    
    settings = get_settings()
    api_key = str(settings.get_secret("openai_api_key"))
    
    # Use gpt-5-mini for medium complexity queries
    llm = OpenAI(
        model="gpt-5-mini",
        api_key=api_key,
        temperature=0.5,
        max_tokens=2048
    )
    
    system_prompt = """You are a helpful AI assistant with access to conversation history.
    
    Use the conversation history to provide context-aware responses.
    Reference previous messages when relevant.
    For follow-up questions, build upon what was already discussed.
    Format your response in markdown for better readability.
    Be thorough but concise."""
    
    from llama_index.core.llms import ChatMessage
    
    # Build message list with history
    messages = [ChatMessage(role="system", content=system_prompt)]
    
    # Add conversation history (limit to last 10 messages to avoid token limits)
    if conversation_history:
        recent_history = conversation_history[-10:]
        for msg in recent_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if content:
                messages.append(ChatMessage(role=role, content=content))
    
    # Add current query
    messages.append(ChatMessage(role="user", content=query))
    
    try:
        if stream_callback:
            stream_callback({
                "type": "step_update",
                "step": "context_response",
                "title": "Generating Response",
                "session_id": session_id
            })
        
        # Stream response from LLM
        accumulated_answer = ""
        
        # Get streaming response generator (don't await here!)
        response = await llm.astream_chat(messages)
        
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
        
        logger.info(f"✅ Medium workflow completed: {len(accumulated_answer)} chars")
        
        # Save to database if assistant_message_id provided
        if assistant_message_id:
            try:
                from app.database.session import get_async_session
                from app.database.repositories.chat_message import ChatMessageRepository
                from datetime import datetime
                
                async with get_async_session() as db:
                    await ChatMessageRepository.update(
                        db=db,
                        message_id=assistant_message_id,
                        content=accumulated_answer,
                        completed_at=datetime.utcnow()
                    )
                    await db.commit()
                    logger.info(f"💾 Saved medium workflow response to DB (message_id={assistant_message_id})")
            except Exception as db_error:
                logger.error(f"Failed to save to database: {db_error}", exc_info=True)
        
        if stream_callback:
            # Emit step complete
            stream_callback({
                "type": "step_complete",
                "step": "context_response",
                "title": "Response Generated",
                "session_id": session_id,
                "result": {
                    "status": "success",
                    "history_used": len(conversation_history) if conversation_history else 0
                }
            })
            
            # Emit final complete event with full response
            from datetime import datetime
            stream_callback({
                "type": "complete",
                "data": {
                    "message_id": str(assistant_message_id) if assistant_message_id else session_id,
                    "message": accumulated_answer,
                    "session_id": session_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "metadata": {
                        "model": "gpt-5-mini",
                        "workflow": "medium",
                        "provider": "openai",
                        "history_messages": len(conversation_history) if conversation_history else 0
                    }
                }
            })
        
        return accumulated_answer
        
    except Exception as e:
        logger.error(f"Error in medium workflow: {e}", exc_info=True)
        
        if stream_callback:
            stream_callback({
                "type": "step_error",
                "step": "context_response",
                "error": str(e),
                "session_id": session_id
            })
        
        return "I apologize, but I encountered an error processing your request. Please try again."

