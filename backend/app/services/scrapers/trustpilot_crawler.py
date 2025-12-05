"""
Trustpilot scraper using Apify's Website Content Crawler.

Uses the generic website-content-crawler actor to scrape Trustpilot reviews
and extract them as markdown content for LLM processing.
"""

import asyncio
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp

from app.exceptions import ExternalServiceError
from app.utils.logging import get_logger

from .base import BaseReviewScraper, ScrapedReview

logger = get_logger("trustpilot_crawler")


class TrustpilotCrawler(BaseReviewScraper):
    """
    Trustpilot scraper using Apify's Website Content Crawler.
    
    Crawls Trustpilot review pages and extracts content as markdown.
    Better for LLM processing than structured scraping.
    """

    ACTOR_ID = "apify~website-content-crawler"
    BASE_URL = "https://www.trustpilot.com"

    def __init__(self, settings: Any):
        super().__init__(settings)
        self.api_token = settings.get_secret("apify_api_token")
        self.cost_per_page = 0.02  # Approximate cost per page crawled

    def build_trustpilot_url(self, company: str, page: int = 1) -> str:
        """
        Build Trustpilot URL for a company.
        
        Args:
            company: Company name or slug (e.g., "notion.so" or "https://trustpilot.com/review/notion.so")
            page: Page number for pagination
            
        Returns:
            Full Trustpilot URL
        """
        # If already a full URL, extract the company slug
        if company.startswith("http"):
            match = re.search(r"trustpilot\.com/review/([^/?]+)", company)
            if match:
                company = match.group(1)
            else:
                # Try to use as-is if it looks like a URL path
                company = company.rstrip("/").split("/")[-1]
        
        # Clean up company name
        company = company.lower().strip()
        
        # Build URL with pagination
        url = f"{self.BASE_URL}/review/{company}"
        if page > 1:
            url += f"?page={page}"
        
        return url

    async def scrape(
        self,
        query: str,
        limit: int,
        **kwargs
    ) -> List[ScrapedReview]:
        """
        Scrape Trustpilot reviews using Website Content Crawler.
        
        Args:
            query: Company name, slug, or Trustpilot URL
            limit: Maximum number of reviews to collect
            **kwargs: Additional parameters:
                - max_pages: Max pages to crawl (default: calculated from limit)
                - wait_for_selector: CSS selector to wait for
                
        Returns:
            List of scraped reviews
        """
        if not await self.validate_query(query):
            raise ValueError(f"Invalid query: {query}")

        if not self.api_token:
            raise ExternalServiceError("Apify API token not configured", service="apify")

        try:
            # Calculate pages needed (Trustpilot shows ~20 reviews per page)
            reviews_per_page = 20
            max_pages = kwargs.get("max_pages", (limit // reviews_per_page) + 1)
            max_pages = min(max_pages, 50)  # Cap at 50 pages
            
            # Build start URLs for multiple pages
            start_urls = []
            for page in range(1, max_pages + 1):
                url = self.build_trustpilot_url(query, page)
                start_urls.append({"url": url})
            
            # Prepare Website Content Crawler input
            actor_input = {
                "startUrls": start_urls,
                "maxCrawlPages": max_pages,
                "maxResults": max_pages,
                "crawlerType": "playwright:firefox",  # Better for JS-heavy sites
                "includeUrlGlobs": [
                    f"{self.BASE_URL}/review/*"
                ],
                "excludeUrlGlobs": [
                    "*/users/*",
                    "*/categories/*",
                    "*/about/*",
                    "*/business/*",
                ],
                "htmlTransformer": "readableText",
                "saveMarkdown": True,
                "saveHtml": False,
                "saveScreenshots": False,
                "maxScrollHeightPixels": 10000,  # Scroll to load more content
                "pageLoadTimeoutSecs": 60,
                "maxConcurrency": 5,
            }

            # Start Apify actor run
            async with aiohttp.ClientSession() as session:
                run_id = await self._start_actor_run(session, actor_input)
                logger.info(f"Started Apify Website Content Crawler run: {run_id}")

                # Wait for completion
                status_data = await self._wait_for_completion(session, run_id)

                # Get results
                dataset_id = status_data["data"]["defaultDatasetId"]
                items = await self._get_results(session, dataset_id)

            # Parse crawled pages into reviews
            reviews = []
            for item in items:
                page_reviews = self._parse_page_content(item)
                reviews.extend(page_reviews)

            logger.info(f"Extracted {len(reviews)} reviews from Trustpilot")
            return reviews[:limit]

        except aiohttp.ClientError as e:
            logger.error(f"Network error in Trustpilot crawler: {e}")
            raise ExternalServiceError(
                f"Trustpilot crawling failed: {e}", 
                service="apify", 
                retryable=True
            )
        except Exception as e:
            logger.error(f"Error in Trustpilot crawler: {e}")
            raise ExternalServiceError(
                f"Trustpilot crawling failed: {e}", 
                service="trustpilot_crawler"
            )

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
        max_wait: int = 600  # 10 minutes for crawling
    ) -> Dict[str, Any]:
        """Wait for actor run to complete."""
        headers = {"Authorization": f"Bearer {self.api_token}"}
        waited = 0
        status_data = None
        
        while waited < max_wait:
            await asyncio.sleep(10)  # Check every 10 seconds
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
                
                logger.debug(f"Crawler status: {status}, waited: {waited}s")

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

    def _parse_page_content(self, item: Dict[str, Any]) -> List[ScrapedReview]:
        """
        Parse a crawled page's markdown content into individual reviews.
        
        Trustpilot pages contain multiple reviews. We extract them from
        the markdown content.
        """
        reviews = []
        markdown = item.get("markdown", "") or item.get("text", "")
        page_url = item.get("url", "")
        
        if not markdown:
            return reviews

        # Extract company name from URL
        company_match = re.search(r"trustpilot\.com/review/([^/?]+)", page_url)
        company_name = company_match.group(1) if company_match else "Unknown"

        # Parse individual reviews from markdown
        # Trustpilot reviews typically have patterns like:
        # - Star ratings (★★★★★ or "Rated X out of 5")
        # - Review dates
        # - Review text
        
        # Try to split by review boundaries (common patterns)
        review_blocks = self._split_into_review_blocks(markdown)
        
        for block in review_blocks:
            review = self._parse_review_block(block, company_name, page_url)
            if review:
                reviews.append(review)

        return reviews

    def _split_into_review_blocks(self, markdown: str) -> List[str]:
        """Split markdown content into individual review blocks."""
        # Common patterns that separate reviews on Trustpilot
        # - "Rated X out of 5" or star patterns
        # - Date patterns like "Date of experience: ..."
        
        # Try splitting by rating patterns
        patterns = [
            r"(?=Rated \d+ out of 5)",
            r"(?=★{1,5})",
            r"(?=\d+ star)",
            r"(?=Date of experience:)",
        ]
        
        blocks = [markdown]
        for pattern in patterns:
            new_blocks = []
            for block in blocks:
                splits = re.split(pattern, block, flags=re.IGNORECASE)
                new_blocks.extend([s.strip() for s in splits if s.strip()])
            if len(new_blocks) > len(blocks):
                blocks = new_blocks
                break
        
        # Filter out blocks that are too short (likely not reviews)
        return [b for b in blocks if len(b) > 50]

    def _parse_review_block(
        self, 
        block: str, 
        company_name: str,
        page_url: str
    ) -> Optional[ScrapedReview]:
        """Parse a single review block into a ScrapedReview."""
        if not block or len(block) < 20:
            return None

        # Extract rating
        rating = self._extract_rating(block)
        
        # Extract date
        review_date = self._extract_date(block)
        
        # Extract author
        author = self._extract_author(block)
        
        # Clean content - remove metadata, keep the actual review text
        content = self._clean_review_content(block)
        
        if not content or len(content) < 10:
            return None

        return ScrapedReview(
            content=self.clean_content(content),
            author=author,
            url=page_url,
            review_date=review_date,
            metadata={
                "type": "trustpilot_review",
                "source": "website_crawler",
                "rating": rating,
                "company_name": company_name,
                "verified": "Verified" in block,
                "raw_block_length": len(block)
            }
        )

    def _extract_rating(self, text: str) -> Optional[int]:
        """Extract star rating from text."""
        # "Rated X out of 5"
        match = re.search(r"Rated (\d) out of 5", text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        
        # Count stars
        stars = text.count("★")
        if stars > 0:
            return min(stars, 5)
        
        # "X star" pattern
        match = re.search(r"(\d)\s*star", text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        
        return None

    def _extract_date(self, text: str) -> Optional[datetime]:
        """Extract review date from text."""
        # "Date of experience: Month Day, Year"
        patterns = [
            r"Date of experience:\s*(\w+ \d{1,2},? \d{4})",
            r"(\w+ \d{1,2},? \d{4})",
            r"(\d{1,2}/\d{1,2}/\d{4})",
            r"(\d{4}-\d{2}-\d{2})",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    from dateutil import parser
                    return parser.parse(match.group(1))
                except:
                    continue
        
        return None

    def _extract_author(self, text: str) -> Optional[str]:
        """Extract author name from text."""
        # Look for name patterns at the start or end of block
        # Trustpilot often shows "Name • Location" or just a name
        
        lines = text.strip().split("\n")
        for line in lines[:3]:  # Check first 3 lines
            line = line.strip()
            # Skip if it looks like a rating or date
            if re.match(r"^(Rated|★|\d+ star|Date of)", line, re.IGNORECASE):
                continue
            # Skip very long lines (likely review content)
            if len(line) > 50:
                continue
            # Extract name before bullet or location info
            name_match = re.match(r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", line)
            if name_match:
                return name_match.group(1)
        
        return None

    def _clean_review_content(self, text: str) -> str:
        """Clean review block to extract just the review text."""
        # Remove common metadata patterns
        patterns_to_remove = [
            r"Rated \d+ out of 5.*?(?=\n|$)",
            r"Date of experience:.*?(?=\n|$)",
            r"★+",
            r"Verified",
            r"\d+ reviews?",
            r"Reply from.*",
            r"Updated.*",
        ]
        
        content = text
        for pattern in patterns_to_remove:
            content = re.sub(pattern, "", content, flags=re.IGNORECASE)
        
        # Clean up whitespace
        content = re.sub(r"\n{3,}", "\n\n", content)
        content = content.strip()
        
        return content

    async def estimate_cost(self, limit: int) -> float:
        """Estimate cost for crawling Trustpilot."""
        reviews_per_page = 20
        pages_needed = (limit // reviews_per_page) + 1
        return pages_needed * self.cost_per_page

    def get_source_name(self) -> str:
        """Get source name."""
        return "Trustpilot"


# Alternative: Simple single-page scraper for quick lookups
class TrustpilotQuickScraper(TrustpilotCrawler):
    """
    Quick Trustpilot scraper for single company pages.
    
    Faster but less comprehensive than full crawler.
    Good for getting a quick sample of reviews.
    """

    async def scrape_single_page(
        self, 
        company: str
    ) -> List[ScrapedReview]:
        """Scrape just the first page of reviews for quick results."""
        return await self.scrape(company, limit=20, max_pages=1)

