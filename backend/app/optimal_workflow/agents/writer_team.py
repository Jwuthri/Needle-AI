"""
Workflow orchestrator for creating and managing the LlamaIndex AgentWorkflow.
"""

from llama_index.core.agent.workflow import AgentWorkflow
from llama_index.core.workflow import Context

from .markdown_writer import create_markdown_writer
from .table_writer import create_table_writer
from .chart_writer import create_chart_writer
from .json_writer import create_json_writer
from .report_coordinator import create_report_coordinator


def create_answer_writer_workflow(format_type: str = "markdown") -> AgentWorkflow:
    """
    Create a LlamaIndex AgentWorkflow with specialized writer agents.
    """
    # Create specialized writer agents
    markdown_writer = create_markdown_writer()
    table_writer = create_table_writer()
    chart_writer = create_chart_writer()
    json_writer = create_json_writer()
    coordinator = create_report_coordinator(format_type)
    
    # Determine root agent based on format
    if format_type.lower() in ['markdown', 'report', 'bullet points']:
        root_agent = "MarkdownWriter"
    elif format_type.lower() in ['table', 'tabular', 'csv']:
        root_agent = "TableWriter"
    elif format_type.lower() in ['chart', 'visualization', 'graph']:
        root_agent = "ChartWriter"
    elif format_type.lower() in ['json', 'api', 'structured']:
        root_agent = "JsonWriter"
    else:
        root_agent = "MarkdownWriter"  # Default
    
    # Create the workflow
    workflow = AgentWorkflow(
        agents=[markdown_writer, table_writer, chart_writer, json_writer],
        root_agent=root_agent,
        initial_state={
            "format_type": format_type,
            "report_content": "",
            "status": "initialized"
        },
    )
    
    return workflow


async def generate_answer(context: str, format_type: str = "markdown") -> str:
    """
    Generate final answer using the LlamaIndex AgentWorkflow.
    """
    workflow = create_answer_writer_workflow(format_type)
    
    # Create a proper Context object
    ctx = Context(workflow)

    # Store initial data in context
    await ctx.store.set("context", context)
    await ctx.store.set("format_type", format_type)
    
    # Run the workflow with the user message and context
    result = await workflow.run(
        user_msg=f"Please create a {format_type} report based on this context: {context}",
        ctx=ctx
    )
    
    return str(result)