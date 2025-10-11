"""
Input sanitization and validation utilities for security.

This module provides protection against:
- HTML/XSS attacks
- SQL injection
- Prompt injection attacks
- Path traversal
- Command injection
- SSRF attacks
- Unicode obfuscation attacks
"""

import html
import ipaddress
import re
import socket
import unicodedata
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from app.exceptions import ValidationError
from app.utils.logging import get_logger
from bleach import clean

logger = get_logger("input_sanitization")


class InputSanitizer:
    """Comprehensive input sanitization utility."""

    # Allowed HTML tags for rich text (very restrictive)
    ALLOWED_HTML_TAGS = [
        'p', 'br', 'strong', 'b', 'em', 'i', 'u', 'ul', 'ol', 'li',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'code'
    ]

    # Allowed HTML attributes (stricter)
    ALLOWED_HTML_ATTRIBUTES = {
        '*': ['class'],
        'a': ['href', 'title'],
        'abbr': ['title'],
        'acronym': ['title'],
    }

    # Forbidden HTML attributes (explicitly blocked)
    FORBIDDEN_ATTRIBUTES = [
        r'on\w+',  # onclick, onload, etc.
        'style', 'srcdoc', 'srcset', 'javascript:', 'vbscript:',
        'data:', 'blob:', 'file:'
    ]

    # Safe URL protocols
    SAFE_PROTOCOLS = ['http', 'https', 'mailto']

    # Prompt injection patterns (enhanced)
    PROMPT_INJECTION_PATTERNS = [
        # Direct instruction attempts
        r'(?i)ignore\s+(?:previous|above|prior|all)\s+(?:instructions?|commands?|prompts?|rules?)',
        r'(?i)forget\s+(?:previous|above|prior|all)\s+(?:instructions?|commands?|prompts?|rules?)',
        r'(?i)disregard\s+(?:previous|above|prior|all)\s+(?:instructions?|commands?|prompts?|rules?)',
        r'(?i)override\s+(?:previous|above|prior|all)\s+(?:instructions?|commands?|prompts?|rules?)',

        # Role/system attempts
        r'(?i)you\s+are\s+now\s+(?:a|an)\s+(?:different|new|helpful|harmful)',
        r'(?i)act\s+as\s+(?:a|an)\s+(?:different|new|jailbroken|unrestricted)',
        r'(?i)pretend\s+(?:you\s+are|to\s+be)\s+(?:a|an)',
        r'(?i)system:?\s*(?:role|prompt|message)',
        r'(?i)assistant:?\s*(?:role|prompt|message)',
        r'(?i)(?:become|transform\s+into)\s+(?:a|an)',

        # Instruction overrides
        r'(?i)new\s+(?:instructions?|commands?|rules?|system)',
        r'(?i)instead\s+of\s+(?:following|doing|obeying)',
        r'(?i)replace\s+(?:instructions?|commands?|rules?)',
        r'(?i)update\s+(?:instructions?|commands?|rules?)',

        # Jailbreak attempts
        r'(?i)jailbreak(?:ing)?',
        r'(?i)dan\s+mode',
        r'(?i)developer\s+mode',
        r'(?i)god\s+mode',
        r'(?i)unrestricted\s+mode',
        r'(?i)admin\s+mode',

        # Code execution attempts
        r'(?i)execute\s+(?:python|javascript|bash|shell|cmd|code)',
        r'(?i)run\s+(?:code|script|command|program)',
        r'```(?:python|javascript|bash|shell|cmd|powershell)',
        r'(?i)eval\s*\(',
        r'(?i)exec\s*\(',

        # System access attempts
        r'(?i)access\s+(?:system|database|files?|memory)',
        r'(?i)show\s+(?:system|config|env|environment|secrets?)',
        r'(?i)reveal\s+(?:system|config|secrets?|password)',
        r'(?i)dump\s+(?:database|config|memory)',

        # Manipulation tactics
        r'(?i)this\s+is\s+(?:urgent|critical|emergency|important)',
        r'(?i)the\s+user\s+(?:said|told|asked|commanded)\s+you\s+to',
        r'(?i)(?:ignore|bypass|disable|turn\s+off)\s+(?:safety|security|filters?)',
        r'(?i)for\s+(?:testing|research|educational)\s+purposes?',

        # Prompt leaking attempts
        r'(?i)what\s+(?:are\s+your|is\s+your)\s+(?:instructions?|system\s+prompt)',
        r'(?i)show\s+me\s+your\s+(?:instructions?|prompt|system)',
        r'(?i)repeat\s+(?:your|the)\s+(?:instructions?|prompt|system)',
    ]

    # High-risk imperative verbs for contextual detection
    IMPERATIVE_VERBS = [
        'ignore', 'forget', 'disregard', 'override', 'bypass', 'disable',
        'execute', 'run', 'eval', 'exec', 'access', 'show', 'reveal',
        'dump', 'become', 'act', 'pretend', 'replace', 'update'
    ]

    # Instruction/command target nouns
    TARGET_NOUNS = [
        'instructions', 'commands', 'prompts', 'rules', 'system', 'safety',
        'security', 'filters', 'restrictions', 'limitations'
    ]

    # Dangerous file extensions (expanded)
    DANGEROUS_EXTENSIONS = {
        'exe', 'bat', 'cmd', 'com', 'pif', 'scr', 'vbs', 'js', 'jar',
        'dll', 'msi', 'bin', 'sh', 'ps1', 'py', 'php', 'asp', 'aspx',
        'jsp', 'jspx', 'cgi', 'pl', 'rb', 'go', 'rs', 'swift'
    }

    # Reserved Windows device names
    RESERVED_NAMES = {
        'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4',
        'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2',
        'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }

    # Risk thresholds
    RISK_THRESHOLDS = {
        'low': 0.3,
        'medium': 0.5,
        'high': 0.8,
        'critical': 1.0
    }

    def __init__(self):
        self.injection_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.PROMPT_INJECTION_PATTERNS]
        self.imperative_pattern = re.compile(r'\b(' + '|'.join(self.IMPERATIVE_VERBS) + r')\b', re.IGNORECASE)
        self.target_pattern = re.compile(r'\b(' + '|'.join(self.TARGET_NOUNS) + r')\b', re.IGNORECASE)
        self.forbidden_attr_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.FORBIDDEN_ATTRIBUTES]

    def normalize_text(self, text: str) -> str:
        """
        Normalize text to prevent unicode obfuscation attacks.

        Args:
            text: Raw input text

        Returns:
            Normalized text with obfuscation removed
        """
        if not text:
            return ""

        # Normalize to NFC form (canonical decomposition, then canonical composition)
        text = unicodedata.normalize("NFC", text)

        # Remove zero-width spaces and similar invisible characters
        text = re.sub(r'[\u200B-\u200D\uFEFF\u2060\u180E]', '', text)

        # Remove other problematic unicode categories
        # Cf = Format characters, Cn = Unassigned characters
        text = ''.join(char for char in text if unicodedata.category(char) not in ['Cf', 'Cn'])

        # Normalize multiple whitespace to single space
        text = re.sub(r'\s+', ' ', text)

        return text.strip()

    def _calculate_instruction_density(self, text: str) -> float:
        """Calculate density of imperative instructions in text."""
        if not text:
            return 0.0

        words = text.lower().split()
        if len(words) < 3:
            return 0.0

        imperative_count = len(self.imperative_pattern.findall(text))
        target_count = len(self.target_pattern.findall(text))

        # Weight imperatives followed by targets higher
        combined_score = (imperative_count * 2 + target_count) / len(words)
        return min(combined_score, 1.0)

    def _get_risk_level(self, score: float) -> str:
        """Convert risk score to categorical level."""
        if score >= self.RISK_THRESHOLDS['critical']:
            return 'critical'
        elif score >= self.RISK_THRESHOLDS['high']:
            return 'high'
        elif score >= self.RISK_THRESHOLDS['medium']:
            return 'medium'
        elif score >= self.RISK_THRESHOLDS['low']:
            return 'low'
        else:
            return 'minimal'

    def _filter_href(self, name: str, value: str) -> Optional[str]:
        """Filter href attributes to safe protocols only."""
        if name == 'href' and value:
            # Check if URL starts with safe protocol
            if not any(value.lower().startswith(protocol + '://') or value.lower().startswith(protocol + ':')
                      for protocol in self.SAFE_PROTOCOLS):
                return None
        return value

    def _is_safe_netloc(self, netloc: str) -> bool:
        """Check if network location is safe (not internal/private)."""
        try:
            # Extract hostname (remove port)
            hostname = netloc.split(':')[0]

            # Try to resolve to IP
            ip = socket.gethostbyname(hostname)
            ip_obj = ipaddress.ip_address(ip)

            # Block private, loopback, multicast, and reserved addresses
            return not (
                ip_obj.is_private or
                ip_obj.is_loopback or
                ip_obj.is_multicast or
                ip_obj.is_reserved or
                ip_obj.is_link_local
            )
        except Exception:
            # If we can't resolve, err on the side of caution
            return False

    def sanitize_html(self, text: str, strip_tags: bool = True) -> str:
        """
        Sanitize HTML content to prevent XSS attacks.

        Args:
            text: Raw HTML/text input
            strip_tags: If True, remove all HTML tags; if False, allow safe tags

        Returns:
            Sanitized text
        """
        if not text:
            return ""

        if strip_tags:
            # Remove all HTML tags and decode entities
            return html.unescape(clean(text, tags=[], strip=True))
        else:
            # First pass - allow only safe HTML tags and attributes
            cleaned = clean(
                text,
                tags=self.ALLOWED_HTML_TAGS,
                attributes=self.ALLOWED_HTML_ATTRIBUTES,
                protocols=self.SAFE_PROTOCOLS,
                strip=True
            )

            # Second pass - remove any forbidden attributes that might have slipped through
            for pattern in self.forbidden_attr_patterns:
                cleaned = pattern.sub('', cleaned)

            return cleaned

    def detect_prompt_injection(self, text: str) -> Dict[str, Any]:
        """
        Detect potential prompt injection attempts with enhanced heuristics.

        Args:
            text: User input to analyze

        Returns:
            Dict with detection results and details
        """
        if not text:
            return {
                "is_injection": False,
                "patterns": [],
                "risk_score": 0.0,
                "risk_level": "minimal"
            }

        # Normalize text first to prevent obfuscation
        normalized_text = self.normalize_text(text)

        detected_patterns = []
        risk_score = 0.0

        # Check against known injection patterns
        for pattern in self.injection_patterns:
            matches = pattern.findall(normalized_text)
            if matches:
                detected_patterns.append({
                    "pattern": pattern.pattern,
                    "matches": matches[:3],  # Limit matches in logs
                    "severity": "high",
                    "type": "pattern_match"
                })
                risk_score += 0.8

        # Check for suspicious patterns
        suspicious_indicators = [
            (r'(?i)```[\w]*\n', "code_block", 0.3),
            (r'(?i)\b(?:sudo|rm|del|format|chmod|kill)\b', "system_commands", 0.6),
            (r'(?i)<!--[\s\S]*?-->', "html_comments", 0.2),
            (r'(?i)<script[\s\S]*?</script>', "script_tags", 0.9),
            (r'(?i)eval\s*\(', "eval_function", 0.7),
            (r'(?i)document\.cookie', "cookie_access", 0.8),
            (r'(?i)window\.location', "location_manipulation", 0.7),
            (r'(?i)\\x[0-9a-f]{2}', "hex_encoding", 0.4),
            (r'(?i)%[0-9a-f]{2}', "url_encoding", 0.3),
        ]

        for pattern, name, score in suspicious_indicators:
            if re.search(pattern, normalized_text):
                detected_patterns.append({
                    "pattern": pattern,
                    "name": name,
                    "severity": "medium" if score < 0.5 else "high",
                    "type": "suspicious_indicator"
                })
                risk_score += score

        # Calculate instruction density
        instruction_density = self._calculate_instruction_density(normalized_text)
        if instruction_density > 0.2:
            detected_patterns.append({
                "name": "high_instruction_density",
                "severity": "medium" if instruction_density < 0.4 else "high",
                "type": "contextual_analysis",
                "density": instruction_density
            })
            risk_score += instruction_density * 0.6

        # Check for excessive length (could indicate flooding/confusion attempts)
        if len(normalized_text) > 2000:
            long_text_risk = min(len(normalized_text) / 10000, 0.3)
            detected_patterns.append({
                "name": "excessive_length",
                "severity": "low",
                "type": "length_analysis",
                "length": len(normalized_text)
            })
            risk_score += long_text_risk

        # Check for repetitive patterns (could indicate confusion attempts)
        words = normalized_text.lower().split()
        if len(words) > 10:
            unique_words = len(set(words))
            repetition_ratio = 1 - (unique_words / len(words))
            if repetition_ratio > 0.7:
                detected_patterns.append({
                    "name": "high_repetition",
                    "severity": "medium",
                    "type": "repetition_analysis",
                    "ratio": repetition_ratio
                })
                risk_score += repetition_ratio * 0.4

        # Normalize risk score (0-1)
        risk_score = min(risk_score, 1.0)
        risk_level = self._get_risk_level(risk_score)

        # Determine if injection based on risk level
        is_injection = risk_level in ['high', 'critical'] or any(
            p["severity"] == "high" for p in detected_patterns
        )

        # Redact sensitive parts for logging
        redacted_text = self._redact_sensitive_content(text)

        if is_injection:
            logger.warning(
                f"Potential prompt injection detected - Risk: {risk_level} ({risk_score:.2f}), "
                f"Patterns: {len(detected_patterns)}, Text: {redacted_text[:100]}..."
            )
        elif risk_level in ['medium', 'low']:
            logger.info(
                f"Suspicious content detected - Risk: {risk_level} ({risk_score:.2f}), "
                f"Patterns: {len(detected_patterns)}"
            )

        return {
            "is_injection": is_injection,
            "patterns": detected_patterns,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "text_length": len(text),
            "normalized_length": len(normalized_text),
            "instruction_density": instruction_density
        }

    def _redact_sensitive_content(self, text: str) -> str:
        """Redact potentially sensitive content from logs."""
        if not text:
            return ""

        # Replace potential injection patterns with [REDACTED]
        redacted = text
        for pattern in self.injection_patterns:
            redacted = pattern.sub('[REDACTED]', redacted)

        return redacted

    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename to prevent path traversal and dangerous files.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        if not filename:
            return "unnamed_file"

        # Normalize first to handle unicode tricks
        filename = self.normalize_text(filename)

        # Remove path components
        filename = filename.split('/')[-1].split('\\')[-1]

        # Convert to ASCII-only (helps prevent exotic unicode attacks)
        filename = filename.encode("ascii", "ignore").decode()

        # Remove dangerous characters (expanded set)
        filename = re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f-\x9f]', '', filename)

        # Remove dots at start/end (can cause issues on some systems)
        filename = filename.strip('.')

        if not filename:
            return "sanitized_file"

        # Check for Windows reserved device names
        name_part = filename.split('.')[0].upper()
        if name_part in self.RESERVED_NAMES:
            filename = f"safe_{filename}"

        # Check extension for dangerous types
        if '.' in filename:
            ext = filename.split('.')[-1].lower()
            if ext in self.DANGEROUS_EXTENSIONS:
                filename = filename + '_safe'

        # Limit length (accounting for filesystem limits)
        if len(filename) > 255:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            max_name_length = 250 - len(ext) - 1 if ext else 250
            filename = name[:max_name_length] + ('.' + ext if ext else '')

        return filename or "sanitized_file"

    def sanitize_url(self, url: str) -> Optional[str]:
        """
        Sanitize and validate URL with SSRF protection.

        Args:
            url: URL to sanitize

        Returns:
            Sanitized URL or None if invalid/dangerous
        """
        if not url:
            return None

        try:
            # Normalize and strip whitespace
            url = self.normalize_text(url.strip())

            parsed = urlparse(url)

            # Only allow safe protocols
            if parsed.scheme not in self.SAFE_PROTOCOLS:
                logger.warning(f"Blocked unsafe URL scheme: {parsed.scheme}")
                return None

            # Skip SSRF check for mailto (no network request)
            if parsed.scheme != 'mailto':
                # Check for SSRF attempts (internal/private IPs)
                if not self._is_safe_netloc(parsed.netloc):
                    logger.warning(f"Blocked potentially unsafe netloc: {parsed.netloc}")
                    return None

            # Reconstruct clean URL (strip query and fragment to remove potential payloads)
            if parsed.scheme == 'mailto':
                # For mailto, preserve the path (email address) but strip query/fragment
                return f"{parsed.scheme}:{parsed.path}"
            else:
                return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

        except Exception as e:
            logger.warning(f"URL parsing failed: {e}")
            return None

    def validate_and_sanitize_input(
        self,
        text: str,
        max_length: int = 10000,
        allow_html: bool = False,
        check_injection: bool = True
    ) -> Dict[str, Any]:
        """
        Comprehensive input validation and sanitization with layered approach.

        Args:
            text: Input text to validate
            max_length: Maximum allowed length
            allow_html: Whether to allow safe HTML tags
            check_injection: Whether to check for prompt injection

        Returns:
            Dict with sanitized text and validation results
        """
        if not text:
            return {
                "sanitized": "",
                "is_valid": True,
                "warnings": [],
                "injection_check": None,
                "risk_level": "minimal"
            }

        original_text = text
        warnings = []

        # Layer 1: Normalize text (prevent unicode obfuscation)
        text = self.normalize_text(text)
        if text != original_text:
            warnings.append("Text normalized to prevent obfuscation")

        # Layer 2: Length enforcement
        if len(text) > max_length:
            warnings.append(f"Text truncated from {len(text)} to {max_length} characters")
            text = text[:max_length]

        # Layer 3: Prompt injection detection (before HTML sanitization to catch more)
        injection_result = None
        if check_injection:
            injection_result = self.detect_prompt_injection(text)
            if injection_result["is_injection"]:
                severity = injection_result["risk_level"]
                warnings.append(f"Prompt injection detected ({severity}, risk: {injection_result['risk_score']:.2f})")

        # Layer 4: HTML sanitization
        sanitized = self.sanitize_html(text, strip_tags=not allow_html)

        # Layer 5: Final validation
        is_valid = not (injection_result and injection_result["is_injection"])
        risk_level = injection_result["risk_level"] if injection_result else "minimal"

        # Enhanced logging based on severity
        if warnings:
            if risk_level in ['high', 'critical']:
                logger.warning(f"High-risk input processed: {warnings}")
            elif risk_level in ['medium']:
                logger.info(f"Medium-risk input processed: {warnings}")

        return {
            "sanitized": sanitized,
            "is_valid": is_valid,
            "warnings": warnings,
            "injection_check": injection_result,
            "risk_level": risk_level,
            "original_length": len(original_text),
            "normalized_length": len(text),
            "sanitized_length": len(sanitized),
            "normalization_applied": text != original_text
        }


# Global sanitizer instance
input_sanitizer = InputSanitizer()


def sanitize_chat_message(message: str) -> Dict[str, Any]:
    """
    Sanitize chat message with strict prompt injection checking.

    Args:
        message: Chat message from user

    Returns:
        Sanitization results with cleaned message
    """
    return input_sanitizer.validate_and_sanitize_input(
        text=message,
        max_length=5000,  # Reasonable chat message limit
        allow_html=False,  # No HTML in chat messages
        check_injection=True  # Always check for prompt injection
    )


def sanitize_user_input(
    text: str,
    field_name: str = "input",
    allow_html: bool = False
) -> str:
    """
    Quick sanitization function for user inputs with enhanced error reporting.

    Args:
        text: Input text
        field_name: Field name for error reporting
        allow_html: Whether to allow safe HTML

    Returns:
        Sanitized text

    Raises:
        ValidationError: If input contains dangerous content
    """
    result = input_sanitizer.validate_and_sanitize_input(
        text=text,
        allow_html=allow_html,
        check_injection=True
    )

    if not result["is_valid"]:
        injection = result["injection_check"]
        risk_level = result["risk_level"]

        # Enhanced error context
        context = {
            "risk_level": risk_level,
            "risk_score": injection["risk_score"] if injection else 0,
            "patterns_detected": len(injection["patterns"]) if injection else 0,
            "field": field_name
        }

        # Add instruction density if available
        if injection and "instruction_density" in injection:
            context["instruction_density"] = injection["instruction_density"]

        raise ValidationError(
            message=f"Potentially dangerous content detected in {field_name} (risk: {risk_level})",
            field=field_name,
            context=context
        )

    if result["warnings"]:
        # Log warnings with appropriate severity
        risk_level = result["risk_level"]
        if risk_level in ['high', 'critical']:
            logger.warning(f"Input sanitization warnings for {field_name}: {result['warnings']}")
        else:
            logger.info(f"Input sanitization warnings for {field_name}: {result['warnings']}")

    return result["sanitized"]


# Additional helper functions for common use cases

def sanitize_search_query(query: str) -> str:
    """Sanitize search queries with moderate restrictions."""
    return input_sanitizer.validate_and_sanitize_input(
        text=query,
        max_length=500,
        allow_html=False,
        check_injection=True
    )["sanitized"]


def sanitize_display_name(name: str) -> str:
    """Sanitize user display names."""
    result = input_sanitizer.validate_and_sanitize_input(
        text=name,
        max_length=100,
        allow_html=False,
        check_injection=False  # Display names don't need injection checking
    )
    return result["sanitized"]


def validate_file_upload_name(filename: str) -> str:
    """Validate and sanitize uploaded file names."""
    return input_sanitizer.sanitize_filename(filename)


def validate_external_url(url: str) -> Optional[str]:
    """Validate external URLs with SSRF protection."""
    return input_sanitizer.sanitize_url(url)
