"""Agent modules for the LangGraph workflow."""
from .researcher import researcher_node
from .reporter import reporter_node
from .supervisor import supervisor_node

# Export the list of agent members for supervisor
members = ["DataLibrarian", "DataAnalyst", "Coder", "Researcher", "Visualizer", "Reporter"]

__all__ = [
    "researcher_node",
    "reporter_node", 
    "supervisor_node",
    "members",
]
