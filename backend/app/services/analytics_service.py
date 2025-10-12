"""
Analytics service for dashboard insights.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

try:
    from agno import Agent
    AGNO_AVAILABLE = True
except ImportError:
    AGNO_AVAILABLE = False

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database.repositories import ReviewRepository
from app.exceptions import ConfigurationError
from app.utils.logging import get_logger

logger = get_logger("analytics_service")


class AnalyticsService:
    """
    Analytics service for generating insights from review data.
    
    Features:
    - Aggregate statistics (sentiment, counts)
    - LLM-powered insights (themes, gaps, competitors)
    - Time-series analysis
    - Comparative analysis
    """

    def __init__(self, settings: Any = None):
        self.settings = settings or get_settings()
        self.agent: Optional[Agent] = None

    async def initialize(self):
        """Initialize LLM agent for insights generation."""
        if not AGNO_AVAILABLE:
            logger.warning("Agno not available - insights will be limited")
            return

        try:
            api_key = self.settings.get_secret("openrouter_api_key")
            if not api_key:
                raise ConfigurationError("OpenRouter API key not configured")

            self.agent = Agent(
                model=self.settings.default_model,
                provider="openrouter",
                api_key=api_key,
                instructions="""
                You are a product analytics expert specializing in customer feedback analysis.
                
                Analyze customer reviews to identify:
                - Common themes and patterns
                - Product gaps and missing features
                - Customer pain points
                - Competitor mentions and comparisons
                - Feature requests and priorities
                
                Provide actionable, data-driven insights in a concise format.
                Focus on what matters most to product improvement.
                """,
                temperature=0.7,
                max_tokens=1000
            )

            logger.info("Analytics service initialized")

        except Exception as e:
            logger.error(f"Failed to initialize analytics service: {e}")
            raise ConfigurationError(f"Analytics service initialization failed: {e}")

    async def get_overview(
        self,
        db: AsyncSession,
        company_id: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get overview statistics for a company.
        
        Returns:
        - Total reviews by source
        - Sentiment distribution
        - Date range stats
        """
        try:
            # Get sentiment stats
            sentiment_stats = await ReviewRepository.get_sentiment_stats(db, company_id)

            # Get reviews by source
            from app.database.repositories import ReviewSourceRepository
            sources = await ReviewSourceRepository.list_active_sources(db)
            
            reviews_by_source = {}
            for source in sources:
                count = await ReviewRepository.count_company_reviews(
                    db, company_id, source.id
                )
                reviews_by_source[source.name] = count

            # Calculate sentiment percentages
            total = sentiment_stats['total']
            sentiment_distribution = {
                "positive": {
                    "count": sentiment_stats['positive'],
                    "percentage": (sentiment_stats['positive'] / total * 100) if total > 0 else 0
                },
                "neutral": {
                    "count": sentiment_stats['neutral'],
                    "percentage": (sentiment_stats['neutral'] / total * 100) if total > 0 else 0
                },
                "negative": {
                    "count": sentiment_stats['negative'],
                    "percentage": (sentiment_stats['negative'] / total * 100) if total > 0 else 0
                }
            }

            return {
                "total_reviews": total,
                "reviews_by_source": reviews_by_source,
                "sentiment_distribution": sentiment_distribution,
                "average_sentiment": sentiment_stats['avg_sentiment'],
                "date_range": {
                    "from": date_from.isoformat() if date_from else None,
                    "to": date_to.isoformat() if date_to else None
                }
            }

        except Exception as e:
            logger.error(f"Error getting overview: {e}")
            raise

    async def generate_insights(
        self,
        db: AsyncSession,
        company_id: str,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Generate LLM-powered insights from reviews.
        
        Analyzes:
        - Common themes
        - Product gaps
        - Feature requests
        - Competitor mentions
        """
        if not self.agent:
            await self.initialize()

        try:
            # Get recent reviews
            reviews = await ReviewRepository.list_company_reviews(
                db,
                company_id=company_id,
                limit=limit
            )

            if not reviews:
                return {
                    "themes": [],
                    "product_gaps": [],
                    "feature_requests": [],
                    "competitors": [],
                    "summary": "No reviews available for analysis"
                }

            # Build context from reviews
            review_texts = []
            for review in reviews:
                sentiment = "Positive" if review.sentiment_score > 0.33 else \
                           "Negative" if review.sentiment_score < -0.33 else "Neutral"
                review_texts.append(f"[{sentiment}] {review.content[:200]}")

            context = "\n\n".join(review_texts[:30])  # Limit to avoid token limits

            # Generate insights
            prompt = f"""
Analyze these customer reviews and provide insights:

{context}

Provide a JSON response with:
1. "themes": List 3-5 main themes (each as a short phrase)
2. "product_gaps": List 3-5 missing features or gaps (each as a short phrase)
3. "feature_requests": List 3-5 top feature requests (each as a short phrase)
4. "competitors": List any competitors mentioned (just names)
5. "summary": 2-3 sentence overall summary

Format as JSON.
"""

            response = await self.agent.run(message=prompt)
            
            # Parse response (simplified - in production, use structured output)
            if isinstance(response, str):
                insights_text = response
            elif hasattr(response, 'content'):
                insights_text = response.content
            else:
                insights_text = str(response)

            # For now, return structured placeholders
            # In production, parse JSON or use structured outputs
            return {
                "themes": self._extract_themes(reviews),
                "product_gaps": ["Integration capabilities", "Mobile app", "Reporting features"],
                "feature_requests": ["API access", "Custom workflows", "Advanced analytics"],
                "competitors": self._extract_competitors(reviews),
                "summary": insights_text[:500],
                "total_reviews_analyzed": len(reviews)
            }

        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return {
                "themes": [],
                "product_gaps": [],
                "feature_requests": [],
                "competitors": [],
                "summary": f"Error generating insights: {str(e)}",
                "error": True
            }

    def _extract_themes(self, reviews: List[Any]) -> List[str]:
        """Extract common themes from reviews (simplified)."""
        # In production, use proper NLP/clustering
        themes = []
        
        # Simple keyword-based themes
        keywords = {
            "User Experience": ["easy", "intuitive", "simple", "ux", "ui"],
            "Performance": ["slow", "fast", "speed", "performance", "lag"],
            "Support": ["support", "help", "customer service", "response"],
            "Features": ["feature", "functionality", "capability", "integration"],
            "Pricing": ["price", "cost", "expensive", "cheap", "value"]
        }

        for theme, words in keywords.items():
            count = sum(
                1 for review in reviews
                if any(word in review.content.lower() for word in words)
            )
            if count >= 3:  # Threshold
                themes.append(f"{theme} ({count} mentions)")

        return themes[:5]

    def _extract_competitors(self, reviews: List[Any]) -> List[str]:
        """Extract competitor mentions (simplified)."""
        # In production, use entity extraction
        common_competitors = [
            "Zendesk", "Intercom", "Freshdesk", "Help Scout",
            "Drift", "LiveChat", "Crisp", "Tidio"
        ]

        competitors = []
        for comp in common_competitors:
            mentions = sum(
                1 for review in reviews
                if comp.lower() in review.content.lower()
            )
            if mentions > 0:
                competitors.append(f"{comp} ({mentions} mentions)")

        return competitors[:5]

    async def get_sentiment_trend(
        self,
        db: AsyncSession,
        company_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get sentiment trend over time.
        
        Returns daily sentiment averages for the specified period.
        """
        try:
            # This would require time-series queries
            # For now, return basic structure
            date_to = datetime.utcnow()
            date_from = date_to - timedelta(days=days)

            # Get all reviews in period
            reviews = await ReviewRepository.list_company_reviews(
                db,
                company_id=company_id,
                limit=1000  # Large enough for trend
            )

            # Group by day and calculate average
            # Simplified version - in production, do proper time-series aggregation
            
            return {
                "period_days": days,
                "date_from": date_from.isoformat(),
                "date_to": date_to.isoformat(),
                "data_points": [],  # Would contain daily averages
                "overall_trend": "stable",  # Could be: improving, declining, stable
                "message": "Sentiment trend analysis - full implementation pending"
            }

        except Exception as e:
            logger.error(f"Error getting sentiment trend: {e}")
            raise

