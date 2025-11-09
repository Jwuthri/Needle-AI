"""
Multi-Agent Customer Support System using LlamaIndex Workflow
================================================

This implements a real multi-agent customer support system with:
- Multiple specialized agents (Coordinator, Order, Refund, Product)
- Agent handoffs between specialists
- Tool calling capabilities
- Streaming support to see each agent's actions
- State management with Context

Install required packages:
pip install llama-index-core llama-index-llms-openai llama-index-agent-openai llama-index-utils-workflow
"""

import asyncio
import os
from typing import Any, List

from app.core.config.settings import get_settings
from llama_index.core.agent.workflow import (
    AgentWorkflow,
    FunctionAgent,
)
from llama_index.core.tools import FunctionTool
from llama_index.core.llms import ChatMessage
from llama_index.core.workflow import (
    Event,
    StartEvent,
    StopEvent,
    Workflow,
    step,
    Context,
)
from llama_index.llms.openai import OpenAI
settings = get_settings()

# Get API key from settings
api_key = settings.get_secret("openai_api_key")
# ============================================================================
# Tool Definitions - Functions that agents can call
# ============================================================================


def search_knowledge_base(query: str, category: str = "general") -> str:
    """Search the knowledge base for company policies and information.
    
    Args:
        query: The search query
        category: Category to search in (refund, shipping, account, products)
    """
    knowledge = {
        "refund": {
            "policy": "Full refund within 30 days of purchase",
            "process": "Contact support with order number, we'll process within 2-3 business days",
            "exceptions": "Digital downloads are non-refundable after download"
        },
        "shipping": {
            "standard": "5-7 business days, free on orders over $50",
            "express": "2-3 business days, $15 flat rate",
            "international": "10-15 business days, calculated at checkout"
        },
        "account": {
            "reset_password": "Use 'Forgot Password' link on login page",
            "update_email": "Go to Account Settings > Profile > Update Email",
            "delete_account": "Contact support for account deletion requests"
        },
        "products": {
            "warranty": "1-year limited warranty on all products",
            "compatibility": "Check product page for compatibility information",
            "stock": "Updated daily, sign up for restock notifications"
        }
    }
    
    result = knowledge.get(category, {})
    if result:
        return f"Knowledge Base - {category.upper()}:\n" + "\n".join(
            f"  • {k}: {v}" for k, v in result.items()
        )
    return f"No information found for category: {category}"


def check_order_status(order_id: str) -> str:
    """Check the status of a customer order.
    
    Args:
        order_id: The order ID to check (e.g., ORD-12345)
    """
    # Simulate order lookup
    if order_id.upper().startswith("ORD"):
        return f"""Order Status for {order_id}:
  • Status: Shipped
  • Tracking Number: TRK123456789
  • Estimated Delivery: November 12, 2025
  • Items: Premium Headphones (1x) - $199.99
  • Shipping Address: 123 Main St, Oakland, CA"""
    else:
        return f"Error: Order {order_id} not found in system. Please verify the order ID."


def process_refund(order_id: str, reason: str = "Customer request") -> str:
    """Process a refund for an order.
    
    Args:
        order_id: The order ID to refund
        reason: Reason for the refund
    """
    return f"""Refund Processed for {order_id}:
  • Refund Amount: $199.99
  • Status: Approved
  • Processing Time: 3-5 business days
  • Refund ID: REF-{order_id.split('-')[-1]}
  • Method: Original payment method
  
Your refund has been approved and will be processed shortly."""


def check_product_availability(product_name: str) -> str:
    """Check if a product is in stock and available.
    
    Args:
        product_name: Name of the product to check
    """
    products = {
        "premium headphones": {
            "in_stock": True,
            "quantity": 47,
            "price": 199.99
        },
        "wireless mouse": {
            "in_stock": True,
            "quantity": 23,
            "price": 49.99
        },
        "mechanical keyboard": {
            "in_stock": False,
            "quantity": 0,
            "price": 149.99,
            "restock": "November 15, 2025"
        }
    }
    
    prod_key = product_name.lower()
    product = products.get(prod_key, {
        "in_stock": False,
        "quantity": 0,
        "price": 0
    })
    
    if product["in_stock"]:
        return f"""Product: {product_name.title()}
  • Status: In Stock ✓
  • Available: {product['quantity']} units
  • Price: ${product['price']}
  • Ready to ship within 1 business day"""
    else:
        restock = product.get("restock", "Unknown")
        return f"""Product: {product_name.title()}
  • Status: Out of Stock ✗
  • Expected Restock: {restock}
  • You can sign up for restock notifications on the product page"""


def create_support_ticket(issue: str, priority: str = "normal") -> str:
    """Create a support ticket for complex issues.
    
    Args:
        issue: Description of the issue
        priority: Priority level (low, normal, high, urgent)
    """
    import datetime
    ticket_id = f"TICKET-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    return f"""Support Ticket Created:
  • Ticket ID: {ticket_id}
  • Priority: {priority.upper()}
  • Status: Open
  • Issue: {issue}
  • Estimated Response: 2-4 hours
  
A specialist will contact you soon to assist with your request."""


# ============================================================================
# Create Agent Workflow with Multiple Specialized Agents
# ============================================================================

def create_customer_support_workflow(llm: OpenAI) -> AgentWorkflow:
    """
    Create a multi-agent customer support workflow with specialized agents.
    
    Each agent has:
    - Specific tools for their domain
    - A system prompt defining their role
    - Ability to hand off to other agents
    """
    
    # Create tools
    search_kb_tool = FunctionTool.from_defaults(fn=search_knowledge_base)
    check_order_tool = FunctionTool.from_defaults(fn=check_order_status)
    process_refund_tool = FunctionTool.from_defaults(fn=process_refund)
    check_product_tool = FunctionTool.from_defaults(fn=check_product_availability)
    create_ticket_tool = FunctionTool.from_defaults(fn=create_support_ticket)
    
    # ========================================================================
    # Coordinator Agent - Routes customers to specialists
    # ========================================================================
    coordinator_agent = FunctionAgent(
        name="coordinator",
        description="First point of contact. Routes customers to the right specialist agent.",
        system_prompt="""You are a friendly customer service coordinator. Your role is to:
1. Greet customers warmly
2. Understand their needs
3. Route them to the appropriate specialist:
   - Order Agent: for order tracking, shipping, delivery questions
   - Refund Agent: for returns, refunds, cancellations
   - Product Agent: for product info, availability, specifications

When handing off, explain to the customer which specialist will help them.
Be concise and helpful.""",
        tools=[search_kb_tool],
        llm=llm,
    )
    
    # ========================================================================
    # Order Agent - Handles order tracking and shipping
    # ========================================================================
    order_agent = FunctionAgent(
        name="order_agent",
        description="Specialist in order tracking, shipping, and delivery inquiries",
        system_prompt="""You are an order tracking specialist. You help customers:
1. Track their orders by order ID
2. Answer shipping and delivery questions
3. Provide tracking information
4. Explain shipping policies

If a customer wants a refund or return, hand off to the Refund Agent.
Always ask for the order ID if not provided.""",
        tools=[check_order_tool, search_kb_tool],
        llm=llm,
    )
    
    # ========================================================================
    # Refund Agent - Processes refunds and returns
    # ========================================================================
    refund_agent = FunctionAgent(
        name="refund_agent",
        description="Specialist in processing refunds, returns, and cancellations",
        system_prompt="""You are a refund specialist. You help customers:
1. Process refunds and returns
2. Explain refund policies
3. Check order status before refunding
4. Handle cancellations

Always verify the order exists before processing a refund.
Be empathetic and clear about the refund process and timeline.""",
        tools=[process_refund_tool, check_order_tool, search_kb_tool],
        llm=llm,
    )
    
    # ========================================================================
    # Product Agent - Answers product questions
    # ========================================================================
    product_agent = FunctionAgent(
        name="product_agent",
        description="Specialist in product information, availability, and specifications",
        system_prompt="""You are a product specialist. You help customers:
1. Check product availability and stock
2. Answer product specification questions
3. Provide pricing information
4. Explain warranty and compatibility

If they want to check an order after asking about products, hand off to the Order Agent.""",
        tools=[check_product_tool, search_kb_tool],
        llm=llm,
    )
    
    # ========================================================================
    # Create the Agent Workflow
    # ========================================================================
    workflow = AgentWorkflow(
        agents=[
            coordinator_agent,
            order_agent,
            refund_agent,
            product_agent,
        ],
        root_agent="coordinator",  # Start with coordinator
        timeout=120,
    )
    
    return workflow


# ============================================================================
# Custom Workflow for Enhanced Streaming and Visualization
# ============================================================================

class CustomerSupportEvent(Event):
    """Custom event to track workflow progress"""
    agent_name: str
    action: str
    details: dict


class StreamingCustomerSupportWorkflow(Workflow):
    """
    Enhanced workflow that provides detailed streaming of agent actions.
    This wraps the AgentWorkflow to add custom event streaming.
    """
    
    def __init__(self, agent_workflow: AgentWorkflow, **kwargs):
        super().__init__(**kwargs)
        self.agent_workflow = agent_workflow
    
    @step
    async def process_request(self, ev: StartEvent) -> StopEvent:
        """Process customer request with detailed streaming"""
        user_msg = ev.get("user_msg")
        
        print(f"\n{'='*80}")
        print(f"🎯 Customer Request: {user_msg}")
        print(f"{'='*80}\n")
        
        # Create a task to run the agent workflow
        handler = self.agent_workflow.run(user_msg=user_msg)
        
        current_agent = None
        response_started = False
        
        # Stream events from the agent workflow
        async for event in handler.stream_events():
            # Format and display different event types
            if hasattr(event, 'agent_name'):
                current_agent = event.agent_name
                print(f"\n🤖 Agent: {event.agent_name}")
            
            if hasattr(event, 'tool_call'):
                tool_call = event.tool_call
                print(f"   🔧 Tool: {tool_call.tool_name}")
                print(f"   📝 Args: {tool_call.tool_kwargs}")
            
            if hasattr(event, 'tool_output'):
                output = event.tool_output.content
                print(f"   ✅ Result: {output[:150]}{'...' if len(output) > 150 else ''}")
            
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
        
        # print(f"\n{'─'*80}")
        # print(f"✨ Final Response:")
        # print(f"{'─'*80}")
        
        # # Handle different result structures
        # if isinstance(result, dict):
        #     if 'response' in result:
        #         response_content = result['response'].message.content
        #     elif 'result' in result:
        #         response_content = result['result']
        #     else:
        #         response_content = str(result)
        # else:
        #     response_content = str(result)
        
        # print(response_content)
        # print()
        
        return StopEvent(result=result)


# ============================================================================
# Demo / Test Runner
# ============================================================================

async def main():
    """
    Run the multi-agent customer support system with test scenarios
    """
    
    # Set up your OpenAI API key
    # os.environ["OPENAI_API_KEY"] = "your-api-key-here"
    
    # Initialize LLM
    llm = OpenAI(model="gpt-4", temperature=0.3)
    
    print("\n" + "="*80)
    print("LLAMAINDEX MULTI-AGENT CUSTOMER SUPPORT SYSTEM")
    print("="*80)
    print("\nFeatures:")
    print("  ✓ Multiple specialized agents with handoffs")
    print("  ✓ Real-time streaming of agent actions")
    print("  ✓ Tool calling for order tracking, refunds, products")
    print("  ✓ Context management across agents")
    print("="*80 + "\n")
    
    # Create the agent workflow
    agent_workflow = create_customer_support_workflow(llm)
    
    # Wrap it in our streaming workflow for better visibility
    workflow = StreamingCustomerSupportWorkflow(
        agent_workflow=agent_workflow,
        timeout=120,
        verbose=True
    )
    
    # Test scenarios
    test_queries = [
        "What's the status of my order ORD-12345?",
        "I want to return order ORD-12345 and get a refund",
        "Are the Premium Headphones in stock?",
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


async def simple_demo():
    """
    Simpler demo that shows text streaming clearly
    """
    
    # Set up your OpenAI API key
    # os.environ["OPENAI_API_KEY"] = "your-api-key-here"
    
    llm = OpenAI(model="gpt-4", temperature=0.3)
    
    # Create workflow
    workflow = create_customer_support_workflow(llm)
    
    # Run a query
    print("\n" + "="*80)
    print("🎯 Customer: What's the status of my order ORD-12345?")
    print("="*80 + "\n")
    
    handler = workflow.run(user_msg="What's the status of my order ORD-12345?")
    
    current_agent = None
    response_text = ""
    
    # Stream events with text streaming
    async for event in handler.stream_events():
        if hasattr(event, 'agent_name') and event.agent_name != current_agent:
            current_agent = event.agent_name
            print(f"\n🤖 {event.agent_name.upper()}")
            print("   " + "─"*60)
        
        if hasattr(event, 'tool_call'):
            print(f"   🔧 Calling: {event.tool_call.tool_name}({event.tool_call.tool_kwargs})")
        
        if hasattr(event, 'tool_output'):
            print(f"   ✅ Tool completed")
        
        # Stream response text token by token
        if hasattr(event, 'delta') and event.delta:
            if not response_text:
                print(f"\n   💬 ", end='', flush=True)
            print(event.delta, end='', flush=True)
            response_text += event.delta
    
    if response_text:
        print("\n")
    
    # Get final result
    result = await handler
    
    print("\n" + "─"*80)
    print("✨ Complete!")
    print("─"*80 + "\n")


async def interactive_demo():
    """
    Interactive demo where you can type your own queries
    """
    
    # os.environ["OPENAI_API_KEY"] = "your-api-key-here"
    
    llm = OpenAI(model="gpt-5-mini", temperature=0.3, streaming=True, api_key=api_key)  # Enable streaming!
    workflow = create_customer_support_workflow(llm)
    
    print("\n" + "="*80)
    print("🎯 INTERACTIVE CUSTOMER SUPPORT - Type 'quit' to exit")
    print("="*80)
    
    while True:
        print("\n" + "─"*80)
        user_input = input("👤 You: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("\nGoodbye! 👋\n")
            break
        
        if not user_input:
            continue
        
        print()
        
        handler = workflow.run(user_msg=user_input)
        
        current_agent = None
        
        async for event in handler.stream_events():
            if hasattr(event, 'agent_name') and event.agent_name != current_agent:
                current_agent = event.agent_name
                print(f"🤖 {event.agent_name.upper()}")
            
            if hasattr(event, 'tool_call'):
                print(f"   🔧 {event.tool_call.tool_name}(...)")
            
            # Stream the response text
            if hasattr(event, 'delta') and event.delta:
                print(event.delta, end='', flush=True)
        
        print("\n")
        await handler  # Ensure completion


# ============================================================================
# Usage Instructions
# ============================================================================

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║                  LlamaIndex Multi-Agent Workflow Demo                    ║
╚══════════════════════════════════════════════════════════════════════════╝

SETUP:
1. Install dependencies:
   pip install llama-index-core llama-index-llms-openai llama-index-agent-openai

2. Set your OpenAI API key:
   export OPENAI_API_KEY="your-key-here"
   # OR uncomment the line in the code

3. Run the demo:
   python this_file.py

FEATURES:
• Coordinator Agent - Routes to specialists
• Order Agent - Tracks orders and shipping
• Refund Agent - Processes refunds and returns
• Product Agent - Checks product availability

• STREAMING: Responses are streamed token-by-token in real-time!
• Agents can hand off to each other based on conversation context
• Each agent has specialized tools for their domain

ARCHITECTURE:
This uses LlamaIndex's AgentWorkflow which orchestrates multiple
FunctionAgent instances. Each agent can:
- Call tools/functions to perform actions
- Hand off control to other agents when needed
- Maintain conversation context
- Stream their actions and responses in real-time

CHOOSE YOUR MODE:
""")
    
    import sys
    
    mode = None
    if len(sys.argv) > 1:
        mode = sys.argv[1]
    else:
        print("1. Full Demo (automated test scenarios)")
        print("2. Interactive Mode (type your own questions)")
        print("3. Simple Demo (single quick test)")
        choice = input("\nSelect mode (1/2/3): ").strip()
        
        if choice == "1":
            mode = "full"
        elif choice == "2":
            mode = "interactive"
        elif choice == "3":
            mode = "simple"
        else:
            mode = "full"
    
    # Run the selected demo
    try:
        if mode == "interactive":
            asyncio.run(interactive_demo())
        elif mode == "simple":
            asyncio.run(simple_demo())
        else:
            asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
    except Exception as e:
        if "OPENAI_API_KEY" in str(e):
            print("\n❌ ERROR: Please set your OPENAI_API_KEY environment variable")
            print("   export OPENAI_API_KEY='your-key-here'")
        else:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()