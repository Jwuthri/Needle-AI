"""
Simple test script for Agno Team streaming.

This demonstrates the basic Agno Team streaming pattern without
the full orchestrator setup.

Run from backend directory:
    cd backend
    python -m examples.test_agno_team_simple
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from agno.team import Team
from app.config import get_settings


async def main():
    """Test basic Agno Team streaming."""
    print("🚀 Testing Agno Team Streaming\n")
    
    # Get settings for API keys
    settings = get_settings()
    api_key = settings.get_secret("openrouter_api_key")
    
    if not api_key:
        print("❌ Error: OPENROUTER_API_KEY not configured")
        return
    
    # Create model
    print("📦 Creating OpenRouter model...")
    model = OpenRouter(
        id=settings.default_model,
        api_key=str(api_key)
    )
    print(f"✅ Model: {settings.default_model}\n")
    
    # Create a simple agent
    print("🤖 Creating agent...")
    agent = Agent(
        name="Assistant",
        role="Helpful AI assistant",
        model=model,
        instructions="You are a helpful AI assistant. Keep responses concise and friendly."
    )
    
    # Create team with streaming enabled
    print("👥 Creating team with streaming...\n")
    team = Team(
        name="Test Team",
        members=[agent],
        model=model,
        stream=True,
        stream_intermediate_steps=True,
        stream_member_events=True,
    )
    
    # Test query
    test_query = "Explain what product analytics is in 2 sentences."
    print(f"💬 Query: {test_query}\n")
    print("=" * 60)
    print("\n🔄 Streaming Response:\n")
    
    try:
        # Run team with streaming
        stream = team.arun(
            test_query,
            session_id="test_session",
            stream=True
        )
        
        response_content = ""
        chunk_count = 0
        
        async for chunk in stream:
            chunk_count += 1
            
            # Check what type of chunk we got
            event_type = getattr(chunk, 'event', 'unknown')
            
            if event_type == "TeamRunContent":
                # This is streaming content!
                content = chunk.content
                response_content += content
                print(content, end="", flush=True)
            
            elif event_type == "TeamRunResponse":
                # Final response
                if hasattr(chunk, 'content'):
                    response_content = chunk.content
                print("\n\n[Final response received]")
            
            else:
                # Other event types
                print(f"\n[Event: {event_type}]")
        
        print("\n\n" + "=" * 60)
        print(f"✅ Streaming complete!")
        print(f"📊 Chunks received: {chunk_count}")
        print(f"📝 Total length: {len(response_content)} characters")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✅ Test complete!\n")


if __name__ == "__main__":
    asyncio.run(main())

