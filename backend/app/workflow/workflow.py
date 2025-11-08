"""
Main workflow definition using LlamaIndex.

This workflow implements the product gap detection logic with multi-step execution.
"""

import json
from datetime import datetime, date
from typing import Any, Dict, Optional
from llama_index.core.workflow import (
    Workflow,
    StartEvent,
    StopEvent,
    Event,
    step,
    Context
)
from llama_index.utils.workflow import draw_all_possible_flows

from app import get_logger
from app.database.base import SessionLocal
from app.services.schema_service import SchemaService
from app.workflow.agents import (
    analyze_query,
    detect_format,
    plan_retrieval,
    generate_answer,
    RetrievalPlan,
    QueryAnalysis
)
from app.workflow.services import DataRetrievalService
from app.workflow.services.nlp_service import NLPService

logger = get_logger(__name__)


def _sanitize_for_json(data: Any) -> Any:
    """Recursively sanitize data for JSON serialization, handling Timestamp keys and values."""
    from datetime import datetime, date
    
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            # Convert non-standard keys to strings
            if isinstance(key, (datetime, date)):
                sanitized_key = key.isoformat()
            elif not isinstance(key, (str, int, float, bool, type(None))):
                # Try pandas Timestamp
                try:
                    import pandas as pd
                    if isinstance(key, pd.Timestamp):
                        sanitized_key = key.isoformat()
                    else:
                        sanitized_key = str(key)
                except (ImportError, AttributeError):
                    sanitized_key = str(key)
            else:
                sanitized_key = key
            
            sanitized[sanitized_key] = _sanitize_for_json(value)
        return sanitized
    elif isinstance(data, (list, tuple)):
        return [_sanitize_for_json(item) for item in data]
    elif isinstance(data, (datetime, date)):
        return data.isoformat()
    else:
        # Handle pandas/numpy types
        try:
            import pandas as pd
            if isinstance(data, pd.Timestamp):
                return data.isoformat()
        except (ImportError, AttributeError):
            pass
        try:
            import numpy as np
            if isinstance(data, (np.datetime64, np.integer, np.floating)):
                return data.item() if hasattr(data, 'item') else str(data)
        except (ImportError, AttributeError):
            pass
        return data


# Define custom events for workflow steps
class QueryAnalyzedEvent(Event):
    """Event triggered after query analysis is complete."""
    query: str
    analysis: Any


class FormatDetectedEvent(Event):
    """Event triggered after format detection is complete."""
    query: str
    analysis: Any
    format_info: Any


class RetrievalPlanEvent(Event):
    """Event triggered when retrieval planning is needed."""
    query: str
    analysis: Any
    format_info: Any
    plan: RetrievalPlan


class DataRetrievedEvent(Event):
    """Event triggered after data retrieval is complete."""
    query: str
    analysis: Any
    format_info: Any
    retrieved_data: Optional[Dict[str, Any]]


class SkipRetrievalEvent(Event):
    """Event triggered when data retrieval is not needed."""
    query: str
    analysis: Any
    format_info: Any


class NLPAnalysisCompleteEvent(Event):
    """Event triggered after NLP analysis is complete."""
    query: str
    analysis: Any
    format_info: Any
    retrieved_data: Optional[Dict[str, Any]]
    nlp_results: Optional[Dict[str, Any]]


class ProductGapWorkflow(Workflow):
    """
    Product Gap Detection Workflow using LlamaIndex.
    
    Multi-step Flow:
    1. Start -> Query Analysis
    2. Query Analysis -> Format Detection  
    3. Format Detection -> Retrieval Planning (if needed) OR Skip Retrieval
    4. Retrieval Planning -> Data Retrieval
    5. Data Retrieval -> NLP Analysis
    6. NLP Analysis OR Skip Retrieval -> Generate Answer
    """

    def __init__(self, user_id: int = 1, conversation_id: int = None, stream_callback=None, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.message_id = None  # Will be set in start_workflow step
        self.stream_callback = stream_callback  # Callback for streaming events
        
        # Load table schemas
        db_session = SessionLocal()
        try:
            schema_service = SchemaService(db_session)
            self.table_schemas = schema_service.get_all_available_schemas(user_id)
            logger.info(f"Loaded table schemas")
        finally:
            db_session.close()
    
    def _emit_event(self, event_type: str, data: dict):
        """Emit a streaming event if callback is provided."""
        if self.stream_callback:
            try:
                event = {
                    "type": event_type,
                    **data
                }
                logger.info(f"Emitting event: {event_type} - {str(event)[:100]}")  # Debug log
                self.stream_callback(event)
            except Exception as e:
                logger.warning(f"Failed to emit event: {e}")

    def draw_steps(self, filename: str = "workflow.html"):
        """Draw the workflow steps."""
        draw_all_possible_flows(self, filename=filename)

    def _track_step(self, step_name: str, step_type: str, input_data: dict = None, output_data: dict = None, status: str = "completed", error_message: str = None):
        """Track workflow step in database."""
        if not self.message_id:
            return None
        
        from app.database.repositories import WorkflowStepRepository
        from datetime import datetime
        
        db_session = SessionLocal()
        try:
            repo = WorkflowStepRepository()
            step = repo.create(
                db=db_session,
                message_id=self.message_id,
                step_name=step_name,
                step_type=step_type,
                input_data=input_data,
                output_data=output_data,
                status=status,
                error_message=error_message,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
            return step
        finally:
            db_session.close()
    
    def _track_tool_calls(self, workflow_step_id: int, tool_calls: list):
        """Track tool calls in database."""
        if not workflow_step_id:
            return
        
        from app.database.repositories import ToolCallRepository
        from datetime import datetime
        
        db_session = SessionLocal()
        try:
            repo = ToolCallRepository()
            for tool_call in tool_calls:
                repo.create(
                    db=db_session,
                    workflow_step_id=workflow_step_id,
                    tool_name=tool_call.get('tool_name', 'unknown'),
                    tool_input=tool_call.get('parameters', {}),
                    tool_output=tool_call.get('result', {}),
                    status=tool_call.get('status', 'completed'),
                    error_message=tool_call.get('error', None),
                    started_at=datetime.utcnow(),
                    completed_at=datetime.utcnow()
                )
        finally:
            db_session.close()

    @step
    async def start_workflow(self, ctx: Context, ev: StartEvent) -> QueryAnalyzedEvent:
        """Step 1: Create user message and analyze the incoming query."""
        query = ev.query
        logger.info(f"🚀 Workflow started with query: {query}")
        
        self._emit_event("step_start", {
            "step": 1,
            "step_name": "Query Analysis",
            "description": "Analyzing your question to understand what data is needed..."
        })
        
        # Create user message in the database
        if self.conversation_id:
            from app.database.repositories import MessageRepository
            
            db_session = SessionLocal()
            try:
                msg_repo = MessageRepository()
                user_message = msg_repo.create(
                    db=db_session,
                    conversation_id=self.conversation_id,
                    role="user",
                    content=query
                )
                self.message_id = user_message.id
                logger.info(f"Created user message: {self.message_id}")
            finally:
                db_session.close()
        
        logger.info("▶️  Step 1: Query Analysis")
        analysis = await analyze_query(query)
        logger.info(f"✓ Query Analysis complete: needs_data={analysis.needs_data_retrieval}")
        
        # Track step in database
        self._track_step(
            step_name="start_workflow",
            step_type="query_analysis",
            input_data={"query": query},
            output_data={
                "needs_data_retrieval": analysis.needs_data_retrieval,
                "needs_nlp_analysis": analysis.needs_nlp_analysis,
                "query_type": analysis.query_type
            }
        )
        
        self._emit_event("step_complete", {
            "step": 1,
            "step_name": "Query Analysis",
            "result": {
                "needs_data_retrieval": analysis.needs_data_retrieval,
                "needs_nlp_analysis": analysis.needs_nlp_analysis,
                "query_type": analysis.query_type
            }
        })
        
        return QueryAnalyzedEvent(query=query, analysis=analysis)

    @step
    async def detect_output_format(self, ctx: Context, ev: QueryAnalyzedEvent) -> FormatDetectedEvent:
        """Step 2: Detect the desired output format."""
        self._emit_event("step_start", {
            "step": 2,
            "step_name": "Format Detection",
            "description": "Detecting the desired output format..."
        })
        
        logger.info("▶️  Step 2: Format Detection")
        format_info = await detect_format(ev.query)
        logger.info(f"✓ Format Detection complete: {format_info.format_type}")
        
        # Track step in database
        self._track_step(
            step_name="detect_output_format",
            step_type="format_detection",
            input_data={"query": ev.query},
            output_data={
                "format_type": format_info.format_type,
                "format_details": format_info.format_details
            }
        )
        
        self._emit_event("step_complete", {
            "step": 2,
            "step_name": "Format Detection",
            "result": {
                "format_type": format_info.format_type,
                "format_details": format_info.format_details
            }
        })
        
        return FormatDetectedEvent(
            query=ev.query,
            analysis=ev.analysis,
            format_info=format_info
        )

    @step
    async def plan_data_retrieval(self, ctx: Context, ev: FormatDetectedEvent) -> RetrievalPlanEvent | SkipRetrievalEvent:
        """Step 3: Plan data retrieval if needed, otherwise skip."""
        if not ev.analysis.needs_data_retrieval:
            self._emit_event("step_start", {
                "step": 3,
                "step_name": "Data Retrieval Planning",
                "description": "Skipping data retrieval (not needed)..."
            })
            
            logger.info("▶️  Step 3: Skipping data retrieval (not needed)")
            
            # Track skip step in database
            self._track_step(
                step_name="plan_data_retrieval",
                step_type="skip_retrieval",
                input_data={"needs_data_retrieval": False},
                output_data={"skipped": True}
            )
            
            self._emit_event("step_complete", {
                "step": 3,
                "step_name": "Data Retrieval Planning",
                "result": {"skipped": True}
            })
            
            return SkipRetrievalEvent(
                query=ev.query,
                analysis=ev.analysis,
                format_info=ev.format_info
            )
        
        self._emit_event("step_start", {
            "step": 3,
            "step_name": "Data Retrieval Planning",
            "description": "Planning which data to retrieve from your datasets..."
        })
        
        logger.info("▶️  Step 3: Retrieval Planning")
        plan = await plan_retrieval(ev.query, self.table_schemas, ev.analysis)
        logger.info(f"✓ Retrieval Planning complete: {len(plan.sql_queries)} queries")
        
        # Track step in database
        self._track_step(
            step_name="plan_data_retrieval",
            step_type="retrieval_planning",
            input_data={"query": ev.query, "num_schemas": len(self.table_schemas)},
            output_data={
                "num_queries": len(plan.sql_queries),
                "reasoning": plan.reasoning
            }
        )
        
        self._emit_event("step_complete", {
            "step": 3,
            "step_name": "Data Retrieval Planning",
            "result": {
                "num_queries": len(plan.sql_queries),
                "reasoning": plan.reasoning
            }
        })
        
        return RetrievalPlanEvent(
            query=ev.query,
            analysis=ev.analysis,
            format_info=ev.format_info,
            plan=plan
        )

    @step
    async def retrieve_data(self, ctx: Context, ev: RetrievalPlanEvent) -> DataRetrievedEvent:
        """Step 4: Execute data retrieval based on the plan."""
        self._emit_event("step_start", {
            "step": 4,
            "step_name": "Data Retrieval",
            "description": f"Executing {len(ev.plan.sql_queries)} data queries..."
        })
        
        logger.info("▶️  Step 4: Data Retrieval")
        
        # Choose format based on whether NLP analysis is needed
        data_format = "json" if ev.analysis.needs_nlp_analysis else "csv"
        logger.info(f"Using {data_format} format for data retrieval (NLP analysis: {ev.analysis.needs_nlp_analysis})")
        
        db_session = SessionLocal()
        try:
            service = DataRetrievalService(db_session)
            retrieved_data = service.execute_retrieval_plan(ev.plan, format=data_format)
            logger.info(f"✓ Data Retrieval complete: {retrieved_data['total_rows']} rows")
        finally:
            db_session.close()
        
        # Track step in database
        self._track_step(
            step_name="retrieve_data",
            step_type="data_retrieval",
            input_data={
                "num_queries": len(ev.plan.sql_queries),
                "data_format": data_format
            },
            output_data={
                "total_rows": retrieved_data['total_rows'],
                "reasoning": retrieved_data['reasoning']
            }
        )
        
        self._emit_event("step_complete", {
            "step": 4,
            "step_name": "Data Retrieval",
            "result": {
                "total_rows": retrieved_data['total_rows'],
                "reasoning": retrieved_data['reasoning']
            }
        })
        
        return DataRetrievedEvent(
            query=ev.query,
            analysis=ev.analysis,
            format_info=ev.format_info,
            retrieved_data=retrieved_data
        )

    @step
    async def nlp_analysis(self, ctx: Context, ev: DataRetrievedEvent) -> NLPAnalysisCompleteEvent:
        """Step 5: Perform NLP analysis if needed."""
        if not ev.analysis.needs_nlp_analysis:
            self._emit_event("step_start", {
                "step": 5,
                "step_name": "NLP Analysis",
                "description": "Skipping NLP analysis (not needed)..."
            })
            
            logger.info("Skipping NLP analysis (not needed)")
            
            # Track skip step in database
            self._track_step(
                step_name="nlp_analysis",
                step_type="nlp_analysis",
                input_data={"needs_nlp_analysis": False},
                output_data={"skipped": True}
            )
            
            self._emit_event("step_complete", {
                "step": 5,
                "step_name": "NLP Analysis",
                "result": {"skipped": True}
            })
            
            return NLPAnalysisCompleteEvent(
                query=ev.query,
                analysis=ev.analysis,
                format_info=ev.format_info,
                retrieved_data=ev.retrieved_data,
                nlp_results=None
            )
        
        self._emit_event("step_start", {
            "step": 5,
            "step_name": "NLP Analysis",
            "description": "Analyzing text data with NLP tools..."
        })
        
        logger.info("▶️  Step 5: NLP Analysis")
        
        # Import here to avoid circular dependency
        from app.workflow.agents.nlp_agent import perform_nlp_analysis
        
        # Step 5a: Agent selects which NLP tools to use
        nlp_plan = await perform_nlp_analysis(
            query=ev.query,
            analysis=ev.analysis,
            retrieved_data=ev.retrieved_data
        )
        
        logger.info(f"✓ NLP Planning complete: {len(nlp_plan.get('tool_calls', []))} tool calls planned")
        
        # Step 5b: Execute the NLP tools on the data
        nlp_service = NLPService()
        tool_calls = nlp_plan.get('tool_calls', [])
        
        # Emit tool call events as they execute
        for tool_call in tool_calls:
            tool_name = tool_call.get('tool_name', 'unknown')
            dataset_name = tool_call.get('dataset_name', 'unknown')
            
            self._emit_event("tool_call_start", {
                "tool_name": tool_name,
                "dataset_name": dataset_name,
                "parameters": tool_call.get('parameters', {})
            })
        
        nlp_results = nlp_service.execute_tool_calls(
            tool_calls=tool_calls,
            retrieved_data=ev.retrieved_data
        )
        
        # Combine plan and results
        nlp_results['plan'] = nlp_plan
        
        # Emit tool call results
        if nlp_results.get('tool_results'):
            seen_calls = nlp_results.get('seen_calls', [])
            for tool_key, result in nlp_results.get('tool_results', {}).items():
                parts = tool_key.rsplit('@', 1)
                tool_name = parts[0] if len(parts) > 1 else tool_key
                dataset_name = parts[1] if len(parts) > 1 else 'unknown'
                
                # Find matching seen_call to get full parameters
                parameters = {'dataset_name': dataset_name}
                for seen_call in seen_calls:
                    seen_tool_name, seen_dataset_name, param_key = seen_call
                    if seen_tool_name == tool_name and seen_dataset_name == dataset_name:
                        if isinstance(param_key, tuple):
                            parameters = dict(param_key)
                            parameters['dataset_name'] = dataset_name
                        break
                
                # Sanitize result
                sanitized_result = _sanitize_for_json(result) if result else None
                
                self._emit_event("tool_call_complete", {
                    "tool_name": tool_name,
                    "dataset_name": dataset_name,
                    "parameters": _sanitize_for_json(parameters),
                    "result": sanitized_result if not result.get('error') else None,
                    "status": 'failed' if result.get('error') else 'completed',
                    "error": result.get('error', None)
                })
        
        logger.info(f"✓ NLP Execution complete: {nlp_results.get('successful', 0)} tools succeeded")
        
        # Track step in database (including tool calls)
        step = self._track_step(
            step_name="nlp_analysis",
            step_type="nlp_analysis",
            input_data={
                "num_tool_calls": len(nlp_plan.get('tool_calls', [])),
                "tools_requested": nlp_results.get('total_tools_requested', 0)
            },
            output_data={
                "tools_executed": nlp_results.get('total_tools_executed', 0),
                "successful": nlp_results.get('successful', 0),
                "deduplicated": nlp_results.get('deduplicated', 0)
            }
        )
        
        self._emit_event("step_complete", {
            "step": 5,
            "step_name": "NLP Analysis",
            "result": {
                "tools_executed": nlp_results.get('total_tools_executed', 0),
                "successful": nlp_results.get('successful', 0),
                "deduplicated": nlp_results.get('deduplicated', 0)
            }
        })
        # Track individual tool calls
        if step and nlp_results.get('tool_results'):
            tool_calls_for_db = []
            seen_calls = nlp_results.get('seen_calls', [])
            
            for tool_key, result in nlp_results.get('tool_results', {}).items():
                parts = tool_key.rsplit('@', 1)  # DONT CHANGE THAT FUCKING LLM
                tool_name = parts[0] if len(parts) > 1 else tool_key
                dataset_name = parts[1] if len(parts) > 1 else 'unknown'
                
                # Find matching seen_call to get full parameters
                parameters = {'dataset_name': dataset_name}
                for seen_call in seen_calls:
                    seen_tool_name, seen_dataset_name, param_key = seen_call
                    if seen_tool_name == tool_name and seen_dataset_name == dataset_name:
                        # param_key is a tuple of parameter items
                        if isinstance(param_key, tuple):
                            parameters = dict(param_key)
                            parameters['dataset_name'] = dataset_name
                        break
                
                # Sanitize result to handle Timestamp keys/values
                sanitized_result = _sanitize_for_json(result) if result else None
                
                tool_calls_for_db.append({
                    'tool_name': tool_name,
                    'parameters': _sanitize_for_json(parameters),
                    'result': sanitized_result if not result.get('error') else None,
                    'status': 'failed' if result.get('error') else 'completed',
                    'error': result.get('error', None)
                })
            
            self._track_tool_calls(step.id, tool_calls_for_db)
        
        return NLPAnalysisCompleteEvent(
            query=ev.query,
            analysis=ev.analysis,
            format_info=ev.format_info,
            retrieved_data=ev.retrieved_data,
            nlp_results=nlp_results
        )

    @step
    async def generate_final_answer(self, ctx: Context, ev: NLPAnalysisCompleteEvent | SkipRetrievalEvent) -> StopEvent:
        """Step 6: Generate the final answer using all collected information."""
        self._emit_event("step_start", {
            "step": 6,
            "step_name": "Answer Generation",
            "description": "Generating your final answer..."
        })
        
        logger.info("▶️  Step 6: Generate Answer")
        
        # Build context string
        context_parts = [f"Query: {ev.query}"]
        
        if ev.format_info:
            context_parts.append(f"\nDesired Format: {ev.format_info.format_type}")
            context_parts.append(f"Format Details: {ev.format_info.format_details}")
        
        if ev.analysis:
            context_parts.append(f"\nQuery Type: {ev.analysis.query_type}")
        
        # Handle retrieved data if available
        if isinstance(ev, NLPAnalysisCompleteEvent) and ev.retrieved_data:
            retrieved_data = ev.retrieved_data
            
            # Convert JSON data to CSV format for token efficiency
            formatted_data = {}
            for key, value in retrieved_data['data'].items():
                if key.endswith('_error'):
                    formatted_data[key] = value
                elif isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                    # Convert list of dicts to CSV format
                    formatted_data[key] = DataRetrievalService._format_as_csv(value)
                else:
                    # Already CSV string or other format
                    formatted_data[key] = value
            
            context_parts.append(f"\nRetrieved Data contains ({retrieved_data['total_rows']} rows): <data>{formatted_data}</data>")
            context_parts.append(f"\nReasoning: {retrieved_data['reasoning']}")
            context_parts.append(f"\nNlp analysis results: <nlp>{ev.nlp_results}</nlp>")
        
        context = "\n".join(context_parts)
        
        # Generate final answer by directly streaming from the appropriate writer agent
        format_type = ev.format_info.format_type if ev.format_info else "markdown"
        
        # Import the specific writer based on format
        from app.workflow.agents.base import get_llm
        
        # Determine which agent to use based on format
        if format_type.lower() in ['markdown', 'report', 'bullet points']:
            from app.workflow.agents.markdown_writer import create_markdown_writer
            agent = create_markdown_writer()
            system_prompt = agent.system_prompt
        elif format_type.lower() in ['table', 'tabular', 'csv']:
            from app.workflow.agents.table_writer import create_table_writer
            agent = create_table_writer()
            system_prompt = agent.system_prompt
        elif format_type.lower() in ['chart', 'visualization', 'graph']:
            from app.workflow.agents.chart_writer import create_chart_writer
            agent = create_chart_writer()
            system_prompt = agent.system_prompt
        elif format_type.lower() in ['json', 'api', 'structured']:
            from app.workflow.agents.json_writer import create_json_writer
            agent = create_json_writer()
            system_prompt = agent.system_prompt
        else:
            from app.workflow.agents.markdown_writer import create_markdown_writer
            agent = create_markdown_writer()
            system_prompt = agent.system_prompt
        
        user_msg = f"Please create a {format_type} report based on this context:\n\n{context}"
        
        # Get LLM from agent
        llm = agent.llm if hasattr(agent, 'llm') else get_llm()
        
        answer_parts = []
        
        logger.info(f"Starting to stream answer from {agent.name} using LlamaIndex...")
        
        # Use LlamaIndex's astream_chat for proper streaming
        try:
            from llama_index.core.llms import ChatMessage, MessageRole
            
            messages = [
                ChatMessage(role=MessageRole.SYSTEM, content=system_prompt),
                ChatMessage(role=MessageRole.USER, content=user_msg)
            ]
            
            # Stream using LlamaIndex
            response = await llm.astream_chat(messages)
            
            async for chunk in response:
                content_chunk = chunk.delta if hasattr(chunk, 'delta') else str(chunk)
                if content_chunk:
                    answer_parts.append(content_chunk)
                    self._emit_event("answer_chunk", {
                        "chunk": content_chunk,
                        "position": None,
                        "total_length": None
                    })
            
            answer = "".join(answer_parts)
            
        except Exception as e:
            logger.warning(f"LlamaIndex streaming failed: {e}, falling back to non-streaming")
            # Fallback to non-streaming
            from app.workflow.agents.writer_team import generate_answer
            answer = await generate_answer(context, format_type)
            
            # Stream in chunks as fallback
            chunk_size = 30
            for i in range(0, len(answer), chunk_size):
                chunk = answer[i:i + chunk_size]
                self._emit_event("answer_chunk", {
                    "chunk": chunk,
                    "position": i,
                    "total_length": len(answer)
                })
                import asyncio
                await asyncio.sleep(0.01)
        
        logger.info("✓ Answer generation complete")
        
        # Track step in database
        self._track_step(
            step_name="generate_final_answer",
            step_type="answer_generation",
            input_data={
                "context_length": len(context),
                "format_type": format_type
            },
            output_data={
                "answer_length": len(answer)
            }
        )
        
        # Create assistant message with the answer
        if self.conversation_id:
            from app.database.repositories import MessageRepository
            
            db_session = SessionLocal()
            try:
                msg_repo = MessageRepository()
                # Create assistant message
                assistant_message = msg_repo.create(
                    db=db_session,
                    conversation_id=self.conversation_id,
                    role="assistant",
                    content=answer
                )
                logger.info(f"Created assistant message: {assistant_message.id}")
            finally:
                db_session.close()
        
        self._emit_event("step_complete", {
            "step": 6,
            "step_name": "Answer Generation",
            "result": {"answer_length": len(answer)}
        })
        
        self._emit_event("workflow_complete", {
            "conversation_id": self.conversation_id,
            "message_id": self.message_id
        })
        
        logger.info("🏁 Workflow completed")
        
        return StopEvent(result=answer)

if __name__ == "__main__":
    workflow = ProductGapWorkflow()
    workflow.draw_steps("workflow.html")
