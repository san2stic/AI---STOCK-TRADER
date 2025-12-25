"""
Google Cloud Vertex AI client for Gemini 3 Pro.
Migrated from Claude/Anthropic to native Gemini API.
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
    Client for Google Cloud Vertex AI API (Gemini models).
    Uses native Gemini API format for function calling and generation.
    """
    
    def __init__(self):
        self.project_id = settings.vertex_ai_project_id
        self.location = settings.vertex_ai_location
        # Default to Gemini model from settings
        self.default_model = settings.vertex_ai_model
        
        # Mapping from legacy/generic names to Vertex AI Model IDs
        self.model_mapping = {
            # Gemini 3 models (preview - latest generation)
            "google/gemini-3-pro-preview": "gemini-3-pro-preview",
            "google/gemini-3-flash-preview": "gemini-3-flash-preview",
            "gemini-3-pro-preview": "gemini-3-pro-preview",
            "gemini-3-flash-preview": "gemini-3-flash-preview",
            
            # Gemini models (actual Vertex AI models)
            "google/gemini-2.0-flash-exp": "gemini-2.0-flash-exp",
            "google/gemini-exp-1206": "gemini-exp-1206",
            "google/gemini-1.5-pro": "gemini-1.5-pro-002",
            "google/gemini-1.5-flash": "gemini-1.5-flash-002",
            "gemini-2.0-flash-exp": "gemini-2.0-flash-exp",
            "gemini-exp-1206": "gemini-exp-1206",
            "gemini-1.5-pro": "gemini-1.5-pro-002",
            "gemini-1.5-flash": "gemini-1.5-flash-002",
            
            # Legacy Claude mappings -> redirect to Gemini 3 Preview
            "anthropic/claude-4.5-sonnet": "gemini-3-pro-preview",
            "anthropic/claude-3.5-sonnet": "gemini-3-pro-preview",
            "anthropic/claude-3-opus": "gemini-3-pro-preview",
            "anthropic/claude-3-haiku": "gemini-3-flash-preview",
            
            # Legacy OpenAI mappings -> redirect to Gemini 3 Preview
            "openai/gpt-4o": "gemini-3-pro-preview",
            "openai/gpt-4-turbo-preview": "gemini-3-pro-preview",
            "openai/gpt-5.2": "gemini-3-pro-preview",
            
            # Legacy non-existent models -> redirect to valid ones
            "google/gemini-3-pro": "gemini-3-pro-preview",
            "gemini-3-pro": "gemini-3-pro-preview",
        }
        
    def _get_access_token(self) -> str:
        """Get Google Cloud access token using ADC."""
        try:
            credentials, project = google.auth.default()
            auth_req = google.auth.transport.requests.Request()
            credentials.refresh(auth_req)
            return credentials.token
        except Exception as e:
            logger.error("vertex_auth_error", error=str(e))
            raise

    def _get_vertex_endpoint(self, model: str) -> str:
        """
        Get the Vertex AI endpoint URL for Gemini models.
        Format: https://{REGION}-aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/{REGION}/publishers/google/models/{MODEL}:generateContent
        """
        # Resolve model ID
        vertex_model_id = self.model_mapping.get(model, model)
        
        # Default fallback
        if not vertex_model_id or vertex_model_id not in self.model_mapping.values():
            vertex_model_id = self.default_model
            
        return f"https://{self.location}-aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/{self.location}/publishers/google/models/{vertex_model_id}:generateContent"

    def _convert_to_gemini_tools(self, tools: List[Dict]) -> List[Dict]:
        """
        Convert OpenAI/Anthropic tool format to Gemini functionDeclarations format.
        
        Input (OpenAI format):
        {"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}
        
        Output (Gemini format):
        {"functionDeclarations": [{"name": ..., "description": ..., "parameters": ...}]}
        """
        if not tools:
            return []
            
        function_declarations = []
        for tool in tools:
            if "function" in tool:
                fn = tool["function"]
                function_declarations.append({
                    "name": fn["name"],
                    "description": fn.get("description", ""),
                    "parameters": fn.get("parameters", {"type": "object", "properties": {}})
                })
            elif "name" in tool:
                # Already in Gemini-like format
                function_declarations.append({
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", tool.get("input_schema", {"type": "object", "properties": {}}))
                })
        
        return [{"functionDeclarations": function_declarations}] if function_declarations else []

    async def call_agent(
        self,
        model: str,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """
        Call Gemini model on Vertex AI.
        API matches OpenRouterClient.call_agent for compatibility.
        """
        token = self._get_access_token()
        url = self._get_vertex_endpoint(model)
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }
        
        # Convert messages to Gemini format
        # Gemini format:
        # {
        #   "contents": [{"role": "user", "parts": [{"text": "..."}]}],
        #   "systemInstruction": {"parts": [{"text": "..."}]},
        #   "tools": [{"functionDeclarations": [...]}],
        #   "generationConfig": {...}
        # }
        
        system_instruction = ""
        gemini_contents = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_instruction += msg["content"] + "\n"
            elif msg["role"] == "user":
                gemini_contents.append({
                    "role": "user",
                    "parts": [{"text": msg["content"]}]
                })
            elif msg["role"] == "assistant":
                gemini_contents.append({
                    "role": "model",
                    "parts": [{"text": msg["content"]}]
                })
        
        payload = {
            "contents": gemini_contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "topP": 0.95,
                "topK": 40,
            }
        }
        
        if system_instruction.strip():
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction.strip()}]
            }
            
        if tools:
            gemini_tools = self._convert_to_gemini_tools(tools)
            if gemini_tools:
                payload["tools"] = gemini_tools
                # Enable automatic function calling
                payload["toolConfig"] = {
                    "functionCallingConfig": {
                        "mode": "AUTO"
                    }
                }
            
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                logger.info(
                    "vertex_request",
                    model=model,
                    resolved_model=self.model_mapping.get(model, model),
                    endpoint="generateContent",
                    message_count=len(gemini_contents),
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
                        body=response.text[:500]
                    )
                    response.raise_for_status()
                    
                data = response.json()
                
                # Transform Gemini response to OpenAI-compatible format
                # Gemini response:
                # {
                #   "candidates": [{
                #     "content": {
                #       "parts": [{"text": "..."} or {"functionCall": {"name": ..., "args": ...}}],
                #       "role": "model"
                #     }
                #   }],
                #   "usageMetadata": {...}
                # }
                
                content = ""
                tool_calls = []
                
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    for idx, part in enumerate(parts):
                        if "text" in part:
                            content += part["text"]
                        elif "functionCall" in part:
                            fc = part["functionCall"]
                            tool_calls.append({
                                "id": f"call_{idx}",
                                "type": "function",
                                "function": {
                                    "name": fc["name"],
                                    "arguments": json.dumps(fc.get("args", {}))
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
                    "usage": data.get("usageMetadata", {})
                }
                
                # Log usage
                usage = data.get("usageMetadata", {})
                logger.info(
                    "vertex_usage",
                    model=model,
                    input_tokens=usage.get("promptTokenCount", 0),
                    output_tokens=usage.get("candidatesTokenCount", 0),
                )
                
                return simulated_response
                
        except Exception as e:
            logger.error("vertex_error", model=model, error=str(e))
            raise

    # Compatibility methods (unchanged interface)
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
