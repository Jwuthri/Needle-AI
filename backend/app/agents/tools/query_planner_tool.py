"""
Query Planner Tool - Analyzes queries to determine optimal response strategy.
"""

from typing import Any, Dict, Literal

from app.agents.tools.base_tool import BaseTool, ToolResult
from app.utils.logging import get_logger

logger = get_logger("query_planner_tool")


class QueryPlannerTool(BaseTool):
    """
    Analyzes user queries to determine:
    1. Output format (text, visualization, cited_summary)
    2. Intent (Summarization, Aggregation, Filtering, etc.)
    3. Required data sources (RAG, web search)
    4. Required processing (analytics, NLP)
    
    This is exposed as a tool that the LLM can call with structured parameters.
    """
    
    @property
    def name(self) -> str:
        return "analyze_query"
    
    @property
    def description(self) -> str:
        return """Analyze a user query to determine the optimal response strategy.

Use this tool FIRST to understand what the user wants before retrieving or processing data.

Determine:
- Intent: What the user wants to accomplish (Summarization, Aggregation, Filtering, Ranking, Trend Analysis, Gap Analysis, Competitive Analysis)
- Output format: How to present results (text, visualization, cited_summary)
- Data needs: Whether RAG retrieval (for reviews/feedback) or web search (for external data) is needed
- Processing needs: Whether analytics (statistics/calculations) or NLP (keyword extraction/themes) is needed

Provide clear reasoning for your analysis."""
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The user's query to analyze, optimize it based on previous conversations for rag search and web search. Also to give a better answer in the end."
                },
                "intent": {
                    "type": "string",
                    "enum": [
                        "Summarization",
                        "Aggregation", 
                        "Filtering",
                        "Ranking",
                        "Trend Analysis",
                        "Gap Analysis",
                        "Competitive Analysis"
                    ],
                    "description": "What the user wants to accomplish"
                },
                "output_format": {
                    "type": "string",
                    "enum": ["text", "visualization", "cited_summary"],
                    "description": "Best way to present results: text (markdown), visualization (charts/tables), or cited_summary (with source citations)"
                },
                "needs_rag": {
                    "type": "boolean",
                    "description": "True if query asks about reviews, customers, products, companies, or feedback from your database"
                },
                "needs_web_search": {
                    "type": "boolean",
                    "description": "True if query needs current info, competitor data, or external facts from the web"
                },
                "needs_analytics": {
                    "type": "boolean",
                    "description": "True if query asks for statistics, calculations, or aggregations"
                },
                "needs_nlp": {
                    "type": "boolean",
                    "description": "True if query needs keyword extraction, theme analysis, or text processing"
                },
                "reasoning": {
                    "type": "string",
                    "description": "Brief explanation of your analysis (1-2 sentences)"
                }
            },
            "required": ["query", "intent", "output_format", "needs_rag", "needs_web_search", "needs_analytics", "needs_nlp", "reasoning"]
        }
    
    async def execute(
        self,
        query: str,
        intent: str,
        output_format: Literal["text", "visualization", "cited_summary"],
        needs_rag: bool,
        needs_web_search: bool,
        needs_analytics: bool,
        needs_nlp: bool,
        reasoning: str
    ) -> ToolResult:
        """
        Process the query analysis parameters provided by the LLM.
        
        This is called when the LLM invokes the tool with structured parameters
        after analyzing the user's query.
        
        Args:
            query: The original user query
            intent: What the user wants to accomplish
            output_format: How to present the results
            needs_rag: Whether RAG retrieval is needed
            needs_web_search: Whether web search is needed
            needs_analytics: Whether analytics/calculations are needed
            needs_nlp: Whether NLP processing is needed
            reasoning: LLM's explanation of the analysis
            
        Returns:
            ToolResult with the structured plan
        """
        try:
            plan = {
                "intent": intent,
                "output_format": output_format,
                "needs_rag": needs_rag,
                "needs_web_search": needs_web_search,
                "needs_analytics": needs_analytics,
                "needs_nlp": needs_nlp,
                "reasoning": reasoning
            }
            
            # Validate the plan
            plan = self._validate_plan(plan)
            
            # Create summary
            summary = f"Intent: {plan['intent']}, Format: {plan['output_format']}"
            tools_needed = []
            if plan['needs_rag']:
                tools_needed.append("RAG")
            if plan['needs_web_search']:
                tools_needed.append("Web Search")
            if plan['needs_analytics']:
                tools_needed.append("Analytics")
            if plan['needs_nlp']:
                tools_needed.append("NLP")
            
            if tools_needed:
                summary += f", Tools: {', '.join(tools_needed)}"
            
            logger.info(f"Query analysis complete: {summary}")
            logger.debug(f"Reasoning: {reasoning}")
            
            return ToolResult(
                success=True,
                data=plan,
                summary=summary,
                metadata={
                    "query_length": len(query),
                    "tools_needed": len(tools_needed)
                }
            )
            
        except Exception as e:
            logger.error(f"Query planning failed: {e}", exc_info=True)
            return ToolResult(
                success=False,
                error=str(e),
                summary="Query analysis failed"
            )
    
    def _validate_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize the plan."""
        valid_intents = [
            "Summarization", "Aggregation", "Filtering", "Ranking",
            "Trend Analysis", "Gap Analysis", "Competitive Analysis"
        ]
        valid_formats = ["text", "visualization", "cited_summary"]
        
        # Normalize intent
        if plan.get("intent") not in valid_intents:
            logger.warning(f"Invalid intent '{plan.get('intent')}', defaulting to Summarization")
            plan["intent"] = "Summarization"
        
        # Normalize format
        if plan.get("output_format") not in valid_formats:
            logger.warning(f"Invalid output_format '{plan.get('output_format')}', defaulting to text")
            plan["output_format"] = "text"
        
        # Ensure boolean fields
        for field in ["needs_rag", "needs_web_search", "needs_analytics", "needs_nlp"]:
            if field not in plan:
                plan[field] = False
            elif not isinstance(plan[field], bool):
                plan[field] = bool(plan[field])
        
        # Ensure reasoning exists
        if not plan.get("reasoning"):
            plan["reasoning"] = "Query analysis complete"
        
        return plan

