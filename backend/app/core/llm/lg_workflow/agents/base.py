"""Base utilities for agent creation."""
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from app.core.config.settings import get_settings

# Initialize settings and LLM
settings = get_settings()
llm = ChatOpenAI(
    model="gpt-5.1", 
    temperature=0.1, 
    api_key=settings.openai_api_key,
    streaming=True  # Enable streaming for token-by-token output
)
cheap_llm = ChatOpenAI(
    model="gpt-4o-mini", 
    temperature=0.1, 
    api_key=settings.openai_api_key,
    streaming=True  # Enable streaming for token-by-token output
)


def create_agent(llm, tools, system_prompt: str):
    """Creates a standard ReAct agent node."""
    # We use the prebuilt create_react_agent which handles tool calling loops
    agent = create_react_agent(llm, tools, prompt=system_prompt)
    return agent
