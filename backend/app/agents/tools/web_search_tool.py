"""
Web Search Tool - Searches the internet using DuckDuckGo (free).
"""

from typing import Any, Dict, List, Optional

from app.agents.tools.base_tool import BaseTool, ToolResult
from app.utils.logging import get_logger

logger = get_logger("web_search_tool")


class WebSearchTool(BaseTool):
    """
    Searches the web using DuckDuckGo for external information.
    
    Use when query needs current information, competitor data,
    industry trends, or definitions not in the local database.
    """
    
    def __init__(self):
        super().__init__()
        self._search_client = None
    
    @property
    def name(self) -> str:
        return "web_search"
    
    @property
    def description(self) -> str:
        return """Search the internet for current information, news, competitor data, or external knowledge.

Use this tool when:
- Query asks about current events, news, or recent information
- User mentions competitors or market trends
- Query needs external facts or definitions
- Local database doesn't have the required information

Parameters:
- query: Search query (what to search for)
- max_results: Maximum number of results to return (default 5)

Returns search results with titles, snippets, and URLs.
"""
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    
    def _get_search_client(self):
        """Lazy load the DuckDuckGo search client."""
        if self._search_client is None:
            try:
                from duckduckgo_search import DDGS
                self._search_client = DDGS()
            except ImportError:
                raise ImportError(
                    "duckduckgo-search not installed. "
                    "Install with: pip install duckduckgo-search"
                )
        return self._search_client
    
    async def execute(
        self,
        query: str,
        max_results: int = 5,
        **kwargs
    ) -> ToolResult:
        """
        Search the web using DuckDuckGo.
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            ToolResult with search results
        """
        try:
            # Get search client
            ddgs = self._get_search_client()
            
            # Perform search
            results = []
            search_results = ddgs.text(
                query,
                max_results=max_results,
                region="wt-wt",  # Worldwide
                safesearch="moderate"
            )
            
            for result in search_results:
                results.append({
                    "title": result.get("title", ""),
                    "snippet": result.get("body", ""),
                    "url": result.get("href", ""),
                    "source": self._extract_domain(result.get("href", ""))
                })
            
            if not results:
                return ToolResult(
                    success=True,
                    data={"results": [], "count": 0},
                    summary=f"No results found for: {query}"
                )
            
            result_data = {
                "results": results,
                "count": len(results),
                "query": query
            }
            
            summary = f"Found {len(results)} web results for '{query}'"
            if results:
                top_sources = [r["source"] for r in results[:3]]
                summary += f" from {', '.join(top_sources)}"
            
            return ToolResult(
                success=True,
                data=result_data,
                summary=summary,
                metadata={
                    "max_results": max_results,
                    "search_engine": "duckduckgo"
                }
            )
            
        except ImportError as e:
            return ToolResult(
                success=False,
                summary="Web search unavailable - DuckDuckGo library not installed",
                error=str(e)
            )
        except Exception as e:
            logger.error(f"Web search failed: {e}", exc_info=True)
            return ToolResult(
                success=False,
                summary=f"Web search failed: {str(e)}",
                error=str(e)
            )
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc or parsed.path
            # Remove www. prefix
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except:
            return "unknown"

