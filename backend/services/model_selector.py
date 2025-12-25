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
    "google/gemini-2.0-flash-exp:free",
    "google/gemini-pro-1.5",
    "mistralai/mistral-large-2411",
    "meta-llama/llama-3.3-70b-instruct",
    "openai/gpt-4o-mini",          # Cost effective
]


class ModelSelector:
    """
    Intelligent model selection (Simplified for Vertex AI migration).
    Now serves static configuration forcing Claude 3.5 Sonnet for all tasks.
    """
    
    def __init__(self):
        # No API key needed for static Vertex AI configuration
        self._cache = {}
        
    async def get_available_models(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Return static list containing only the Vertex AI model."""
        return [{
            "id": "anthropic/claude-4.5-sonnet",
            "name": "Claude 3.5 Sonnet (Vertex AI)",
            "description": "High-performance model via Google Cloud Vertex AI",
            "context_length": 200000,
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
        For Vertex AI migration, this returns the same model for everything.
        """
        # Force unified model for all categories
        unified_model = "anthropic/claude-4.5-sonnet"
        return {cat: unified_model for cat in MODEL_CATEGORIES}
    
    def _select_for_category(
        self,
        models: List[Dict[str, Any]],
        category: str,
        requirements: Dict[str, Any],
    ) -> str:
        """Select best model for a specific category."""
        req = requirements["requirements"]
        
        # Filter models
        candidates = []
        for model in models:
            model_id = model.get("id", "")
            
            # CRITICAL: Enforce Static Candidate List
            # We ONLY consider models in our approved static list
            if model_id not in STATIC_CANDIDATES:
                continue

            model_name = model.get("name", "").lower()
            model_desc = model.get("description", "").lower()
            
            # Check context length
            context_length = model.get("context_length", 0)
            if context_length < req.get("min_context", 0):
                continue
            
            # Check provider preference
            provider = model_id.split("/")[0] if "/" in model_id else ""
            
            # Calculate score
            score = 0
            
            # Provider preference
            if provider in req.get("preferred_providers", []):
                score += 10
                
            # Check for keywords in description
            for keyword in req.get("keywords", []):
                if keyword in model_name or keyword in model_desc:
                    score += 5
            
            # Prefer models with more context
            score += min(context_length / 10000, 5)
            
            # Popular models (based on naming patterns)
            if any(x in model_id.lower() for x in ["gpt-4", "claude-3", "claude-sonnet", "deepseek-r1", "gemini-3", "grok-4"]):
                score += 8
            
            # Specific high-quality models for finance and general tasks
            # Boost specific STABLE proven models
            if "anthropic/claude-3.5-sonnet" in model_id:
                score += 20
            elif model_id == "openai/gpt-4o":
                score += 25
            elif "openai/gpt-4o" in model_id and "mini" not in model_id and "audio" not in model_id and "search" not in model_id:
                score += 20
            elif "google/gemini-pro-1.5" in model_id:
                score += 15
            elif "x-ai/grok-2" in model_id:
                score += 15
                
            # Category specific adjustments
            if category == "finance":
                if "claude-3.5-sonnet" in model_id or "gpt-4o" in model_id:
                    score += 10
                if "deepseek-chat" in model_id or "deepseek-v3" in model_id:
                    score += 8
                    
            # For data analysis, prefer reasoning models
            if category == "data_analysis":
                if "deepseek-reasoner" in model_id or "deepseek-r1" in model_id:
                    score += 15
                if "claude-3.5-sonnet" in model_id:
                    score += 12
                if "gemini-pro-1.5" in model_id:
                    score += 10
            
            candidates.append({
                "id": model_id,
                "score": score,
                "context": context_length,
            })
        
        # Sort by score
        candidates.sort(key=lambda x: x["score"], reverse=True)
        
        # Return best model or fallback
        if candidates:
            return candidates[0]["id"]
        else:
            logger.warning(
                "model_selector_no_candidates",
                category=category,
                using_fallback=requirements["fallback"],
            )
            return requirements["fallback"]
    
    async def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific model."""
        # Always return mock info for our target model
        if "claude" in model_id.lower() or "sonnet" in model_id.lower():
             return {
                "id": model_id,
                "name": "Claude 3.5 Sonnet (Vertex AI)",
                "context_length": 200000,
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


# Singleton instance
_selector: Optional[ModelSelector] = None


def get_model_selector() -> ModelSelector:
    """Get or create ModelSelector instance."""
    global _selector
    if _selector is None:
        _selector = ModelSelector()
    return _selector
