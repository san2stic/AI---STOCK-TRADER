"""
Learning Analytics API - Endpoints for viewing agent learning data.
Provides access to error patterns, strategy performance, and feedback history.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import structlog

from database import get_db
from models.error_pattern import ErrorPattern
from models.strategy_performance import StrategyPerformance
from models.trade_outcome import TradeOutcome
from models.database import AgentReflection, Trade
from services.error_tracker import get_error_tracker
from services.error_pattern_detector import get_error_pattern_detector

router = APIRouter(prefix="/api/learning", tags=["learning"])
logger = structlog.get_logger()


@router.get("/errors/{agent_name}")
async def get_error_patterns(
    agent_name: str,
    include_resolved: bool = Query(False, description="Include resolved patterns"),
    limit: int = Query(10, ge=1, le=50)
) -> Dict[str, Any]:
    """Get error patterns for a specific agent."""
    try:
        with get_db() as db:
            query = db.query(ErrorPattern).filter(
                ErrorPattern.agent_name == agent_name
            )
            
            if not include_resolved:
                query = query.filter(ErrorPattern.is_resolved == False)
            
            patterns = query.order_by(
                ErrorPattern.severity_score.desc()
            ).limit(limit).all()
            
            return{
                "agent_name": agent_name,
                "total_patterns": len(patterns),
                "patterns": [p.to_dict() for p in patterns],
                "timestamp": datetime.utcnow().isoformat()
            }
    except Exception as e:
        logger.error("get_error_patterns_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strategies/{agent_name}")
async def get_strategy_performance(
    agent_name: str,
    market_condition: Optional[str] = Query(None, description="Filter by market condition"),
    min_trades: int = Query(3, description="Minimum trades required")
) -> Dict[str, Any]:
    """Get strategy performance breakdown for an agent."""
    try:
        with get_db() as db:
            query = db.query(StrategyPerformance).filter(
                StrategyPerformance.agent_name == agent_name,
                StrategyPerformance.total_trades >= min_trades
            )
            
            if market_condition:
                query = query.filter(
                    StrategyPerformance.market_condition == market_condition
                )
            
            strategies = query.order_by(
                StrategyPerformance.win_rate.desc()
            ).all()
            
            # Categorize strategies
            top_strategies = [s for s in strategies if s.get_recommendation_strength() in ['strong_recommend', 'recommend']]
            avoid_strategies = [s for s in strategies if s.get_recommendation_strength() == 'avoid']
            
            return {
                "agent_name": agent_name,
                "total_strategies_tracked": len(strategies),
                "top_strategies": [s.to_dict() for s in top_strategies[:5]],
                "avoid_strategies": [s.to_dict() for s in avoid_strategies],
                "all_strategies": [s.to_dict() for s in strategies],
                "timestamp": datetime.utcnow().isoformat()
            }
    except Exception as e:
        logger.error("get_strategy_performance_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feedback/{agent_name}")
async def get_learning_feedback(
    agent_name: str,
    days: int = Query(30, ge=1, le=365, description="Days to look back"),
    limit: int = Query(20, ge=1, le=100)
) -> Dict[str, Any]:
    """Get recent learning feedback for an agent."""
    try:
        with get_db() as db:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            reflections = db.query(AgentReflection).filter(
                AgentReflection.agent_name == agent_name,
                AgentReflection.created_at >= cutoff_date
            ).order_by(AgentReflection.created_at.desc()).limit(limit).all()
            
            feedback_list = []
            for r in reflections:
                feedback_list.append({
                    "id": r.id,
                    "date": r.created_at.isoformat(),
                    "trades_analyzed": len(r.trades_analyzed) if r.trades_analyzed else 0,
                    "what_went_well": r.what_went_well,
                    "what_went_wrong": r.what_went_wrong,
                    "improvements_planned": r.improvements_planned,
                    "performance_stats": r.performance_stats
                })
            
            return {
                "agent_name": agent_name,
                "period_days": days,
                "feedback_count": len(feedback_list),
                "feedback": feedback_list,
                "timestamp": datetime.utcnow().isoformat()
            }
    except Exception as e:
        logger.error("get_learning_feedback_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary/{agent_name}")
async def get_learning_summary(
    agent_name: str,
    days: int = Query(30, ge=1, le=365)
) -> Dict[str, Any]:
    """Get comprehensive learning summary for an agent."""
    try:
        error_tracker = get_error_tracker()
        
        # Get error summary
        error_summary = await error_tracker.get_agent_error_summary(agent_name, days)
        
        # Get top strategy
        with get_db() as db:
            top_strategy = db.query(StrategyPerformance).filter(
                StrategyPerformance.agent_name == agent_name,
                StrategyPerformance.total_trades >= 3
            ).order_by(StrategyPerformance.win_rate.desc()).first()
            
            # Get recent outcomes
            recent_outcomes = db.query(TradeOutcome).join(
                Trade, TradeOutcome.trade_id == Trade.id
            ).filter(
                Trade.agent_name == agent_name,
                TradeOutcome.close_date >= datetime.utcnow() - timedelta(days=days)
            ).count()
        
        return {
            "agent_name": agent_name,
            "period_days": days,
            "trades_completed": recent_outcomes,
            "error_summary": error_summary,
            "best_strategy": top_strategy.to_dict() if top_strategy else None,
            "learning_status": "active" if error_summary.get("active_error_patterns", 0) > 0 else "good",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error("get_learning_summary_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collective")
async def get_collective_insights(
    days: int = Query(30, ge=1, le=365)
) -> Dict[str, Any]:
    """Get collective learning insights across all agents."""
    try:
        with get_db() as db:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Most common error patterns across all agents
            common_errors = db.query(
                ErrorPattern.pattern_type,
                ErrorPattern
            ).filter(
                ErrorPattern.is_resolved == False,
                ErrorPattern.last_seen >= cutoff_date
            ).order_by(ErrorPattern.occurrence_count.desc()).limit(10).all()
            
            # Best performing strategies across all agents
            best_strategies = db.query(StrategyPerformance).filter(
                StrategyPerformance.total_trades >= 5,
                StrategyPerformance.last_trade_date >= cutoff_date
            ).order_by(StrategyPerformance.win_rate.desc()).limit(10).all()
            
            return {
                "period_days": days,
                "common_error_types": [
                    {
                        "pattern_type": e[0],
                        "occurrences": e[1].occurrence_count,
                        "avg_loss": e[1].avg_loss_percent
                    }
                    for e in common_errors
                ],
                "best_strategies_overall": [s.to_dict() for s in best_strategies],
                "timestamp": datetime.utcnow().isoformat()  
            }
    except Exception as e:
        logger.error("get_collective_insights_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/manual-feedback")
async def add_manual_feedback(
    agent_name: str,
    feedback: str,
    category: str = Query("manual", description="Feedback category")
) -> Dict[str, str]:
    """Allow manual feedback injection for an agent."""
    try:
        with get_db() as db:
            reflection = AgentReflection(
                agent_name=agent_name,
                trades_analyzed=[],
                performance_stats={"manual_entry": True, "category": category},
                improvements_planned=feedback,
                raw_reflection=feedback
            )
            
            db.add(reflection)
            db.commit()
            
            logger.info(
                "manual_feedback_added",
                agent_name=agent_name,
                category=category
            )
            
            return {
                "status": "success",
                "message": f"Manual feedback added for {agent_name}",
                "timestamp": datetime.utcnow().isoformat()
            }
    except Exception as e:
        logger.error("add_manual_feedback_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset/{agent_name}")
async def reset_learning_data(
    agent_name: str,
    confirm: bool = Query(False, description="Must be true to proceed")
) -> Dict[str, str]:
    """Reset learning data for an agent (use with caution)."""
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Must set confirm=true to reset learning data"
        )
    
    try:
        with get_db() as db:
            # Mark all error patterns as resolved
            db.query(ErrorPattern).filter(
                ErrorPattern.agent_name == agent_name
            ).update({"is_resolved": True, "resolution_date": datetime.utcnow()})
            
            # Don't delete strategy performance or outcomes (valuable historical data)
            # Just mark patterns as resolved
            
            db.commit()
            
            logger.warning(
                "learning_data_reset",
                agent_name=agent_name,
                action="patterns_marked_resolved"
            )
            
            return {
                "status": "success",
                "message": f"Learning data reset for {agent_name} (patterns marked resolved)",
                "timestamp": datetime.utcnow().isoformat()
            }
    except Exception as e:
        logger.error("reset_learning_data_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
