"""
G2 scraper using Apify's omkar-cloud/g2-product-scraper actor.

See backend/docs/G2_SCRAPER_SCHEMA.md for full response schema.
"""

import asyncio
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp

from app.exceptions import ExternalServiceError
from app.utils.logging import get_logger

from .base import BaseReviewScraper, ScrapedProductIntelligence, ScrapedReview, ScrapeResult

logger = get_logger("g2_scraper")


class G2Scraper(BaseReviewScraper):
    """
    G2 scraper using Apify's G2 Product Scraper actor.
    
    Actor: omkar-cloud/g2-product-scraper
    Collects product reviews from G2.com based on product URL.
    Also extracts product intelligence: alternatives, pricing, features, etc.
    """

    ACTOR_ID = "omkar-cloud~g2-product-scraper"
    BASE_URL = "https://www.g2.com"

    def __init__(self, settings: Any):
        super().__init__(settings)
        self.api_token = settings.get_secret("apify_api_token")
        self.cost_per_review = settings.g2_review_cost
        self._last_intelligence: Optional[ScrapedProductIntelligence] = None

    def build_g2_url(self, product: str) -> str:
        """
        Build G2 product reviews URL.
        
        Args:
            product: Product name/slug or full G2 URL
            
        Returns:
            Full G2 reviews URL
        """
        if product.startswith("http"):
            # Ensure it ends with /reviews
            url = product.rstrip("/")
            if not url.endswith("/reviews"):
                url += "/reviews"
            return url
        
        # Clean up product name - G2 uses kebab-case slugs
        product = product.lower().strip().replace(" ", "-")
        return f"{self.BASE_URL}/products/{product}/reviews"

    async def scrape(
        self,
        query: str,
        limit: int,
        **kwargs
    ) -> List[ScrapedReview]:
        """
        Scrape G2 reviews.
        
        Args:
            query: Product URL or product name/slug
            limit: Maximum number of reviews
            **kwargs: Additional parameters
            
        Returns:
            List of scraped reviews
        """
        if not await self.validate_query(query):
            raise ValueError(f"Invalid query: {query}")

        if not self.api_token:
            raise ExternalServiceError("Apify API token not configured", service="apify")

        try:
            # Build G2 URL
            g2_url = self.build_g2_url(query)
            
            # Prepare Apify actor input (omkar-cloud/g2-product-scraper format)
            actor_input = {
                "g2ProductUrls": [{"url": g2_url}]
            }

            # Start Apify actor run
            async with aiohttp.ClientSession() as session:
                run_id = await self._start_actor_run(session, actor_input)
                logger.info(f"Started Apify G2 scraper run: {run_id}")

                # Wait for run to complete
                status_data = await self._wait_for_completion(session, run_id)

                # Get results
                dataset_id = status_data["data"]["defaultDatasetId"]
                items = await self._get_results(session, dataset_id)

            # Parse results - actor returns product objects with all_reviews array
            reviews = []
            intelligence = None
            
            for product in items:
                product_name = product.get("product_name", "Unknown")
                product_reviews = product.get("all_reviews", []) or product.get("initial_reviews", [])
                
                # Extract product intelligence (first product only)
                if intelligence is None:
                    intelligence = self._parse_product_intelligence(product)
                
                for review_item in product_reviews:
                    review = self._parse_review(review_item, product_name)
                    if review:
                        reviews.append(review)

            logger.info(f"Scraped {len(reviews)} reviews from G2")
            
            # Store intelligence for later retrieval
            self._last_intelligence = intelligence
            
            return reviews[:limit]

        except aiohttp.ClientError as e:
            logger.error(f"Network error in G2 scraper: {e}")
            raise ExternalServiceError(f"G2 scraping failed: {e}", service="apify", retryable=True)
        except Exception as e:
            logger.error(f"Error in G2 scraper: {e}")
            raise ExternalServiceError(f"G2 scraping failed: {e}", service="g2_scraper")

    async def _start_actor_run(
        self, 
        session: aiohttp.ClientSession, 
        actor_input: Dict[str, Any]
    ) -> str:
        """Start the Apify actor run."""
        start_url = f"https://api.apify.com/v2/acts/{self.ACTOR_ID}/runs"
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

        return run_data["data"]["id"]

    async def _wait_for_completion(
        self, 
        session: aiohttp.ClientSession, 
        run_id: str,
        max_wait: int = 600  # 10 minutes
    ) -> Dict[str, Any]:
        """Wait for actor run to complete."""
        headers = {"Authorization": f"Bearer {self.api_token}"}
        waited = 0
        status_data = None
        
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
                    raise ExternalServiceError(
                        f"Apify actor run failed with status: {status}",
                        service="apify"
                    )

            logger.debug(f"G2 scraper status: {status}, waited: {waited}s")

        raise ExternalServiceError(
            "Apify actor run timeout",
            service="apify",
            retryable=True
        )

    async def _get_results(
        self, 
        session: aiohttp.ClientSession, 
        dataset_id: str
    ) -> List[Dict[str, Any]]:
        """Get results from the dataset."""
        headers = {"Authorization": f"Bearer {self.api_token}"}
        results_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items"
        
        async with session.get(results_url, headers=headers) as response:
            return await response.json()

    def _parse_review(self, item: Dict[str, Any], product_name: str) -> Optional[ScrapedReview]:
        """
        Parse G2 review into ScrapedReview.
        
        Schema from omkar-cloud/g2-product-scraper:
        - review_id: int
        - review_title: string
        - review_content: string
        - review_rating: int (1-5)
        - publish_date: ISO 8601 string
        - review_link: string
        - reviewer_company_size: string
        - review_question_answers: array of {question, answer}
        - reviewer: {reviewer_name, reviewer_job_title, reviewer_link}
        """
        # Build content from title and Q&A answers
        title = item.get("review_title", "")
        content_parts = []
        
        if title:
            content_parts.append(title)
        
        # Extract Q&A content
        qa_answers = item.get("review_question_answers", [])
        likes = None
        dislikes = None
        problems_solved = None
        
        for qa in qa_answers:
            question = qa.get("question", "").lower()
            answer = qa.get("answer", "")
            
            if not answer:
                continue
                
            if "like best" in question:
                likes = answer
                content_parts.append(f"Likes: {answer}")
            elif "dislike" in question:
                dislikes = answer
                content_parts.append(f"Dislikes: {answer}")
            elif "problems" in question or "solving" in question:
                problems_solved = answer
                content_parts.append(f"Problems Solved: {answer}")
            else:
                content_parts.append(answer)
        
        # Fallback to review_content if no Q&A
        if not content_parts and item.get("review_content"):
            content_parts.append(item["review_content"])
        
        content = "\n\n".join(content_parts)
        
        if not content:
            return None

        # Extract reviewer info
        reviewer = item.get("reviewer", {})
        author = reviewer.get("reviewer_name")
        job_title = reviewer.get("reviewer_job_title")

        return ScrapedReview(
            content=self.clean_content(content),
            author=author,
            url=item.get("review_link"),
            review_date=self._parse_date(item.get("publish_date")),
            metadata={
                "type": "g2_review",
                "review_id": item.get("review_id"),
                "rating": item.get("review_rating"),
                "product_name": product_name,
                "company_size": item.get("reviewer_company_size"),
                "job_title": job_title,
                "likes": likes,
                "dislikes": dislikes,
                "problems_solved": problems_solved,
                "video_link": item.get("video_link"),
            }
        )

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse ISO 8601 date string to datetime."""
        if not date_str:
            return None
        try:
            # ISO format: 2024-07-24T00:00:00
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except:
            try:
                from dateutil import parser
                return parser.parse(date_str)
            except:
                return None

    def _parse_product_intelligence(self, product: Dict[str, Any]) -> ScrapedProductIntelligence:
        """
        Parse G2 product data into ScrapedProductIntelligence.
        
        Extracts: alternatives, pricing, features, company info, social links, etc.
        """
        # Extract primary category
        category = product.get("category", {})
        primary_category = category.get("name") if isinstance(category, dict) else None
        
        # Extract parent category
        parent_cat = product.get("parent_category", {})
        parent_category = parent_cat.get("name") if isinstance(parent_cat, dict) else None
        
        # Build feature summary from features array
        feature_summary = []
        features = product.get("features", [])
        for cat in features:
            if isinstance(cat, dict):
                cat_features = cat.get("features", [])
                if isinstance(cat_features, list):
                    for f in cat_features:
                        if isinstance(f, str):
                            feature_summary.append({"name": f, "category": cat.get("name")})
        
        return ScrapedProductIntelligence(
            source="g2",
            
            # External IDs
            external_product_id=str(product.get("product_id")) if product.get("product_id") else None,
            external_company_id=str(product.get("company_id")) if product.get("company_id") else None,
            external_url=product.get("g2_link"),
            
            # Product Info
            product_name=product.get("product_name"),
            product_logo=product.get("product_logo"),
            product_description=product.get("product_description"),
            what_is=product.get("what_is"),
            positioning=product.get("positioning_against_competitor"),
            
            # Rating Summary
            total_reviews=product.get("reviews"),
            average_rating=product.get("rating"),
            medal_image=product.get("medal_image"),
            
            # Company Info
            vendor_name=product.get("seller"),
            company_location=product.get("company_location"),
            company_founded_year=product.get("company_founded_year"),
            company_website=product.get("company_website"),
            product_website=product.get("product_website"),
            
            # Social Media
            twitter_url=product.get("twitter"),
            twitter_followers=product.get("number_of_followers_on_twitter"),
            linkedin_url=product.get("linkedin"),
            linkedin_employees=product.get("number_of_employees_on_linkedin"),
            
            # Categories
            categories=product.get("categories"),
            primary_category=primary_category,
            parent_category=parent_category,
            
            # Alternatives & Comparisons
            alternatives=product.get("alternatives"),
            comparisons=product.get("comparisons"),
            
            # Features
            features=product.get("detailed_features"),
            feature_summary=feature_summary if feature_summary else None,
            
            # Pricing
            pricing_plans=product.get("pricing_plans"),
            
            # Media
            screenshots=product.get("screenshots"),
            videos=product.get("videos"),
            
            # Additional
            supported_languages=product.get("supported_languages"),
            services_offered=product.get("services_offered"),
            
            # Store raw data for debugging
            raw_data=None,  # Set to `product` if you want full raw data
        )

    async def scrape_with_intelligence(
        self,
        query: str,
        limit: int,
        **kwargs
    ) -> ScrapeResult:
        """
        Scrape G2 reviews AND product intelligence.
        
        Returns both reviews and competitive intelligence data.
        """
        reviews = await self.scrape(query, limit, **kwargs)
        return ScrapeResult(
            reviews=reviews,
            intelligence=self._last_intelligence
        )

    def get_last_intelligence(self) -> Optional[ScrapedProductIntelligence]:
        """Get the product intelligence from the last scrape."""
        return self._last_intelligence

    async def estimate_cost(self, limit: int) -> float:
        """Estimate cost for scraping G2."""
        return limit * self.cost_per_review

    def get_source_name(self) -> str:
        """Get source name."""
        return "G2"

