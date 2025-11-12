"""
Anomaly Detection Agent for Product Review Analysis Workflow.

The Anomaly Detection Agent identifies unusual patterns, spikes, and anomalies in review data,
generating high-severity insights for critical issues that require immediate attention.
"""

import json
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.core.llm.base import BaseLLMClient
from app.database.repositories.chat_message_step import ChatMessageStepRepository
from app.models.workflow import ExecutionContext, Insight
from app.utils.logging import get_logger
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


class AnomalyDetectionAgent:
    """
    Specialized agent for detecting anomalies and unusual patterns in product reviews.
    
    The Anomaly Detection Agent:
    1. Detects sudden spikes or drops in review ratings
    2. Identifies unusual topic emergence
    3. Detects source-specific anomalies (platform-specific issues)
    4. Generates high-severity Insight objects for critical issues
    5. Tracks reasoning and execution in Chat Message Steps
    """
    
    def __init__(
        self,
        llm_client: BaseLLMClient,
        stream_callback: Optional[Callable] = None
    ):
        """
        Initialize the Anomaly Detection Agent.
        
        Args:
            llm_client: LLM client for anomaly analysis
            stream_callback: Optional callback for streaming events
        """
        self.llm_client = llm_client
        self.stream_callback = stream_callback
        logger.info("Initialized AnomalyDetectionAgent")
    
    async def detect_anomalies(
        self,
        reviews: List[Dict[str, Any]],
        context: ExecutionContext,
        db: AsyncSession,
        step_order: int,
        time_window: str = "daily"
    ) -> List[Insight]:
        """
        Detect anomalies and unusual patterns in reviews.
        
        This method:
        1. Generates a thought explaining the anomaly detection strategy
        2. Detects rating spikes and drops
        3. Identifies unusual topic emergence
        4. Detects source-specific anomalies
        5. Generates high-severity Insight objects
        6. Tracks execution in Chat Message Steps
        
        Args:
            reviews: List of review dictionaries
            context: Execution context
            db: Database session for tracking
            step_order: Step order in execution
            time_window: Time window for analysis (daily, weekly)
            
        Returns:
            List of Insight objects with anomaly findings
        """
        logger.info(f"Detecting anomalies in {len(reviews)} reviews")
        
        # Emit step start event
        await self._emit_event("agent_step_start", {
            "agent_name": "anomaly_detection",
            "action": "detect_anomalies",
            "review_count": len(reviews),
            "time_window": time_window
        })
        
        try:
            # Generate thought before analysis
            thought = await self.generate_thought(
                reviews=reviews,
                context=context
            )
            
            # Save thought step
            await ChatMessageStepRepository.create(
                db=db,
                message_id=context.message_id,
                agent_name="anomaly_detection",
                step_order=step_order,
                thought=thought
            )
            
            # Perform anomaly detection
            insights = []
            
            # 1. Detect rating spikes and drops
            rating_anomalies = await self._detect_rating_anomalies(
                reviews=reviews,
                time_window=time_window,
                context=context
            )
            insights.extend(rating_anomalies)
            
            # 2. Detect unusual topic emergence
            topic_anomalies = await self._detect_topic_anomalies(
                reviews=reviews,
                context=context
            )
            insights.extend(topic_anomalies)
            
            # 3. Detect source-specific anomalies
            source_anomalies = await self._detect_source_anomalies(
                reviews=reviews,
                context=context
            )
            insights.extend(source_anomalies)
            
            # Save insights to context
            context.insights.extend(insights)
            
            # Save structured output step
            await ChatMessageStepRepository.create(
                db=db,
                message_id=context.message_id,
                agent_name="anomaly_detection",
                step_order=step_order + 1,
                structured_output={
                    "insights_generated": len(insights),
                    "anomaly_types": [i.metadata.get("anomaly_type") for i in insights],
                    "critical_anomalies": sum(1 for i in insights if i.severity_score > 0.9)
                }
            )
            
            # Emit step complete event
            await self._emit_event("agent_step_complete", {
                "agent_name": "anomaly_detection",
                "action": "detect_anomalies",
                "success": True,
                "insights_generated": len(insights),
                "critical_anomalies": sum(1 for i in insights if i.severity_score > 0.9)
            })
            
            logger.info(f"Generated {len(insights)} anomaly insights")
            return insights
            
        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}", exc_info=True)
            
            # Emit error event
            await self._emit_event("agent_step_error", {
                "agent_name": "anomaly_detection",
                "action": "detect_anomalies",
                "error": str(e)
            })
            
            # Track error in Chat Message Steps
            await ChatMessageStepRepository.create(
                db=db,
                message_id=context.message_id,
                agent_name="anomaly_detection",
                step_order=step_order + 1,
                thought=f"Failed to detect anomalies: {str(e)}"
            )
            
            return []
    
    async def generate_thought(
        self,
        reviews: List[Dict[str, Any]],
        context: ExecutionContext
    ) -> str:
        """
        Generate reasoning trace before performing anomaly detection.
        
        This method creates a thought explaining:
        - The anomaly detection strategy
        - Baseline calculation approach
        - What types of anomalies to look for
        
        Args:
            reviews: List of reviews to analyze
            context: Execution context
            
        Returns:
            Thought string explaining the anomaly detection plan
        """
        logger.info("Generating anomaly detection thought")
        
        # Build thought prompt
        system_prompt = """You are an anomaly detection expert planning an analysis strategy.
Explain your approach clearly and concisely."""
        
        # Calculate basic statistics for context
        ratings = [r.get("rating", 0) for r in reviews if r.get("rating")]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        
        user_prompt = f"""I need to detect anomalies and unusual patterns in {len(reviews)} product reviews.

Average rating: {avg_rating:.2f} / 5.0
Total reviews: {len(reviews)}

Generate a brief thought explaining:
1. Your anomaly detection strategy
2. How you'll establish baseline behavior
3. What types of anomalies you'll look for (rating spikes, unusual topics, source-specific issues)
4. What threshold you'll use to flag critical anomalies

Keep it concise (2-3 sentences)."""
        
        try:
            thought = await self.llm_client.generate_completion(
                prompt=user_prompt,
                system_message=system_prompt,
                temperature=0.3,
                max_tokens=200
            )
            
            logger.debug(f"Generated thought: {thought[:100]}...")
            return thought.strip()
            
        except Exception as e:
            logger.error(f"Error generating thought: {e}")
            # Fallback thought
            return (
                f"I will analyze {len(reviews)} reviews to detect anomalies. "
                f"I'll establish baseline patterns for ratings and topics, then identify "
                f"significant deviations such as rating spikes, unusual topic emergence, "
                f"and platform-specific issues. Critical anomalies (>90% severity) will be flagged."
            )

    
    async def _detect_rating_anomalies(
        self,
        reviews: List[Dict[str, Any]],
        time_window: str,
        context: ExecutionContext
    ) -> List[Insight]:
        """
        Detect sudden spikes or drops in review ratings.
        
        Analyzes rating patterns over time and identifies significant deviations
        from baseline behavior.
        
        Args:
            reviews: List of reviews
            time_window: Time window for grouping (daily, weekly)
            context: Execution context
            
        Returns:
            List of Insight objects for rating anomalies
        """
        logger.info("Detecting rating anomalies")
        
        insights = []
        
        # Check if reviews have date information
        reviews_with_dates = [
            r for r in reviews
            if (r.get("date") or r.get("created_at") or r.get("timestamp")) and r.get("rating")
        ]
        
        if len(reviews_with_dates) < 10:
            logger.info("Not enough reviews with dates for rating anomaly detection")
            return insights
        
        # Sort reviews by date
        sorted_reviews = sorted(reviews_with_dates, key=self._get_review_date)
        
        # Group reviews by time period
        time_groups = self._group_reviews_by_time(sorted_reviews, time_window)
        
        if len(time_groups) < 3:
            logger.info("Not enough time periods for rating anomaly detection")
            return insights
        
        # Calculate statistics for each period
        period_stats = []
        for period_name, period_reviews in time_groups.items():
            ratings = [r.get("rating", 0) for r in period_reviews]
            low_ratings = [r for r in ratings if r <= 2]
            
            period_stats.append({
                "period": period_name,
                "avg_rating": sum(ratings) / len(ratings) if ratings else 0,
                "review_count": len(period_reviews),
                "low_rating_count": len(low_ratings),
                "low_rating_pct": (len(low_ratings) / len(ratings) * 100) if ratings else 0,
                "reviews": period_reviews
            })
        
        # Calculate baseline (average of all periods except the most recent)
        if len(period_stats) >= 3:
            baseline_periods = period_stats[:-1]  # Exclude most recent
            baseline_low_rating_count = sum(p["low_rating_count"] for p in baseline_periods) / len(baseline_periods)
            baseline_avg_rating = sum(p["avg_rating"] for p in baseline_periods) / len(baseline_periods)
            
            # Check most recent period for anomalies
            recent_period = period_stats[-1]
            
            # Detect low rating spike
            if baseline_low_rating_count > 0:
                spike_ratio = recent_period["low_rating_count"] / baseline_low_rating_count
            else:
                spike_ratio = recent_period["low_rating_count"] if recent_period["low_rating_count"] > 0 else 0
            
            # Create insight if spike is significant (>200% increase)
            if spike_ratio >= 2.0 and recent_period["low_rating_count"] >= 3:
                spike_pct = (spike_ratio - 1) * 100
                
                insight_text = (
                    f"CRITICAL: Low-rating reviews (1-2 stars) spiked {spike_pct:.0f}% in {recent_period['period']} "
                    f"({recent_period['low_rating_count']} reviews vs {baseline_low_rating_count:.1f} avg)"
                )
                
                # Calculate severity (higher spike = higher severity)
                severity_score = min(0.95, 0.7 + (spike_ratio - 2.0) * 0.1)
                
                # Use LLM to analyze the spike and provide recommendations
                recommended_action = await self._analyze_rating_spike(
                    recent_reviews=recent_period["reviews"],
                    spike_ratio=spike_ratio,
                    context=context
                )
                
                insight = Insight(
                    source_agent="anomaly_detection",
                    insight_text=insight_text,
                    severity_score=severity_score,
                    confidence_score=0.93,
                    supporting_reviews=[r.get("id", "") for r in recent_period["reviews"]],
                    visualization_hint="line_chart",
                    visualization_data={
                        "x": [p["period"] for p in period_stats],
                        "y": [p["low_rating_count"] for p in period_stats],
                        "chart_type": "line",
                        "title": "Low-Rating Review Spike",
                        "x_label": "Time Period",
                        "y_label": "Number of 1-2 Star Reviews",
                        "annotations": [{
                            "x": recent_period["period"],
                            "text": "Spike detected"
                        }]
                    },
                    metadata={
                        "anomaly_type": "rating_spike",
                        "baseline": baseline_low_rating_count,
                        "spike_value": recent_period["low_rating_count"],
                        "spike_ratio": spike_ratio,
                        "spike_date": recent_period["period"],
                        "recommended_action": recommended_action
                    }
                )
                
                insights.append(insight)
                logger.info(f"Detected rating spike: {spike_ratio:.1f}x increase")
            
            # Detect rating drop (average rating decline)
            rating_decline = baseline_avg_rating - recent_period["avg_rating"]
            if rating_decline >= 0.5 and recent_period["review_count"] >= 5:
                decline_pct = (rating_decline / baseline_avg_rating * 100) if baseline_avg_rating > 0 else 0
                
                insight_text = (
                    f"Average rating dropped {rating_decline:.2f} points in {recent_period['period']} "
                    f"(from {baseline_avg_rating:.2f} to {recent_period['avg_rating']:.2f})"
                )
                
                severity_score = min(0.90, rating_decline / 5.0 + 0.5)
                
                insight = Insight(
                    source_agent="anomaly_detection",
                    insight_text=insight_text,
                    severity_score=severity_score,
                    confidence_score=0.88,
                    supporting_reviews=[r.get("id", "") for r in recent_period["reviews"]],
                    visualization_hint="line_chart",
                    visualization_data={
                        "x": [p["period"] for p in period_stats],
                        "y": [p["avg_rating"] for p in period_stats],
                        "chart_type": "line",
                        "title": "Average Rating Decline",
                        "x_label": "Time Period",
                        "y_label": "Average Rating"
                    },
                    metadata={
                        "anomaly_type": "rating_decline",
                        "baseline": baseline_avg_rating,
                        "current_value": recent_period["avg_rating"],
                        "decline_amount": rating_decline,
                        "decline_percentage": decline_pct,
                        "recommended_action": "Investigate recent product changes or service issues"
                    }
                )
                
                insights.append(insight)
                logger.info(f"Detected rating decline: {rating_decline:.2f} points")
        
        return insights
    
    async def _analyze_rating_spike(
        self,
        recent_reviews: List[Dict[str, Any]],
        spike_ratio: float,
        context: ExecutionContext
    ) -> str:
        """
        Use LLM to analyze a rating spike and provide recommendations.
        
        Args:
            recent_reviews: Reviews from the spike period
            spike_ratio: Magnitude of the spike
            context: Execution context
            
        Returns:
            Recommended action string
        """
        try:
            # Get low-rating reviews from the spike period
            low_rating_reviews = [r for r in recent_reviews if r.get("rating", 0) <= 2]
            
            if not low_rating_reviews:
                return "Investigate recent changes or updates"
            
            review_texts = [r.get("text", "")[:200] for r in low_rating_reviews[:10]]
            
            system_prompt = """You are an expert at analyzing customer feedback patterns.
Provide a concise recommendation based on the spike in negative reviews."""
            
            user_prompt = f"""There has been a {spike_ratio:.1f}x spike in low-rating (1-2 star) reviews.

Sample recent low-rating reviews:
{chr(10).join(f"- {text}" for text in review_texts)}

Based on these reviews, provide ONE specific recommended action (1 sentence, max 20 words).
Focus on the most likely root cause."""
            
            recommendation = await self.llm_client.generate_completion(
                prompt=user_prompt,
                system_message=system_prompt,
                temperature=0.2,
                max_tokens=50
            )
            
            return recommendation.strip()
            
        except Exception as e:
            logger.error(f"Error analyzing rating spike: {e}")
            return "Investigate recent product changes or service issues"
    
    async def _detect_topic_anomalies(
        self,
        reviews: List[Dict[str, Any]],
        context: ExecutionContext
    ) -> List[Insight]:
        """
        Detect unusual topic emergence or sudden topic spikes.
        
        Identifies topics that appear suddenly or increase dramatically,
        which may indicate new issues or emerging problems.
        
        Args:
            reviews: List of reviews
            context: Execution context
            
        Returns:
            List of Insight objects for topic anomalies
        """
        logger.info("Detecting topic anomalies")
        
        insights = []
        
        # Check if reviews have date information
        reviews_with_dates = [
            r for r in reviews
            if r.get("date") or r.get("created_at") or r.get("timestamp")
        ]
        
        if len(reviews_with_dates) < 15:
            logger.info("Not enough reviews with dates for topic anomaly detection")
            return insights
        
        # Sort reviews by date
        sorted_reviews = sorted(reviews_with_dates, key=self._get_review_date)
        
        # Split into recent and historical
        split_point = int(len(sorted_reviews) * 0.7)
        historical_reviews = sorted_reviews[:split_point]
        recent_reviews = sorted_reviews[split_point:]
        
        if len(recent_reviews) < 5:
            logger.info("Not enough recent reviews for topic anomaly detection")
            return insights
        
        # Use LLM to identify emerging topics in recent reviews
        emerging_topics = await self._identify_emerging_topics(
            historical_reviews=historical_reviews,
            recent_reviews=recent_reviews,
            context=context
        )
        
        # Create insights for significant emerging topics
        for topic in emerging_topics:
            topic_name = topic.get("topic_name", "Unknown")
            recent_count = topic.get("recent_count", 0)
            historical_count = topic.get("historical_count", 0)
            severity = topic.get("severity", "medium")
            
            # Calculate emergence ratio
            if historical_count > 0:
                emergence_ratio = recent_count / historical_count
            else:
                emergence_ratio = float('inf') if recent_count > 0 else 0
            
            # Only create insight for significant emergence
            if emergence_ratio >= 3.0 or (historical_count == 0 and recent_count >= 3):
                if emergence_ratio == float('inf'):
                    insight_text = (
                        f"NEW ISSUE: '{topic_name}' emerged suddenly with {recent_count} mentions "
                        f"in recent reviews (not seen in historical data)"
                    )
                else:
                    insight_text = (
                        f"EMERGING ISSUE: '{topic_name}' mentions increased {emergence_ratio:.1f}x "
                        f"({historical_count} → {recent_count} reviews)"
                    )
                
                # Higher severity for completely new topics
                if historical_count == 0:
                    severity_score = min(0.92, 0.75 + (recent_count * 0.03))
                else:
                    severity_score = min(0.88, 0.6 + (emergence_ratio * 0.05))
                
                insight = Insight(
                    source_agent="anomaly_detection",
                    insight_text=insight_text,
                    severity_score=severity_score,
                    confidence_score=0.85,
                    supporting_reviews=[r.get("id", "") for r in recent_reviews if topic_name.lower() in r.get("text", "").lower()][:10],
                    visualization_hint="bar_chart",
                    visualization_data={
                        "x": ["Historical", "Recent"],
                        "y": [historical_count, recent_count],
                        "chart_type": "bar",
                        "title": f"Topic Emergence: {topic_name}",
                        "x_label": "Time Period",
                        "y_label": "Number of Mentions"
                    },
                    metadata={
                        "anomaly_type": "topic_emergence",
                        "topic_name": topic_name,
                        "historical_count": historical_count,
                        "recent_count": recent_count,
                        "emergence_ratio": emergence_ratio if emergence_ratio != float('inf') else None,
                        "severity": severity,
                        "recommended_action": f"Investigate root cause of {topic_name} complaints"
                    }
                )
                
                insights.append(insight)
                logger.info(f"Detected emerging topic: {topic_name} ({emergence_ratio:.1f}x)")
        
        return insights
    
    async def _identify_emerging_topics(
        self,
        historical_reviews: List[Dict[str, Any]],
        recent_reviews: List[Dict[str, Any]],
        context: ExecutionContext
    ) -> List[Dict[str, Any]]:
        """
        Use LLM to identify topics that are emerging in recent reviews.
        
        Args:
            historical_reviews: Older reviews for baseline
            recent_reviews: Recent reviews to analyze
            context: Execution context
            
        Returns:
            List of emerging topic dictionaries
        """
        try:
            system_prompt = """You are an expert at identifying emerging issues in customer feedback.
Compare historical and recent reviews to find new or increasing topics."""
            
            historical_texts = [r.get("text", "")[:200] for r in historical_reviews[:30]]
            recent_texts = [r.get("text", "")[:200] for r in recent_reviews[:20]]
            
            user_prompt = f"""Compare these two sets of product reviews to identify emerging topics.

HISTORICAL REVIEWS ({len(historical_reviews)} total):
{chr(10).join(f"- {text}" for text in historical_texts[:15])}

RECENT REVIEWS ({len(recent_reviews)} total):
{chr(10).join(f"- {text}" for text in recent_texts[:15])}

Identify topics that are NEW or SIGNIFICANTLY MORE FREQUENT in recent reviews.

Respond in JSON format:
[
    {{
        "topic_name": "<topic name>",
        "recent_count": <estimated count in recent>,
        "historical_count": <estimated count in historical>,
        "severity": "high" | "medium" | "low",
        "description": "<one sentence>"
    }},
    ...
]

Only include topics with significant emergence. Respond with ONLY the JSON array."""
            
            response = await self.llm_client.generate_completion(
                prompt=user_prompt,
                system_message=system_prompt,
                temperature=0.2,
                max_tokens=800
            )
            
            # Parse JSON response
            response_text = response.strip()
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            topics = json.loads(response_text)
            return topics
            
        except Exception as e:
            logger.error(f"Error identifying emerging topics: {e}")
            return []
