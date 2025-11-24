from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool

@tool
def web_search_tool(query: str) -> str:
    """
    Search the web for information using DuckDuckGo.
    Use this tool when you need to find current events, external data, or general knowledge 
    that is not available in the local datasets.
    """
    search = DuckDuckGoSearchRun()
    return search.invoke(query)
