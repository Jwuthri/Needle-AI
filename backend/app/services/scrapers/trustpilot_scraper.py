"""
Trustpilot scraper using Apify.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List

import aiohttp

from app.exceptions import ExternalServiceError
from app.utils.logging import get_logger

from .base import BaseReviewScraper, ScrapedReview

logger = get_logger("trustpilot_scraper")


class TrustpilotScraper(BaseReviewScraper):
    """
    Trustpilot scraper using Apify's Trustpilot Scraper actor.
    
    Collects reviews from Trustpilot based on company URL or search.
    """

    def __init__(self, settings: Any):
        super().__init__(settings)
        self.api_token = settings.get_secret("apify_api_token")
        self.actor_id = settings.apify_trustpilot_actor_id
        self.cost_per_review = settings.trustpilot_review_cost

    async def scrape(
        self,
        query: str,
        limit: int,
        **kwargs
    ) -> List[ScrapedReview]:
        """
        Scrape Trustpilot reviews.
        
        Args:
            query: Company URL or search query
            limit: Maximum number of reviews
            **kwargs: Additional parameters (sort, language)
            
        Returns:
            List of scraped reviews
        """
        if not await self.validate_query(query):
            raise ValueError(f"Invalid query: {query}")

        if not self.api_token:
            raise ExternalServiceError("Apify API token not configured", service="apify")

        try:
            # Prepare Apify actor input
            actor_input = {
                "startUrls": [{"url": query}] if query.startswith("http") else [],
                "searchTerms": [] if query.startswith("http") else [query],
                "maxReviews": limit,
                "includeReviewText": True,
                "language": kwargs.get("language", "all"),
                "sort": kwargs.get("sort", "recency")
            }

            # Start Apify actor run
            async with aiohttp.ClientSession() as session:
                # Start actor
                start_url = f"https://api.apify.com/v2/acts/{self.actor_id}/runs"
                headers = {"Authorization": f"Bearer {self.api_token}"}
                
                async with session.post(
                    start_url,
                    json=actor_input,
                    headers=headers
                ) as response:
                    if response.status != 201:
                        error_text = await response.text()
                        raise ExternalServiceError(
                            f"Failed to start Apify actor: {error_text}",
                            service="apify"
                        )
                    
                    run_data = await response.json()
                    run_id = run_data["data"]["id"]
                    logger.info(f"Started Apify Trustpilot scraper run: {run_id}")

                # Wait for run to complete (with timeout)
                max_wait = 300  # 5 minutes
                waited = 0
                while waited < max_wait:
                    await asyncio.sleep(5)
                    waited += 5

                    status_url = f"https://api.apify.com/v2/acts/{self.actor_id}/runs/{run_id}"
                    async with session.get(status_url, headers=headers) as response:
                        status_data = await response.json()
                        status = status_data["data"]["status"]

                        if status == "SUCCEEDED":
                            break
                        elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                            raise ExternalServiceError(
                                f"Apify actor run failed with status: {status}",
                                service="apify"
                            )

                if waited >= max_wait:
                    raise ExternalServiceError(
                        "Apify actor run timeout",
                        service="apify",
                        retryable=True
                    )

                # Get results
                dataset_id = status_data["data"]["defaultDatasetId"]
                results_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items"
                
                async with session.get(results_url, headers=headers) as response:
                    items = await response.json()

            # Parse results into ScrapedReview format
            reviews = []
            for item in items:
                review = self._parse_review(item)
                if review:
                    reviews.append(review)

            logger.info(f"Scraped {len(reviews)} reviews from Trustpilot")
            return reviews[:limit]

        except aiohttp.ClientError as e:
            logger.error(f"Network error in Trustpilot scraper: {e}")
            raise ExternalServiceError(f"Trustpilot scraping failed: {e}", service="apify", retryable=True)
        except Exception as e:
            logger.error(f"Error in Trustpilot scraper: {e}")
            raise ExternalServiceError(f"Trustpilot scraping failed: {e}", service="trustpilot_scraper")

    def _parse_review(self, item: Dict[str, Any]) -> ScrapedReview:
        """Parse Trustpilot review into ScrapedReview."""
        # Trustpilot review structure
        title = item.get("title", "")
        text = item.get("text", "") or item.get("reviewText", "")
        content = f"{title}\n\n{text}".strip() if title else text
        
        if not content:
            return None

        return ScrapedReview(
            content=self.clean_content(content),
            author=item.get("author") or item.get("reviewerName"),
            url=item.get("url") or item.get("reviewUrl"),
            review_date=self._parse_date(item.get("publishedDate") or item.get("date")),
            metadata={
                "type": "trustpilot_review",
                "rating": item.get("rating"),
                "stars": item.get("stars"),
                "company_name": item.get("companyName"),
                "company_reply": item.get("companyReply"),
                "verified": item.get("verified", False),
                "location": item.get("location"),
                "helpful_count": item.get("helpfulCount", 0),
                "language": item.get("language")
            }
        )

    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime."""
        if not date_str:
            return None
        try:
            # Try ISO format first
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except:
            try:
                # Try common date formats
                from dateutil import parser
                return parser.parse(date_str)
            except:
                return None

    async def estimate_cost(self, limit: int) -> float:
        """Estimate cost for scraping Trustpilot."""
        return limit * self.cost_per_review

    def get_source_name(self) -> str:
        """Get source name."""
        return "Trustpilot"

