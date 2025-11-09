import asyncio
from app.core.config.settings import get_settings
from llama_index.core.agent.workflow import AgentWorkflow, FunctionAgent
from llama_index.llms.openai import OpenAI
settings = get_settings()

# Get API key from settings
api_key = settings.get_secret("openai_api_key")
# Define tools for each agent (replace ... with your tool functions)
intake_tools = [ ... ]
support_tools = [ ... ]
escalation_tools = [ ... ]

llm = OpenAI(model="gpt-5-mini", api_key=api_key)

intake_agent = FunctionAgent(
    name="IntakeAgent",
    description="Handles initial customer queries and gathers information.",
    system_prompt="You are the first point of contact. Handoff to SupportAgent as needed.",
    llm=llm,
    tools=intake_tools,
    can_handoff_to=["SupportAgent"],
)

support_agent = FunctionAgent(
    name="SupportAgent",
    description="Resolves common customer issues.",
    system_prompt="You resolve issues or escalate to EscalationAgent.",
    llm=llm,
    tools=support_tools,
    can_handoff_to=["EscalationAgent", "IntakeAgent"],
)

escalation_agent = FunctionAgent(
    name="EscalationAgent",
    description="Handles complex or unresolved issues.",
    system_prompt="You handle escalated cases and close the loop.",
    llm=llm,
    tools=escalation_tools,
    can_handoff_to=["SupportAgent"],
)

workflow = AgentWorkflow(
    agents=[intake_agent, support_agent, escalation_agent],
    root_agent="IntakeAgent",
    initial_state={"customer_info": "", "issue": "", "resolution": ""},
)


async def main():
    handler = await workflow.run(user_msg="My internet is down, can you help?")
    async for event in handler.stream_events():
        print(event)  # See each agent's action and output in real time

if __name__ == "__main__":
    asyncio.run(main())
