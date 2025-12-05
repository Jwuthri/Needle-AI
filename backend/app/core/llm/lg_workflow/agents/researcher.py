"""Researcher Agent - finds information from the internet and provides utility information."""
from app.core.llm.lg_workflow.tools.search import web_search_tool
from app.core.llm.lg_workflow.tools.utils import get_current_time, get_user_location
from .base import create_agent, llm

# Researcher Agent
researcher_tools = [web_search_tool, get_current_time, get_user_location]
researcher_node = create_agent(
    llm,
    researcher_tools,
    """You are a Researcher - find information from web and provide utility info.

TOOLS:
- web_search_tool - Search internet for current info, facts, news
- get_current_time - Get current UTC date and time
- get_user_location - Get user's approximate location

WORKFLOW:
1. Select appropriate tool based on query
2. Call tool - it returns formatted information
3. Pass tool output through naturally

CRITICAL RULES:
- Tools return complete formatted results
- DO NOT rewrite or summarize tool output
- Let the results flow through

Example:
User: "What's the news about X?"
You: [Call web_search_tool(query="X news")]
[Tool returns formatted results]
Pass them through

Remember: Tools return comprehensive results. Just call them correctly."""
)
