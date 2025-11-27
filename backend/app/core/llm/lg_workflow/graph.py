from typing import Annotated, List, TypedDict
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, RemoveMessage, SystemMessage
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages
import dotenv
from typing import Annotated, List, TypedDict, Union, Literal, Optional
# Import agents from the agents module
from app.core.llm.lg_workflow.agents.librarian import create_librarian_node
from app.core.llm.lg_workflow.agents.analyst import create_analyst_node
from app.core.llm.lg_workflow.agents.visualizer import create_visualizer_node
from app.core.llm.lg_workflow.agents import (
    researcher_node,
    reporter_node,
    supervisor_node,
    members,
)
from app.core.llm.lg_workflow.agents.base import settings

dotenv.load_dotenv()


# --- State Definition ---
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    next: str
    summary: str

def summarize_conversation(state: AgentState):
    summary = state.get("summary", "")
    messages = state["messages"]

    if len(messages) > 20:
        print("===== Summarizing conversation =====")
        summarize_model = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, api_key=settings.openai_api_key)
        summary_message = SystemMessage(content=f"Distill the following conversation into a concise summary. Include key actions and results. Current summary: {summary}")
        response = summarize_model.invoke([summary_message] + messages[:-2])

        new_summary = response.content
        delete_messages = [RemoveMessage(id=m.id) for m in messages[:-2]]

        return {"summary": new_summary, "messages": delete_messages}
    return {}

# --- Graph Construction ---
def create_workflow(user_id: str, dataset_table_name: Optional[str] = None):
    """
    Create the multi-agent workflow.
    
    Args:
        user_id: The user's ID for data access
        dataset_table_name: Optional - if provided, agents will focus exclusively on this dataset
    """
    workflow = StateGraph(AgentState)
    
    # Create agent nodes with user_id and optional focused dataset
    librarian_node = create_librarian_node(user_id, dataset_table_name)
    analyst_node = create_analyst_node(user_id, dataset_table_name)
    visualizer_node = create_visualizer_node(user_id, dataset_table_name)

    workflow.add_node("Supervisor", supervisor_node)
    workflow.add_node("DataLibrarian", librarian_node)
    workflow.add_node("DataAnalyst", analyst_node)
    workflow.add_node("Researcher", researcher_node)
    workflow.add_node("Visualizer", visualizer_node)
    workflow.add_node("Reporter", reporter_node)
    workflow.add_node("Summarize", summarize_conversation)

    def check_summary(state: AgentState) -> Literal["Summarize", "Supervisor"]:
        if len(state["messages"]) > 20:
            return "Summarize"
        return "Supervisor"

    workflow.add_conditional_edges(START, check_summary)
    workflow.add_edge("Summarize", "Supervisor")

    # Edges from workers back to Supervisor
    workflow.add_edge("DataLibrarian", "Supervisor")
    workflow.add_edge("DataAnalyst", "Supervisor")
    workflow.add_edge("Researcher", "Supervisor")
    workflow.add_edge("Visualizer", "Supervisor")
    workflow.add_edge("Reporter", END) # Reporter finishes the flow

    # Conditional edge for the Supervisor's decision
    def should_continue(state: AgentState) -> str:
        return state["next"]

    workflow.add_conditional_edges("Supervisor", should_continue)

    # Compile
    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer)
    return app
