"""
Multi-Agent Pipeline with Agno
Demonstrates streaming communication between agents with structured outputs
"""

import os
from typing import Iterator, Optional
from pydantic import BaseModel, Field
from agno.agent import Agent
from agno.team import Team
from agno.models.openai import OpenAIChat

# Set your API key
os.environ["OPENAI_API_KEY"] = "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"

def capture_agent_output(run_output) -> None:
    print(f"Agent output: {run_output.content}")


# Define structured output for intent detection
class IntentOutput(BaseModel):
    intent: str = Field(description="The detected intent (e.g., 'order_status', 'product_info', 'complaint')")
    confidence: float = Field(description="Confidence score between 0 and 1")
    extracted_entities: Optional[dict] = Field(default={}, description="Any entities extracted")


# Agent 1: Intent Detector
intent_detector = Agent(
    name="Intent Detector",
    role="Analyze user queries and detect their intent",
    model=OpenAIChat(id="gpt-4o-mini"),
    instructions=[
        "You are an intent detection specialist.",
        "Analyze the user's query and determine their intent.",
        "Provide a confidence score for your detection.",
        "Extract any relevant entities (order IDs, product names, dates, etc.)",
        "Common intents: order_status, product_info, complaint, refund, general_inquiry"
    ],
    output_schema=IntentOutput,
    markdown=True,
    # post_hooks=[capture_agent_output]
)


# Agent 2: Answer Generator
answer_agent = Agent(
    name="Answer Agent",
    role="Generate helpful responses based on detected intent",
    model=OpenAIChat(id="gpt-4o-mini"),
    instructions=[
        "You are a customer service agent.",
        "Based on the detected intent and entities, provide a helpful response.",
        "Be friendly, concise, and actionable.",
        "If an order ID is mentioned, acknowledge it specifically.",
        "Provide next steps when appropriate."
    ],
    markdown=True,
    # post_hooks=[capture_agent_output]
)


# Create the team
customer_service_team = Team(
    name="Customer Service Team",
    members=[intent_detector, answer_agent],
    # mode="collaborate",
    show_members_responses=False,
)


def run_pipeline_with_streaming(query: str):
    """
    Run the pipeline and stream outputs from each agent with type detection
    """
    print(f"\n{'='*60}")
    print(f"USER QUERY: {query}")
    print(f"{'='*60}\n")
    
    response_stream: Iterator = customer_service_team.run(
        query, stream=True, stream_intermediate_steps=False, show_members_responses=False, debug_mode=False
    )
    
    current_agent = None
    full_response = ""
    for chunk in response_stream:
        if hasattr(chunk, 'event'):
            print(f"\n[DEBUG: {chunk.event}]", end="")
            # Skip these events to avoid duplicates
            if chunk.event in ["TeamRunCompleted", "TeamRunResponse"]:
                continue
                
            agent_name = getattr(chunk, 'agent_id', None) or getattr(chunk, 'agent', None)
            
            if agent_name and agent_name != current_agent:
                current_agent = agent_name
                print(f"\n🤖 [{current_agent}]")
            
            # Only print content from actual streaming events
            if chunk.event in ["RunResponse", "RunContent", "AgentRunContent"]:
                if hasattr(chunk, 'content') and chunk.content:
                    if isinstance(chunk.content, BaseModel):
                        print(f"  📊 {chunk.content}")
                    elif isinstance(chunk.content, str):
                        print(chunk.content, end="", flush=True)
        
    print("\n")
    return full_response



def run_pipeline_non_streaming(query: str):
    """
    Alternative: Run without streaming to see structured output clearly
    """
    print(f"\n{'='*60}")
    print(f"USER QUERY: {query}")
    print(f"{'='*60}\n")
    
    # Get response from the team
    response = customer_service_team.run(query, stream=False)
    
    print("\n📊 FINAL RESPONSE:")
    print(response.content)
    
    # If you want to access individual agent outputs:
    if hasattr(response, 'messages'):
        print("\n📝 AGENT MESSAGES:")
        for msg in response.messages:
            if hasattr(msg, 'role') and hasattr(msg, 'content'):
                print(f"\n[{msg.role}]: {msg.content}")
    
    return response


# Alternative approach: Manual orchestration for more control
def manual_pipeline_with_streaming(query: str):
    """
    Manually orchestrate agents for maximum control over streaming
    """
    print(f"\n{'='*60}")
    print(f"USER QUERY: {query}")
    print(f"{'='*60}\n")
    
    # Step 1: Intent Detection
    print("\n🔍 STEP 1: INTENT DETECTION")
    print("-" * 40)
    
    intent_response = intent_detector.run(query, stream=False)
    intent_data = intent_response.content
    
    print(f"\nIntent: {intent_data.intent}")
    print(f"Confidence: {intent_data.confidence}")
    print(f"Entities: {intent_data.extracted_entities}")
    
    # Step 2: Generate Answer based on intent
    print("\n\n💬 STEP 2: GENERATING ANSWER")
    print("-" * 40)
    
    answer_prompt = f"""
    Based on this intent analysis:
    - Intent: {intent_data.intent}
    - Confidence: {intent_data.confidence}
    - Entities: {intent_data.extracted_entities}
    
    Original query: {query}
    
    Generate an appropriate response.
    """
    
    print("\n")
    answer_stream = answer_agent.run(answer_prompt, stream=True)
    
    full_answer = ""
    for chunk in answer_stream:
        if hasattr(chunk, 'content') and chunk.content:
            print(chunk.content, end="", flush=True)
            full_answer += chunk.content
    
    print("\n")
    
    return {
        "intent": intent_data,
        "answer": full_answer
    }


if __name__ == "__main__":
    # Example queries to test
    test_queries = [
        "What is my order status? My order ID is #12345",
        "I want to return a damaged product",
        "Do you have the iPhone 15 in stock?",
    ]
    
    # Choose your preferred method:
    
    # Method 1: Team with streaming (simplest)
    print("\n" + "="*60)
    print("METHOD 1: TEAM WITH STREAMING")
    print("="*60)
    run_pipeline_with_streaming(test_queries[0])
    
    # # Method 2: Manual orchestration (most control)
    # print("\n" + "="*60)
    # print("METHOD 2: MANUAL ORCHESTRATION")
    # print("="*60)
    # manual_pipeline_with_streaming(test_queries[1)
    
    # # Method 3: Non-streaming (clearest structure)
    # print("\n" + "="*60)
    # print("METHOD 3: NON-STREAMING")
    # print("="*60)
    # run_pipeline_non_streaming(test_queries[2])