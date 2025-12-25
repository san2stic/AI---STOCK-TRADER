"""
Error Tracker Service - Monitors trade outcomes and detects errors.
Automatically analyzes closed positions and generates feedback for agents.
"""
import structlog
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from models.database import Trade, TradeStatus, Portfolio
from models.trade_outcome import TradeOutcome, OutcomeCategory, ErrorClassification
from models.error_pattern import ErrorPattern
from database import get_db

logger = structlog.get_logger()


class ErrorTracker:
    """
    Tracks trade outcomes and identifies error patterns.
    Singleton service for monitoring agent performance.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ErrorTracker, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            logger.info("error_tracker_initialized")
    
    async def scan_closed_positions(self) -> List[int]:
        """
        Scan for trades that have been closed but not yet analyzed.
        Returns list of trade IDs that were processed.
        """
        processed_trades = []
        
        try:
            with get_db() as db:
                # Find executed trades without outcomes
                unanalyzed_trades = db.query(Trade).filter(
                    Trade.status == TradeStatus.EXECUTED,
                    ~Trade.id.in_(
                        db.query(TradeOutcome.trade_id)
                    )
                ).all()
                
                logger.info(
                    "scanning_closed_positions",
                    unanalyzed_count=len(unanalyzed_trades)
                )
                
                for trade in unanalyzed_trades:
                    # Check if position is actually closed
                    if await self._is_position_closed(trade, db):
                        outcome_id = await self.track_trade_outcome(trade.id)
                        if outcome_id:
                            processed_trades.append(trade.id)
                
                logger.info(
                    "closed_positions_processed",
                    processed_count=len(processed_trades)
                )
                
        except Exception as e:
            logger.error("scan_closed_positions_error", error=str(e))
        
        return processed_trades
    
    async def _is_position_closed(self, trade: Trade, db: Session) -> bool:
        """
        Check if a position is fully closed.
        For now, we consider a trade closed if it was executed more than 1 hour ago.
        In production, you'd check actual portfolio positions.
        """
        # Get agent's current portfolio
        portfolio = db.query(Portfolio).filter(
            Portfolio.agent_name == trade.agent_name
        ).first()
        
        if not portfolio or not portfolio.positions:
            return True
        
        # Check if symbol still in positions
        symbol = trade.symbol
        positions = portfolio.positions
        
        if isinstance(positions, dict):
            if symbol not in positions or positions[symbol].get('quantity', 0) == 0:
                return True
        
        # Also consider closed if trade is old enough
        if trade.executed_at:
            hours_since = (datetime.utcnow() - trade.executed_at).total_seconds() / 3600
            if hours_since > 24:  # Assume closed after 24 hours
                return True
        
        return False
    
    async def track_trade_outcome(self, trade_id: int) -> Optional[int]:
        """
        Calculate and store outcome for a completed trade.
        Returns outcome ID if successful.
        """
        try:
            with get_db() as db:
                trade = db.query(Trade).filter(Trade.id == trade_id).first()
                
                if not trade:
                    logger.warning("trade_not_found", trade_id=trade_id)
                    return None
                
                # Check if outcome already exists
                existing = db.query(TradeOutcome).filter(
                    TradeOutcome.trade_id == trade_id
                ).first()
                
                if existing:
                    return existing.id
                
                # Calculate outcome metrics
                outcome = await self._calculate_outcome(trade, db)
                
                if outcome:
                    db.add(outcome)
                    db.commit()
                    db.refresh(outcome)
                    
                    logger.info(
                        "trade_outcome_tracked",
                        trade_id=trade_id,
                        outcome_id=outcome.id,
                        category=outcome.outcome_category.value,
                        pnl_percent=round(outcome.pnl_percent, 2)
                    )
                    
                    # If it's a loss, check for error patterns
                    if outcome.outcome_category == OutcomeCategory.LOSS:
                        await self.detect_error_patterns(trade.agent_name, outcome, db)
                    
                    return outcome.id
                
        except Exception as e:
            logger.error("track_trade_outcome_error", trade_id=trade_id, error=str(e))
        
        return None
    
    async def _calculate_outcome(self, trade: Trade, db: Session) -> Optional[TradeOutcome]:
        """Calculate outcome metrics for a trade."""
        try:
            # For now, simulate closing prices
            # In production, you'd get actual close price from broker/exchange
            entry_price = trade.price or 0
            
            if entry_price == 0:
                return None
            
            # Simulate a close price (±5% random for testing)
            # TODO: Replace with actual close price from broker
            import random
            close_price = entry_price * (1 + random.uniform(-0.05, 0.05))
            
            # Calculate hold duration
            if trade.executed_at:
                hold_hours = (datetime.utcnow() - trade.executed_at).total_seconds() / 3600
            else:
                hold_hours = 0
            
            # Create outcome
            outcome = TradeOutcome(
                trade_id=trade.id,
                close_date=datetime.utcnow()
            )
            
            # Calculate metrics
            outcome.calculate_metrics(
                entry_price=entry_price,
                close_price=close_price,
                quantity=trade.quantity,
                hold_hours=hold_hours
            )
            
            # Simulate max gain/loss during hold (for testing)
            outcome.max_gain_percent = abs(random.uniform(0, outcome.pnl_percent * 1.5))
            outcome.max_loss_percent = abs(random.uniform(0, outcome.pnl_percent * 1.5))
            
            # Classify error if applicable
            outcome.classify_error(trade.reasoning)
            
            # Extract strategy from reasoning if available
            if trade.reasoning:
                outcome.strategy_used = self._extract_strategy(trade.reasoning)
            
            # Detect market condition (simplified)
            outcome.market_condition = "neutral"  # TODO: Enhance with actual market analysis
            
            outcome.analyzed_at = datetime.utcnow()
            
            return outcome
            
        except Exception as e:
            logger.error("calculate_outcome_error", error=str(e))
            return None
    
    def _extract_strategy(self, reasoning: str) -> str:
        """Extract strategy type from trade reasoning."""
        reasoning_lower = reasoning.lower()
        
        # Simple keyword matching
        if "momentum" in reasoning_lower:
            return "momentum"
        elif "breakout" in reasoning_lower:
            return "breakout"
        elif "reversal" in reasoning_lower or "mean reversion" in reasoning_lower:
            return "mean_reversion"
        elif "value" in reasoning_lower:
            return "value"
        elif "swing" in reasoning_lower:
            return "swing"
        else:
            return "general"
    
    async def detect_error_patterns(
        self, 
        agent_name: str, 
        outcome: TradeOutcome,
        db: Session
    ) -> Optional[ErrorPattern]:
        """
        Detect if this error matches an existing pattern or create a new one.
        """
        try:
            error_type = outcome.error_classification.value if outcome.error_classification else "unknown"
            
            # Generate context for pattern matching
            context = f"{outcome.strategy_used or 'unknown'}_{outcome.market_condition or 'unknown'}"
            signature = ErrorPattern.generate_signature(agent_name, error_type, context)
            
            # Check if pattern exists
            pattern = db.query(ErrorPattern).filter(
                ErrorPattern.agent_name == agent_name,
                ErrorPattern.pattern_signature == signature
            ).first()
            
            if pattern:
                # Update existing pattern
                pattern.update_occurrence(
                    loss_amount=abs(outcome.pnl_amount),
                    loss_percent=abs(outcome.pnl_percent),
                    trade_id=outcome.trade_id
                )
                db.commit()
                
                logger.info(
                    "error_pattern_updated",
                    agent_name=agent_name,
                    pattern_id=pattern.id,
                    occurrences=pattern.occurrence_count
                )
            else:
                # Create new pattern
                pattern = ErrorPattern(
                    agent_name=agent_name,
                    pattern_type=error_type,
                    pattern_signature=signature,
                    title=f"{error_type.replace('_', ' ').title()} Pattern",
                    description=f"Agent tends to experience {error_type} errors when trading {outcome.strategy_used} strategy in {outcome.market_condition} conditions",
                    total_loss_amount=abs(outcome.pnl_amount),
                    avg_loss_amount=abs(outcome.pnl_amount),
                    avg_loss_percent=abs(outcome.pnl_percent),
                    first_seen=datetime.utcnow(),
                    last_seen=datetime.utcnow(),
                    example_trade_ids=str(outcome.trade_id)
                )
                
                # Generate suggested fix
                pattern.suggested_fix = self._generate_fix_suggestion(error_type, outcome)
                pattern.actionable_rule = self._generate_actionable_rule(error_type, outcome)
                
                db.add(pattern)
                db.commit()
                
                logger.info(
                    "error_pattern_created",
                    agent_name=agent_name,
                    pattern_id=pattern.id,
                    pattern_type=error_type
                )
            
            return pattern
            
        except Exception as e:
            logger.error("detect_error_patterns_error", error=str(e))
            return None
    
    def _generate_fix_suggestion(self, error_type: str, outcome: TradeOutcome) -> str:
        """Generate remediation suggestion based on error type."""
        suggestions = {
            "bad_timing": "Wait for confirmation signals before entry. Use multiple timeframe analysis.",
            "wrong_sizing": f"Limit position size to max 5% of portfolio. Your loss was {abs(outcome.pnl_percent):.1f}%.",
            "missed_signals": "Set alerts for key technical levels. Review indicators before entry.",
            "emotional": "Implement mandatory stop-loss orders. Take profits at predetermined targets.",
            "poor_risk_management": "Always use stop-loss orders. Risk no more than 2% per trade.",
            "market_condition": "Adjust strategy to current market regime. Consider sitting out unfavorable conditions.",
            "strategy_mismatch": f"Avoid {outcome.strategy_used} strategy in {outcome.market_condition} markets."
        }
        return suggestions.get(error_type, "Review trade criteria and risk parameters.")
    
    def _generate_actionable_rule(self, error_type: str, outcome: TradeOutcome) -> str:
        """Generate IF-THEN rule to prevent recurrence."""
        rules = {
            "bad_timing": "IF position goes against you within 2 hours THEN exit immediately and reassess",
            "wrong_sizing": "IF trade size > 5% of portfolio THEN reduce to maximum 5%",
            "missed_signals": "IF RSI > 70 or < 30 THEN wait for mean reversion before entering",
            "emotional": "IF unrealized gain > 5% THEN take at least 50% profit",
            "poor_risk_management": "IF no stop-loss set THEN do not enter trade",
            "market_condition": f"IF market is {outcome.market_condition} THEN reduce position sizing by 50%",
            "strategy_mismatch": f"IF using {outcome.strategy_used} AND market is {outcome.market_condition} THEN skip trade"
        }
        return rules.get(error_type, "IF similar setup appears THEN review past outcomes first")
    
    async def get_agent_error_summary(
        self, 
        agent_name: str, 
        days: int = 30
    ) -> Dict[str, Any]:
        """Get aggregated error statistics for an agent."""
        try:
            with get_db() as db:
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                
                # Get outcomes in time range
                outcomes = db.query(TradeOutcome).join(
                    Trade, TradeOutcome.trade_id == Trade.id
                ).filter(
                    Trade.agent_name == agent_name,
                    TradeOutcome.close_date >= cutoff_date
                ).all()
                
                # Get active error patterns
                patterns = db.query(ErrorPattern).filter(
                    ErrorPattern.agent_name == agent_name,
                    ErrorPattern.is_resolved == False
                ).order_by(ErrorPattern.severity_score.desc()).all()
                
                # Calculate stats
                total_outcomes = len(outcomes)
                losses = [o for o in outcomes if o.outcome_category == OutcomeCategory.LOSS]
                wins = [o for o in outcomes if o.outcome_category == OutcomeCategory.WIN]
                
                return {
                    "agent_name": agent_name,
                    "period_days": days,
                    "total_trades": total_outcomes,
                    "losses": len(losses),
                    "wins": len(wins),
                    "win_rate": (len(wins) / total_outcomes * 100) if total_outcomes > 0 else 0,
                    "active_error_patterns": len(patterns),
                    "top_patterns": [p.to_dict() for p in patterns[:5]],
                    "most_severe_error": patterns[0].to_dict() if patterns else None
                }
                
        except Exception as e:
            logger.error("get_agent_error_summary_error", error=str(e))
            return {}


# Singleton instance
def get_error_tracker() -> ErrorTracker:
    """Get the singleton ErrorTracker instance."""
    return ErrorTracker()
