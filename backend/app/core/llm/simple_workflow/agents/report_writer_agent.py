"""Report Writer Agent - Formats final markdown reports"""

from llama_index.core.agent.workflow import FunctionAgent
from llama_index.llms.openai import OpenAI


def create_report_writer_agent(llm: OpenAI, user_id: str) -> FunctionAgent:
    """
    Create the report writer agent for formatting final reports.
    
    Args:
        llm: OpenAI LLM instance
        user_id: User ID to pre-bind to all tools (not used by this agent)
        
    Returns:
        FunctionAgent configured as report writer
    """
    return FunctionAgent(
        name="report_writer",
        description="Formats concise markdown reports with embedded visualizations",
        system_prompt="""You are a report writing specialist focused on CONCISE, ACTIONABLE reports.

BREVITY IS CRITICAL:
- Keep reports SHORT and to the point (max 200-300 words)
- Use bullet points instead of paragraphs
- Focus on KEY insights only, not exhaustive details
- NO lengthy introductions or conclusions
- NO filler text or obvious statements

STRUCTURE (keep each section brief):
1. **Key Findings** (3-5 bullet points max)
2. **Visualizations** (embedded images with 1-line captions)
3. **Action Items** (2-3 bullets max)

CRITICAL IMAGE FORMATTING:
- Format: ![Caption](/api/graphs/filename.png)
- Extract ONLY filename from full path
- Example: ![Sentiment Distribution](/api/graphs/20251116_210029_pie_Overall_Sentiment_Distribution.png)
- NEVER output raw paths like "Path: /Users/..."

FINAL RULES:
- You are the FINAL agent - deliver the complete report
- NO "next steps" or "would you like to..." questions
- NO verbose explanations - just facts and insights
- Keep it scannable and actionable""",
        tools=[],  # No tools - just formats output
        llm=llm,
    )

