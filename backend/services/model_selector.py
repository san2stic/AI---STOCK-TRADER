"""
Dynamic model selection service for OpenRouter.
Automatically selects the best models for finance and data analysis tasks.
"""
import asyncio
import httpx
import structlog
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from config import get_settings
from services.gemini_client import get_gemini_client

logger = structlog.get_logger()
settings = get_settings()


# Model categories with their requirements
MODEL_CATEGORIES = {
    "finance": {
        "description": "Best models for financial analysis and trading decisions",
        "requirements": {
            "min_context": 8000,
            "supports_function_calling": True,
            "preferred_providers": ["anthropic", "openai", "deepseek", "x-ai"],
            "keywords": ["reasoning", "analysis", "financial", "thinking"],
        },
        "fallback": "anthropic/claude-3.5-sonnet",
    },
    "data_analysis": {
        "description": "Best models for data processing and statistical analysis",
        "requirements": {
            "min_context": 8000,
            "supports_function_calling": True,
            "preferred_providers": ["anthropic", "openai", "google", "deepseek"],
            "keywords": ["data", "analysis", "reasoning", "math"],
        },
        "fallback": "deepseek/deepseek-chat",
    },
    "general": {
        "description": "General purpose models for various tasks",
        "requirements": {
            "min_context": 4000,
            "supports_function_calling": True,
            "preferred_providers": ["openai", "anthropic", "mistralai"],
            "keywords": [],
        },
        "fallback": "openai/gpt-4o",
    },
    "parsing": {
        "description": "Models optimized for parsing and structured output",
        "requirements": {
            "min_context": 4000,
            "supports_function_calling": True,
            "preferred_providers": ["anthropic", "openai"],
            "keywords": ["structured", "json", "parsing"],
        },
        "fallback": "anthropic/claude-3.5-sonnet",
    },
}

# STATIC CANDIDATES - The "Static" part of "Dynamic but Static"
# We only select from this curated list to ensure reliability and tool support.
STATIC_CANDIDATES = [
    "anthropic/claude-3.5-sonnet",
    "openai/gpt-4o",
    "deepseek/deepseek-chat",     # DeepSeek V3
    "x-ai/grok-2-1212",
    "gemini-3-pro-preview",
    "gemini-3-flash-preview",
    "google/gemini-2.0-flash-exp",
    "google/gemini-pro-1.5",
    "mistralai/mistral-large-2411",
    "meta-llama/llama-3.3-70b-instruct",
    "openai/gpt-4o-mini",          # Cost effective
]


class ModelSelector:
    """
    Intelligent model selection (Simplified for Google AI Studio migration).
    Now serves static configuration forcing Gemini 3.0 Pro for all tasks.
    """
    
    def __init__(self):
        self._cache = {}
        
    async def get_available_models(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Return static list containing only the Gemini model."""
        return [{
            "id": "gemini-3-pro-preview",
            "name": "Gemini 3.0 Pro (Preview)",
            "description": "High-performance model via Google AI Studio Key",
            "context_length": 1000000,
            "pricing": {"prompt": "0", "completion": "0"}
        }]
    
    def _is_cache_valid(self) -> bool:
        return True
    
    async def select_best_models(
        self, 
        force_refresh: bool = False
    ) -> Dict[str, str]:
        """
        Select the best model for each category.
        For Google AI Studio migration, this returns the same model for everything.
        """
        # Force unified model for all categories to Gemini 3.0
        unified_model = "gemini-3-pro-preview"
        return {cat: unified_model for cat in MODEL_CATEGORIES}
    
    def _select_for_category(
        self,
        models: List[Dict[str, Any]],
        category: str,
        requirements: Dict[str, Any],
    ) -> str:
        """Select best model for a specific category."""
        return "gemini-3-pro-preview"
    
    async def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific model."""
        # Always return mock info for our target model
        if "gemini" in model_id.lower():
             return {
                "id": model_id,
                "name": "Gemini 3.0 Pro (Preview)",
                "context_length": 1000000,
             }
        return None
    
    def get_category_for_agent(self, agent_key: str, personality: str) -> str:
        """
        Determine which model category to use for an agent.
        (Kept for compatibility, though all point to same model now)
        """
        return "finance"

    async def is_model_available(self, model_id: str) -> bool:
        """Check if a specific model is available."""
        return True
    
    def get_client(self, model_id: str = None):
        """
        Get the Gemini client.
        In this simplified version, we always return the GeminiClient.
        """
        return get_gemini_client()


# Singleton instance
_selector: Optional[ModelSelector] = None


def get_model_selector() -> ModelSelector:
    """Get or create ModelSelector instance."""
    global _selector
    if _selector is None:
        _selector = ModelSelector()
    return _selector
