"""
Twitter/X scraper using Apify.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List

import aiohttp

from app.exceptions import ExternalServiceError
from app.utils.logging import get_logger

from .base import BaseReviewScraper, ScrapedReview

logger = get_logger("twitter_scraper")


class TwitterScraper(BaseReviewScraper):
    """
    Twitter/X scraper using Apify's Twitter Scraper actor.
    
    Collects tweets and replies based on search queries.
    """

    def __init__(self, settings: Any):
        super().__init__(settings)
        self.api_token = settings.get_secret("apify_api_token")
        self.actor_id = settings.apify_twitter_actor_id
        self.cost_per_review = settings.twitter_review_cost

    async def scrape(
        self,
        query: str,
        limit: int,
        **kwargs
    ) -> List[ScrapedReview]:
        """
        Scrape Twitter/X posts.
        
        Args:
            query: Search query or hashtag
            limit: Maximum number of tweets
            **kwargs: Additional parameters (include_replies, lang)
            
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
                "searchTerms": [query],
                "maxItems": limit,
                "includeSearchTerms": True,
                "onlyImage": False,
                "onlyVideo": False,
                "onlyQuote": False,
                "sort": kwargs.get("sort", "Latest"),
                "tweetLanguage": kwargs.get("lang", "en")
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
                    logger.info(f"Started Apify Twitter scraper run: {run_id}")

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
                review = self._parse_tweet(item)
                if review:
                    reviews.append(review)

            logger.info(f"Scraped {len(reviews)} tweets from Twitter")
            return reviews[:limit]

        except aiohttp.ClientError as e:
            logger.error(f"Network error in Twitter scraper: {e}")
            raise ExternalServiceError(f"Twitter scraping failed: {e}", service="apify", retryable=True)
        except Exception as e:
            logger.error(f"Error in Twitter scraper: {e}")
            raise ExternalServiceError(f"Twitter scraping failed: {e}", service="twitter_scraper")

    def _parse_tweet(self, item: Dict[str, Any]) -> ScrapedReview:
        """Parse tweet into ScrapedReview."""
        content = item.get("text", "") or item.get("full_text", "")
        
        if not content:
            return None

        return ScrapedReview(
            content=self.clean_content(content),
            author=item.get("author", {}).get("userName") or item.get("userName"),
            url=item.get("url"),
            review_date=self._parse_date(item.get("createdAt")),
            metadata={
                "type": "tweet",
                "likes": item.get("likeCount", 0),
                "retweets": item.get("retweetCount", 0),
                "replies": item.get("replyCount", 0),
                "views": item.get("viewCount", 0),
                "is_retweet": item.get("isRetweet", False),
                "is_reply": item.get("isReply", False)
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
        """Estimate cost for scraping Twitter."""
        return limit * self.cost_per_review

    def get_source_name(self) -> str:
        """Get source name."""
        return "Twitter/X"

