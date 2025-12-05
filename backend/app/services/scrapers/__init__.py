"""
Scraper services for collecting reviews from various sources.

Working scrapers:
- G2Scraper: Uses omkar-cloud/g2-product-scraper Apify actor
- TrustpilotCrawler: Uses apify/website-content-crawler
- TrustRadiusScraper: Uses scraped/trustradius-review-scraper Apify actor
- CSVImporter: User uploads their own review data
"""

from .base import BaseReviewScraper, ScrapedProductIntelligence, ScrapedReview, ScrapeResult
from .csv_importer import CSVImporter
from .g2_scraper import G2Scraper
from .trustpilot_crawler import TrustpilotCrawler, TrustpilotQuickScraper
from .trustradius_scraper import TrustRadiusScraper

__all__ = [
    "BaseReviewScraper",
    "ScrapedReview",
    "ScrapedProductIntelligence",
    "ScrapeResult",
    "G2Scraper",
    "TrustpilotCrawler",
    "TrustpilotQuickScraper",
    "TrustRadiusScraper",
    "CSVImporter",
]

