"""
Multi-Agent Product Review Analysis System using LlamaIndex Workflow
====================================================================

This implements an advanced multi-agent product review analysis system with:
- Multiple specialized agents (Coordinator, General Assistant, Data Discovery, Gap Analysis, etc.)
- Agent handoffs between specialists
- Tool calling capabilities for data access, analysis, and visualization
- Streaming support to see each agent's actions
- PNG graph generation with plotly
- State management with Context

Install required packages:
pip install llama-index-core llama-index-llms-openai llama-index-agent-openai plotly kaleido
"""

import asyncio
from typing import Any, Dict, List, Optional

from app.core.config.settings import get_settings
from app.core.llm.simple_workflow.workflow import create_product_review_workflow
from llama_index.core.agent.workflow import AgentWorkflow
from llama_index.core.workflow import Event, StartEvent, StopEvent, Workflow, step, Context
from llama_index.llms.openai import OpenAI

from llama_index.core.agent.workflow import (
    AgentInput,
    AgentOutput,
    ToolCall,
    ToolCallResult,
    AgentStream,
)

settings = get_settings()


# ============================================================================
# Custom Workflow for Enhanced Streaming and Visualization
# ============================================================================


class StreamingProductReviewWorkflow(Workflow):
    """
    Enhanced workflow that provides detailed streaming of agent actions.
    This wraps the AgentWorkflow to add custom event streaming.
    """
    
    def __init__(self, agent_workflow: AgentWorkflow, user_id: str, **kwargs):
        super().__init__(**kwargs)
        self.agent_workflow = agent_workflow
        self.user_id = user_id
    
    @step
    async def process_request(self, ev: StartEvent) -> StopEvent:
        """Process product review analysis request with detailed streaming"""
        user_msg = ev.get("user_msg")
        conversation_history = ev.get("conversation_history", [])
        session_id = ev.get("session_id")
        
        print(f"\n{'='*80}")
        print(f"🎯 User Query: {user_msg}")
        if conversation_history:
            print(f"📜 History: {len(conversation_history)} messages")
        print(f"{'='*80}\n")
        
        # Create LlamaIndex Context object for this workflow run
        from llama_index.core.workflow import Context
        from app.core.llm.workflow.tools.review_analysis_tools import (
            register_workflow_context,
            clear_workflow_context,
            set_workflow_context_value,
        )
        
        # Clear any previous context for this user
        clear_workflow_context(self.user_id)
        
        # Create Context object and register it
        ctx = Context(self.agent_workflow)
        await ctx.store.set("user_id", self.user_id)
        register_workflow_context(self.user_id, ctx)
        
        # Load previous context state from session if available
        if session_id:
            from app.core.llm.simple_workflow.utils.context_persistence import load_context_from_session
            from app.database.session import get_async_session
            
            async with get_async_session() as db:
                context_loaded = await load_context_from_session(session_id, ctx, db)
                if context_loaded:
                    print(f"✅ Restored context state from session {session_id}")
        
        # Store conversation history in context for agents to access
        if conversation_history:
            await ctx.store.set("conversation_history", conversation_history)
            print(f"✅ Added {len(conversation_history)} messages to context")
        
        # Sync any data from sync store to Context
        from app.core.llm.workflow.tools.review_analysis_tools import _sync_context_store
        if self.user_id in _sync_context_store:
            for key, value in _sync_context_store[self.user_id].items():
                await ctx.store.set(key, value)
        
        # Create a task to run the agent workflow with Context
        handler = self.agent_workflow.run(
            user_msg=user_msg,
            initial_state={"user_id": self.user_id},
            ctx=ctx
        )
        
        current_agent = None
        response_started = False
        
        # Stream events from the agent workflow
        async for event in handler.stream_events():
            # Debug: Print event type and attributes
            # event_attrs = [attr for attr in dir(event) if not attr.startswith('_')]
            # print(f"\n[DEBUG] Event type: {type(event).__name__}, attrs: {event_attrs}")
            
            if isinstance(event, ToolCall):
                print(f"🔨 Calling Tool: {event.tool_name}: With arguments: {event.tool_kwargs}")

            elif isinstance(event, ToolCallResult):
                print(f"🔧 Tool Result ({event.tool_name}): Arguments: {event.tool_kwargs} ||||  Output: {event.tool_output}")
                print("================================================")

            # Format and display different event types
            if hasattr(event, 'agent_name'):
                current_agent = event.agent_name
                print(f"\n🤖 Agent: {event.agent_name.upper()}")
            
            # if hasattr(event, 'tool_call'):
            #     tool_call = event.tool_call
            #     print(f"   🔧 Tool: {tool_call.tool_name}")
            #     if hasattr(tool_call, 'tool_kwargs'):
            #         # Format kwargs nicely
            #         kwargs_str = ", ".join(f"{k}={v}" for k, v in tool_call.tool_kwargs.items() if k != 'user_id')
            #         print(f"   📝 Args: {kwargs_str}")
            
            # if hasattr(event, 'tool_output'):
            #     output = event.tool_output.content if hasattr(event.tool_output, 'content') else str(event.tool_output)
            #     # Truncate long outputs
            #     output_str = str(output)[:200]
            #     if len(str(output)) > 200:
            #         output_str += "..."
            #     print(f"   ✅ Result: {output_str}")
            
            # Stream the actual response text
            if hasattr(event, 'delta'):
                if not response_started:
                    print(f"\n   💬 Response: ", end='', flush=True)
                    response_started = True
                print(event.delta, end='', flush=True)
            
            if hasattr(event, 'msg'):
                msg = event.msg
                if hasattr(msg, 'content') and msg.content and not response_started:
                    # Fallback if streaming doesn't work
                    print(f"\n   💬 Response: {msg.content}")
        
        if response_started:
            print()  # New line after streaming
        
        # Get final result
        result = await handler
        
        # Save context state to session for next message
        if session_id:
            from app.core.llm.simple_workflow.utils.context_persistence import save_context_to_session
            from app.database.session import get_async_session
            
            try:
                async with get_async_session() as db:
                    await save_context_to_session(session_id, ctx, db)
                    await db.commit()
                    print(f"✅ Saved context state to session {session_id}")
            except Exception as e:
                print(f"⚠️  Failed to save context state: {e}")
        
        return StopEvent(result=result)



# ============================================================================
# Demo / Test Runner
# ============================================================================

async def main():
    """
    Run the multi-agent product review analysis system with test scenarios
    """
    # Get API key from settings
    api_key = settings.get_secret("openai_api_key")
    # Initialize LLM with lower temperature for more concise responses
    llm = OpenAI(model="gpt-5-mini", temperature=0.1, streaming=True, api_key=api_key)
    
    print("\n" + "="*80)
    print("LLAMAINDEX MULTI-AGENT PRODUCT REVIEW ANALYSIS SYSTEM")
    print("="*80)
    print("\nFeatures:")
    print("  ✓ Multiple specialized agents with handoffs")
    print("  ✓ Real-time streaming of agent actions")
    print("  ✓ Tool calling for data access, analysis, visualization")
    print("  ✓ PNG graph generation with plotly")
    print("  ✓ Context management across agents")
    print("="*80 + "\n")
    
    # Create the agent workflow
    test_user_id = "user_33gDeY7n9vlwAzkUBRgdS1Yy4lS"
    
    agent_workflow = create_product_review_workflow(llm, test_user_id)
    
    # Wrap it in our streaming workflow for better visibility
    workflow = StreamingProductReviewWorkflow(
        agent_workflow=agent_workflow,
        user_id=test_user_id,
        timeout=300,
        verbose=True
    )
    
    # Test scenarios with conversation history
    test_session_id = "test_session_123"
    conversation_history = []
    
    test_queries = [
        "What time is it?",
        "What are my main product gaps?",
        "What about sentiment?",  # Follow-up question - should reuse loaded data
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'█'*80}")
        print(f"TEST SCENARIO {i}/{len(test_queries)}")
        print(f"{'█'*80}")
        
        # Run the workflow with conversation history
        result = await workflow.run(
            user_msg=query,
            conversation_history=conversation_history,
            session_id=test_session_id
        )
        
        # Add to conversation history for next iteration
        conversation_history.append({"role": "user", "content": query})
        # Note: In real usage, the assistant response would also be added
        # For demo purposes, we're just tracking user messages
        
        # Pause between scenarios
        if i < len(test_queries):
            await asyncio.sleep(2)
    
    print("\n" + "="*80)
    print("Demo complete! 🎉")
    print("="*80 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
    except Exception as e:
        if "OPENAI_API_KEY" in str(e) or "api_key" in str(e).lower():
            print("\n❌ ERROR: Please set your OPENAI_API_KEY environment variable")
            print("   export OPENAI_API_KEY='your-key-here'")
        else:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

