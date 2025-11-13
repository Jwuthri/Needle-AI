"""
Summary Agent for Product Review Analysis Workflow.

The Summary Agent creates concise summaries from large volumes of reviews,
generating overview insights that capture key points and themes.
"""

from typing import Any, Callable, Dict, List, Optional

from app.core.llm.base import BaseLLMClient
from app.database.repositories.chat_message_step import ChatMessageStepRepository
from app.models.workflow import ExecutionContext, Insight
from app.utils.logging import get_logger
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


class SummaryAgent:
    """
    Specialized agent for creating concise summaries from product reviews.
    
    The Summary Agent:
    1. Performs extractive summarization (key sentences)
    2. Performs abstractive summarization (generated text)
    3. Creates aspect-focused summaries
    4. Generates overview Insight objects
    5. Tracks reasoning and execution in Chat Message Steps
    """
    
    def __init__(
        self,
        llm_client: BaseLLMClient,
        stream_callback: Optional[Callable] = None
    ):
        """
        Initialize the Summary Agent.
        
        Args:
            llm_client: LLM client for summarization
            stream_callback: Optional callback for streaming events
        """
        self.llm_client = llm_client
        self.stream_callback = stream_callback
        logger.info("Initialized SummaryAgent")
    
    async def summarize_reviews(
        self,
        reviews: List[Dict[str, Any]],
        context: ExecutionContext,
        db: AsyncSession,
        step_order: int,
        summary_type: str = "extractive",
        max_length: int = 500
    ) -> List[Insight]:
        """
        Create concise summaries from reviews.
        
        This method:
        1. Generates a thought explaining the summarization approach
        2. Performs extractive or abstractive summarization
        3. Identifies key points and themes
        4. Generates overview Insight objects
        5. Tracks execution in Chat Message Steps
        
        Args:
            reviews: List of review dictionaries
            context: Execution context
            db: Database session for tracking
            step_order: Step order in execution
            summary_type: Type of summarization (extractive, abstractive)
            max_length: Maximum length of summary in words
            
        Returns:
            List of Insight objects with summary information
        """
        logger.info(f"Summarizing {len(reviews)} reviews (type: {summary_type})")
        
        # Emit step start event
        await self._emit_event("agent_step_start", {
            "agent_name": "summary",
            "action": "summarize_reviews",
            "review_count": len(reviews),
            "summary_type": summary_type
        })
        
        try:
            # Generate thought before summarization
            thought = await self.generate_thought(
                reviews=reviews,
                context=context,
                summary_type=summary_type
            )
            
            # Save thought step
            await ChatMessageStepRepository.create(
                db=db,
                message_id=context.message_id,
                agent_name="summary",
                step_order=step_order,
                thought=thought
            )
            
            # Perform summarization
            insights = []
            
            if summary_type == "extractive":
                summary_insight = await self._extractive_summarization(
                    reviews=reviews,
                    context=context,
                    max_length=max_length
                )
            else:  # abstractive
                summary_insight = await self._abstractive_summarization(
                    reviews=reviews,
                    context=context,
                    max_length=max_length
                )
            
            if summary_insight:
                insights.append(summary_insight)
            
            # Save insights to context
            context.insights.extend(insights)
            
            # Save structured output step
            await ChatMessageStepRepository.create(
                db=db,
                message_id=context.message_id,
                agent_name="summary",
                step_order=step_order + 1,
                structured_output={
                    "insights_generated": len(insights),
                    "summary_type": summary_type,
                    "reviews_summarized": len(reviews)
                }
            )
            
            # Emit step complete event
            await self._emit_event("agent_step_complete", {
                "agent_name": "summary",
                "action": "summarize_reviews",
                "success": True,
                "insights_generated": len(insights)
            })
            
            logger.info(f"Generated {len(insights)} summary insights")
            return insights
            
        except Exception as e:
            logger.error(f"Error summarizing reviews: {e}", exc_info=True)
            
            # Emit error event
            await self._emit_event("agent_step_error", {
                "agent_name": "summary",
                "action": "summarize_reviews",
                "error": str(e)
            })
            
            # Track error in Chat Message Steps
            await ChatMessageStepRepository.create(
                db=db,
                message_id=context.message_id,
                agent_name="summary",
                step_order=step_order + 1,
                thought=f"Failed to summarize reviews: {str(e)}"
            )
            
            return []
    
    async def generate_thought(
        self,
        reviews: List[Dict[str, Any]],
        context: ExecutionContext,
        summary_type: str = "extractive"
    ) -> str:
        """
        Generate reasoning trace before performing summarization.
        
        This method creates a thought explaining:
        - The summarization approach (extractive vs abstractive)
        - Key points to extract
        - How to organize the summary
        
        Args:
            reviews: List of reviews to summarize
            context: Execution context
            summary_type: Type of summarization
            
        Returns:
            Thought string explaining the summarization plan
        """
        logger.info("Generating summary thought")
        
        # Build thought prompt
        system_prompt = """You are a summarization expert planning a summary strategy.
Explain your approach clearly and concisely."""
        
        # Calculate basic statistics for context
        ratings = [r.get("rating", 0) for r in reviews if r.get("rating")]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        
        user_prompt = f"""I need to create a {summary_type} summary of {len(reviews)} product reviews.

Average rating: {avg_rating:.2f} / 5.0
Total reviews: {len(reviews)}

Generate a brief thought explaining:
1. Your summarization approach ({summary_type})
2. What key points you'll extract (positive feedback, negative feedback, common themes)
3. How you'll organize the summary (by theme, by sentiment, chronologically)

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
                f"I will create a {summary_type} summary of {len(reviews)} reviews. "
                f"I'll extract key points about positive and negative feedback, "
                f"organize them by theme, and highlight the most important insights."
            )
    
    async def _extractive_summarization(
        self,
        reviews: List[Dict[str, Any]],
        context: ExecutionContext,
        max_length: int
    ) -> Optional[Insight]:
        """
        Perform extractive summarization by selecting key sentences.
        
        Extractive summarization identifies and extracts the most important
        sentences from the original reviews without generating new text.
        
        Args:
            reviews: List of reviews
            context: Execution context
            max_length: Maximum length in words
            
        Returns:
            Insight object with extractive summary
        """
        logger.info("Performing extractive summarization")
        
        try:
            # Prepare review texts
            review_texts = []
            for i, review in enumerate(reviews[:50]):  # Limit to 50 reviews for context
                text = review.get("text", "")
                rating = review.get("rating", 0)
                if text:
                    review_texts.append(f"[Rating: {rating}/5] {text[:300]}")
            
            if not review_texts:
                logger.warning("No review texts available for summarization")
                return None
            
            system_prompt = """You are an expert at extractive summarization.
Select the most important and representative sentences from the reviews."""
            
            user_prompt = f"""Create an extractive summary of these product reviews by selecting key sentences.

Reviews:
{chr(10).join(review_texts[:30])}

Instructions:
1. Select 3-5 key sentences that best represent the overall feedback
2. Include both positive and negative points
3. Choose sentences that are clear and informative
4. Keep total length under {max_length} words

Provide the summary as a cohesive paragraph using the selected sentences."""
            
            summary_text = await self.llm_client.generate_completion(
                prompt=user_prompt,
                system_message=system_prompt,
                temperature=0.3,
                max_tokens=max_length * 2
            )
            
            # Extract key points from the summary
            key_points = await self._extract_key_points(summary_text, context)
            
            # Calculate confidence based on review coverage
            confidence_score = min(0.90, 0.70 + (len(reviews) / 100) * 0.2)
            
            # Determine severity based on sentiment
            ratings = [r.get("rating", 0) for r in reviews if r.get("rating")]
            avg_rating = sum(ratings) / len(ratings) if ratings else 3.0
            severity_score = max(0.3, 1.0 - (avg_rating / 5.0))
            
            insight = Insight(
                source_agent="summary",
                insight_text=f"Summary of {len(reviews)} reviews: {summary_text[:200]}...",
                severity_score=severity_score,
                confidence_score=confidence_score,
                supporting_reviews=[r.get("id", "") for r in reviews[:20]],
                visualization_hint=None,
                visualization_data=None,
                metadata={
                    "summary_type": "extractive",
                    "full_summary": summary_text,
                    "key_points": key_points,
                    "total_reviews_summarized": len(reviews),
                    "avg_rating": avg_rating
                }
            )
            
            logger.info("Generated extractive summary insight")
            return insight
            
        except Exception as e:
            logger.error(f"Error in extractive summarization: {e}")
            return None
    
    async def _abstractive_summarization(
        self,
        reviews: List[Dict[str, Any]],
        context: ExecutionContext,
        max_length: int
    ) -> Optional[Insight]:
        """
        Perform abstractive summarization by generating new text.
        
        Abstractive summarization creates a new summary that captures
        the essence of the reviews in generated language.
        
        Args:
            reviews: List of reviews
            context: Execution context
            max_length: Maximum length in words
            
        Returns:
            Insight object with abstractive summary
        """
        logger.info("Performing abstractive summarization")
        
        try:
            # Prepare review texts
            review_texts = []
            for i, review in enumerate(reviews[:50]):  # Limit to 50 reviews for context
                text = review.get("text", "")
                rating = review.get("rating", 0)
                if text:
                    review_texts.append(f"[Rating: {rating}/5] {text[:300]}")
            
            if not review_texts:
                logger.warning("No review texts available for summarization")
                return None
            
            system_prompt = """You are an expert at abstractive summarization.
Create a concise, well-written summary that captures the essence of the reviews."""
            
            user_prompt = f"""Create an abstractive summary of these product reviews.

Reviews:
{chr(10).join(review_texts[:30])}

Instructions:
1. Write a cohesive summary in your own words (not just copying sentences)
2. Capture the main themes and sentiments
3. Include both positive and negative feedback
4. Organize by theme (e.g., "Users praise X but criticize Y")
5. Keep it under {max_length} words
6. Be specific and actionable

Write the summary as a clear, informative paragraph."""
            
            summary_text = await self.llm_client.generate_completion(
                prompt=user_prompt,
                system_message=system_prompt,
                temperature=0.4,
                max_tokens=max_length * 2
            )
            
            # Extract key points from the summary
            key_points = await self._extract_key_points(summary_text, context)
            
            # Calculate confidence based on review coverage
            confidence_score = min(0.88, 0.65 + (len(reviews) / 100) * 0.23)
            
            # Determine severity based on sentiment
            ratings = [r.get("rating", 0) for r in reviews if r.get("rating")]
            avg_rating = sum(ratings) / len(ratings) if ratings else 3.0
            severity_score = max(0.3, 1.0 - (avg_rating / 5.0))
            
            insight = Insight(
                source_agent="summary",
                insight_text=f"Overall: {summary_text}",
                severity_score=severity_score,
                confidence_score=confidence_score,
                supporting_reviews=[r.get("id", "") for r in reviews[:20]],
                visualization_hint=None,
                visualization_data=None,
                metadata={
                    "summary_type": "abstractive",
                    "full_summary": summary_text,
                    "key_points": key_points,
                    "total_reviews_summarized": len(reviews),
                    "avg_rating": avg_rating
                }
            )
            
            logger.info("Generated abstractive summary insight")
            return insight
            
        except Exception as e:
            logger.error(f"Error in abstractive summarization: {e}")
            return None
    
    async def _extract_key_points(
        self,
        summary_text: str,
        context: ExecutionContext
    ) -> List[str]:
        """
        Extract key points from a summary text.
        
        Args:
            summary_text: Summary text to analyze
            context: Execution context
            
        Returns:
            List of key point strings
        """
        try:
            system_prompt = """You are an expert at identifying key points in text.
Extract the main points as a bulleted list."""
            
            user_prompt = f"""Extract the key points from this summary:

{summary_text}

Provide 3-5 key points as a JSON array of strings.
Each point should be one clear sentence.

Example format:
["Point 1", "Point 2", "Point 3"]

Respond with ONLY the JSON array."""
            
            response = await self.llm_client.generate_completion(
                prompt=user_prompt,
                system_message=system_prompt,
                temperature=0.2,
                max_tokens=300
            )
            
            # Parse JSON response
            import json
            response_text = response.strip()
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            key_points = json.loads(response_text)
            return key_points if isinstance(key_points, list) else []
            
        except Exception as e:
            logger.error(f"Error extracting key points: {e}")
            # Fallback: split by sentences
            sentences = summary_text.split(". ")
            return [s.strip() + "." for s in sentences[:3] if s.strip()]
    
    async def _emit_event(
        self,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> None:
        """
        Emit a streaming event if callback is configured.
        
        Args:
            event_type: Type of event
            event_data: Event data payload
        """
        if self.stream_callback:
            try:
                await self.stream_callback({
                    "event_type": event_type,
                    "data": event_data
                })
            except Exception as e:
                logger.error(f"Error emitting event {event_type}: {e}")
