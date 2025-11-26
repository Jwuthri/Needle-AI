"""Reporter Agent - synthesizes the final answer."""
from .base import create_agent, llm

# Reporter Agent
reporter_node = create_agent(
    llm,
    [], # No tools for the reporter, just context
    "You are the Reporter. Your job is to read the conversation history and provide the final answer to the user. "
    "Summarize the findings from the other agents. "
    "Be concise but comprehensive. "
    "When you are done, the conversation will end. Never imagine that the user sees the workflow steps he will only see his query and your final answer."
)
