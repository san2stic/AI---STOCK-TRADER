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


class ModelSelector:
    """Intelligent model selection from OpenRouter."""
    
    def __init__(self):
        self.api_key = settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url
        self._cache: Dict[str, Any] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = timedelta(hours=1)
        
    async def get_available_models(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Fetch available models from OpenRouter API.
        
        Args:
            force_refresh: Force refresh cache even if valid
            
        Returns:
            List of model metadata dictionaries
        """
        # Check cache
        if not force_refresh and self._is_cache_valid():
            logger.info("model_selector_using_cache", cached_models=len(self._cache.get("models", [])))
            return self._cache.get("models", [])
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                models = data.get("data", [])
                
                # Cache the results
                self._cache = {"models": models}
                self._cache_timestamp = datetime.now()
                
                logger.info(
                    "model_selector_fetched_models",
                    total_models=len(models),
                    cached_until=(datetime.now() + self._cache_ttl).isoformat(),
                )
                
                return models
                
        except Exception as e:
            logger.error("model_selector_fetch_error", error=str(e))
            # Return cached data if available, even if expired
            if self._cache.get("models"):
                logger.warning("model_selector_using_expired_cache")
                return self._cache["models"]
            return []
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if not self._cache_timestamp or not self._cache.get("models"):
            return False
        return datetime.now() - self._cache_timestamp < self._cache_ttl
    
    async def select_best_models(
        self, 
        force_refresh: bool = False
    ) -> Dict[str, str]:
        """
        Select the best model for each category.
        
        Args:
            force_refresh: Force refresh of model list
            
        Returns:
            Dictionary mapping category -> model_id
        """
        models = await self.get_available_models(force_refresh)
        
        if not models:
            logger.warning("model_selector_no_models_using_fallback")
            return {cat: info["fallback"] for cat, info in MODEL_CATEGORIES.items()}
        
        selected: Dict[str, str] = {}
        
        for category, requirements in MODEL_CATEGORIES.items():
            best_model = self._select_for_category(models, category, requirements)
            selected[category] = best_model
            
            logger.info(
                "model_selector_selected",
                category=category,
                model=best_model,
            )
        
        return selected
    
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
        models = await self.get_available_models()
        
        for model in models:
            if model.get("id") == model_id:
                return model
        
        return None
    
    def get_category_for_agent(self, agent_key: str, personality: str) -> str:
        """
        Determine which model category to use for an agent.
        
        Args:
            agent_key: Agent identifier
            personality: Agent personality description
            
        Returns:
            Category name (finance, data_analysis, general)
        """
        personality_lower = personality.lower()
        
        # Finance-focused agents
        if any(keyword in personality_lower for keyword in [
            "trader", "investor", "trading", "momentum", "conservative",
            "aggressive", "diversified", "opportunistic"
        ]):
            return "finance"
        
        # Data analysis focus
        if any(keyword in personality_lower for keyword in [
            "analytical", "data", "technical", "quantitative"
        ]):
            return "data_analysis"
        
        # Default to finance for trading system
        return "finance"


# Singleton instance
_selector: Optional[ModelSelector] = None


def get_model_selector() -> ModelSelector:
    """Get or create ModelSelector instance."""
    global _selector
    if _selector is None:
        _selector = ModelSelector()
    return _selector
