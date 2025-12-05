"""
Coder Agent - executes custom Python code for advanced data analysis.

Uses Claude Sonnet 4.5 for superior code generation capabilities.
This agent is called when other agents cannot handle complex data requests.
"""

from typing import Optional, List, Dict, Any
from langchain_core.tools import tool
from langchain_core.messages import AIMessage
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent
from app.core.config.settings import get_settings

settings = get_settings()

# Use Claude Sonnet 4.5 for code generation
claude_llm = ChatAnthropic(
    model="claude-sonnet-4-5-20250929",
    temperature=0.1,
    api_key=settings.anthropic_api_key,
    max_tokens=16000,
)


async def fetch_datasets_info(user_id: str) -> List[Dict[str, Any]]:
    """Fetch all dataset info for user at runtime."""
    from app.services.user_dataset_service import UserDatasetService
    from app.database.session import get_async_session
    
    try:
        async with get_async_session() as session:
            service = UserDatasetService(session)
            datasets = await service.list_datasets(user_id, limit=20, offset=0)
            
            datasets_info = []
            for ds in datasets:
                # list_datasets returns dicts, not objects
                info = {
                    'id': ds.get('id') if isinstance(ds, dict) else ds.id,
                    'table_name': ds.get('table_name') if isinstance(ds, dict) else ds.table_name,
                    'row_count': ds.get('row_count') if isinstance(ds, dict) else getattr(ds, 'row_count', 0),
                    'columns': [],
                }
                
                # Get column names from field_metadata
                field_metadata = ds.get('field_metadata') if isinstance(ds, dict) else getattr(ds, 'field_metadata', None)
                if field_metadata:
                    info['columns'] = [f.get('field_name') for f in field_metadata if f.get('field_name')]
                
                datasets_info.append(info)
            
            return datasets_info
    except Exception as e:
        print(f"Error fetching datasets: {e}")
        return []


def build_coder_prompt(datasets_info: List[Dict[str, Any]]) -> str:
    """Build system prompt with dataset info baked in."""
    
    if datasets_info:
        datasets_section = "## YOUR DATASETS\n\n"
        for ds in datasets_info:
            datasets_section += f"**`{ds['table_name']}`** ({ds.get('row_count', '?')} rows)\n"
            if ds.get('columns'):
                cols = ds['columns'][:15]
                datasets_section += f"  Columns: {', '.join(cols)}"
                if len(ds.get('columns', [])) > 15:
                    datasets_section += f" (+{len(ds['columns']) - 15} more)"
                datasets_section += "\n"
            datasets_section += "\n"
        example_table = datasets_info[0]['table_name']
    else:
        datasets_section = "## DATASETS\nNo datasets found.\n"
        example_table = "your_table_name"
    
    return f"""You are a Python data analyst. Write code to analyze data.

{datasets_section}
## LOAD DATA
```python
df = get_dataset("{example_table}")
```

## LIBRARIES: pandas (pd), numpy (np), math, statistics, datetime, collections, itertools, json, re

## RULES
1. Use exact table names from above with get_dataset()
2. Store result in `result` variable
3. Use print() for outputs
4. NO file I/O, NO network, NO system commands

Write code and execute with execute_python_code tool."""


def create_coder_node(user_id: str, dataset_table_name: Optional[str] = None):
    """Create coder agent node - fetches dataset info at runtime."""
    
    @tool
    async def execute_python_code(code: str) -> str:
        """
        Execute Python code for data analysis.
        
        Use get_dataset("table_name") to load data as DataFrame.
        Store final result in `result` variable.
        
        Args:
            code: Python code to execute
        """
        from app.core.llm.lg_workflow.tools.code_execution import execute_code_tool
        
        return await execute_code_tool(
            code=code,
            dataset_id=dataset_table_name,
            user_id=user_id
        )
    
    tools = [execute_python_code]
    
    async def coder_node(state):
        """Async node that fetches dataset info then runs the agent."""
        
        # Fetch datasets at runtime
        datasets_info = await fetch_datasets_info(user_id)
        
        # Build prompt with current dataset info
        system_prompt = build_coder_prompt(datasets_info)
        
        # Create agent with fresh prompt
        agent = create_react_agent(
            claude_llm,
            tools,
            prompt=system_prompt
        )
        
        # Run the agent
        result = await agent.ainvoke(state)
        
        # Tag messages as from Coder
        if result.get("messages"):
            for msg in result["messages"]:
                if isinstance(msg, AIMessage):
                    msg.name = "Coder"
        
        return result
    
    return coder_node
