"""Researcher Agent - finds information from the internet."""
from app.core.llm.lg_workflow.tools.search import web_search_tool
from .base import create_agent, llm

# Researcher Agent
researcher_tools = [web_search_tool]
researcher_node = create_agent(
    llm,
    researcher_tools,
    "You are a Researcher. Your goal is to find information from the internet. "
    "Use `web_search_tool` to find current events, external data, or general knowledge. "
    "Synthesize the information you find and report it back."
)
