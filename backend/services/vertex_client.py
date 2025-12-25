"""
Google Cloud Vertex AI client for Claude access.
Replaces OpenRouter with direct Vertex AI API calls.
"""
import httpx
import json
import logging
import google.auth
import google.auth.transport.requests
from typing import Dict, List, Optional, Any
from config import get_settings
import structlog

logger = structlog.get_logger()
settings = get_settings()

class VertexAIClient:
    """
    Client for Google Cloud Vertex AI API (specifically for Anthropic models).
    Handles authentication via Google credentials (ADC) and raw prediction calls.
    """
    
    def __init__(self):
        self.project_id = settings.vertex_ai_project_id
        self.location = settings.vertex_ai_location
        # Default fallback if not specified in method
        self.default_model = "claude-3-5-sonnet@20240620"
        
        # Mapping from generic names/OpenRouter names to Vertex AI Model IDs
        self.model_mapping = {
            "anthropic/claude-4.5-sonnet": "claude-3-5-sonnet@20240620",
            "anthropic/claude-3.5-sonnet": "claude-3-5-sonnet@20240620",
            "anthropic/claude-3-opus": "claude-3-opus@20240229",
            "anthropic/claude-3-haiku": "claude-3-haiku@20240307",
            # Fallbacks for other models if requested, mapping to Sonnet as requested "use only claude 4.5"
            "openai/gpt-4o": "claude-3-5-sonnet@20240620",
            "google/gemini-3-pro-preview": "claude-3-5-sonnet@20240620",
        }
        
    def _get_access_token(self) -> str:
        """Get Google Cloud access token using ADC."""
        try:
            # Load credentials from ADC or Environment
            credentials, project = google.auth.default()
            
            # Refresh token if needed
            auth_req = google.auth.transport.requests.Request()
            credentials.refresh(auth_req)
            
            return credentials.token
        except Exception as e:
            logger.error("vertex_auth_error", error=str(e))
            raise

    def _get_vertex_endpoint(self, model: str) -> str:
        """
        Get the Vertex AI endpoint URL for a specific model.
        Format: https://{REGION}-aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/{REGION}/publishers/anthropic/models/{MODEL}:streamRawPredict
        """
        # Resolve model ID
        vertex_model_id = self.model_mapping.get(model, model)
        # If it doesn't look like a Vertex ID (no @ version), assume it's the default
        if "@" not in vertex_model_id and "claude" in vertex_model_id:
            vertex_model_id = "claude-3-5-sonnet@20240620"
            
        return f"https://{self.location}-aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/{self.location}/publishers/anthropic/models/{vertex_model_id}:streamRawPredict"

    async def call_agent(
        self,
        model: str,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """
        Call Anthropic model on Vertex AI.
        API matches OpenRouterClient.call_agent for compatibility.
        """
        token = self._get_access_token()
        url = self._get_vertex_endpoint(model)
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }
        
        # Convert OpenRouter/OpenAI message format to Anthropic format if needed
        # Anthropic Vertex API expects:
        # {
        #   "anthropic_version": "vertex-2023-10-16",
        #   "messages": [...],
        #   "system": "...",
        #   "tools": [...]
        # }
        
        # Extract system prompt if present in messages
        system_prompt = ""
        anthropic_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_prompt += msg["content"] + "\n"
            else:
                anthropic_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        payload = {
            "anthropic_version": "vertex-2023-10-16",
            "messages": anthropic_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False 
        }
        
        if system_prompt:
            payload["system"] = system_prompt.strip()
            
        if tools:
            # Convert tools to Anthropic format
            # OpenAI format: {"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}
            # Anthropic format: {"name": ..., "description": ..., "input_schema": ...}
            anthropic_tools = []
            for tool in tools:
                if "function" in tool:
                    fn = tool["function"]
                    anthropic_tools.append({
                        "name": fn["name"],
                        "description": fn.get("description", ""),
                        "input_schema": fn["parameters"]
                    })
                else:
                    # Assume already in Anthropic format or compatible
                    anthropic_tools.append(tool)
            
            payload["tools"] = anthropic_tools
            # Force auto tool choice (default behavior)
            
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                logger.info(
                    "vertex_request",
                    model=model,
                    endpoint=url.split("/")[-1],
                    message_count=len(anthropic_messages),
                    has_tools=bool(tools),
                )
                
                response = await client.post(
                    url,
                    headers=headers,
                    json=payload,
                )
                
                if response.status_code != 200:
                    logger.error(
                        "vertex_http_error",
                        status=response.status_code,
                        body=response.text
                    )
                    response.raise_for_status()
                    
                data = response.json()
                
                # Transform response to match OpenRouter/OpenAI structure for compatibility
                # Anthropic response:
                # {
                #   "content": [{"type": "text", "text": "..."} or {"type": "tool_use", ...}],
                #   ...
                # }
                # Target format (OpenAI-like):
                # { "choices": [{ "message": { "content": "...", "tool_calls": [...] } }] }
                
                content = ""
                tool_calls = []
                
                for item in data.get("content", []):
                    if item["type"] == "text":
                        content += item["text"]
                    elif item["type"] == "tool_use":
                        tool_calls.append({
                            "id": item["id"],
                            "type": "function",
                            "function": {
                                "name": item["name"],
                                "arguments": json.dumps(item["input"])
                            }
                        })
                
                simulated_response = {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": content,
                                "tool_calls": tool_calls if tool_calls else None
                            }
                        }
                    ],
                    "usage": data.get("usage", {})
                }
                
                # Log usage
                usage = data.get("usage", {})
                logger.info(
                    "vertex_usage",
                    model=model,
                    input_tokens=usage.get("input_tokens", 0),
                    output_tokens=usage.get("output_tokens", 0),
                )
                
                return simulated_response
                
        except Exception as e:
            logger.error("vertex_error", model=model, error=str(e))
            raise

    # Compatibility methods
    def parse_tool_calls(self, response: Dict[str, Any]) -> List[Dict]:
        """Extract tool calls from response (same as OpenRouterClient)."""
        try:
            choice = response.get("choices", [{}])[0]
            message = choice.get("message", {})
            tool_calls = message.get("tool_calls", [])
            
            parsed = []
            if tool_calls:
                for call in tool_calls:
                    function = call.get("function", {})
                    parsed.append({
                        "name": function.get("name"),
                        "args": json.loads(function.get("arguments", "{}")) 
                                if isinstance(function.get("arguments"), str) 
                                else function.get("arguments")
                    })
            return parsed
        except Exception as e:
            logger.warning("tool_call_parse_error", error=str(e))
            return []

    def get_message_content(self, response: Dict[str, Any]) -> str:
        """Extract text content from response."""
        try:
            choice = response.get("choices", [{}])[0]
            message = choice.get("message", {})
            return message.get("content", "")
        except Exception:
            return ""

# Singleton instance
_client: Optional[VertexAIClient] = None

def get_vertex_client() -> VertexAIClient:
    """Get or create VertexAI client instance."""
    global _client
    if _client is None:
        _client = VertexAIClient()
    return _client
