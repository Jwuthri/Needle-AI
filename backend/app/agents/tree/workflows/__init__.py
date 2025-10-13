"""
Pre-configured tree workflows.

Contains workflow templates inspired by Elysia's architecture:
- Multi-branch workflow (query/aggregate split)
- One-branch workflow (simpler linear flow)
"""

from app.agents.tree.workflows.multi_branch import create_multi_branch_workflow
from app.agents.tree.workflows.elysia_tools import (
    QueryTool,
    AggregateTool,
    VisualizeTool,
    SummarizeItemsTool,
    CitedSummarizerTool,
    TextResponseTool
)

__all__ = [
    "create_multi_branch_workflow",
    "QueryTool",
    "AggregateTool",
    "VisualizeTool",
    "SummarizeItemsTool",
    "CitedSummarizerTool",
    "TextResponseTool",
]

