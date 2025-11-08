"""
MCP API Tool - Call external APIs via Model Context Protocol or direct HTTP.
"""

import httpx
from typing import Any, Dict, Optional
from urllib.parse import urljoin

from app.agents.tools.base_tool import BaseTool, ToolResult
from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger("mcp_api_tool")


class MCPAPITool(BaseTool):
    """
    Call external APIs for specialized data.
    
    Supports REST API calls with authentication and rate limiting.
    """
    
    def __init__(self):
        super().__init__()
        self.settings = get_settings()
        self.timeout = 30.0
        self.max_retries = 3
    
    @property
    def name(self) -> str:
        return "mcp_api_call"
    
    @property
    def description(self) -> str:
        return """Call external APIs for specialized data and integrations.

Use this tool when:
- Need data from external services not in our database
- Want to integrate with third-party APIs
- Need specialized information from configured API endpoints

Parameters:
- api_name: Name of the configured API (e.g., "stripe", "github", "slack")
- endpoint: API endpoint path (e.g., "/users", "/repos")
- method: HTTP method (GET, POST, PUT, DELETE)
- params: Query parameters as dict
- body: Request body as dict (for POST/PUT)
- headers: Additional headers as dict

Configured APIs must be set up in settings.
Returns the API response data.
"""
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "api_name": {
                    "type": "string",
                    "description": "Name of the configured API"
                },
                "endpoint": {
                    "type": "string",
                    "description": "API endpoint path"
                },
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST", "PUT", "DELETE"],
                    "default": "GET",
                    "description": "HTTP method"
                },
                "params": {
                    "type": "object",
                    "description": "Query parameters"
                },
                "body": {
                    "type": "object",
                    "description": "Request body (for POST/PUT)"
                },
                "headers": {
                    "type": "object",
                    "description": "Additional headers"
                }
            },
            "required": ["api_name", "endpoint"]
        }
    
    async def execute(
        self,
        api_name: str,
        endpoint: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> ToolResult:
        """
        Call external API.
        
        Args:
            api_name: Name of configured API
            endpoint: API endpoint path
            method: HTTP method
            params: Query parameters
            body: Request body
            headers: Additional headers
            
        Returns:
            ToolResult with API response
        """
        try:
            # Get API configuration
            api_config = self._get_api_config(api_name)
            if not api_config:
                return ToolResult(
                    success=False,
                    summary=f"API '{api_name}' not configured",
                    error=f"No configuration found for {api_name}. Configure in settings.mcp_apis"
                )
            
            # Build request
            base_url = api_config.get("base_url")
            if not base_url:
                return ToolResult(
                    success=False,
                    summary=f"API '{api_name}' has no base_url",
                    error="base_url is required in API configuration"
                )
            
            url = urljoin(base_url, endpoint.lstrip("/"))
            
            # Build headers
            request_headers = {}
            
            # Add authentication
            auth = api_config.get("auth", {})
            if auth.get("type") == "bearer":
                token = auth.get("token")
                if token:
                    request_headers["Authorization"] = f"Bearer {token}"
            elif auth.get("type") == "api_key":
                key_name = auth.get("key_name", "X-API-Key")
                token = auth.get("token")
                if token:
                    request_headers[key_name] = token
            elif auth.get("type") == "basic":
                # Basic auth handled by httpx
                pass
            
            # Add additional headers
            if headers:
                request_headers.update(headers)
            
            # Set default content type for POST/PUT
            if method in ["POST", "PUT"] and "Content-Type" not in request_headers:
                request_headers["Content-Type"] = "application/json"
            
            # Make request with retry logic
            response_data = None
            error = None
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                for attempt in range(self.max_retries):
                    try:
                        response = await client.request(
                            method=method,
                            url=url,
                            params=params,
                            json=body if method in ["POST", "PUT"] else None,
                            headers=request_headers
                        )
                        
                        # Check for success
                        response.raise_for_status()
                        
                        # Parse response
                        try:
                            response_data = response.json()
                        except:
                            response_data = {"text": response.text}
                        
                        break  # Success
                        
                    except httpx.HTTPStatusError as e:
                        error = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
                        if attempt == self.max_retries - 1:
                            logger.error(f"API call failed after {self.max_retries} attempts: {error}")
                        elif e.response.status_code < 500:
                            # Don't retry client errors
                            break
                    except httpx.TimeoutException:
                        error = "Request timeout"
                        if attempt == self.max_retries - 1:
                            logger.error(f"API call timeout after {self.max_retries} attempts")
                    except Exception as e:
                        error = str(e)
                        if attempt == self.max_retries - 1:
                            logger.error(f"API call failed: {error}")
            
            if response_data is None:
                return ToolResult(
                    success=False,
                    summary=f"API call to {api_name} failed",
                    error=error or "Unknown error"
                )
            
            # Build summary
            summary = f"Called {api_name} API: {method} {endpoint}"
            if isinstance(response_data, dict):
                summary += f" (returned {len(response_data)} fields)"
            elif isinstance(response_data, list):
                summary += f" (returned {len(response_data)} items)"
            
            return ToolResult(
                success=True,
                data={
                    "api": api_name,
                    "endpoint": endpoint,
                    "method": method,
                    "response": response_data
                },
                summary=summary,
                metadata={
                    "url": url,
                    "method": method
                }
            )
            
        except Exception as e:
            logger.error(f"MCP API tool failed: {e}", exc_info=True)
            return ToolResult(
                success=False,
                summary=f"API tool failed: {str(e)}",
                error=str(e)
            )
    
    def _get_api_config(self, api_name: str) -> Optional[Dict[str, Any]]:
        """Get API configuration from settings."""
        mcp_apis = getattr(self.settings, "mcp_apis", {})
        return mcp_apis.get(api_name)
    
    def get_configured_apis(self) -> list[str]:
        """Get list of configured API names."""
        mcp_apis = getattr(self.settings, "mcp_apis", {})
        return list(mcp_apis.keys())

