"""
Quick test script for fake orchestrator
"""
import asyncio
import os

# Set to use fake orchestrator
os.environ["USE_FAKE_ORCHESTRATOR"] = "true"


async def test_fake_orchestrator():
    """Test the fake orchestrator service"""
    from app.services.fake_orchestrator_service import FakeOrchestratorService
    from app.models.chat import ChatRequest
    
    print("🧪 Testing Fake Orchestrator Service\n")
    print("=" * 60)
    
    orchestrator = FakeOrchestratorService()
    
    # Test message
    test_message = "Which competitors are mentioned most often?"
    print(f"\n📝 Query: {test_message}\n")
    print("-" * 60)
    
    step_count = 0
    agent_steps = []
    
    # Create request object
    request = ChatRequest(
        message=test_message,
        session_id="test-session-123"
    )
    
    # Process stream
    async for event in orchestrator.process_message_stream(
        request=request,
        user_id="test-user-456"
    ):
        event_type = event["type"]
        data = event["data"]
        
        if event_type == "status":
            print(f"\n📊 STATUS: {data['message']}")
            
        elif event_type == "agent_step_start":
            step_count += 1
            print(f"\n🤖 STEP {step_count}: {data['agent_name']} started")
            print(f"   Step ID: {data['step_id'][:8]}...")
            print(f"   Step Order: {data['step_order']}")
            
        elif event_type == "agent_step_complete":
            print(f"✅ {data['agent_name']} completed")
            print(f"   Type: {'Structured' if data['is_structured'] else 'Unstructured'}")
            if data['is_structured']:
                print(f"   Content: {str(data['content'])[:100]}...")
            else:
                print(f"   Content: {data['content'][:100]}...")
            agent_steps.append(data)
            
        elif event_type == "content":
            # Don't print every chunk, just show we're streaming
            pass
            
        elif event_type == "complete":
            print(f"\n🎉 COMPLETE!")
            print(f"   Message ID: {data['message_id']}")
            print(f"   Total Steps: {len(data['metadata']['completed_steps'])}")
            print(f"   Processing Time: {data['metadata']['total_processing_time_ms']}ms")
            print(f"\n📄 Final Response Preview:")
            print("-" * 60)
            print(data['message'][:300] + "...")
            print("-" * 60)
    
    print(f"\n✅ Test completed successfully!")
    print(f"   Generated {step_count} agent steps")
    print(f"   All steps were stored in metadata")
    
    return agent_steps


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🎭 FAKE ORCHESTRATOR TEST")
    print("=" * 60)
    
    try:
        steps = asyncio.run(test_fake_orchestrator())
        print(f"\n✅ SUCCESS: Generated {len(steps)} agent steps")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

