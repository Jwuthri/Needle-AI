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
    Context,
)

from app.utils.logging import get_logger
from app.database.base import SessionLocal
from app.optimal_workflow.agents import (
    analyze_query,
    detect_format,
    plan_retrieval,
    generate_answer,
    RetrievalPlan,
    QueryAnalysis
)
from app.optimal_workflow.services.data_retrieval_service import DataRetrievalService
from app.optimal_workflow.services.nlp_service import NLPService

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

    def __init__(self, user_id: str = None, session_id: str = None, assistant_message_id: int = None, stream_callback=None, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.session_id = session_id
        self.assistant_message_id = assistant_message_id  # For saving steps to DB
        self.message_id = None  # Will be set in start_workflow step
        self.stream_callback = stream_callback  # Callback for streaming events
        self.table_schemas = {}
        # # Load table schemas
        # db_session = SessionLocal()
        # try:
        #     schema_service = SchemaService(db_session)
        #     self.table_schemas = schema_service.get_all_available_schemas(user_id)
        #     logger.info(f"Loaded table schemas")
        # finally:
        #     db_session.close()
    
    def _emit_event(self, event_type: str, data: dict):
        """Emit a streaming event if callback is provided."""
        if self.stream_callback:
            try:
                event = {
                    "type": event_type,
                    "data": data
                }
                logger.info(f"Emitting event: {event_type} - {str(event)[:100]}")  # Debug log
                self.stream_callback(event)
            except Exception as e:
                logger.warning(f"Failed to emit event: {e}")
    
    def _emit_event_from_agent(self, event: dict):
        """Wrapper for agent callbacks that pass a single dict with type and data."""
        if isinstance(event, dict) and 'type' in event and 'data' in event:
            self._emit_event(event['type'], event['data'])
        else:
            logger.warning(f"Invalid event format from agent: {event}")

    async def _track_step_in_db(self, agent_name: str, step_order: int, content: Any, is_structured: bool):
        """
        Track workflow step in database immediately.
        
        This stores the step execution details in the database for persistence and auditing.
        
        Returns:
            The created ChatMessageStep object, or None if tracking failed
        """
        if not self.assistant_message_id:
            logger.warning(f"Cannot save step {agent_name} - no assistant_message_id set")
            return None
            
        try:
            from app.database.session import get_async_session
            from app.database.repositories.chat_message_step import ChatMessageStepRepository
            
            async with get_async_session() as db:
                logger.info(f"[WORKFLOW DB] Saving step: {agent_name} (order: {step_order})")
                
                if is_structured:
                    step = await ChatMessageStepRepository.create(
                        db=db,
                        message_id=self.assistant_message_id,
                        agent_name=agent_name,
                        step_order=step_order,
                        structured_output=content
                    )
                else:
                    step = await ChatMessageStepRepository.create(
                        db=db,
                        message_id=self.assistant_message_id,
                        agent_name=agent_name,
                        step_order=step_order,
                        prediction=content if isinstance(content, str) else str(content)
                    )
                await db.commit()
                logger.info(f"[WORKFLOW DB] ✅ Saved step: {agent_name}")
                return step
        except Exception as e:
            logger.error(f"[WORKFLOW DB] Failed to save step {agent_name}: {e}", exc_info=True)
            return None
    
    def _track_tool_calls(self, workflow_step_id: int, tool_calls: list):
        """Track tool calls in database."""
        # Tool calls are tracked as part of step content via agent_step_complete events
        logger.debug(f"Tool calls tracked: {len(tool_calls) if tool_calls else 0}")
        return None

    @step
    async def start_workflow(self, ctx: Context, ev: StartEvent) -> QueryAnalyzedEvent:
        """Step 1: Create user message and analyze the incoming query."""
        query = ev.query
        logger.info(f"🚀 Workflow started with query: {query}")
        
        # Generate step_id for this workflow step
        import uuid
        step_id = str(uuid.uuid4())
        
        self._emit_event("agent_step_start", {
            "agent_name": "Query Analyzer",
            "step_id": step_id,
            "timestamp": datetime.utcnow().isoformat(),
            "step_order": 0
        })
        
        # Note: User message creation is handled by chat API endpoint
        # We just track the message_id when it's provided
        
        logger.info("▶️  Step 1: Query Analysis")
        analysis = await analyze_query(query, stream_callback=self._emit_event_from_agent)
        logger.info(f"✓ Query Analysis complete: needs_data={analysis.needs_data_retrieval}")
        
        # Emit completion event for streaming
        self._emit_event("agent_step_complete", {
            "step_id": step_id,
            "agent_name": "Query Analyzer",
            "content": analysis.dict(),
            "is_structured": True,
            "step_order": 0
        })
        
        # Save to database immediately
        await self._track_step_in_db(
            agent_name="Query Analyzer",
            step_order=0,
            content=analysis.dict(),
            is_structured=True
        )
        
        return QueryAnalyzedEvent(query=query, analysis=analysis)

    @step
    async def detect_output_format(self, ctx: Context, ev: QueryAnalyzedEvent) -> FormatDetectedEvent:
        """Step 2: Detect the desired output format."""
        import uuid
        step_id = str(uuid.uuid4())
        
        self._emit_event("agent_step_start", {
            "agent_name": "Format Detector",
            "step_id": step_id,
            "timestamp": datetime.utcnow().isoformat(),
            "step_order": 1
        })
        
        logger.info("▶️  Step 2: Format Detection")
        format_info = await detect_format(ev.query, stream_callback=self._emit_event_from_agent)
        logger.info(f"✓ Format Detection complete: {format_info.format_type}")
        
        # Emit completion event for streaming
        self._emit_event("agent_step_complete", {
            "step_id": step_id,
            "agent_name": "Format Detector",
            "content": format_info.dict(),
            "is_structured": True,
            "step_order": 1
        })
        
        # Save to database immediately
        await self._track_step_in_db(
            agent_name="Format Detector",
            step_order=1,
            content=format_info.dict(),
            is_structured=True
        )
        
        return FormatDetectedEvent(
            query=ev.query,
            analysis=ev.analysis,
            format_info=format_info
        )

    @step
    async def plan_data_retrieval(self, ctx: Context, ev: FormatDetectedEvent) -> RetrievalPlanEvent | SkipRetrievalEvent:
        """Step 3: Plan data retrieval if needed, otherwise skip."""
        import uuid
        step_id = str(uuid.uuid4())
        
        if not ev.analysis.needs_data_retrieval:
            self._emit_event("agent_step_start", {
                "agent_name": "Retrieval Planner",
                "step_id": step_id,
                "timestamp": datetime.utcnow().isoformat(),
                "step_order": 2
            })
            
            logger.info("▶️  Step 3: Skipping data retrieval (not needed)")
            
            # Emit completion event for streaming
            self._emit_event("agent_step_complete", {
                "step_id": step_id,
                "agent_name": "Retrieval Planner",
                "content": {"skipped": True},
                "is_structured": True,
                "step_order": 2
            })
            
            # Save to database immediately
            await self._track_step_in_db(
                agent_name="Retrieval Planner",
                step_order=2,
                content={"skipped": True},
                is_structured=True
            )
            
            return SkipRetrievalEvent(
                query=ev.query,
                analysis=ev.analysis,
                format_info=ev.format_info
            )
        
        self._emit_event("agent_step_start", {
            "agent_name": "Retrieval Planner",
            "step_id": step_id,
            "timestamp": datetime.utcnow().isoformat(),
            "step_order": 2
        })
        
        logger.info("▶️  Step 3: Retrieval Planning")
        # Initialize table_schemas if None
        if self.table_schemas is None:
            self.table_schemas = {}
        plan = await plan_retrieval(ev.query, self.table_schemas, ev.analysis, stream_callback=self._emit_event_from_agent)
        logger.info(f"✓ Retrieval Planning complete: {len(plan.sql_queries)} queries")
        
        # Emit completion event for streaming
        self._emit_event("agent_step_complete", {
            "step_id": step_id,
            "agent_name": "Retrieval Planner",
            "content": {
                "num_queries": len(plan.sql_queries),
                "reasoning": plan.reasoning
            },
            "is_structured": True,
            "step_order": 2
        })
        
        # Save to database immediately
        await self._track_step_in_db(
            agent_name="Retrieval Planner",
            step_order=2,
            content={
                "num_queries": len(plan.sql_queries),
                "reasoning": plan.reasoning
            },
            is_structured=True
        )
        
        return RetrievalPlanEvent(
            query=ev.query,
            analysis=ev.analysis,
            format_info=ev.format_info,
            plan=plan
        )

    @step
    async def retrieve_data(self, ctx: Context, ev: RetrievalPlanEvent) -> DataRetrievedEvent:
        """Step 4: Execute data retrieval based on the plan."""
        import uuid
        step_id = str(uuid.uuid4())
        
        self._emit_event("agent_step_start", {
            "agent_name": "Data Retriever",
            "step_id": step_id,
            "timestamp": datetime.utcnow().isoformat(),
            "step_order": 3
        })
        
        logger.info("▶️  Step 4: Data Retrieval")
        
        # Choose format based on whether NLP analysis is needed
        data_format = "json" if ev.analysis.needs_nlp_analysis else "csv"
        logger.info(f"Using {data_format} format for data retrieval (NLP analysis: {ev.analysis.needs_nlp_analysis})")
        
        # db_session = SessionLocal()
        # try:
        #     service = DataRetrievalService(db_session)
        #     retrieved_data = service.execute_retrieval_plan(ev.plan, format=data_format)
        #     logger.info(f"✓ Data Retrieval complete: {retrieved_data['total_rows']} rows")
        # finally:
        #     db_session.close()
        
        # # Track step in database
        # self._track_step(
        #     step_name="retrieve_data",
        #     step_type="data_retrieval",
        #     input_data={
        #         "num_queries": len(ev.plan.sql_queries),
        #         "data_format": data_format
        #     },
        #     output_data={
        #         "total_rows": retrieved_data['total_rows'],
        #         "reasoning": retrieved_data['reasoning']
        #     }
        # )
        
        # self._emit_event("agent_step_complete", {
        #     "step_id": step_id,
        #     "agent_name": "Data Retriever",
        #     "content": {
        #         "total_rows": retrieved_data['total_rows'],
        #         "reasoning": retrieved_data['reasoning']
        #     },
        #     "is_structured": True,
        #     "step_order": 3
        # })
        
        return DataRetrievedEvent(
            query=ev.query,
            analysis=ev.analysis,
            format_info=ev.format_info,
            retrieved_data={}
        )

    # @step
    # async def retrieve_data(self, ctx: Context, ev: RetrievalPlanEvent) -> DataRetrievedEvent:
    #     """Step 4: Execute data retrieval based on the plan."""
    #     import uuid
    #     step_id = str(uuid.uuid4())
        
    #     self._emit_event("agent_step_start", {
    #         "agent_name": "Data Retriever",
    #         "step_id": step_id,
    #         "timestamp": datetime.utcnow().isoformat(),
    #         "step_order": 3
    #     })
        
    #     logger.info("▶️  Step 4: Data Retrieval")
        
    #     # Choose format based on whether NLP analysis is needed
    #     data_format = "json" if ev.analysis.needs_nlp_analysis else "csv"
    #     logger.info(f"Using {data_format} format for data retrieval (NLP analysis: {ev.analysis.needs_nlp_analysis})")
        
    #     db_session = SessionLocal()
    #     try:
    #         service = DataRetrievalService(db_session)
    #         retrieved_data = service.execute_retrieval_plan(ev.plan, format=data_format)
    #         logger.info(f"✓ Data Retrieval complete: {retrieved_data['total_rows']} rows")
    #     finally:
    #         db_session.close()
        
    #     # Track step in database
    #     self._track_step(
    #         step_name="retrieve_data",
    #         step_type="data_retrieval",
    #         input_data={
    #             "num_queries": len(ev.plan.sql_queries),
    #             "data_format": data_format
    #         },
    #         output_data={
    #             "total_rows": retrieved_data['total_rows'],
    #             "reasoning": retrieved_data['reasoning']
    #         }
    #     )
        
    #     self._emit_event("agent_step_complete", {
    #         "step_id": step_id,
    #         "agent_name": "Data Retriever",
    #         "content": {
    #             "total_rows": retrieved_data['total_rows'],
    #             "reasoning": retrieved_data['reasoning']
    #         },
    #         "is_structured": True,
    #         "step_order": 3
    #     })
        
    #     return DataRetrievedEvent(
    #         query=ev.query,
    #         analysis=ev.analysis,
    #         format_info=ev.format_info,
    #         retrieved_data=retrieved_data
    #     )

    @step
    async def nlp_analysis(self, ctx: Context, ev: DataRetrievedEvent) -> NLPAnalysisCompleteEvent:
        """Step 5: Perform NLP analysis if needed."""
        import uuid
        step_id = str(uuid.uuid4())
        
        if not ev.analysis.needs_nlp_analysis:
            self._emit_event("agent_step_start", {
                "agent_name": "NLP Analyzer",
                "step_id": step_id,
                "timestamp": datetime.utcnow().isoformat(),
                "step_order": 4
            })
            
            logger.info("Skipping NLP analysis (not needed)")
            
            # Track skip step in database
            await self._track_step_in_db(
                agent_name="NLP Analyzer",
                step_order=4,
                content={"skipped": True},
                is_structured=True
            )
            
            self._emit_event("agent_step_complete", {
                "step_id": step_id,
                "agent_name": "NLP Analyzer",
                "content": {"skipped": True},
                "is_structured": True,
                "step_order": 4
            })
            
            return NLPAnalysisCompleteEvent(
                query=ev.query,
                analysis=ev.analysis,
                format_info=ev.format_info,
                retrieved_data=ev.retrieved_data,
                nlp_results=None
            )
        
        self._emit_event("agent_step_start", {
            "agent_name": "NLP Analyzer",
            "step_id": step_id,
            "timestamp": datetime.utcnow().isoformat(),
            "step_order": 4
        })
        
        logger.info("▶️  Step 5: NLP Analysis")
        
        # Import here to avoid circular dependency
        from app.optimal_workflow.agents.nlp_agent import perform_nlp_analysis
        
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
        
        nlp_results = nlp_service.execute_tool_calls(
            tool_calls=tool_calls,
            retrieved_data=ev.retrieved_data
        )
        
        # Combine plan and results
        nlp_results['plan'] = nlp_plan
        
        logger.info(f"✓ NLP Execution complete: {nlp_results.get('successful', 0)} tools succeeded")
        
        # Track step in database (including tool calls)
        step = await self._track_step_in_db(
            agent_name="NLP Analyzer",
            step_order=4,
            content={
                "num_tool_calls": len(nlp_plan.get('tool_calls', [])),
                "tools_requested": nlp_results.get('total_tools_requested', 0),
                "tools_executed": nlp_results.get('total_tools_executed', 0),
                "successful": nlp_results.get('successful', 0),
                "deduplicated": nlp_results.get('deduplicated', 0)
            },
            is_structured=True
        )
        
        self._emit_event("agent_step_complete", {
            "step_id": step_id,
            "agent_name": "NLP Analyzer",
            "content": {
                "tools_executed": nlp_results.get('total_tools_executed', 0),
                "successful": nlp_results.get('successful', 0),
                "deduplicated": nlp_results.get('deduplicated', 0)
            },
            "is_structured": True,
            "step_order": 4
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
        import uuid
        step_id = str(uuid.uuid4())
        
        self._emit_event("agent_step_start", {
            "agent_name": "Answer Generator",
            "step_id": step_id,
            "timestamp": datetime.utcnow().isoformat(),
            "step_order": 5
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
        from app.optimal_workflow.agents.base import get_llm
        
        # Determine which agent to use based on format
        if format_type.lower() in ['markdown', 'report', 'bullet points']:
            from app.optimal_workflow.agents.markdown_writer import create_markdown_writer
            agent = create_markdown_writer()
            system_prompt = agent.system_prompt
        elif format_type.lower() in ['table', 'tabular', 'csv']:
            from app.optimal_workflow.agents.table_writer import create_table_writer
            agent = create_table_writer()
            system_prompt = agent.system_prompt
        elif format_type.lower() in ['chart', 'visualization', 'graph']:
            from app.optimal_workflow.agents.chart_writer import create_chart_writer
            agent = create_chart_writer()
            system_prompt = agent.system_prompt
        elif format_type.lower() in ['json', 'api', 'structured']:
            from app.optimal_workflow.agents.json_writer import create_json_writer
            agent = create_json_writer()
            system_prompt = agent.system_prompt
        else:
            from app.optimal_workflow.agents.markdown_writer import create_markdown_writer
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
                    self._emit_event("content", {
                        "content": content_chunk
                    })
            
            answer = "".join(answer_parts)
            
        except Exception as e:
            logger.warning(f"LlamaIndex streaming failed: {e}, falling back to non-streaming")
            # Fallback to non-streaming
            from app.optimal_workflow.agents.writer_team import generate_answer
            answer = await generate_answer(context, format_type)
            
            # Stream in chunks as fallback
            chunk_size = 30
            for i in range(0, len(answer), chunk_size):
                chunk = answer[i:i + chunk_size]
                self._emit_event("content", {
                    "content": chunk
                })
                import asyncio
                await asyncio.sleep(0.01)
        
        logger.info("✓ Answer generation complete")
        
        # Emit completion event for streaming
        self._emit_event("agent_step_complete", {
            "step_id": step_id,
            "agent_name": "Answer Generator",
            "content": {"answer_length": len(answer)},
            "is_structured": True,
            "step_order": 5
        })
        
        # Save to database immediately
        await self._track_step_in_db(
            agent_name="Answer Generator",
            step_order=5,
            content={"answer_length": len(answer)},
            is_structured=True
        )
        
        # Update assistant message with final answer
        if self.assistant_message_id:
            try:
                from app.database.session import get_async_session
                from app.database.repositories.chat_message import ChatMessageRepository
                
                async with get_async_session() as db:
                    assistant_msg = await ChatMessageRepository.get_by_id(db, self.assistant_message_id)
                    if assistant_msg:
                        assistant_msg.content = answer
                        assistant_msg.completed_at = datetime.utcnow()  # Set completion timestamp
                        await db.commit()
                        logger.info(f"[WORKFLOW] Updated assistant message {self.assistant_message_id} with final answer and completed_at")
            except Exception as e:
                logger.error(f"[WORKFLOW] Failed to update assistant message: {e}", exc_info=True)
        
        # Create ChatResponse for complete event
        from app.models.chat import ChatResponse as ChatResponseModel
        chat_response_obj = ChatResponseModel(
            message=answer,
            session_id=self.session_id if self.session_id else "default",
            message_id=str(self.assistant_message_id) if self.assistant_message_id else str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            completed_at=datetime.utcnow(),  # Include completion timestamp
            metadata={
                "workflow": "llamaindex_optimal",
                "user_id": self.user_id
            }
        )
        
        self._emit_event("complete", chat_response_obj.dict())
        
        logger.info("🏁 Workflow completed")
        
        return StopEvent(result=answer)

if __name__ == "__main__":
    workflow = ProductGapWorkflow()
    workflow.draw_steps("workflow.html")
