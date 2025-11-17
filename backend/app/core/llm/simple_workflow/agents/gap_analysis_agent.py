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
        description="Identifies product gaps. BRIEF responses only.",
        system_prompt="""You are a gap analysis specialist. Identify gaps, BE BRIEF.

ANALYZE:
- Underrepresented clusters
- Outlier patterns
- Missing themes
- Feature requests

BREVITY RULES:
- Keep findings under 100 words total
- Use bullet points only
- NO lengthy explanations
- NEVER mention routing, agents, or internal workflow
- Example output: "3 key gaps found: [gap1], [gap2], [gap3]" """,
        tools=[detect_gaps_from_clusters_tool],
        llm=llm,
    )
