"""
Hybrid Orchestrator Service - Coordinates router and specialist agents with security guardrails.
"""

from typing import Any, AsyncGenerator, Dict, Optional
from datetime import datetime

from app.services.security_guardrails_service import SecurityGuardrailsService
from app.services.router_agent_service import RouterAgentService, RouterDecision
from app.services.specialists import ProductAgent, ResearchAgent, AnalyticsAgent, GeneralAgent
from app.config import get_settings
from app.models.chat import ChatRequest, ChatResponse
from app.utils.logging import get_logger

logger = get_logger("hybrid_orchestrator")


class HybridOrchestratorService:
    """
    Main orchestrator for hybrid router + specialist architecture.
    
    Flow:
    1. Security guardrails (PII, prompt injection, moderation)
    2. Router classification
    3. Specialist execution with ReAct loop
    4. Response post-processing (PII check)
    5. Streaming to frontend
    """
    
    def __init__(self, settings: Any = None):
        self.settings = settings or get_settings()
        
        # Initialize components
        self.security = SecurityGuardrailsService(self.settings)
        self.router = RouterAgentService(self.settings)
        
        # Initialize specialists
        self.specialists = {
            "product": ProductAgent(self.settings),
            "research": ResearchAgent(self.settings),
            "analytics": AnalyticsAgent(self.settings),
            "general": GeneralAgent(self.settings)
        }
        
        self._initialized = False
    
    async def initialize(self):
        """Initialize all specialists."""
        if self._initialized:
            return
        
        try:
            logger.info("Initializing hybrid orchestrator...")
            
            # Initialize all specialists in parallel
            import asyncio
            await asyncio.gather(*[
                specialist.initialize()
                for specialist in self.specialists.values()
            ])
            
            self._initialized = True
            logger.info("Hybrid orchestrator initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize hybrid orchestrator: {e}")
            raise
    
    async def process_message_stream(
        self,
        request: ChatRequest,
        user_id: Optional[str] = None,
        db: Optional[Any] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process message with full streaming pipeline.
        
        Yields:
            Stream events for frontend (SSE format)
        """
        if not self._initialized:
            await self.initialize()
        
        start_time = datetime.now()
        
        try:
            # 1. Security Guardrails
            yield {
                "type": "security_check",
                "data": {
                    "status": "checking",
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            security_result = await self.security.check_query(request.message)
            
            yield {
                "type": "security_check",
                "data": {
                    "status": "complete",
                    "safe": security_result["safe"],
                    "pii_redacted": len(security_result["checks"]["pii"]["detections"]),
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            if not security_result["safe"]:
                yield {
                    "type": "error",
                    "data": {
                        "error": security_result["blocked_reason"],
                        "timestamp": datetime.now().isoformat()
                    }
                }
                return
            
            # Use sanitized query
            sanitized_query = security_result["sanitized_query"]
            
            # 2. Router Classification
            yield {
                "type": "routing",
                "data": {
                    "status": "classifying",
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            context = {
                "company_id": request.company_id,
                "session_id": request.session_id
            }
            
            # Force specialist if specified in context
            if request.context and "force_specialist" in request.context:
                forced_specialist = request.context["force_specialist"]
                if forced_specialist in self.specialists:
                    router_decision = RouterDecision(
                        specialist=forced_specialist,
                        confidence=1.0,
                        reasoning=f"Forced to {forced_specialist} by user request",
                        detected_entities=[],
                        suggested_tools=[]
                    )
                else:
                    router_decision = await self.router.classify_query(sanitized_query, context)
            else:
                router_decision = await self.router.classify_query(sanitized_query, context)
            
            yield {
                "type": "routing",
                "data": {
                    "specialist": router_decision.specialist,
                    "confidence": router_decision.confidence,
                    "reasoning": router_decision.reasoning,
                    "detected_entities": router_decision.detected_entities,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            # 3. Get specialist
            specialist = self.specialists[router_decision.specialist]
            
            # Set DB session for tools if available
            if db:
                await specialist.set_db_session(db)
            
            # 4. Process with specialist (streams all events)
            accumulated_content = ""
            
            async for event in specialist.process_query(sanitized_query, context):
                # Accumulate content for post-processing
                if event["type"] == "content":
                    accumulated_content += event["data"].get("content", "")
                
                yield event
            
            # 5. Post-process response for PII
            if accumulated_content:
                response_check = await self.security.check_response(accumulated_content)
                
                if response_check["modified"]:
                    logger.warning(f"PII detected in response, redacted {len(response_check['pii_detections'])} items")
                    
                    # Send updated content if PII was found
                    yield {
                        "type": "security_postprocess",
                        "data": {
                            "pii_redacted": len(response_check["pii_detections"]),
                            "timestamp": datetime.now().isoformat()
                        }
                    }
            
            # 6. Final metadata
            total_duration = int((datetime.now() - start_time).total_seconds() * 1000)
            
            yield {
                "type": "metadata",
                "data": {
                    "total_duration_ms": total_duration,
                    "security_checks_passed": True,
                    "router_decision": router_decision.model_dump(),
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Hybrid orchestrator error: {e}", exc_info=True)
            yield {
                "type": "error",
                "data": {
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            }
    
    async def process_message(
        self,
        request: ChatRequest,
        user_id: Optional[str] = None,
        db: Optional[Any] = None
    ) -> ChatResponse:
        """
        Process message without streaming (for backward compatibility).
        
        Returns:
            ChatResponse with complete response
        """
        accumulated_content = ""
        final_metadata = {}
        
        async for event in self.process_message_stream(request, user_id, db):
            if event["type"] == "content":
                accumulated_content += event["data"].get("content", "")
            elif event["type"] == "complete":
                final_metadata = event["data"].get("metadata", {})
            elif event["type"] == "error":
                raise Exception(event["data"]["error"])
        
        import uuid
        
        return ChatResponse(
            message=accumulated_content,
            session_id=request.session_id or str(uuid.uuid4()),
            message_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            metadata=final_metadata
        )
    
    def get_config(self) -> Dict[str, Any]:
        """Get orchestrator configuration for frontend."""
        return {
            "specialists": {
                name: {
                    "description": spec.description,
                    "tools": [t.name for t in spec.tools],
                    "model": spec.model_name
                }
                for name, spec in self.specialists.items()
            },
            "router": {
                "model": getattr(self.settings, "router_model", "openai/gpt-5-nano"),
                "confidence_threshold": self.router.confidence_threshold
            },
            "security": {
                "pii_detection": True,
                "injection_detection": True,
                "content_moderation": self.security.moderator is not None
            }
        }

