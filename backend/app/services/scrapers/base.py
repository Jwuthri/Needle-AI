"""
Base scraper interface for review collection.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.utils.logging import get_logger

logger = get_logger("scraper_base")


@dataclass
class ScrapedReview:
    """Standardized review data structure."""
    content: str
    author: Optional[str] = None
    url: Optional[str] = None
    review_date: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            "content": self.content,
            "author": self.author,
            "url": self.url,
            "review_date": self.review_date,
            "metadata": self.metadata or {}
        }


class BaseReviewScraper(ABC):
    """
    Abstract base class for review scrapers.
    
    All scrapers must implement:
    - scrape(): Collect reviews from the source
    - estimate_cost(): Calculate cost before scraping
    """

    def __init__(self, settings: Any):
        """
        Initialize scraper with settings.
        
        Args:
            settings: Application settings object
        """
        self.settings = settings

    @abstractmethod
    async def scrape(
        self,
        query: str,
        limit: int,
        **kwargs
    ) -> List[ScrapedReview]:
        """
        Scrape reviews from the source.
        
        Args:
            query: Search query (e.g., company name, product name)
            limit: Maximum number of reviews to collect
            **kwargs: Source-specific parameters
            
        Returns:
            List of scraped reviews
        """
        pass

    @abstractmethod
    async def estimate_cost(self, limit: int) -> float:
        """
        Estimate the cost of scraping.
        
        Args:
            limit: Number of reviews to scrape
            
        Returns:
            Estimated cost in credits
        """
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        """Get the name of this scraper's source."""
        pass

    async def validate_query(self, query: str) -> bool:
        """
        Validate if the query is acceptable for this scraper.
        
        Args:
            query: Search query
            
        Returns:
            True if query is valid
        """
        if not query or len(query.strip()) < 2:
            return False
        return True

    def clean_content(self, content: str) -> str:
        """
        Clean and normalize content.
        
        Args:
            content: Raw content text
            
        Returns:
            Cleaned content
        """
        if not content:
            return ""
        
        # Remove extra whitespace
        content = " ".join(content.split())
        
        # Truncate if too long (max 10000 chars)
        if len(content) > 10000:
            content = content[:10000] + "..."
        
        return content.strip()

