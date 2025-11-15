"""
Service for generating fake reviews using LLM.
"""

import json
import random
from datetime import datetime, timedelta
from typing import Dict, Optional

from app.config import get_settings
from app.optimal_workflow.agents.base import get_llm
from app.utils.logging import get_logger

logger = get_logger(__name__)


class FakeReviewGenerator:
    """Service for generating realistic fake reviews using LLM."""

    def __init__(self, model: Optional[str] = None):
        """Initialize the fake review generator.
        
        Args:
            model: Optional model name override. If None, uses default from settings.
        """
        self.settings = get_settings()
        self.model = model or self.settings.default_model
        self.llm = get_llm(model=self.model)

    async def generate_review(
        self,
        company_name: str,
        platform: str = "reddit",
        industry: Optional[str] = None
    ) -> Dict:
        """
        Generate a single fake review using LLM.

        Args:
            company_name: Name of the company to generate review for
            platform: Platform the review is from (reddit, twitter, etc.)
            industry: Optional industry context for more realistic reviews

        Returns:
            Dictionary with review data including all required fields
        """
        try:
            # Create a prompt for the LLM to generate realistic review data
            industry_context = f" in the {industry} industry" if industry else ""
            
            prompt = f"""Generate a SHORT customer review for {company_name}{industry_context} on {platform}.

Return ONLY valid JSON (no markdown):
{{
    "content": "Brief review (MAX 30 words, 2-3 short sentences)",
    "author": "username",
    "rating": 1-5,
    "sentiment_score": -1.0 to 1.0
}}

BE CONCISE. Keep content under 30 words. Mix positive/negative randomly."""

            # Generate the review using LLM
            from llama_index.core.llms import ChatMessage, MessageRole
            
            messages = [
                ChatMessage(
                    role=MessageRole.SYSTEM,
                    content="You generate short, realistic customer reviews. Be concise."
                ),
                ChatMessage(
                    role=MessageRole.USER,
                    content=prompt
                )
            ]
            
            response = await self.llm.achat(messages)
            response_text = response.message.content

            # Parse the LLM response
            review_data = self._parse_llm_response(response_text)

            # Add additional fields
            review_data["review_date"] = self._generate_random_date()
            review_data["platform"] = platform
            review_data["url"] = self._generate_fake_url(platform, company_name)

            # Validate the review data
            self._validate_review_data(review_data)

            logger.info(f"Generated fake review for {company_name} on {platform}")
            return review_data

        except Exception as e:
            logger.error(f"Error generating fake review: {e}")
            # Return a fallback simple review if LLM fails
            return self._generate_fallback_review(company_name, platform)

    def _parse_llm_response(self, response: str) -> Dict:
        """Parse the LLM response into a dictionary."""
        try:
            # Clean up the response - remove markdown code blocks if present
            cleaned = response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            # Parse JSON
            data = json.loads(cleaned)

            # Add random platform-specific data
            extra_metadata = {
                "upvotes": random.randint(0, 100),
                "comments_count": random.randint(0, 20)
            }

            # Ensure required fields
            result = {
                "content": data.get("content", ""),
                "author": data.get("author", "anonymous"),
                "rating": int(data.get("rating", 3)),
                "sentiment_score": float(data.get("sentiment_score", 0.0)),
                "extra_metadata": extra_metadata
            }

            return result

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            # Try to extract content from raw text
            return {
                "content": response[:500],  # Use first 500 chars as content
                "author": "anonymous",
                "rating": 3,
                "sentiment_score": 0.0,
                "extra_metadata": {}
            }

    def _generate_random_date(self) -> datetime:
        """Generate a random date within the last 2 years."""
        days_ago = random.randint(0, 730)  # 2 years
        return datetime.utcnow() - timedelta(days=days_ago)

    def _generate_fake_url(self, platform: str, company_name: str) -> str:
        """Generate a fake URL for the review."""
        company_slug = company_name.lower().replace(" ", "-")
        random_id = random.randint(100000, 999999)

        if platform.lower() == "reddit":
            return f"https://reddit.com/r/reviews/comments/{random_id}/review_{company_slug}"
        elif platform.lower() in ["twitter", "twitter/x", "x"]:
            return f"https://twitter.com/user{random_id}/status/{random_id}"
        else:
            return f"https://{platform}.com/reviews/{company_slug}/{random_id}"

    def _validate_review_data(self, data: Dict) -> None:
        """Validate that the review data has all required fields."""
        required_fields = ["content", "author", "rating", "sentiment_score"]
        
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        # Validate rating range
        if not 1 <= data["rating"] <= 5:
            data["rating"] = max(1, min(5, data["rating"]))

        # Validate sentiment score range
        if not -1.0 <= data["sentiment_score"] <= 1.0:
            data["sentiment_score"] = max(-1.0, min(1.0, data["sentiment_score"]))

    def _generate_fallback_review(self, company_name: str, platform: str) -> Dict:
        """Generate a simple fallback review if LLM fails."""
        rating = random.randint(1, 5)
        
        # Generate sentiment based on rating
        if rating >= 4:
            sentiment = random.uniform(0.5, 1.0)
            content = f"Great experience with {company_name}! Would definitely recommend."
        elif rating == 3:
            sentiment = random.uniform(-0.2, 0.2)
            content = f"My experience with {company_name} was okay. Some good, some bad."
        else:
            sentiment = random.uniform(-1.0, -0.5)
            content = f"Not satisfied with {company_name}. Expected better."

        return {
            "content": content,
            "author": f"user_{random.randint(1000, 9999)}",
            "rating": rating,
            "sentiment_score": sentiment,
            "review_date": self._generate_random_date(),
            "platform": platform,
            "url": self._generate_fake_url(platform, company_name),
            "extra_metadata": {
                "upvotes": random.randint(0, 100),
                "comments_count": random.randint(0, 20),
                "fallback": True
            }
        }


# Singleton instance
_generator: Optional[FakeReviewGenerator] = None


def get_fake_review_generator() -> FakeReviewGenerator:
    """Get or create the fake review generator singleton."""
    global _generator
    if _generator is None:
        _generator = FakeReviewGenerator()
    return _generator

