"""
Citation Tool - Formats sources and creates cited summaries.
"""

from typing import Any, Dict, List, Optional

from app.agents.tools.base_tool import BaseTool, ToolResult
from app.utils.logging import get_logger

logger = get_logger("citation_tool")


class CitationTool(BaseTool):
    """
    Formats sources and creates properly cited summaries.
    
    Takes review data and formats it with citations that can be
    displayed in the UI with expandable source details.
    """
    
    @property
    def name(self) -> str:
        return "citation"
    
    @property
    def description(self) -> str:
        return """Format sources and create cited summaries from review data.

Use this tool when you need to:
- Format sources with proper attribution
- Create citations for reviews used in analysis
- Generate reference lists

Parameters:
- reviews: List of review objects with content and metadata
- format: Citation format (inline, footnote, numbered)
- include_quotes: Whether to include relevant quotes

Returns formatted sources that can be displayed in the UI.
"""
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "reviews": {
                    "type": "array",
                    "description": "List of reviews to cite"
                },
                "format": {
                    "type": "string",
                    "enum": ["inline", "footnote", "numbered"],
                    "description": "Citation format style",
                    "default": "numbered"
                },
                "include_quotes": {
                    "type": "boolean",
                    "description": "Include relevant quotes from reviews",
                    "default": True
                },
                "max_quote_length": {
                    "type": "integer",
                    "description": "Maximum length of quotes",
                    "default": 150
                }
            },
            "required": ["reviews"]
        }
    
    async def execute(
        self,
        reviews: List[Dict[str, Any]],
        format: str = "numbered",
        include_quotes: bool = True,
        max_quote_length: int = 150,
        **kwargs
    ) -> ToolResult:
        """
        Format sources and create citations.
        
        Args:
            reviews: List of reviews to cite
            format: Citation format
            include_quotes: Include quotes
            max_quote_length: Max quote length
            
        Returns:
            ToolResult with formatted citations
        """
        try:
            if not reviews:
                return ToolResult(
                    success=False,
                    summary="No reviews provided for citation",
                    error="Reviews list is empty"
                )
            
            formatted_sources = []
            
            for idx, review in enumerate(reviews, 1):
                citation = self._format_citation(
                    review,
                    idx,
                    format,
                    include_quotes,
                    max_quote_length
                )
                formatted_sources.append(citation)
            
            result_data = {
                "sources": formatted_sources,
                "count": len(formatted_sources),
                "format": format
            }
            
            summary = f"Formatted {len(formatted_sources)} citations in {format} style"
            
            return ToolResult(
                success=True,
                data=result_data,
                summary=summary,
                metadata={
                    "citation_count": len(formatted_sources),
                    "format": format,
                    "includes_quotes": include_quotes
                }
            )
            
        except Exception as e:
            logger.error(f"Citation formatting failed: {e}", exc_info=True)
            return ToolResult(
                success=False,
                summary=f"Failed to format citations: {str(e)}",
                error=str(e)
            )
    
    def _format_citation(
        self,
        review: Dict[str, Any],
        index: int,
        format: str,
        include_quotes: bool,
        max_quote_length: int
    ) -> Dict[str, Any]:
        """Format a single review citation."""
        
        # Extract review details
        review_id = review.get("review_id", f"review_{index}")
        content = review.get("content", "")
        author = review.get("author", "Anonymous")
        source = review.get("source", "Unknown")
        url = review.get("url")
        sentiment = review.get("sentiment_score")
        relevance = review.get("relevance_score")
        date = review.get("date")
        
        # Create quote if requested
        quote = None
        if include_quotes and content:
            quote = self._extract_quote(content, max_quote_length)
        
        # Format sentiment label
        sentiment_label = None
        if sentiment is not None:
            if sentiment > 0.33:
                sentiment_label = "Positive"
            elif sentiment < -0.33:
                sentiment_label = "Negative"
            else:
                sentiment_label = "Neutral"
        
        # Build citation
        citation = {
            "id": review_id,
            "index": index,
            "author": author,
            "source": source,
            "url": url,
            "date": date,
            "sentiment": sentiment_label,
            "relevance_score": relevance,
            "quote": quote,
            "full_content": content
        }
        
        # Add formatted text based on style
        if format == "numbered":
            citation["citation_text"] = f"[{index}] {author} on {source}"
        elif format == "inline":
            citation["citation_text"] = f"({author}, {source})"
        elif format == "footnote":
            citation["citation_text"] = f"^{index}"
        
        return citation
    
    def _extract_quote(self, content: str, max_length: int) -> str:
        """Extract a relevant quote from review content."""
        if len(content) <= max_length:
            return content
        
        # Try to find a complete sentence
        sentences = content.split(". ")
        
        # Return first sentence if it fits
        if sentences and len(sentences[0]) <= max_length:
            return sentences[0] + "."
        
        # Otherwise truncate with ellipsis
        return content[:max_length].rsplit(" ", 1)[0] + "..."

