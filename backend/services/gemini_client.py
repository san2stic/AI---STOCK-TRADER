"""
Google AI Studio client for Gemini 2.0.
Replaces Vertex AI client with direct API access using API Key.
"""
import httpx
import json
import logging
from typing import Dict, List, Optional, Any
from config import get_settings
import structlog

logger = structlog.get_logger()
settings = get_settings()


class GeminiClient:
    """
    Client for Google AI Studio (Gemini API).
    Uses native Gemini API format.
    """
    
    def __init__(self):
        self.api_key = settings.google_ai_api_key
        # Default to Gemini model from settings
        self.default_model = settings.gemini_model
        
        # Mapping from generic names to Google AI Studio Model IDs
        self.model_mapping = {
            # Gemini 3 (Preview)
            "google/gemini-3-flash-preview": "gemini-3-flash-preview",
            "gemini-3-flash-preview": "gemini-3-flash-preview",
            "models/gemini-3-flash-preview": "gemini-3-flash-preview",

            # Gemini 2.0 (Experimental)
            "google/gemini-2.0-flash-exp": "gemini-2.0-flash-exp",
            "gemini-2.0-flash-exp": "gemini-2.0-flash-exp",
            
            # Gemini 1.5
            "google/gemini-1.5-pro": "gemini-1.5-pro",
            "google/gemini-1.5-flash": "gemini-1.5-flash",
            "gemini-1.5-pro": "gemini-1.5-pro",
            "gemini-1.5-flash": "gemini-1.5-flash",
            
            # Legacy/Generic redirections -> Default
            "google/gemini-3-pro": "gemini-3-flash-preview", 
            "anthropic/claude-4.5-sonnet": "gemini-3-flash-preview",
            "openai/gpt-4o": "gemini-3-flash-preview",
        }
        
    def _get_api_url(self, model: str) -> str:
        """
        Get the Google AI Studio endpoint URL.
        Format: https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}
        """
        # Resolve model ID
        gemini_model_id = self.model_mapping.get(model, model)
        
        # Default fallback if looked up failed or not found (and not a valid ID itself)
        # Simple heuristic: if it contains '/', it's likely a mapped name like "google/..." that wasn't found
        if "/" in gemini_model_id: 
             gemini_model_id = self.default_model

        return f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model_id}:generateContent?key={self.api_key}"

    def _convert_to_gemini_tools(self, tools: List[Dict]) -> List[Dict]:
        """
        Convert OpenAI/Anthropic tool format to Gemini functionDeclarations format.
        """
        if not tools:
            return []
            
        function_declarations = []
        for tool in tools:
            if "function" in tool:
                fn = tool["function"]
                # Ensure parameters is not empty if missing
                params = fn.get("parameters", {"type": "object", "properties": {}})
                function_declarations.append({
                    "name": fn["name"],
                    "description": fn.get("description", ""),
                    "parameters": params
                })
            elif "name" in tool:
                # Already in Gemini-like format or simplified format
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
        Call Gemini API via Google AI Studio.
        Compatible with OpenRouterClient/VertexAIClient interface.
        """
        if not self.api_key:
             raise ValueError("GOOGLE_AI_API_KEY is not set in environment variables.")

        url = self._get_api_url(model)
        
        headers = {
            "Content-Type": "application/json",
        }
        
        # Conversion to Gemini format
        system_instruction = ""
        gemini_contents = []
        
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            if role == "system":
                system_instruction += content + "\n"
            elif role == "user":
                gemini_contents.append({
                    "role": "user",
                    "parts": [{"text": content}]
                })
            elif role == "assistant":
                # Handle tool calls in history if present (complex, skipping for now for simple agent flow)
                # But for standard text response:
                gemini_contents.append({
                    "role": "model",
                    "parts": [{"text": content}]
                })
        
        payload = {
            "contents": gemini_contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                # "topP": 0.95,
                # "topK": 40,
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
                # Auto function calling
                # payload["toolConfig"] = {"functionCallingConfig": {"mode": "AUTO"}} 
                # Note: 'toolConfig' might differ slightly in v1beta public API vs Vertex, 
                # but usually AUTO is default if tools provided.
            
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                logger.info(
                    "gemini_request",
                    model=model,
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
                        "gemini_http_error",
                        status=response.status_code,
                        body=response.text[:500]
                    )
                    response.raise_for_status()
                    
                data = response.json()
                
                # Transform response to OpenAI-compatible format
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
                
                # Usage metadata (might vary in structure)
                usage = data.get("usageMetadata", {})
                
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
                    "usage": usage
                }
                
                logger.info(
                    "gemini_usage",
                    model=model,
                    input_tokens=usage.get("promptTokenCount", 0),
                    output_tokens=usage.get("candidatesTokenCount", 0),
                )
                
                return simulated_response
                
        except Exception as e:
            logger.error("gemini_error", model=model, error=str(e))
            raise

    # Compatibility methods
    def parse_tool_calls(self, response: Dict[str, Any]) -> List[Dict]:
        """Extract tool calls from response."""
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
_client: Optional[GeminiClient] = None

def get_gemini_client() -> GeminiClient:
    """Get or create GeminiClient instance."""
    global _client
    if _client is None:
        _client = GeminiClient()
    return _client
