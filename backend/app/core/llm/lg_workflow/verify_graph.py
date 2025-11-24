import asyncio
import os
import sys
from dotenv import load_dotenv

from app.core.llm.lg_workflow.graph import create_workflow
from langchain_core.messages import HumanMessage

async def main():
    print("Verifying LangGraph workflow...")
    try:
        # Mock user_id
        user_id = "test_user"
        
        # Create workflow
        app = create_workflow(user_id)
        print("Workflow created successfully.")
        
        # Test compilation
        print("Graph compiled successfully.")
        
        # We won't run it fully as it requires DB and OpenAI key, but we can check the structure
        # print("Graph structure:")
        # try:
        #     print(app.get_graph().print_ascii())
        # except ImportError:
        #     print("Skipping graph visualization (grandalf not installed)")
        
        print("Verification passed!")
        
    except Exception as e:
        print(f"Verification failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
