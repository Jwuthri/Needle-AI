"""
Debug script to see what Agno actually sends in stream chunks.
"""

import asyncio
from app.agents.tree.workflows.multi_branch import create_multi_branch_workflow
from app.config import get_settings
from agno.models.openrouter import OpenRouter


async def debug_stream():
    """Debug what Agno sends in stream chunks."""
    print("=" * 80)
    print("Debugging Agno Stream Chunks")
    print("=" * 80)
    
    # Get settings
    settings = get_settings()
    
    # Create model
    api_key = settings.get_secret("openrouter_api_key")
    model = OpenRouter(
        id=settings.default_model,
        api_key=str(api_key),
        max_tokens=4096
    )
    
    # Create workflow
    executor = create_multi_branch_workflow(
        name="Debug Workflow",
        model=model,
        settings=settings
    )
    
    print("\n🔍 Streaming chunks from Agno...\n")
    
    chunk_num = 0
    async for chunk in executor.run(
        user_prompt="What are customer complaints?",
        user_id="debug",
        session_id="debug"
    ):
        chunk_num += 1
        
        # Print all chunk attributes
        print(f"\n{'='*60}")
        print(f"Chunk #{chunk_num}")
        print(f"{'='*60}")
        print(f"Type: {type(chunk).__name__}")
        
        # Print all attributes
        for attr in dir(chunk):
            if not attr.startswith('_'):
                try:
                    value = getattr(chunk, attr)
                    if not callable(value):
                        value_str = str(value)
                        if len(value_str) > 100:
                            value_str = value_str[:100] + "..."
                        print(f"  {attr}: {value_str}")
                except Exception as e:
                    print(f"  {attr}: <error: {e}>")
        
        # Focus on key attributes
        if hasattr(chunk, 'event'):
            print(f"\n  ⚡ EVENT: {chunk.event}")
        
        if hasattr(chunk, 'agent_id'):
            print(f"  🤖 AGENT_ID: {chunk.agent_id}")
        elif hasattr(chunk, 'agent'):
            print(f"  🤖 AGENT: {chunk.agent}")
        
        if hasattr(chunk, 'content'):
            content = chunk.content
            print(f"  📝 CONTENT TYPE: {type(content).__name__}")
            if content:
                content_str = str(content)[:200]
                print(f"  📝 CONTENT: {content_str}...")
        
        if chunk_num > 50:  # Limit to first 50 chunks
            print("\n\n⚠️  Stopping after 50 chunks for brevity")
            break
    
    print(f"\n\n{'='*80}")
    print(f"Total chunks: {chunk_num}")
    print(f"{'='*80}")


if __name__ == "__main__":
    asyncio.run(debug_stream())

