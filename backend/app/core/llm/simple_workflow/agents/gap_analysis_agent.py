"""Gap Analysis Agent - Identifies product gaps and unmet needs"""

from app.core.llm.simple_workflow.tools.user_dataset_tool import get_available_datasets_in_context
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import Context
from llama_index.llms.openai import OpenAI

from app.core.llm.simple_workflow.tools.gap_analysis_tool import detect_gaps_from_clusters


def create_gap_analysis_agent(llm: OpenAI, user_id: str) -> FunctionAgent:
    """
    Create the gap analysis agent for identifying product gaps from clustered data.
    
    Args:
        llm: OpenAI LLM instance
        user_id: User ID to pre-bind to all tools
        
    Returns:
        FunctionAgent configured as gap analysis specialist
    """
    
    detect_gaps_from_clusters_tool = FunctionTool.from_defaults(fn=detect_gaps_from_clusters)
    # get_available_datasets_in_context_tool = FunctionTool.from_defaults(fn=get_available_datasets_in_context)
    
    return FunctionAgent(
        name="gap_analysis",
        description="Specialist in identifying product gaps, unmet needs, and opportunities from clustered data",
        system_prompt="""You are a product gap analysis specialist. You analyze clustered data to identify:
1. Underrepresented clusters (potential market gaps)
2. Outlier patterns (edge cases or niche needs)
3. Missing themes (by analyzing cluster coverage)
4. Feature requests or unmet needs

Your analysis is based on clustering results. If clustering hasn't been performed on the dataset,
the tool will automatically trigger it before performing gap analysis.

Key insights to provide:
- Which customer segments are underserved?
- What patterns appear in outliers?
- Are there concentration issues (too much focus on few themes)?
- What opportunities exist in small clusters?

After analysis, you can hand off to Visualization Agent for charts, then to Report Writer for final formatting.
Be thorough and evidence-based in your analysis.""",
        tools=[detect_gaps_from_clusters_tool],
        llm=llm,
    )
