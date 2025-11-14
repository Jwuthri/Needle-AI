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
from app.core.llm.workflow.agents import (
    create_coordinator_agent,
    create_general_assistant_agent,
    create_data_discovery_agent,
    create_gap_analysis_agent,
    create_sentiment_analysis_agent,
    create_trend_analysis_agent,
    create_clustering_agent,
    create_visualization_agent,
    create_report_writer_agent,
)
from llama_index.core.agent.workflow import AgentWorkflow
from llama_index.core.workflow import Event, StartEvent, StopEvent, Workflow, step, Context
from llama_index.llms.openai import OpenAI

settings = get_settings()

# Get API key from settings
api_key = settings.get_secret("openai_api_key")


# ============================================================================
# Create Agent Workflow with Multiple Specialized Agents
# ============================================================================


def create_product_review_workflow(llm: OpenAI, user_id: str) -> AgentWorkflow:
    """
    Create a multi-agent product review analysis workflow with specialized agents.
    
    Each agent has:
    - Specific tools for their domain
    - A system prompt defining their role
    - Ability to hand off to other agents
    
    Args:
        llm: OpenAI LLM instance
        user_id: User ID to pre-bind to all tools
    """
    
    # Create all agents using factory functions with pre-bound user_id
    coordinator_agent = create_coordinator_agent(llm, user_id)
    general_assistant_agent = create_general_assistant_agent(llm, user_id)
    data_discovery_agent = create_data_discovery_agent(llm, user_id)
    gap_analysis_agent = create_gap_analysis_agent(llm, user_id)
    sentiment_analysis_agent = create_sentiment_analysis_agent(llm, user_id)
    trend_analysis_agent = create_trend_analysis_agent(llm, user_id)
    clustering_agent = create_clustering_agent(llm, user_id)
    visualization_agent = create_visualization_agent(llm, user_id)
    report_writer_agent = create_report_writer_agent(llm, user_id)
    
    # Create the Agent Workflow
    workflow = AgentWorkflow(
        agents=[
            coordinator_agent,
            general_assistant_agent,
            data_discovery_agent,
            gap_analysis_agent,
            sentiment_analysis_agent,
            trend_analysis_agent,
            clustering_agent,
            visualization_agent,
            report_writer_agent,
        ],
        root_agent="coordinator",  # Start with coordinator
        timeout=300,  # 5 minutes for complex analysis
    )
    
    return workflow


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
        
        print(f"\n{'='*80}")
        print(f"🎯 User Query: {user_msg}")
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
            # Format and display different event types
            if hasattr(event, 'agent_name'):
                current_agent = event.agent_name
                print(f"\n🤖 Agent: {event.agent_name.upper()}")
            
            if hasattr(event, 'tool_call'):
                tool_call = event.tool_call
                print(f"   🔧 Tool: {tool_call.tool_name}")
                if hasattr(tool_call, 'tool_kwargs'):
                    # Format kwargs nicely
                    kwargs_str = ", ".join(f"{k}={v}" for k, v in tool_call.tool_kwargs.items() if k != 'user_id')
                    print(f"   📝 Args: {kwargs_str}")
            
            if hasattr(event, 'tool_output'):
                output = event.tool_output.content if hasattr(event.tool_output, 'content') else str(event.tool_output)
                # Truncate long outputs
                output_str = str(output)[:200]
                if len(str(output)) > 200:
                    output_str += "..."
                print(f"   ✅ Result: {output_str}")
            
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
        
        return StopEvent(result=result)


# ============================================================================
# Convenience Functions
# ============================================================================


async def create_and_run_workflow(
    user_msg: str,
    user_id: str,
    llm: Optional[OpenAI] = None
) -> Any:
    """
    Create and run the product review analysis workflow.
    
    Args:
        user_msg: User's query message
        user_id: User ID for data access
        llm: Optional LLM instance (creates default if not provided)
        
    Returns:
        Workflow result
    """
    if llm is None:
        llm = OpenAI(
            model="gpt-4",
            temperature=0.3,
            streaming=True,
            api_key=api_key
        )
    
    # Create the agent workflow
    agent_workflow = create_product_review_workflow(llm, user_id)
    
    # Wrap it in our streaming workflow
    workflow = StreamingProductReviewWorkflow(
        agent_workflow=agent_workflow,
        user_id=user_id,
        timeout=300,
        verbose=True
    )
    
    # Run the workflow
    result = await workflow.run(user_msg=user_msg)
    
    return result


# ============================================================================
# Demo / Test Runner
# ============================================================================

async def main():
    """
    Run the multi-agent product review analysis system with test scenarios
    """
    
    # Initialize LLM
    llm = OpenAI(model="gpt-4", temperature=0.3, streaming=True, api_key=api_key)
    
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
    test_user_id = "test-user-1"
    agent_workflow = create_product_review_workflow(llm, test_user_id)
    
    # Wrap it in our streaming workflow for better visibility
    workflow = StreamingProductReviewWorkflow(
        agent_workflow=agent_workflow,
        user_id=test_user_id,
        timeout=300,
        verbose=True
    )
    
    # Test scenarios
    test_queries = [
        "What time is it?",
        "What are my main product gaps?",
        "Show me sentiment trends over time",
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'█'*80}")
        print(f"TEST SCENARIO {i}/{len(test_queries)}")
        print(f"{'█'*80}")
        
        # Run the workflow
        result = await workflow.run(user_msg=query)
        
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

