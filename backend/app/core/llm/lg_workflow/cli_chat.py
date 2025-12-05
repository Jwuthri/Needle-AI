import uuid
import sys
import os

from langsmith import uuid7
from app.core.llm.lg_workflow.graph import create_workflow
from langchain_core.messages import HumanMessage
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt

# Initialize the workflow
# We need a user_id for the workflow creation
app = create_workflow("cli-user")

console = Console()

def main():
    console.print(Panel.fit("[bold blue]Multi-Agent Data System[/bold blue]", border_style="blue"))
    console.print("Type [bold red]'quit'[/bold red] to exit.")
    
    thread_id = str(uuid7())
    config = {"configurable": {"thread_id": thread_id}}
    
    while True:
        user_input = Prompt.ask("\n[bold green]User[/bold green]")
        if user_input.lower() in ["quit", "exit"]:
            break
            
        # Stream the graph execution
        # Stream the graph execution
        # We use stream_mode="messages" to get token-by-token updates
        current_node = None
        current_content = ""
        live_display = None
        
        # Helper to create a panel for the current agent
        def create_panel(content, node_name):
            color = "cyan"
            title = node_name
            if node_name == "DataLibrarian":
                color = "magenta"
            elif node_name == "DataAnalyst":
                color = "orange1"
            elif node_name == "Coder":
                color = "bright_cyan"
                title = "🐍 Coder (Claude)"
            elif node_name == "Reporter":
                color = "green"
                title = "✅ Final Answer"
            elif node_name == "Researcher":
                color = "blue"
            elif node_name == "Visualizer":
                color = "purple"
            elif node_name == "Supervisor":
                color = "yellow"
            
            return Panel(
                Markdown(content),
                title=f"[bold {color}]{title}[/bold {color}]",
                border_style=color
            )

        from rich.live import Live
        
        # We'll use a single Live context for the entire stream, updating it as we go
        # Actually, switching panels inside one Live context is tricky. 
        # Better to have a Live context per agent turn.
        
        try:
            events = app.astream_events(
                {"messages": [HumanMessage(content=user_input)]},
                config,
                version="v2"
            )
            
            import asyncio
            
            async def process_events():
                nonlocal current_node, current_content, live_display
                
                async for event in events:
                    kind = event.get("event")
                    name = event.get("name", "")
                    
                    # Track node transitions
                    if kind == "on_chain_start":
                        # Check if this is an agent node
                        if name in ["DataLibrarian", "DataAnalyst", "Coder", "Researcher", "Visualizer", "Reporter"]:
                            if live_display and current_node != name:
                                live_display.stop()
                            
                            # Show routing decision
                            if current_node != name:
                                console.print(f"\n[bold yellow]next → {name}[/bold yellow]")
                            
                            current_node = name
                            current_content = ""
                            
                            live_display = Live(create_panel("", name), console=console, refresh_per_second=20)
                            live_display.start()
                    
                    # Capture streaming tokens from the LLM
                    elif kind == "on_chat_model_stream":
                        chunk = event.get("data", {}).get("chunk")
                        if chunk and hasattr(chunk, 'content') and chunk.content:
                            current_content += chunk.content
                            
                            if live_display and current_node:
                                # Filter out supervisor routing decisions before display
                                import re
                                display_content = re.sub(r'\{["\']?next["\']?\s*:\s*["\'][^"\']+["\']}\s*', '', current_content)
                                live_display.update(create_panel(display_content, current_node))
                
                if live_display:
                    live_display.stop()
            
            # Run the async function
            asyncio.run(process_events())
                
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
