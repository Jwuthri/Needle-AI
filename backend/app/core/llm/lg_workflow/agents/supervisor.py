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
    " following workers: {members}. \\n"
    "1. IF the user sends a general greeting (e.g. 'hello', 'hi') or a general question not related to data, search, or visualization, route to Reporter.\\n"
    "2. If the user needs to find or understand data, route to DataLibrarian.\\n"
    "3. IF the DataLibrarian has just provided dataset IDs or schema info, AND the user wants analysis, route to DataAnalyst.\\n"
    "4. IF the user wants to search the web or find external info, route to Researcher.\\n"
    "5. IF the user wants to see a plot, chart, or visualization, OR if the user says 'plot it', 'visualize this', etc., YOU MUST ROUTE TO Visualizer. Do not route to Reporter.\\n"
    "6. IF the DataLibrarian has answered the user's question and no further analysis is requested, route to Reporter.\\n"
    "7. IF the DataAnalyst, Researcher, or Visualizer has provided their results, route to Reporter.\\n"
    "CRITICAL RULE: IF a worker responds with text asking for clarification, offering help, or saying they are done, YOU MUST ROUTE TO Reporter. Do not route back to the same worker.\\n"
    "8. The Reporter will provide the final answer.\\n"
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
    # If the last message is from a worker (AIMessage) and not a tool call,
    # and the supervisor wants to route back to them, force a handoff to Reporter.
    last_message = messages[-1]
    if isinstance(last_message, AIMessage) and last_message.content:
        if not last_message.tool_calls:
            # Let's use a heuristic: If the Supervisor chooses a worker, and the last message is a text message from an AI,
            # it's highly likely a request for user input.
            if result["next"] in ["DataLibrarian", "DataAnalyst", "Researcher", "Visualizer"]:
                print(f"Supervisor chose {result['next']}, but last message was text from AI. Forcing Reporter.")
                return {"next": "Reporter"}

    return {"next": result["next"]}
