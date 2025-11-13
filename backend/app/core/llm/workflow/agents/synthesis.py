"""
Synthesis Agent for Product Review Analysis Workflow.

The Synthesis Agent combines insights from multiple analysis agents into
a coherent, well-structured narrative response with embedded visualizations
and source citations.
"""

from typing import Any, Callable, Dict, List, Optional
import asyncio

from app.core.llm.base import BaseLLMClient
from app.database.repositories.chat_message_step import ChatMessageStepRepository
from app.models.workflow import ExecutionContext, Insight, SynthesisThought, VisualizationResult
from app.utils.logging import get_logger
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


class SynthesisAgent:
    """
    Specialized agent for synthesizing insights into coherent responses.
    
    The Synthesis Agent:
    1. Generates a synthesis plan (thought) before creating response
    2. Prioritizes insights by severity and relevance
    3. Groups insights by theme
    4. Embeds visualizations at appropriate locations
    5. Adds source citations with review excerpts
    6. Creates well-structured markdown responses
    7. Tracks reasoning and execution in Chat Message Steps
    """
    
    def __init__(
        self,
        llm_client: BaseLLMClient,
        visualization_agent: Optional[Any] = None,
        stream_callback: Optional[Callable] = None
    ):
        """
        Initialize the Synthesis Agent.
        
        Args:
            llm_client: LLM client for synthesis
            visualization_agent: Optional visualization agent for chart generation
            stream_callback: Optional callback for streaming events
        """
        self.llm_client = llm_client
        self.visualization_agent = visualization_agent
        self.stream_callback = stream_callback
        logger.info("Initialized SynthesisAgent")
    
    async def synthesize_response(
        self,
        query: str,
        insights: List[Insight],
        context: ExecutionContext,
        db: AsyncSession,
        step_order: int,
        format_type: str = "markdown"
    ) -> str:
        """
        Synthesize insights into a coherent narrative response.
        
        This method:
        1. Generates a synthesis plan (thought)
        2. Prioritizes and groups insights
        3. Creates narrative structure
        4. Embeds visualizations
        5. Adds source citations
        6. Tracks execution in Chat Message Steps
        
        Args:
            query: Original user query
            insights: List of insights from analysis agents
            context: Execution context
            db: Database session for tracking
            step_order: Step order in execution
            format_type: Output format (markdown, html, json)
            
        Returns:
            Synthesized response as markdown string
        """
        logger.info(f"Synthesizing response from {len(insights)} insights")
        
        # Emit step start event
        await self._emit_event("agent_step_start", {
            "agent_name": "synthesis",
            "action": "synthesize_response",
            "insight_count": len(insights),
            "format_type": format_type
        })
        
        try:
            # Generate synthesis plan (thought)
            synthesis_thought = await self.generate_synthesis_plan(
                query=query,
                insights=insights,
                context=context
            )
            
            # Save synthesis thought step
            await ChatMessageStepRepository.create(
                db=db,
                message_id=context.message_id,
                agent_name="synthesis",
                step_order=step_order,
                thought=synthesis_thought.reasoning,
                structured_output=synthesis_thought.model_dump()
            )
            
            # Prioritize insights
            prioritized_insights = self._prioritize_insights(insights)
            
            # Group insights by theme
            grouped_insights = self._group_insights_by_theme(prioritized_insights)
            
            # Generate markdown response
            response = await self._generate_markdown_response(
                query=query,
                synthesis_thought=synthesis_thought,
                grouped_insights=grouped_insights,
                context=context,
                db=db
            )
            
            # Save synthesis output step
            await ChatMessageStepRepository.create(
                db=db,
                message_id=context.message_id,
                agent_name="synthesis",
                step_order=step_order + 1,
                prediction=response[:1000],  # Store first 1000 chars
                structured_output={
                    "insights_used": len(prioritized_insights),
                    "sections_created": len(synthesis_thought.outline),
                    "visualizations_embedded": len(synthesis_thought.visualization_placements),
                    "response_length": len(response)
                }
            )
            
            # Emit step complete event
            await self._emit_event("agent_step_complete", {
                "agent_name": "synthesis",
                "action": "synthesize_response",
                "success": True,
                "response_length": len(response)
            })
            
            logger.info(f"Generated synthesis response ({len(response)} chars)")
            return response
            
        except Exception as e:
            logger.error(f"Error synthesizing response: {e}", exc_info=True)
            
            # Emit error event
            await self._emit_event("agent_step_error", {
                "agent_name": "synthesis",
                "action": "synthesize_response",
                "error": str(e)
            })
            
            # Track error in Chat Message Steps
            await ChatMessageStepRepository.create(
                db=db,
                message_id=context.message_id,
                agent_name="synthesis",
                step_order=step_order + 1,
                thought=f"Failed to synthesize response: {str(e)}"
            )
            
            # Return fallback response
            return self._generate_fallback_response(query, insights)

    async def generate_synthesis_plan(
        self,
        query: str,
        insights: List[Insight],
        context: ExecutionContext
    ) -> SynthesisThought:
        """
        Generate synthesis plan before creating response.
        
        This method creates a thought explaining:
        - Section outline and organization
        - Key insights to highlight
        - Visualization placements
        - Narrative strategy
        
        Args:
            query: Original user query
            insights: List of insights to synthesize
            context: Execution context
            
        Returns:
            SynthesisThought with synthesis plan
        """
        logger.info("Generating synthesis plan")
        
        try:
            # Prepare insights summary for LLM
            insights_summary = []
            for i, insight in enumerate(insights[:20]):  # Limit to top 20
                insights_summary.append(
                    f"Insight {i+1} [{insight.source_agent}]: {insight.insight_text} "
                    f"(severity: {insight.severity_score:.2f}, confidence: {insight.confidence_score:.2f})"
                )
            
            system_prompt = """You are an expert at planning structured reports.
Create a clear outline for synthesizing insights into a coherent response."""
            
            user_prompt = f"""I need to create a response to this query: "{query}"

I have {len(insights)} insights from various analysis agents:
{chr(10).join(insights_summary)}

Create a synthesis plan with:
1. Section outline (4-6 section headings)
2. Top 3-5 key insights to highlight (by index number)
3. Narrative strategy (problem-solution, chronological, severity-based, thematic)
4. Brief reasoning for this structure

Respond in JSON format:
{{
    "outline": ["Section 1", "Section 2", ...],
    "key_insights": [0, 1, 2],
    "narrative_strategy": "severity-based",
    "reasoning": "Why this structure works best"
}}

Respond with ONLY the JSON object."""
            
            response = await self.llm_client.generate_completion(
                prompt=user_prompt,
                system_message=system_prompt,
                temperature=0.3,
                max_tokens=500
            )
            
            # Parse JSON response
            import json
            response_text = response.strip()
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            plan_data = json.loads(response_text)
            
            # Map key insight indices to insight IDs
            key_insight_ids = []
            for idx in plan_data.get("key_insights", [])[:5]:
                if 0 <= idx < len(insights):
                    # Use source_agent + text hash as ID
                    insight_id = f"{insights[idx].source_agent}_{hash(insights[idx].insight_text) % 10000}"
                    key_insight_ids.append(insight_id)
            
            # Determine visualization placements
            viz_placements = {}
            for i, insight in enumerate(insights):
                if insight.visualization_hint and insight.visualization_data:
                    # Place visualization in section 2 or 3 (after intro)
                    section_idx = min(2, len(plan_data.get("outline", [])) - 1)
                    insight_id = f"{insight.source_agent}_{hash(insight.insight_text) % 10000}"
                    viz_placements[insight_id] = section_idx
            
            synthesis_thought = SynthesisThought(
                outline=plan_data.get("outline", ["Introduction", "Key Findings", "Recommendations"]),
                key_insights=key_insight_ids,
                visualization_placements=viz_placements,
                narrative_strategy=plan_data.get("narrative_strategy", "severity-based"),
                reasoning=plan_data.get("reasoning", "Organizing insights by importance and relevance to query")
            )
            
            logger.info(f"Generated synthesis plan with {len(synthesis_thought.outline)} sections")
            return synthesis_thought
            
        except Exception as e:
            logger.error(f"Error generating synthesis plan: {e}")
            # Fallback plan
            return SynthesisThought(
                outline=["Executive Summary", "Key Findings", "Detailed Analysis", "Recommendations"],
                key_insights=[],
                visualization_placements={},
                narrative_strategy="severity-based",
                reasoning="Using default structure due to planning error"
            )
    
    def _prioritize_insights(
        self,
        insights: List[Insight]
    ) -> List[Insight]:
        """
        Prioritize insights by severity score and confidence.
        
        Sorts insights to highlight the most important findings first.
        
        Args:
            insights: List of insights to prioritize
            
        Returns:
            Sorted list of insights
        """
        logger.info(f"Prioritizing {len(insights)} insights")
        
        # Sort by combined score (severity * confidence)
        prioritized = sorted(
            insights,
            key=lambda x: x.severity_score * x.confidence_score,
            reverse=True
        )
        
        logger.debug(f"Top insight: {prioritized[0].insight_text[:50]}..." if prioritized else "No insights")
        return prioritized
    
    def _group_insights_by_theme(
        self,
        insights: List[Insight]
    ) -> Dict[str, List[Insight]]:
        """
        Group insights by theme or source agent.
        
        Organizes insights into logical groups for better narrative flow.
        
        Args:
            insights: List of insights to group
            
        Returns:
            Dictionary mapping theme names to insight lists
        """
        logger.info(f"Grouping {len(insights)} insights by theme")
        
        # Group by source agent as primary grouping
        grouped: Dict[str, List[Insight]] = {}
        
        for insight in insights:
            agent_name = insight.source_agent
            
            # Map agent names to user-friendly themes
            theme_map = {
                "sentiment": "Sentiment Analysis",
                "topic_modeling": "Common Themes",
                "anomaly_detection": "Critical Issues",
                "summary": "Overview",
                "data_retrieval": "Data Insights"
            }
            
            theme = theme_map.get(agent_name, agent_name.replace("_", " ").title())
            
            if theme not in grouped:
                grouped[theme] = []
            grouped[theme].append(insight)
        
        # Sort groups by highest severity in each group
        sorted_groups = {}
        for theme, theme_insights in sorted(
            grouped.items(),
            key=lambda x: max((i.severity_score for i in x[1]), default=0),
            reverse=True
        ):
            sorted_groups[theme] = theme_insights
        
        logger.info(f"Created {len(sorted_groups)} theme groups")
        return sorted_groups

    async def _generate_markdown_response(
        self,
        query: str,
        synthesis_thought: SynthesisThought,
        grouped_insights: Dict[str, List[Insight]],
        context: ExecutionContext,
        db: AsyncSession
    ) -> str:
        """
        Generate markdown response with embedded visualizations.
        
        Creates a well-structured markdown document following the synthesis plan.
        
        Args:
            query: Original user query
            synthesis_thought: Synthesis plan
            grouped_insights: Insights grouped by theme
            context: Execution context
            db: Database session
            
        Returns:
            Markdown formatted response
        """
        logger.info("Generating markdown response")
        
        sections = []
        
        # Introduction section
        intro = await self._generate_introduction(query, grouped_insights)
        sections.append(intro)
        
        # Key findings section (top 3-5 insights)
        key_findings = await self._generate_key_findings(
            grouped_insights,
            synthesis_thought.key_insights
        )
        sections.append(key_findings)
        
        # Detailed analysis sections by theme
        for theme, insights in grouped_insights.items():
            theme_section = await self._generate_theme_section(
                theme=theme,
                insights=insights,
                context=context,
                db=db
            )
            sections.append(theme_section)
        
        # Recommendations section
        recommendations = await self._generate_recommendations(grouped_insights)
        sections.append(recommendations)
        
        # Source citations section
        citations = await self._generate_citations(grouped_insights)
        sections.append(citations)
        
        # Combine all sections
        response = "\n\n".join(sections)
        
        logger.info(f"Generated markdown response with {len(sections)} sections")
        return response
    
    async def _generate_introduction(
        self,
        query: str,
        grouped_insights: Dict[str, List[Insight]]
    ) -> str:
        """
        Generate introduction section.
        
        Args:
            query: Original user query
            grouped_insights: Grouped insights
            
        Returns:
            Introduction markdown
        """
        total_insights = sum(len(insights) for insights in grouped_insights.values())
        
        intro = f"""# Analysis Results

**Query:** {query}

I've analyzed your review data and identified **{total_insights} key insights** across {len(grouped_insights)} categories. Here's what I found:
"""
        return intro
    
    async def _generate_key_findings(
        self,
        grouped_insights: Dict[str, List[Insight]],
        key_insight_ids: List[str]
    ) -> str:
        """
        Generate key findings section highlighting top insights.
        
        Args:
            grouped_insights: Grouped insights
            key_insight_ids: IDs of key insights to highlight
            
        Returns:
            Key findings markdown
        """
        section = "## 🔑 Key Findings\n\n"
        
        # Get all insights flattened
        all_insights = []
        for insights in grouped_insights.values():
            all_insights.extend(insights)
        
        # Get top 5 by severity
        top_insights = sorted(
            all_insights,
            key=lambda x: x.severity_score * x.confidence_score,
            reverse=True
        )[:5]
        
        for i, insight in enumerate(top_insights, 1):
            severity_emoji = "🔴" if insight.severity_score > 0.7 else "🟡" if insight.severity_score > 0.4 else "🟢"
            section += f"{i}. {severity_emoji} **{insight.insight_text}**\n"
            section += f"   - Confidence: {insight.confidence_score:.0%}\n"
            section += f"   - Source: {insight.source_agent.replace('_', ' ').title()}\n\n"
        
        return section
    
    async def _generate_theme_section(
        self,
        theme: str,
        insights: List[Insight],
        context: ExecutionContext,
        db: AsyncSession
    ) -> str:
        """
        Generate a section for a specific theme with visualizations.
        
        Args:
            theme: Theme name
            insights: Insights for this theme
            context: Execution context
            db: Database session
            
        Returns:
            Theme section markdown
        """
        section = f"## {theme}\n\n"
        
        # Add insights
        for insight in insights:
            severity_emoji = "🔴" if insight.severity_score > 0.7 else "🟡" if insight.severity_score > 0.4 else "🟢"
            section += f"### {severity_emoji} {insight.insight_text}\n\n"
            
            # Add metadata details if available
            if insight.metadata:
                if "full_summary" in insight.metadata:
                    section += f"{insight.metadata['full_summary']}\n\n"
                elif "key_points" in insight.metadata:
                    section += "**Key Points:**\n"
                    for point in insight.metadata["key_points"]:
                        section += f"- {point}\n"
                    section += "\n"
            
            # Embed visualization if available
            if insight.visualization_hint and insight.visualization_data:
                viz_markdown = await self._embed_visualization(
                    insight=insight,
                    context=context,
                    db=db
                )
                if viz_markdown:
                    section += viz_markdown + "\n\n"
            
            # Add supporting evidence count
            if insight.supporting_reviews:
                section += f"*Based on {len(insight.supporting_reviews)} reviews*\n\n"
        
        return section
    
    async def _embed_visualization(
        self,
        insight: Insight,
        context: ExecutionContext,
        db: AsyncSession
    ) -> Optional[str]:
        """
        Embed visualization for an insight.
        
        Calls Visualization Agent to generate chart and returns markdown.
        
        Args:
            insight: Insight with visualization data
            context: Execution context
            db: Database session
            
        Returns:
            Markdown with embedded image or None
        """
        if not self.visualization_agent or not insight.visualization_data:
            return None
        
        try:
            logger.info(f"Generating visualization for insight: {insight.insight_text[:50]}...")
            
            # Extract visualization parameters
            viz_data = insight.visualization_data
            chart_type = viz_data.get("chart_type", insight.visualization_hint or "bar")
            title = viz_data.get("title", "Analysis Chart")
            
            # Generate visualization
            viz_result = await self.visualization_agent.generate_visualization(
                data=viz_data,
                chart_type=chart_type,
                title=title,
                labels=viz_data.get("labels", {})
            )
            
            # Create markdown with image
            markdown = f"**{title}**\n\n"
            markdown += f"![{title}]({viz_result.filepath})\n"
            
            # Add explanatory text if available
            if "description" in viz_data:
                markdown += f"\n*{viz_data['description']}*\n"
            
            return markdown
            
        except Exception as e:
            logger.error(f"Error embedding visualization: {e}")
            return None
    
    async def _generate_recommendations(
        self,
        grouped_insights: Dict[str, List[Insight]]
    ) -> str:
        """
        Generate recommendations section based on insights.
        
        Args:
            grouped_insights: Grouped insights
            
        Returns:
            Recommendations markdown
        """
        section = "## 💡 Recommendations\n\n"
        
        # Get high-severity insights
        all_insights = []
        for insights in grouped_insights.values():
            all_insights.extend(insights)
        
        high_severity = [i for i in all_insights if i.severity_score > 0.6]
        
        if high_severity:
            section += "Based on the analysis, here are the top priority actions:\n\n"
            
            for i, insight in enumerate(high_severity[:5], 1):
                # Extract recommended action from metadata if available
                if "recommended_action" in insight.metadata:
                    section += f"{i}. {insight.metadata['recommended_action']}\n"
                else:
                    # Generate generic recommendation
                    section += f"{i}. Address: {insight.insight_text}\n"
            
            section += "\n"
        else:
            section += "Continue monitoring review feedback for emerging patterns.\n\n"
        
        return section

    async def _generate_citations(
        self,
        grouped_insights: Dict[str, List[Insight]]
    ) -> str:
        """
        Generate source citations section with review excerpts.
        
        Extracts supporting reviews from insights and formats as citations.
        
        Args:
            grouped_insights: Grouped insights
            
        Returns:
            Citations markdown
        """
        section = "## 📚 Supporting Evidence\n\n"
        
        # Collect all unique review IDs
        all_review_ids = set()
        review_to_insights = {}
        
        for theme, insights in grouped_insights.items():
            for insight in insights:
                for review_id in insight.supporting_reviews[:10]:  # Limit per insight
                    all_review_ids.add(review_id)
                    if review_id not in review_to_insights:
                        review_to_insights[review_id] = []
                    review_to_insights[review_id].append(insight.insight_text[:100])
        
        if not all_review_ids:
            section += "*No specific review citations available.*\n\n"
            return section
        
        section += f"This analysis is based on **{len(all_review_ids)} reviews**. "
        section += "Here are some representative examples:\n\n"
        
        # Format citations (showing first 10)
        for i, review_id in enumerate(list(all_review_ids)[:10], 1):
            section += f"{i}. Review `{review_id}`\n"
            
            # Show which insights reference this review
            if review_id in review_to_insights:
                related = review_to_insights[review_id][:2]  # Show up to 2 insights
                for insight_text in related:
                    section += f"   - Related to: {insight_text}...\n"
            
            section += "\n"
        
        if len(all_review_ids) > 10:
            section += f"*...and {len(all_review_ids) - 10} more reviews*\n\n"
        
        return section
    
    def _generate_fallback_response(
        self,
        query: str,
        insights: List[Insight]
    ) -> str:
        """
        Generate a simple fallback response if synthesis fails.
        
        Args:
            query: Original user query
            insights: List of insights
            
        Returns:
            Simple markdown response
        """
        response = f"# Analysis Results\n\n**Query:** {query}\n\n"
        
        if not insights:
            response += "I couldn't generate specific insights from the data. "
            response += "Please try rephrasing your query or check that you have review data available.\n"
            return response
        
        response += f"I found {len(insights)} insights:\n\n"
        
        for i, insight in enumerate(insights[:10], 1):
            severity_emoji = "🔴" if insight.severity_score > 0.7 else "🟡" if insight.severity_score > 0.4 else "🟢"
            response += f"{i}. {severity_emoji} {insight.insight_text}\n"
        
        if len(insights) > 10:
            response += f"\n*...and {len(insights) - 10} more insights*\n"
        
        return response
    
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
