"""
Security Guardrails Service - Protects against PII, prompt injection, and harmful content.

Runs before the router to ensure safe query processing.
"""

import re
import httpx
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger("security_guardrails")


class PIIDetector:
    """Detects and redacts Personally Identifiable Information."""
    
    # Regex patterns for common PII
    PATTERNS = {
        "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "phone": r'\b(\+\d{1,3}[-.]?)?\(?\d{3}\)?[-.]?\d{3}[-.]?\d{4}\b',
        "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
        "credit_card": r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
        "ip_address": r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
        "api_key": r'\b[A-Za-z0-9]{32,}\b',  # Generic API key pattern
        "address": r'\b\d+\s+[A-Za-z\s]+\s+(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr)\b',
    }
    
    def __init__(self):
        self.compiled_patterns = {
            name: re.compile(pattern, re.IGNORECASE)
            for name, pattern in self.PATTERNS.items()
        }
    
    def detect(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect PII in text.
        
        Returns:
            List of detected PII with type, value, and position
        """
        detections = []
        
        for pii_type, pattern in self.compiled_patterns.items():
            for match in pattern.finditer(text):
                detections.append({
                    "type": pii_type,
                    "value": match.group(),
                    "start": match.start(),
                    "end": match.end()
                })
        
        return detections
    
    def redact(self, text: str, detections: Optional[List[Dict[str, Any]]] = None) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Redact PII from text.
        
        Args:
            text: Original text
            detections: Optional pre-computed detections
            
        Returns:
            Tuple of (redacted_text, detections)
        """
        if detections is None:
            detections = self.detect(text)
        
        if not detections:
            return text, []
        
        # Sort by position (reverse order to maintain indices)
        sorted_detections = sorted(detections, key=lambda x: x["start"], reverse=True)
        
        redacted_text = text
        for detection in sorted_detections:
            pii_type = detection["type"]
            start = detection["start"]
            end = detection["end"]
            
            # Replace with redaction marker
            replacement = f"[REDACTED_{pii_type.upper()}]"
            redacted_text = redacted_text[:start] + replacement + redacted_text[end:]
        
        return redacted_text, detections


class PromptInjectionDetector:
    """Detects potential prompt injection attacks."""
    
    # Suspicious patterns that might indicate injection
    SUSPICIOUS_PATTERNS = [
        r'ignore\s+(previous|above|all)\s+(instructions|rules|prompts)',
        r'forget\s+(everything|all|previous)',
        r'you\s+are\s+now\s+a',
        r'new\s+(instructions|rules|system)',
        r'disregard\s+(previous|above|all)',
        r'override\s+(instructions|rules|system)',
        r'</?\s*(system|prompt|instruction)\s*>',
        r'<\|im_start\|>',
        r'<\|im_end\|>',
        r'\[INST\]',
        r'\[/INST\]',
        r'###\s*System:',
        r'###\s*Instruction:',
    ]
    
    # High-risk keywords
    HIGH_RISK_KEYWORDS = [
        'jailbreak', 'dan mode', 'developer mode',
        'sudo', 'admin mode', 'god mode',
        'bypass', 'exploit', 'override'
    ]
    
    def __init__(self):
        self.compiled_patterns = [
            re.compile(pattern, re.IGNORECASE) 
            for pattern in self.SUSPICIOUS_PATTERNS
        ]
    
    def detect(self, text: str) -> Dict[str, Any]:
        """
        Detect potential prompt injection.
        
        Returns:
            Dict with is_suspicious, confidence, and detected_patterns
        """
        detected_patterns = []
        
        # Check regex patterns
        for pattern in self.compiled_patterns:
            matches = pattern.finditer(text)
            for match in matches:
                detected_patterns.append({
                    "pattern": match.group(),
                    "type": "regex",
                    "position": match.start()
                })
        
        # Check high-risk keywords
        lower_text = text.lower()
        for keyword in self.HIGH_RISK_KEYWORDS:
            if keyword in lower_text:
                detected_patterns.append({
                    "pattern": keyword,
                    "type": "keyword",
                    "position": lower_text.index(keyword)
                })
        
        # Calculate confidence
        confidence = min(len(detected_patterns) * 0.2, 1.0)
        is_suspicious = len(detected_patterns) > 0
        
        return {
            "is_suspicious": is_suspicious,
            "confidence": confidence,
            "detected_patterns": detected_patterns,
            "pattern_count": len(detected_patterns)
        }


class ContentModerator:
    """Uses OpenAI Moderation API to detect harmful content."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.openai.com/v1/moderations"
    
    async def moderate(self, text: str) -> Dict[str, Any]:
        """
        Moderate content using OpenAI API.
        
        Returns:
            Dict with flagged, categories, and category_scores
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.api_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "input": text
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"OpenAI moderation API error: {response.status_code}")
                    return {
                        "flagged": False,
                        "error": f"API error: {response.status_code}",
                        "available": False
                    }
                
                data = response.json()
                result = data["results"][0]
                
                return {
                    "flagged": result["flagged"],
                    "categories": result["categories"],
                    "category_scores": result["category_scores"],
                    "available": True
                }
                
        except httpx.TimeoutException:
            logger.error("OpenAI moderation API timeout")
            return {
                "flagged": False,
                "error": "API timeout",
                "available": False
            }
        except Exception as e:
            logger.error(f"Content moderation failed: {e}")
            return {
                "flagged": False,
                "error": str(e),
                "available": False
            }


class SecurityGuardrailsService:
    """
    Comprehensive security guardrails for chat inputs.
    
    Protects against:
    - PII leakage
    - Prompt injection attacks
    - Harmful content
    """
    
    def __init__(self, settings: Any = None):
        self.settings = settings or get_settings()
        self.pii_detector = PIIDetector()
        self.injection_detector = PromptInjectionDetector()
        
        # Initialize content moderator if OpenAI key available
        openai_key = self.settings.get_secret("openai_api_key")
        self.moderator = ContentModerator(str(openai_key)) if openai_key else None
        
        # Configuration
        self.block_on_pii = False  # Redact instead of block
        self.block_on_injection = True  # Block suspicious prompts
        self.block_on_moderation = True  # Block harmful content
        self.injection_confidence_threshold = 0.4
    
    async def check_query(self, query: str) -> Dict[str, Any]:
        """
        Run all security checks on a query.
        
        Returns:
            Dict with:
            - safe: bool - Whether query passed all checks
            - sanitized_query: str - Cleaned query (PII redacted)
            - checks: Dict - Results from each check
            - blocked_reason: Optional[str] - Why it was blocked
        """
        start_time = datetime.now()
        
        # 1. PII Detection & Redaction
        sanitized_query, pii_detections = self.pii_detector.redact(query)
        
        pii_check = {
            "passed": True,  # We redact instead of blocking
            "detections": pii_detections,
            "count": len(pii_detections),
            "types": list(set(d["type"] for d in pii_detections))
        }
        
        # 2. Prompt Injection Detection
        injection_check = self.injection_detector.detect(sanitized_query)
        injection_blocked = (
            injection_check["is_suspicious"] and 
            injection_check["confidence"] >= self.injection_confidence_threshold
        )
        
        # 3. Content Moderation
        moderation_check = {"available": False, "flagged": False}
        if self.moderator:
            moderation_check = await self.moderator.moderate(sanitized_query)
        
        moderation_blocked = (
            moderation_check.get("flagged", False) and 
            self.block_on_moderation
        )
        
        # Determine if safe
        safe = not (injection_blocked or moderation_blocked)
        
        # Determine block reason
        blocked_reason = None
        if injection_blocked:
            blocked_reason = "Potential prompt injection detected"
        elif moderation_blocked:
            flagged_categories = [
                cat for cat, flagged in moderation_check.get("categories", {}).items()
                if flagged
            ]
            blocked_reason = f"Content policy violation: {', '.join(flagged_categories)}"
        
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        result = {
            "safe": safe,
            "sanitized_query": sanitized_query,
            "original_query": query,
            "blocked_reason": blocked_reason,
            "checks": {
                "pii": pii_check,
                "injection": injection_check,
                "moderation": moderation_check
            },
            "metadata": {
                "duration_ms": duration_ms,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        # Log security events
        if not safe:
            logger.warning(f"Query blocked: {blocked_reason}", extra={
                "query_preview": query[:100],
                "checks": result["checks"]
            })
        elif pii_detections:
            logger.info(f"PII redacted: {len(pii_detections)} items", extra={
                "pii_types": pii_check["types"]
            })
        
        return result
    
    async def check_response(self, response: str) -> Dict[str, Any]:
        """
        Check agent response for PII leakage.
        
        Returns:
            Dict with sanitized_response and detections
        """
        sanitized_response, pii_detections = self.pii_detector.redact(response)
        
        if pii_detections:
            logger.warning(f"PII detected in response: {len(pii_detections)} items", extra={
                "pii_types": list(set(d["type"] for d in pii_detections))
            })
        
        return {
            "sanitized_response": sanitized_response,
            "original_response": response,
            "pii_detections": pii_detections,
            "modified": len(pii_detections) > 0
        }

