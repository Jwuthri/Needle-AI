"""Supervisor Agent - manages conversation between workers."""
from typing import Literal, TypedDict, List
from langchain_core.messages import BaseMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from .base import llm

# List of worker agents
members = ["DataLibrarian", "DataAnalyst", "Researcher", "Visualizer", "Reporter"]

# Supervisor system prompt
system_prompt = (
    "You are a supervisor tasked with managing a conversation between the"
    " following workers: {members}. \n"
    "ROUTING RULES (in priority order):\n"
    "1. IF the user sends a general greeting (e.g. 'hello', 'hi'), route to Reporter.\n"
    "\n"
    "2. CRITICAL - SIMPLE QUESTIONS: IF the user asks 'what datasets do I have' or 'list my datasets' or 'show my data':\n"
    "   → Route to DataLibrarian\n"
    "   → Then IMMEDIATELY route to Reporter (DO NOT route to DataAnalyst!)\n"
    "   → DataLibrarian's output fully answers the question - no analysis needed\n"
    "\n"
    "3. DATA ANALYSIS QUESTIONS: IF the user asks for analysis (sentiment, trends, statistics, clustering):\n"
    "   → IF this is the start OR DataLibrarian hasn't provided exact table name: route to DataLibrarian FIRST\n"
    "   → THEN route to DataAnalyst (only after DataLibrarian has identified table)\n"
    "   → Then route to Reporter\n"
    "\n"
    "4. CRITICAL: Generic names like 'reviews' or 'our data' are NOT actual table names\n"
    "   → Real table names look like: __user_user_123_tablename\n"
    "   → If user says generic name, route to DataLibrarian first\n"
    "\n"
    "5. IF the user wants web search or external info, route to Researcher.\n"
    "\n"
    "6. IF the user wants visualization (plot, chart, graph), route to Visualizer.\n"
    "\n"
    "7. CRITICAL - AFTER AGENTS COMPLETE:\n"
    "   → If DataLibrarian listed datasets AND user asked ONLY about datasets → Reporter\n"
    "   → If DataAnalyst finished analysis → Reporter\n"
    "   → If Researcher finished search → Reporter  \n"
    "   → If Visualizer created chart → Reporter\n"
    "\n"
    "8. DO NOT route to DataAnalyst if the question was already fully answered by DataLibrarian.\n"
    "\n"
    "Remember: Route to Reporter after workers complete their tasks. Don't keep bouncing between agents."
)

# Route response type
class RouteResponse(TypedDict):
    next: Literal["DataLibrarian", "DataAnalyst", "Researcher", "Visualizer", "Reporter"]

# Prompt template
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="messages"),
        (
            "system",
            "Given the conversation above, who should act next? Select one of: {members}.",
        ),
    ]
).partial(members=", ".join(members))


def supervisor_node(state):
    """Supervisor node that routes to the appropriate worker."""
    summary = state.get("summary", "")
    messages = state["messages"]
    if summary:
        system_message = SystemMessage(content=f"Previous conversation summary: {summary}")
        messages = [system_message] + messages

    supervisor_chain = prompt | llm.with_structured_output(RouteResponse)
    result = supervisor_chain.invoke({"messages": messages})
    
    # --- Loop Prevention Logic ---
    # Track the last few agent calls to detect infinite loops (3+ consecutive calls to same agent)
    # Extract agent names from recent AIMessages
    recent_agents = []
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            agent_name = getattr(msg, 'name', None)
            if agent_name and agent_name in members:
                recent_agents.append(agent_name)
            if len(recent_agents) >= 3:
                break
    
    # Count consecutive calls to the same agent
    if len(recent_agents) >= 2:
        # Check if last 2+ agents are the same and we're about to route to them again
        if all(agent == recent_agents[0] for agent in recent_agents) and result["next"] == recent_agents[0]:
            print(f"Preventing loop: {recent_agents[0]} called {len(recent_agents)} times consecutively. Forcing Reporter.")
            return {"next": "Reporter"}

    return {"next": result["next"]}
