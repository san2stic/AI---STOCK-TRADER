"""
API routes for model information and management.
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any
import structlog
from services.model_selector import get_model_selector, MODEL_CATEGORIES
from config import AGENT_CONFIGS, get_settings

logger = structlog.get_logger()
router = APIRouter(prefix="/api/models", tags=["models"])
settings = get_settings()


@router.get("/current")
async def get_current_models() -> Dict[str, Any]:
    """
    Get currently selected models for all agents.
    For Vertex AI migration, all agents use the same high-performance model.
    """
    try:
        # Static configuration for Vertex AI
        agent_models = {}
        for agent_key, config in AGENT_CONFIGS.items():
            agent_models[agent_key] = {
                "name": config.get("name"),
                "model": config.get("model"),
                "category": "finance",  # Unified category
                "personality": config.get("personality"),
                "strategy": config.get("strategy"),
            }
        
        return {
            "agents": agent_models,
            "categories": {"finance": "anthropic/claude-4.5-sonnet"},
            "dynamic_enabled": False,
            "provider": "Google Cloud Vertex AI"
        }
        
    except Exception as e:
        logger.error("get_current_models_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/available")
async def get_available_models() -> Dict[str, Any]:
    """
    Get all available models from OpenRouter.
    
    Returns:
        List of available models with metadata
    """
    try:
        selector = get_model_selector()
        models = await selector.get_available_models()
        
        return {
            "total": len(models),
            "models": models[:50],  # Limit to first 50 for performance
        }
        
    except Exception as e:
        logger.error("get_available_models_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh")
async def refresh_models() -> Dict[str, Any]:
    """
    Force refresh of model cache and selection.
    
    Returns:
        Updated model selections
    """
    try:
        selector = get_model_selector()
        
        # Force refresh
        category_models = await selector.select_best_models(force_refresh=True)
        
        logger.info("models_refreshed", categories=list(category_models.keys()))
        
        return {
            "status": "refreshed",
            "categories": category_models,
        }
        
    except Exception as e:
        logger.error("refresh_models_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories")
async def get_model_categories() -> Dict[str, Any]:
    """
    Get model categories and their requirements.
    
    Returns:
        Category definitions and best models
    """
    try:
        selector = get_model_selector()
        best_models = await selector.select_best_models()
        
        # Format categories with their selected models
        categories = {}
        for category, info in MODEL_CATEGORIES.items():
            categories[category] = {
                "description": info["description"],
                "selected_model": best_models.get(category, info["fallback"]),
                "fallback": info["fallback"],
                "requirements": info["requirements"],
            }
        
        return {"categories": categories}
        
    except Exception as e:
        logger.error("get_categories_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/info/{model_id:path}")
async def get_model_info(model_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific model.
    
    Args:
        model_id: Model identifier (e.g., anthropic/claude-sonnet-4.5)
        
    Returns:
        Model metadata
    """
    try:
        selector = get_model_selector()
        info = await selector.get_model_info(model_id)
        
        if not info:
            raise HTTPException(status_code=404, detail="Model not found")
        
        return info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_model_info_error", model_id=model_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
