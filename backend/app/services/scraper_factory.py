"""
Scraper factory for managing and creating review scrapers.
"""

from typing import Dict, List, Optional, Type

from app.config import get_settings
from app.database.models.review_source import SourceTypeEnum
from app.exceptions import ConfigurationError
from app.services.scrapers import (
    BaseReviewScraper,
    CSVImporter,
    RedditScraper,
    TwitterScraper,
)
from app.utils.logging import get_logger

logger = get_logger("scraper_factory")


class ScraperFactory:
    """
    Factory for creating and managing review scrapers.
    
    Features:
    - Registry of available scrapers
    - Cost estimation across sources
    - Easy addition of new scrapers
    """

    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self._scrapers: Dict[SourceTypeEnum, Type[BaseReviewScraper]] = {}
        self._register_default_scrapers()

    def _register_default_scrapers(self):
        """Register built-in scrapers."""
        self.register_scraper(SourceTypeEnum.REDDIT, RedditScraper)
        self.register_scraper(SourceTypeEnum.TWITTER, TwitterScraper)
        self.register_scraper(SourceTypeEnum.CUSTOM_CSV, CSVImporter)
        logger.info("Registered default scrapers: Reddit, Twitter, CSV")

    def register_scraper(
        self,
        source_type: SourceTypeEnum,
        scraper_class: Type[BaseReviewScraper]
    ):
        """
        Register a new scraper type.
        
        Args:
            source_type: Source type enum
            scraper_class: Scraper class to register
        """
        if not issubclass(scraper_class, BaseReviewScraper):
            raise ValueError(f"{scraper_class} must inherit from BaseReviewScraper")

        self._scrapers[source_type] = scraper_class
        logger.debug(f"Registered scraper: {source_type.value} -> {scraper_class.__name__}")

    def get_scraper(self, source_type: SourceTypeEnum) -> BaseReviewScraper:
        """
        Get a scraper instance for the given source type.
        
        Args:
            source_type: Source type to scrape from
            
        Returns:
            Scraper instance
        """
        scraper_class = self._scrapers.get(source_type)
        
        if not scraper_class:
            available = ", ".join([st.value for st in self._scrapers.keys()])
            raise ConfigurationError(
                f"No scraper registered for source type: {source_type.value}. "
                f"Available: {available}"
            )

        return scraper_class(self.settings)

    def list_available_sources(self) -> List[Dict[str, any]]:
        """
        List all available scraper sources with details.
        
        Returns:
            List of source information dicts
        """
        sources = []
        
        for source_type, scraper_class in self._scrapers.items():
            scraper = scraper_class(self.settings)
            
            # Get cost per review
            if source_type == SourceTypeEnum.REDDIT:
                cost = self.settings.reddit_review_cost
            elif source_type == SourceTypeEnum.TWITTER:
                cost = self.settings.twitter_review_cost
            elif source_type == SourceTypeEnum.CUSTOM_CSV:
                cost = self.settings.csv_review_cost
            else:
                cost = 0.0

            sources.append({
                "source_type": source_type.value,
                "name": scraper.get_source_name(),
                "cost_per_review": cost,
                "description": scraper.__class__.__doc__
            })

        return sources

    async def estimate_total_cost(
        self,
        source_type: SourceTypeEnum,
        review_count: int
    ) -> float:
        """
        Estimate the total cost for scraping.
        
        Args:
            source_type: Source to scrape from
            review_count: Number of reviews to scrape
            
        Returns:
            Estimated cost in credits
        """
        scraper = self.get_scraper(source_type)
        return await scraper.estimate_cost(review_count)

    def is_source_available(self, source_type: SourceTypeEnum) -> bool:
        """Check if a source scraper is available."""
        return source_type in self._scrapers


# Singleton instance
_factory: Optional[ScraperFactory] = None


def get_scraper_factory() -> ScraperFactory:
    """Get or create the global scraper factory instance."""
    global _factory
    if _factory is None:
        _factory = ScraperFactory()
    return _factory

