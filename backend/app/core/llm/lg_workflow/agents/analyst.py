"""Data Analyst Agent - performs computations on datasets."""
from app.core.llm.lg_workflow.tools.analytics import clustering_tool, tfidf_tool, describe_tool
from app.core.llm.lg_workflow.tools.ml import sentiment_analysis_tool, embedding_tool, linear_regression_tool
from .base import create_agent, llm

# Data Analyst Agent
analyst_tools = [clustering_tool, tfidf_tool, describe_tool, sentiment_analysis_tool, embedding_tool, linear_regression_tool]
analyst_node = create_agent(
    llm, 
    analyst_tools,
    "You are a Data Analyst. Your goal is to perform computations on datasets. "
    "You need `dataset_id`s to work. If you don't have them, ask the Librarian (via the supervisor). "
    "Use your tools to analyze data. You can now perform Sentiment Analysis, generate Embeddings, and run Linear Regression. "
    "Always report the result of your analysis and mention the new dataset ID if created."
)
