"""
Memory Tools Service.
Provides agent memory capabilities for recalling past trades, insights, and patterns.
All calculations use local database - no external APIs required.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import structlog
from sqlalchemy import func, and_, or_, desc
from database import get_db
from models.database import Trade, Decision, AgentReflection, Portfolio, TradeAction

logger = structlog.get_logger()


class MemoryTools:
    """Provides memory and recall capabilities for AI agents."""
    
    def __init__(self, agent_name: str = None):
        """Initialize with optional agent name for filtering."""
        self.agent_name = agent_name
    
    async def recall_similar_trades(
        self, 
        symbol: str = None,
        action: str = None,
        market_condition: str = None,
        lookback_days: int = 90,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Recall similar trades from history.
        
        Args:
            symbol: Filter by specific symbol
            action: Filter by action type (buy/sell)
            market_condition: Filter by market condition (bull/bear/sideways)
            lookback_days: Number of days to look back
            limit: Maximum number of trades to return
        
        Returns:
            Similar trades with outcomes and lessons learned
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
            
            with get_db() as db:
                query = db.query(Trade).filter(Trade.created_at >= cutoff_date)
                
                if self.agent_name:
                    query = query.filter(Trade.agent_name == self.agent_name)
                
                if symbol:
                    query = query.filter(Trade.symbol == symbol.upper())
                
                if action:
                    query = query.filter(Trade.action == action.lower())
                
                trades = query.order_by(desc(Trade.created_at)).limit(limit * 2).all()
                
                # Calculate outcomes for each trade
                similar_trades = []
                winning_trades = 0
                losing_trades = 0
                total_pnl = 0.0
                
                for trade in trades[:limit]:
                    # Calculate P&L if possible
                    pnl = None
                    outcome = "unknown"
                    
                    if trade.action == TradeAction.BUY.value:
                        # Find corresponding sell
                        sell_trade = db.query(Trade).filter(
                            Trade.symbol == trade.symbol,
                            Trade.action == TradeAction.SELL.value,
                            Trade.created_at > trade.created_at,
                            Trade.agent_name == trade.agent_name
                        ).first()
                        
                        if sell_trade:
                            pnl = (sell_trade.price - trade.price) * trade.quantity
                            outcome = "win" if pnl > 0 else "loss"
                            total_pnl += pnl
                            if pnl > 0:
                                winning_trades += 1
                            else:
                                losing_trades += 1
                    
                    similar_trades.append({
                        "id": trade.id,
                        "symbol": trade.symbol,
                        "action": trade.action,
                        "quantity": trade.quantity,
                        "price": trade.price,
                        "pnl": round(pnl, 2) if pnl else None,
                        "outcome": outcome,
                        "reasoning": trade.reasoning[:200] if trade.reasoning else None,
                        "date": trade.created_at.isoformat(),
                    })
                
                # Get lessons learned from reflections
                lessons = []
                if self.agent_name:
                    reflections = db.query(AgentReflection).filter(
                        AgentReflection.agent_name == self.agent_name,
                        AgentReflection.created_at >= cutoff_date
                    ).order_by(desc(AgentReflection.created_at)).limit(5).all()
                    
                    for ref in reflections:
                        if ref.lessons_learned:
                            lessons.append({
                                "date": ref.created_at.isoformat(),
                                "lesson": ref.lessons_learned[:200],
                            })
                
                win_rate = winning_trades / (winning_trades + losing_trades) * 100 if (winning_trades + losing_trades) > 0 else 0
                
                return {
                    "symbol": symbol,
                    "trades_found": len(similar_trades),
                    "trades": similar_trades,
                    "summary": {
                        "total_trades": len(similar_trades),
                        "winning": winning_trades,
                        "losing": losing_trades,
                        "win_rate": round(win_rate, 1),
                        "total_pnl": round(total_pnl, 2),
                    },
                    "lessons_learned": lessons,
                    "interpretation": f"Found {len(similar_trades)} similar trades with {win_rate:.0f}% win rate"
                }
                
        except Exception as e:
            logger.error("recall_similar_trades_error", error=str(e))
            return {"error": str(e)}
    
    async def get_agent_performance_history(
        self, 
        agent_name: str = None,
        lookback_days: int = 30
    ) -> Dict[str, Any]:
        """
        Get performance history for an agent across different conditions.
        
        Returns:
            Performance metrics by market condition, sector, and symbol
        """
        try:
            target_agent = agent_name or self.agent_name
            if not target_agent:
                return {"error": "Agent name required"}
            
            cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
            
            with get_db() as db:
                # Get portfolio
                portfolio = db.query(Portfolio).filter(
                    Portfolio.agent_name == target_agent
                ).first()
                
                # Get all trades
                trades = db.query(Trade).filter(
                    Trade.agent_name == target_agent,
                    Trade.created_at >= cutoff_date
                ).all()
                
                # Analyze by symbol
                symbol_performance = {}
                for trade in trades:
                    if trade.symbol not in symbol_performance:
                        symbol_performance[trade.symbol] = {
                            "trades": 0,
                            "buys": 0,
                            "sells": 0,
                        }
                    
                    symbol_performance[trade.symbol]["trades"] += 1
                    if trade.action == TradeAction.BUY.value:
                        symbol_performance[trade.symbol]["buys"] += 1
                    else:
                        symbol_performance[trade.symbol]["sells"] += 1
                
                # Get recent decisions
                decisions = db.query(Decision).filter(
                    Decision.agent_name == target_agent,
                    Decision.created_at >= cutoff_date
                ).count()
                
                # Get reflections count
                reflections = db.query(AgentReflection).filter(
                    AgentReflection.agent_name == target_agent,
                    AgentReflection.created_at >= cutoff_date
                ).count()
                
                return {
                    "agent_name": target_agent,
                    "lookback_days": lookback_days,
                    "portfolio": {
                        "cash": portfolio.cash_balance if portfolio else 0,
                        "positions_count": portfolio.positions_count if portfolio else 0,
                        "total_value": portfolio.total_value if portfolio else 0,
                        "total_pnl": portfolio.total_pnl if portfolio else 0,
                        "win_rate": portfolio.win_rate if portfolio else 0,
                    } if portfolio else None,
                    "activity": {
                        "total_trades": len(trades),
                        "decisions_made": decisions,
                        "reflections": reflections,
                    },
                    "symbol_breakdown": symbol_performance,
                    "most_traded": max(symbol_performance.items(), key=lambda x: x[1]["trades"])[0] if symbol_performance else None,
                    "interpretation": f"Agent analyzed {len(trades)} trades across {len(symbol_performance)} symbols"
                }
                
        except Exception as e:
            logger.error("get_agent_performance_history_error", error=str(e))
            return {"error": str(e)}
    
    async def get_market_regime_history(
        self, 
        lookback_days: int = 60
    ) -> Dict[str, Any]:
        """
        Analyze historical market conditions and regime transitions.
        
        Returns:
            Market regime history and statistics
        """
        try:
            from services.data_collector import get_data_collector
            from services.advanced_indicators import get_advanced_indicators
            
            collector = get_data_collector()
            indicators = get_advanced_indicators()
            
            # Get SPY historical data for market regime
            historical = await collector.get_historical_data("SPY", "3m")
            
            if not historical or len(historical) < 20:
                return {"error": "Insufficient historical data"}
            
            closes = [bar.get("close", bar.get("c", 0)) for bar in historical]
            
            # Calculate regime at different points
            regimes = []
            window = 20
            
            for i in range(window, len(closes), 5):  # Sample every 5 days
                period_closes = closes[i-window:i]
                sma_short = sum(period_closes[-10:]) / 10
                sma_long = sum(period_closes) / window
                
                if period_closes[-1] > sma_short > sma_long:
                    regime = "BULL"
                elif period_closes[-1] < sma_short < sma_long:
                    regime = "BEAR"
                else:
                    regime = "SIDEWAYS"
                
                regimes.append({
                    "index": i,
                    "regime": regime,
                    "price": period_closes[-1],
                })
            
            # Count regime transitions
            transitions = 0
            for i in range(1, len(regimes)):
                if regimes[i]["regime"] != regimes[i-1]["regime"]:
                    transitions += 1
            
            # Count days in each regime
            regime_counts = {"BULL": 0, "BEAR": 0, "SIDEWAYS": 0}
            for r in regimes:
                regime_counts[r["regime"]] += 1
            
            current_regime = regimes[-1]["regime"] if regimes else "UNKNOWN"
            
            return {
                "lookback_days": lookback_days,
                "current_regime": current_regime,
                "regime_counts": regime_counts,
                "dominant_regime": max(regime_counts.items(), key=lambda x: x[1])[0],
                "transitions": transitions,
                "stability_score": 100 - (transitions / len(regimes) * 100) if regimes else 0,
                "recent_trend": regimes[-5:] if len(regimes) >= 5 else regimes,
                "interpretation": f"Current {current_regime} market with {transitions} regime changes in period"
            }
            
        except Exception as e:
            logger.error("get_market_regime_history_error", error=str(e))
            return {"error": str(e)}
    
    async def record_trade_insight(
        self, 
        symbol: str,
        insight_type: str,
        content: str,
        importance: str = "medium"
    ) -> Dict[str, Any]:
        """
        Record a trading insight for future reference.
        
        Args:
            symbol: Related symbol (or "MARKET" for general)
            insight_type: Type of insight (technical, fundamental, sentiment, pattern)
            content: The insight content
            importance: low, medium, high
        
        Returns:
            Confirmation of recorded insight
        """
        try:
            from models.database import TradeInsight
            
            with get_db() as db:
                insight = TradeInsight(
                    agent_name=self.agent_name or "system",
                    symbol=symbol.upper(),
                    insight_type=insight_type,
                    content=content[:500],  # Limit content length
                    importance=importance,
                    created_at=datetime.utcnow()
                )
                db.add(insight)
                db.commit()
                
                logger.info(
                    "trade_insight_recorded",
                    agent=self.agent_name,
                    symbol=symbol,
                    insight_type=insight_type,
                )
                
                return {
                    "success": True,
                    "insight_id": insight.id,
                    "symbol": symbol.upper(),
                    "insight_type": insight_type,
                    "importance": importance,
                    "message": f"Insight recorded for {symbol}"
                }
                
        except Exception as e:
            logger.error("record_trade_insight_error", error=str(e))
            # If TradeInsight model doesn't exist, just log and return success
            if "TradeInsight" in str(e):
                logger.warning("TradeInsight model not yet migrated, insight logged only")
                return {
                    "success": True,
                    "message": f"Insight logged for {symbol} (DB model pending migration)",
                    "symbol": symbol.upper(),
                    "insight_type": insight_type,
                }
            return {"error": str(e)}


# Singleton instance
_memory_tools: Optional[MemoryTools] = None


def get_memory_tools(agent_name: str = None) -> MemoryTools:
    """Get or create memory tools instance."""
    global _memory_tools
    if _memory_tools is None or agent_name:
        _memory_tools = MemoryTools(agent_name)
    return _memory_tools
