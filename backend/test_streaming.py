#!/usr/bin/env python3
"""
Quick test script to verify chat streaming works.
Run this from the backend directory.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_streaming():
    """Test the orchestrator streaming."""
    from app.services.orchestrator_service import OrchestratorService
    from app.models.chat import ChatRequest
    from app.config import get_settings
    
    print("🚀 Testing chat streaming...")
    print("-" * 50)
    
    # Initialize orchestrator
    settings = get_settings()
    orchestrator = OrchestratorService(settings)
    await orchestrator.initialize()
    
    print("✅ Orchestrator initialized")
    print("-" * 50)
    
    # Create test request
    request = ChatRequest(
        message="What is the weather like today?",
        session_id="test-session"
    )
    
    print(f"📤 Sending message: {request.message}")
    print("-" * 50)
    
    # Stream the response
    content_chunks = []
    update_count = 0
    
    async for update in orchestrator.process_message_stream(
        request=request,
        user_id="test-user",
        db=None
    ):
        update_count += 1
        update_type = update.get("type")
        
        if update_type == "status":
            print(f"📊 Status: {update['data']['message']}")
        
        elif update_type == "content":
            chunk = update['data']['content']
            content_chunks.append(chunk)
            print(f"📝 Content chunk #{len(content_chunks)}: {len(chunk)} chars - {chunk[:50]}")
        
        elif update_type == "tool_call_started":
            tool_name = update['data']['tool_name']
            agent_id = update['data']['agent_id']
            print(f"🔧 Tool call started: {agent_id} -> {tool_name}")
        
        elif update_type == "tool_call_completed":
            tool_name = update['data']['tool_name']
            print(f"✅ Tool call completed: {tool_name}")
        
        elif update_type == "complete":
            print(f"🎉 Response complete!")
            print(f"   Total message length: {len(update['data']['message'])} chars")
    
    print("-" * 50)
    print(f"📊 Summary:")
    print(f"   Total updates: {update_count}")
    print(f"   Content chunks: {len(content_chunks)}")
    print(f"   Total content: {''.join(content_chunks)}")
    print("-" * 50)
    
    if len(content_chunks) > 1:
        print("✅ SUCCESS: Content was streamed in chunks!")
    elif len(content_chunks) == 1:
        print("⚠️  WARNING: Content came in a single chunk (fallback worked)")
    else:
        print("❌ ERROR: No content received")
    
    return len(content_chunks) > 0

if __name__ == "__main__":
    try:
        result = asyncio.run(test_streaming())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n❌ Test interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

