"""
Reddit scraper using Apify.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List

import aiohttp

from app.exceptions import ExternalServiceError
from app.utils.logging import get_logger

from .base import BaseReviewScraper, ScrapedReview

logger = get_logger("reddit_scraper")


class RedditScraper(BaseReviewScraper):
    """
    Reddit scraper using Apify's Reddit Scraper actor.
    
    Collects posts and comments from Reddit based on search queries.
    """

    def __init__(self, settings: Any):
        super().__init__(settings)
        self.api_token = settings.get_secret("apify_api_token")
        self.actor_id = settings.apify_reddit_actor_id
        self.cost_per_review = settings.reddit_review_cost

    async def scrape(
        self,
        query: str,
        limit: int,
        **kwargs
    ) -> List[ScrapedReview]:
        """
        Scrape Reddit posts and comments.
        
        Args:
            query: Search query or subreddit
            limit: Maximum number of items
            **kwargs: Additional parameters (subreddits, sort, time_filter)
            
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
                "searches": [query],
                "maxItems": limit,
                "sort": kwargs.get("sort", "relevance"),
                "time": kwargs.get("time_filter", "all"),
                "includeComments": True,
                "maxComments": 10  # Get top comments per post
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
                    logger.info(f"Started Apify Reddit scraper run: {run_id}")

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
                # Handle both posts and comments
                if item.get("type") == "post":
                    review = self._parse_post(item)
                elif item.get("type") == "comment":
                    review = self._parse_comment(item)
                else:
                    continue

                if review:
                    reviews.append(review)

            logger.info(f"Scraped {len(reviews)} items from Reddit")
            return reviews[:limit]

        except aiohttp.ClientError as e:
            logger.error(f"Network error in Reddit scraper: {e}")
            raise ExternalServiceError(f"Reddit scraping failed: {e}", service="apify", retryable=True)
        except Exception as e:
            logger.error(f"Error in Reddit scraper: {e}")
            raise ExternalServiceError(f"Reddit scraping failed: {e}", service="reddit_scraper")

    def _parse_post(self, item: Dict[str, Any]) -> ScrapedReview:
        """Parse Reddit post into ScrapedReview."""
        title = item.get("title", "")
        selftext = item.get("selftext", "")
        content = f"{title}\n\n{selftext}".strip()
        
        if not content:
            return None

        return ScrapedReview(
            content=self.clean_content(content),
            author=item.get("author"),
            url=item.get("url"),
            review_date=self._parse_date(item.get("createdAt")),
            metadata={
                "type": "post",
                "subreddit": item.get("subreddit"),
                "score": item.get("score"),
                "num_comments": item.get("numberOfComments"),
                "upvote_ratio": item.get("upvoteRatio")
            }
        )

    def _parse_comment(self, item: Dict[str, Any]) -> ScrapedReview:
        """Parse Reddit comment into ScrapedReview."""
        content = item.get("body", "")
        
        if not content:
            return None

        return ScrapedReview(
            content=self.clean_content(content),
            author=item.get("author"),
            url=item.get("url"),
            review_date=self._parse_date(item.get("createdAt")),
            metadata={
                "type": "comment",
                "subreddit": item.get("subreddit"),
                "score": item.get("score"),
                "post_id": item.get("postId")
            }
        )

    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime."""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except:
            return None

    async def estimate_cost(self, limit: int) -> float:
        """Estimate cost for scraping Reddit."""
        return limit * self.cost_per_review

    def get_source_name(self) -> str:
        """Get source name."""
        return "Reddit"

