"""
Fake Orchestrator Service for Testing
Simulates multi-agent execution with fake steps and streaming
"""
import asyncio
import random
import uuid
from datetime import datetime
from typing import AsyncGenerator, Dict, List, Any, Optional

from app.utils.logging import get_logger

logger = get_logger(__name__)


class FakeOrchestratorService:
    """
    Fake orchestrator that simulates multi-agent workflow
    with realistic step generation and streaming
    """
    
    # Fake agents that will "run"
    FAKE_AGENTS = [
        "query-planner",
        "research-agent", 
        "data-analyzer",
        "response-writer"
    ]
    
    # Fake responses for different query types
    FAKE_RESPONSES = {
        "default": """Based on my analysis, here are the key insights:

## Overview
I've analyzed the information and identified several important patterns that address your question.

## Key Findings

### Primary Insights
- The data shows a clear trend towards improved performance metrics
- User engagement has increased by approximately 25% over the analyzed period
- Several key factors contribute to these positive outcomes

### Secondary Observations
- Market conditions remain favorable for continued growth
- Competitive positioning has strengthened in recent months
- Strategic initiatives are showing measurable impact

## Recommendations

1. **Continue Current Strategy**: The data supports maintaining the current approach with minor optimizations
2. **Monitor Key Metrics**: Keep tracking the core performance indicators that showed improvement
3. **Adapt as Needed**: Stay flexible to adjust based on market changes

## Conclusion
The analysis indicates positive momentum with strong indicators for future success. The multi-faceted approach appears to be working well.""",
        
        "competitors": """# Competitor Analysis

## Top Competitors Mentioned

Based on the review analysis, here are the most frequently mentioned competitors:

### 1. **Competitor A** (45% mention rate)
- Strengths: User interface, pricing flexibility
- Weaknesses: Limited integrations, slower support
- Market position: Strong in mid-market segment

### 2. **Competitor B** (32% mention rate)
- Strengths: Enterprise features, robust API
- Weaknesses: Higher cost, steeper learning curve
- Market position: Dominant in enterprise space

### 3. **Competitor C** (18% mention rate)
- Strengths: Ease of use, quick setup
- Weaknesses: Limited advanced features
- Market position: Growing in SMB market

## Competitive Gaps

**Features customers want:**
- Better mobile experience
- More automation capabilities
- Improved reporting dashboards
- Faster customer support response

## Strategic Recommendations

1. Focus on automation features to differentiate
2. Enhance mobile experience (mentioned in 60% of comparisons)
3. Competitive pricing for mid-market segment
4. Invest in integration ecosystem""",
        
        "product_gaps": """# Product Gap Analysis

## Critical Missing Features

### High Priority Gaps
1. **Advanced Reporting** (mentioned in 34% of reviews)
   - Custom dashboard creation
   - Scheduled report exports
   - Real-time data visualization
   
2. **Mobile Experience** (mentioned in 28% of reviews)
   - Native mobile app lacking features
   - Inconsistent UX across devices
   - Limited offline capabilities

3. **Integration Ecosystem** (mentioned in 25% of reviews)
   - Missing key third-party integrations
   - API limitations for custom builds
   - Webhook functionality gaps

### Performance Issues
- Page load times on large datasets (18% of reviews)
- Search functionality needs improvement (15% of reviews)
- Bulk operations timeout issues (12% of reviews)

## User Experience Gaps

**Onboarding:**
- Complex initial setup process
- Insufficient documentation for advanced features
- Lack of interactive tutorials

**Support:**
- Response time averaging 24+ hours
- Limited self-service resources
- Missing video tutorials

## Recommendations

1. Prioritize advanced reporting capabilities
2. Invest in mobile app development
3. Expand integration marketplace
4. Improve onboarding experience
5. Enhance support resources"""
    }
    
    async def process_message_stream(
        self,
        request,  # ChatRequest object
        user_id: Optional[str] = None,
        db: Optional[Any] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Simulate multi-agent orchestration with streaming
        
        Args:
            request: ChatRequest object with message and session_id
            user_id: User ID (optional)
            db: Database session (optional, not used in fake)
            
        Yields:
            Stream events with agent steps and final response
        """
        # Extract message and session from request
        message = request.message
        session_id = request.session_id or "fake-session"
        
        logger.info(f"[FAKE ORCHESTRATOR] Starting fake workflow for message: {message[:50]}...")
        
        # Track completed steps for final metadata
        completed_steps = []
        step_counter = 0
        
        # Initial status
        yield {
            "type": "status",
            "data": {"status": "initializing", "message": "Initializing agent pipeline..."}
        }
        
        await asyncio.sleep(0.5)
        
        # Determine response type based on message content
        response_type = "default"
        if "competitor" in message.lower():
            response_type = "competitors"
        elif "gap" in message.lower() or "missing" in message.lower() or "feature" in message.lower():
            response_type = "product_gaps"
        
        # Simulate each agent running
        for agent_name in self.FAKE_AGENTS:
            step_id = str(uuid.uuid4())
            
            # Emit agent step start
            yield {
                "type": "agent_step_start",
                "data": {
                    "agent_name": agent_name,
                    "step_id": step_id,
                    "step_order": step_counter,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            # Simulate agent thinking time
            thinking_time = random.uniform(1.0, 2.5)
            await asyncio.sleep(thinking_time)
            
            # Generate fake step content
            is_structured = random.choice([True, False])
            
            if is_structured:
                # Structured output (BaseModel-like)
                step_content = {
                    "agent": agent_name,
                    "analysis": f"Completed analysis by {agent_name}",
                    "confidence": round(random.uniform(0.75, 0.95), 2),
                    "insights": [
                        f"Insight {i+1} from {agent_name}" 
                        for i in range(random.randint(2, 4))
                    ],
                    "metadata": {
                        "processing_time_ms": int(thinking_time * 1000),
                        "data_points_analyzed": random.randint(50, 200)
                    }
                }
            else:
                # Unstructured text output
                step_content = f"""Agent {agent_name} completed its analysis.

Key findings:
- Processed user query: "{message[:50]}..."
- Identified {random.randint(3, 8)} relevant data points
- Confidence score: {random.randint(75, 95)}%
- Processing completed in {int(thinking_time * 1000)}ms

Ready for next step in pipeline."""
            
            # Store completed step info
            completed_steps.append({
                'agent_name': agent_name,
                'content': step_content,
                'is_structured': is_structured,
                'step_order': step_counter
            })
            
            # Emit agent step complete
            yield {
                "type": "agent_step_complete",
                "data": {
                    "step_id": step_id,
                    "agent_name": agent_name,
                    "content": step_content,
                    "is_structured": is_structured,
                    "step_order": step_counter
                }
            }
            
            step_counter += 1
            
            # Small delay between agents
            await asyncio.sleep(0.3)
        
        # Stream final response
        yield {
            "type": "status",
            "data": {"status": "generating_response", "message": "Generating final response..."}
        }
        
        await asyncio.sleep(0.5)
        
        # Get appropriate fake response
        final_response = self.FAKE_RESPONSES[response_type]
        
        # Stream the response in chunks (simulate streaming)
        chunk_size = 50
        for i in range(0, len(final_response), chunk_size):
            chunk = final_response[i:i + chunk_size]
            yield {
                "type": "content",
                "data": {"content": chunk}
            }
            await asyncio.sleep(0.05)  # Small delay for realistic streaming
        
        # Complete
        yield {
            "type": "complete",
            "data": {
                "message": final_response,
                "message_id": str(uuid.uuid4()),
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": {
                    "completed_steps": completed_steps,
                    "total_agents": len(self.FAKE_AGENTS),
                    "total_processing_time_ms": int(sum([
                        random.uniform(1000, 2500) for _ in self.FAKE_AGENTS
                    ])),
                    "mode": "fake_orchestrator"
                }
            }
        }
        
        logger.info(f"[FAKE ORCHESTRATOR] Completed workflow with {len(completed_steps)} steps")

