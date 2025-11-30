"""
TrustRadius scraper using Apify's scraped/trustradius-review-scraper actor.
"""

import asyncio
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp

from app.exceptions import ExternalServiceError
from app.utils.logging import get_logger

from .base import BaseReviewScraper, ScrapedReview

logger = get_logger("trustradius_scraper")


class TrustRadiusScraper(BaseReviewScraper):
    """
    TrustRadius scraper using Apify actor.
    
    Actor: scraped/trustradius-review-scraper
    """

    ACTOR_ID = "scraped~trustradius-review-scraper"
    BASE_URL = "https://www.trustradius.com"

    def __init__(self, settings: Any):
        super().__init__(settings)
        self.api_token = settings.get_secret("apify_api_token")
        self.cost_per_review = settings.trustradius_review_cost

    def build_url(self, product: str) -> str:
        """Build TrustRadius product URL."""
        if product.startswith("http"):
            return product.rstrip("/")
        
        product = product.lower().strip().replace(" ", "-")
        return f"{self.BASE_URL}/products/{product}/reviews"

    async def scrape(
        self,
        query: str,
        limit: int,
        **kwargs
    ) -> List[ScrapedReview]:
        """Scrape TrustRadius reviews."""
        if not await self.validate_query(query):
            raise ValueError(f"Invalid query: {query}")

        if not self.api_token:
            raise ExternalServiceError("Apify API token not configured", service="apify")

        try:
            url = self.build_url(query)
            
            actor_input = {
                "url": url,
                "maxReviews": limit
            }

            async with aiohttp.ClientSession() as session:
                run_id = await self._start_actor_run(session, actor_input)
                logger.info(f"Started TrustRadius scraper run: {run_id}")

                status_data = await self._wait_for_completion(session, run_id)

                dataset_id = status_data["data"]["defaultDatasetId"]
                items = await self._get_results(session, dataset_id)

            reviews = []
            for item in items:
                review = self._parse_review(item)
                if review:
                    reviews.append(review)

            logger.info(f"Scraped {len(reviews)} reviews from TrustRadius")
            return reviews[:limit]

        except aiohttp.ClientError as e:
            logger.error(f"Network error: {e}")
            raise ExternalServiceError(f"TrustRadius scraping failed: {e}", service="apify", retryable=True)
        except Exception as e:
            logger.error(f"Error: {e}")
            raise ExternalServiceError(f"TrustRadius scraping failed: {e}", service="trustradius_scraper")

    async def _start_actor_run(self, session: aiohttp.ClientSession, actor_input: Dict[str, Any]) -> str:
        """Start the Apify actor run."""
        start_url = f"https://api.apify.com/v2/acts/{self.ACTOR_ID}/runs"
        headers = {"Authorization": f"Bearer {self.api_token}"}
        
        async with session.post(start_url, json=actor_input, headers=headers) as response:
            if response.status != 201:
                error_text = await response.text()
                raise ExternalServiceError(f"Failed to start Apify actor: {error_text}", service="apify")
            
            run_data = await response.json()
            return run_data["data"]["id"]

    async def _wait_for_completion(self, session: aiohttp.ClientSession, run_id: str, max_wait: int = 600) -> Dict[str, Any]:
        """Wait for actor run to complete."""
        headers = {"Authorization": f"Bearer {self.api_token}"}
        waited = 0
        
        while waited < max_wait:
            await asyncio.sleep(10)
            waited += 10

            status_url = f"https://api.apify.com/v2/acts/{self.ACTOR_ID}/runs/{run_id}"
            async with session.get(status_url, headers=headers) as response:
                status_data = await response.json()
                status = status_data["data"]["status"]

                if status == "SUCCEEDED":
                    return status_data
                elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                    raise ExternalServiceError(f"Apify actor failed: {status}", service="apify")
                
                logger.debug(f"TrustRadius scraper status: {status}, waited: {waited}s")

        raise ExternalServiceError("Apify actor run timeout", service="apify", retryable=True)

    async def _get_results(self, session: aiohttp.ClientSession, dataset_id: str) -> List[Dict[str, Any]]:
        """Get results from the dataset."""
        headers = {"Authorization": f"Bearer {self.api_token}"}
        results_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items"
        
        async with session.get(results_url, headers=headers) as response:
            return await response.json()

    def _parse_review(self, item: Dict[str, Any]) -> Optional[ScrapedReview]:
        """Parse TrustRadius review from scraped/trustradius-review-scraper actor."""
        content_parts = []
        
        # Title/Heading
        title = item.get("Title") or item.get("Heading")
        if title:
            content_parts.append(title)
        
        # Pros - "things-done-well,pros-and-cons_answer"
        pros = item.get("things-done-well,pros-and-cons_answer")
        if pros:
            content_parts.append(f"Pros: {pros}")
        
        # Cons - "things-done-poorly,pros-and-cons_answer"
        cons = item.get("things-done-poorly,pros-and-cons_answer")
        if cons:
            content_parts.append(f"Cons: {cons}")
        
        # Product usage
        usage = item.get("product-usage_answer")
        if usage:
            content_parts.append(f"Usage: {usage}")
        
        # Synopsis
        synopsis = item.get("Synopsis")
        if synopsis:
            content_parts.append(synopsis)
        
        if not content_parts:
            return None
        
        content = "\n\n".join(content_parts)
        
        # Author
        author = item.get("Reviewer Name")
        if not author:
            first = item.get("Reviewer First Name", "")
            last = item.get("Reviewer Last Name", "")
            if first or last:
                author = f"{first} {last}".strip()
        
        # Rating (1-10 scale, convert to 1-5)
        rating = item.get("Rating")
        if rating:
            try:
                rating = float(rating) / 2  # Convert 10-scale to 5-scale
            except:
                rating = None
        
        # Date
        date_str = item.get("Published Date") or item.get("Submitted Date")
        review_date = self._parse_date(date_str)
        
        # Build URL from product slug and review ID
        product_slug = item.get("Product Slug")
        review_id = item.get("Review ID")
        url = None
        if product_slug:
            url = f"https://www.trustradius.com/products/{product_slug}/reviews"
        
        return ScrapedReview(
            content=self.clean_content(content),
            author=author,
            url=url,
            review_date=review_date,
            metadata={
                "type": "trustradius_review",
                "rating": rating,
                "review_id": review_id,
                "product_name": item.get("Product Name"),
                "company": item.get("Company Name"),
                "company_size": item.get("Company Size"),
                "job_title": item.get("Reviewer Job Title"),
                "industry": item.get("Company Industry"),
            }
        )

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string."""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except:
            try:
                from dateutil import parser
                return parser.parse(date_str)
            except:
                return None

    async def estimate_cost(self, limit: int) -> float:
        return limit * self.cost_per_review

    def get_source_name(self) -> str:
        return "TrustRadius"

