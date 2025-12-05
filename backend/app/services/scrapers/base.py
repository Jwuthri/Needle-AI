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


@dataclass
class ScrapedProductIntelligence:
    """
    Standardized product intelligence data from G2, TrustRadius, etc.
    Contains competitive intel: alternatives, pricing, features, company info.
    """
    source: str  # "g2", "trustradius", "trustpilot"
    
    # External IDs
    external_product_id: Optional[str] = None
    external_company_id: Optional[str] = None
    external_url: Optional[str] = None
    
    # Product Info
    product_name: Optional[str] = None
    product_logo: Optional[str] = None
    product_description: Optional[str] = None
    what_is: Optional[str] = None
    positioning: Optional[str] = None
    
    # Rating Summary
    total_reviews: Optional[int] = None
    average_rating: Optional[float] = None
    medal_image: Optional[str] = None
    
    # Company Info
    vendor_name: Optional[str] = None
    company_location: Optional[str] = None
    company_founded_year: Optional[int] = None
    company_website: Optional[str] = None
    product_website: Optional[str] = None
    
    # Social Media
    twitter_url: Optional[str] = None
    twitter_followers: Optional[int] = None
    linkedin_url: Optional[str] = None
    linkedin_employees: Optional[int] = None
    
    # Categories
    categories: Optional[List[Dict[str, Any]]] = None
    primary_category: Optional[str] = None
    parent_category: Optional[str] = None
    
    # Alternatives & Comparisons
    alternatives: Optional[List[Dict[str, Any]]] = None
    comparisons: Optional[List[Dict[str, Any]]] = None
    
    # Features
    features: Optional[List[Dict[str, Any]]] = None
    feature_summary: Optional[List[Dict[str, Any]]] = None
    
    # Pricing
    pricing_plans: Optional[List[Dict[str, Any]]] = None
    
    # Media
    screenshots: Optional[List[str]] = None
    videos: Optional[List[str]] = None
    
    # Additional
    supported_languages: Optional[str] = None
    services_offered: Optional[str] = None
    
    # Raw data for debugging
    raw_data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            "source": self.source,
            "external_product_id": self.external_product_id,
            "external_company_id": self.external_company_id,
            "external_url": self.external_url,
            "product_name": self.product_name,
            "product_logo": self.product_logo,
            "product_description": self.product_description,
            "what_is": self.what_is,
            "positioning": self.positioning,
            "total_reviews": self.total_reviews,
            "average_rating": self.average_rating,
            "medal_image": self.medal_image,
            "vendor_name": self.vendor_name,
            "company_location": self.company_location,
            "company_founded_year": self.company_founded_year,
            "company_website": self.company_website,
            "product_website": self.product_website,
            "twitter_url": self.twitter_url,
            "twitter_followers": self.twitter_followers,
            "linkedin_url": self.linkedin_url,
            "linkedin_employees": self.linkedin_employees,
            "categories": self.categories,
            "primary_category": self.primary_category,
            "parent_category": self.parent_category,
            "alternatives": self.alternatives,
            "comparisons": self.comparisons,
            "features": self.features,
            "feature_summary": self.feature_summary,
            "pricing_plans": self.pricing_plans,
            "screenshots": self.screenshots,
            "videos": self.videos,
            "supported_languages": self.supported_languages,
            "services_offered": self.services_offered,
            "raw_data": self.raw_data,
        }


@dataclass 
class ScrapeResult:
    """Combined result of scraping: reviews + product intelligence."""
    reviews: List[ScrapedReview]
    intelligence: Optional[ScrapedProductIntelligence] = None


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

