"""
Simple Agno Example - Updated to latest API
Shows basic async agent usage with the latest Agno patterns.
"""

import asyncio
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.models.openrouter import OpenRouter
from app.core.config.settings import get_settings


async def simple_agent_example():
    """Simple agent example using latest Agno API."""
    
    settings = get_settings()
    
    # Get API key
    api_key = settings.get_secret("openai_api_key")
    api_key_str = str(api_key) if hasattr(api_key, '__str__') else api_key
    
    # Create agent with model instance
    agent = Agent(
        model=OpenAIChat(
            id="gpt-4o-mini",
            api_key=api_key_str
        ),
        instructions="You are a helpful AI assistant. Be concise and friendly.",
        read_chat_history=True,
    )
    
    print("🤖 Simple Agno Agent Example\n")
    
    # Use async arun() method
    response = await agent.arun("Hello! Tell me a short joke.")
    print(f"Agent: {response.content}\n")
    
    # Follow-up message with context
    response = await agent.arun(
        "That was funny! Tell me another one.",
        session_id="demo_session"
    )
    print(f"Agent: {response.content}\n")
    
    print("✅ Example completed successfully!")


async def openrouter_example():
    """OpenRouter model example using latest API."""
    
    settings = get_settings()
    
    # Get API key
    api_key = settings.get_secret("openrouter_api_key")
    if not api_key:
        print("⚠️  OpenRouter API key not configured, skipping...")
        return
    
    api_key_str = str(api_key) if hasattr(api_key, '__str__') else api_key
    
    # Create agent with OpenRouter model
    agent = Agent(
        model=OpenRouter(
            id="openai/gpt-4o-mini",
            api_key=api_key_str
        ),
        instructions="You are a helpful AI assistant using OpenRouter.",
        read_chat_history=True,
    )
    
    print("🤖 OpenRouter Agent Example\n")
    
    # Use aprint_response for direct output
    await agent.aprint_response(
        "Explain quantum computing in one sentence.",
        markdown=True
    )
    
    print("\n✅ OpenRouter example completed!")


async def persistent_memory_example():
    """Example with persistent memory using PostgreSQL."""
    
    from agno.db.postgres import PostgresDb
    
    settings = get_settings()
    
    # Create PostgreSQL DB for persistence
    password = settings.get_secret("database_password")
    db_url = (
        f"postgresql+psycopg://{settings.database_user}:{password}"
        f"@{settings.database_host}:{settings.database_port}"
        f"/{settings.database_name}"
    )
    
    postgres_db = PostgresDb(
        db_url=db_url,
        table_name="agno_demo",
    )
    
    # Get API key
    api_key = settings.get_secret("openai_api_key")
    api_key_str = str(api_key) if hasattr(api_key, '__str__') else api_key
    
    # Create agent with persistence
    agent = Agent(
        model=OpenAIChat(
            id="gpt-4o-mini",
            api_key=api_key_str
        ),
        db=postgres_db,                   # Persistence via PostgreSQL
        enable_user_memories=True,        # Enable user memories
        read_chat_history=True,           # Auto-load history
        instructions="You have persistent memory. Remember user preferences.",
    )
    
    print("🤖 Persistent Memory Example (PostgreSQL)\n")
    
    user_id = "demo_user"
    session_id = "demo_session_persistent"
    
    # First message
    await agent.aprint_response(
        "My name is Alice and I love Python programming.",
        user_id=user_id,
        session_id=session_id,
    )
    
    # Second message - should remember
    print("\n---\n")
    await agent.aprint_response(
        "What's my name and what do I love?",
        user_id=user_id,
        session_id=session_id,
    )
    
    print("\n✅ Persistent memory example completed!")


async def main():
    """Run all examples."""
    
    print("=" * 60)
    print("Agno Examples - Latest API")
    print("=" * 60 + "\n")
    
    try:
        # Simple example
        await simple_agent_example()
        print("\n" + "-" * 60 + "\n")
        
        # OpenRouter example
        await openrouter_example()
        print("\n" + "-" * 60 + "\n")
        
        # Persistent memory example
        try:
            await persistent_memory_example()
        except Exception as e:
            print(f"⚠️  Persistent memory example skipped: {e}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
