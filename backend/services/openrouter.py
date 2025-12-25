"""
OpenRouter API client for multi-model AI access.
Handles communication with GPT-4, Claude, Gemini, Grok, DeepSeek, and Mistral.
"""
import httpx
import json
from typing import Dict, List, Optional, Any
from config import get_settings
import structlog

logger = structlog.get_logger()
settings = get_settings()


class OpenRouterClient:
    """Client for OpenRouter API with function calling support."""
    
    def __init__(self):
        self.api_key = settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url
        self.timeout = 60.0
        
    async def call_agent(
        self,
        model: str,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> Dict[str, Any]:
        """
        Call an AI model through OpenRouter.
        
        Args:
            model: Model identifier (e.g., "openai/gpt-4-turbo")
            messages: Chat messages list
            tools: Function calling tools definition
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            
        Returns:
            API response with choices and usage
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://trading-ai-system.local",
            "X-Title": "Multi-AI Trading System",
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        # Add tools if provided (function calling)
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(
                    "openrouter_request",
                    model=model,
                    message_count=len(messages),
                    has_tools=bool(tools),
                )
                
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                
                response.raise_for_status()
                data = response.json()
                
                # Log usage for cost tracking
                if "usage" in data:
                    usage = data["usage"]
                    logger.info(
                        "openrouter_usage",
                        model=model,
                        prompt_tokens=usage.get("prompt_tokens", 0),
                        completion_tokens=usage.get("completion_tokens", 0),
                        total_tokens=usage.get("total_tokens", 0),
                    )
                
                return data
                
        except httpx.HTTPStatusError as e:
            logger.error(
                "openrouter_http_error",
                model=model,
                status_code=e.response.status_code,
                error=str(e),
            )
            raise
        except Exception as e:
            logger.error("openrouter_error", model=model, error=str(e))
            raise
    
    def parse_tool_calls(self, response: Dict[str, Any]) -> List[Dict]:
        """
        Extract tool calls from OpenRouter response.
        
        Returns:
            List of tool calls: [{name: str, args: dict}, ...]
        """
        try:
            choice = response.get("choices", [{}])[0]
            message = choice.get("message", {})
            
            # Check for tool calls (OpenAI format)
            tool_calls = message.get("tool_calls", [])
            if tool_calls:
                parsed = []
                for call in tool_calls:
                    function = call.get("function", {})
                    parsed.append({
                        "name": function.get("name"),
                        "args": json.loads(function.get("arguments", "{}")),
                    })
                return parsed
            
            # Fallback: check for function_call (older format)
            function_call = message.get("function_call")
            if function_call:
                return [{
                    "name": function_call.get("name"),
                    "args": json.loads(function_call.get("arguments", "{}")),
                }]
            
            return []
            
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
    
    async def get_model_metadata(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific model.
        
        Args:
            model_id: Model identifier (e.g., "anthropic/claude-sonnet-4.5")
            
        Returns:
            Model metadata or None if not found
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                response.raise_for_status()
                data = response.json()
                
                models = data.get("data", [])
                for model in models:
                    if model.get("id") == model_id:
                        return model
                
                return None
        except Exception as e:
            logger.error("openrouter_metadata_error", model_id=model_id, error=str(e))
            return None
    
    async def healthcheck(self) -> bool:
        """Verify OpenRouter API is accessible."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                return response.status_code == 200
        except Exception as e:
            logger.error("openrouter_healthcheck_failed", error=str(e))
            return False


# Singleton instance
_client: Optional[OpenRouterClient] = None


def get_openrouter_client() -> OpenRouterClient:
    """Get or create OpenRouter client instance."""
    global _client
    if _client is None:
        _client = OpenRouterClient()
    return _client
