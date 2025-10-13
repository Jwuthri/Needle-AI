"""
Test script for the Orchestrator Service with Agno Team.

This script demonstrates:
1. Initializing the orchestrator
2. Processing a message with streaming
3. Displaying real-time updates

Run from backend directory:
    cd backend
    python -m examples.test_orchestrator
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.orchestrator_service import OrchestratorService
from app.models.chat import ChatRequest
from app.config import get_settings


async def main():
    """Test the orchestrator service with streaming."""
    print("🚀 Starting Orchestrator Test\n")
    
    # Initialize orchestrator
    settings = get_settings()
    orchestrator = OrchestratorService(settings)
    
    print("📦 Initializing orchestrator...")
    try:
        await orchestrator.initialize()
        print("✅ Orchestrator initialized successfully\n")
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return
    
    # Create a test request
    test_message = "What is machine learning? Give me a answer with max 300 words in markdown format pls"
    print(f"💬 Test Query: {test_message}\n")
    print("=" * 60)
    
    request = ChatRequest(
        message=test_message,
        session_id="test_session_123",
        company_id=None  # Set to your company_id if testing with data
    )
    
    # Process with streaming
    print("\n🔄 Streaming Response:\n")
    
    try:
        async for update in orchestrator.process_message_stream(
            request=request,
            user_id="test_user",
            db=None  # Pass db session if you want to test with database
        ):
            update_type = update.get("type")
            data = update.get("data", {})
            
            if update_type == "status":
                status = data.get("status", "unknown")
                message = data.get("message", "")
                print(f"\n📊 Status: [{status}] {message}")
            
            elif update_type == "tool_call_started":
                agent_id = data.get("agent_id", "unknown")
                tool_name = data.get("tool_name", "unknown")
                tool_args = data.get("tool_args", {})
                print(f"\n🔧 Tool Call Started:")
                print(f"   Agent: {agent_id}")
                print(f"   Tool: {tool_name}")
                print(f"   Args: {str(tool_args)[:100]}")
            
            elif update_type == "tool_call_completed":
                tool_name = data.get("tool_name", "unknown")
                result = data.get("result", "")
                print(f"\n✅ Tool Call Completed: {tool_name}")
                if result:
                    print(f"   Result: {result[:100]}...")
            
            elif update_type == "content":
                content = data.get("content", "")
                print(content, end="", flush=True)
            
            elif update_type == "tree_update":
                # Tree updates happen frequently, only log occasionally
                pass
            
            elif update_type == "complete":
                response_data = data
                print("\n\n" + "=" * 60)
                print("✅ Response Complete!")
                print(f"📝 Message ID: {response_data.get('message_id')}")
                print(f"📅 Timestamp: {response_data.get('timestamp')}")
                if response_data.get('metadata'):
                    print(f"🤖 Model: {response_data['metadata'].get('model')}")
                    print(f"🔧 Provider: {response_data['metadata'].get('provider')}")
                    # Execution tree has been replaced with agent_steps
                    if response_data['metadata'].get('agent_steps_count'):
                        steps_count = response_data['metadata']['agent_steps_count']
                        print(f"🔧 Agent steps: {steps_count}")
            
            elif update_type == "error":
                error = data.get("error", "Unknown error")
                print(f"\n❌ Error: {error}")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during streaming: {e}")
        import traceback
        traceback.print_exc()
    
    # Cleanup
    print("\n\n🧹 Cleaning up...")
    await orchestrator.cleanup()
    print("✅ Done!\n")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())

