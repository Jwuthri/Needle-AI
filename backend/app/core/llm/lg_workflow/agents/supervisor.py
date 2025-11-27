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
    "1. IF the user sends a general greeting (e.g. 'hello', 'hi') or a general question not related to data, search, or visualization, route to Reporter.\n"
    "2. IF the user asks about data analysis, sentiment, clustering, statistics, trends, or any data operations BUT no table name has been provided yet, route to DataLibrarian FIRST to help identify available datasets.\n"
    "3. If the user needs to find or understand data, route to DataLibrarian.\n"
    "4. IF the DataLibrarian has just provided table names or schema info, AND the user wants analysis (sentiment, clustering, trends, etc.), route to DataAnalyst to perform the analysis.\n"
    "5. SENTIMENT ANALYSIS: Questions about 'sentiment', 'feeling', 'tone', 'positive/negative reviews' should go to DataAnalyst (who has sentiment_analysis tool). Route to DataLibrarian ONLY if table name is unknown.\n"
    "6. IF the user wants to search the web or find external info, route to Researcher.\n"
    "7. IF the user wants to see a plot, chart, or visualization, OR if the user says 'plot it', 'visualize this', 'show as graph', 'display as pie chart', etc., YOU MUST ROUTE TO Visualizer. Do not route to Reporter.\n"
    "8. CRITICAL - VISUALIZATION FOLLOW-UPS: If the user asks to 'regenerate', 'redo', 'remake', 'update', or 'change' a graph/plot/chart mentioned in previous messages, route to Visualizer. Review the conversation history to understand what visualization they're referring to.\n"
    "9. IF the DataLibrarian has answered the user's question and no further analysis is requested, route to Reporter.\n"
    "10. IF the DataAnalyst, Researcher, or Visualizer has provided their results, route to Reporter.\n"
    "11. The Reporter will provide the final answer.\n"
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
