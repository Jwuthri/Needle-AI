from app.core.llm.simple_workflow.agents import create_coordinator_agent, create_general_assistant_agent, create_data_discovery_agent, create_gap_analysis_agent, create_sentiment_analysis_agent, create_trend_analysis_agent, create_clustering_agent, create_visualization_agent, create_report_writer_agent
from llama_index.core.agent.workflow import AgentWorkflow
from llama_index.llms.openai import OpenAI


def create_product_review_workflow(llm: OpenAI, user_id: str) -> AgentWorkflow:
    """
    Create a multi-agent product review analysis workflow with specialized agents.
    
    Each agent has:
    - Specific tools for their domain
    - A system prompt defining their role
    - Ability to hand off to other agents
    
    Args:
        llm: OpenAI LLM instance
        user_id: User ID to pre-bind to all tools
    """
    
    # Create all agents using factory functions with pre-bound user_id
    coordinator_agent = create_coordinator_agent(llm, user_id)
    general_assistant_agent = create_general_assistant_agent(llm, user_id)
    data_discovery_agent = create_data_discovery_agent(llm, user_id)
    gap_analysis_agent = create_gap_analysis_agent(llm, user_id)
    sentiment_analysis_agent = create_sentiment_analysis_agent(llm, user_id)
    trend_analysis_agent = create_trend_analysis_agent(llm, user_id)
    clustering_agent = create_clustering_agent(llm, user_id)
    visualization_agent = create_visualization_agent(llm, user_id)
    report_writer_agent = create_report_writer_agent(llm, user_id)
    
    # Create the Agent Workflow
    workflow = AgentWorkflow(
        agents=[
            coordinator_agent,
            general_assistant_agent,
            data_discovery_agent,
            gap_analysis_agent,
            sentiment_analysis_agent,
            trend_analysis_agent,
            clustering_agent,
            visualization_agent,
            report_writer_agent,
        ],
        root_agent="coordinator",  # Start with coordinator
        timeout=300,  # 5 minutes for complex analysis
    )
    
    return workflow