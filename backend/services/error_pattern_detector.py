"""
Error Pattern Detector Service - Identifies recurring error patterns using statistical analysis.
Scans trade history to find systematic mistakes and generate learning insights.
"""
import structlog
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from models.database import Trade, TradeStatus
from models.trade_outcome import TradeOutcome, OutcomeCategory, ErrorClassification
from models.error_pattern import ErrorPattern
from models.strategy_performance import StrategyPerformance
from database import get_db

logger = structlog.get_logger()


class ErrorPatternDetector:
    """
    Detects and catalogs recurring error patterns.
    Uses statistical analysis to identify systematic mistakes.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ErrorPatternDetector, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            logger.info("error_pattern_detector_initialized")
    
    async def scan_for_patterns(
        self, 
        agent_name: str, 
        lookback_days: int = 90
    ) -> List[ErrorPattern]:
        """
        Scan agent's trade history for recurring error patterns.
        Returns list of detected patterns.
        """
        try:
            with get_db() as db:
                cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
                
                # Get trade outcomes in the period
                outcomes = db.query(TradeOutcome).join(
                    Trade, TradeOutcome.trade_id == Trade.id
                ).filter(
                    Trade.agent_name == agent_name,
                    TradeOutcome.close_date >= cutoff_date
                ).all()
                
                if len(outcomes) < 5:  # Need minimum data
                    logger.info(
                        "insufficient_data_for_patterns",
                        agent_name=agent_name,
                        outcome_count=len(outcomes)
                    )
                    return []
                
                detected_patterns = []
                
                # Pattern 1: Analyze by error classification
                error_patterns = await self._analyze_error_clusters(agent_name, outcomes, db)
                detected_patterns.extend(error_patterns)
                
                # Pattern 2: Analyze by strategy performance
                strategy_patterns = await self._analyze_strategy_performance(agent_name, outcomes, db)
                detected_patterns.extend(strategy_patterns)
                
                # Pattern 3: Analyze by symbol/asset
                symbol_patterns = await self._analyze_symbol_patterns(agent_name, outcomes, db)
                detected_patterns.extend(symbol_patterns)
                
                # Pattern 4: Analyze timing patterns
                timing_patterns = await self._analyze_timing_patterns(agent_name, outcomes,db)
                detected_patterns.extend(timing_patterns)
                
                logger.info(
                    "pattern_scan_complete",
                    agent_name=agent_name,
                    patterns_detected=len(detected_patterns),
                    lookback_days=lookback_days
                )
                
                return detected_patterns
                
        except Exception as e:
            logger.error("scan_for_patterns_error", error=str(e))
            return []
    
    async def _analyze_error_clusters(
        self,
        agent_name: str,
        outcomes: List[TradeOutcome],
        db
    ) -> List[ErrorPattern]:
        """Find patterns in error classifications."""
        patterns = []
        
        # Group losses by error type
        error_groups = defaultdict(list)
        for outcome in outcomes:
            if outcome.outcome_category == OutcomeCategory.LOSS and outcome.error_classification:
                error_groups[outcome.error_classification.value].append(outcome)
        
        # Check each error type for significance
        for error_type, error_outcomes in error_groups.items():
            if len(error_outcomes) >= 3:  # At least 3 occurrences
                # Calculate statistics
                avg_loss = sum(abs(o.pnl_percent) for o in error_outcomes) / len(error_outcomes)
                total_loss = sum(abs(o.pnl_amount) for o in error_outcomes)
                
                # Check if pattern already exists
                context = "general"
                signature = ErrorPattern.generate_signature(agent_name, error_type, context)
                
                existing = db.query(ErrorPattern).filter(
                    ErrorPattern.agent_name == agent_name,
                    ErrorPattern.pattern_signature == signature
                ).first()
                
                if existing:
                    continue
                
                # Create pattern
                pattern = ErrorPattern(
                    agent_name=agent_name,
                    pattern_type=error_type,
                    pattern_signature=signature,
                    title=f"Recurring {error_type.replace('_', ' ').title()}",
                    description=f"Agent has {len(error_outcomes)} instances of {error_type} errors (avg loss: {avg_loss:.1f}%)",
                    occurrence_count=len(error_outcomes),
                    total_loss_amount=total_loss,
                    avg_loss_amount=total_loss / len(error_outcomes),
                    avg_loss_percent=avg_loss,
                    first_seen=min(o.close_date for o in error_outcomes),
                    last_seen=max(o.close_date for o in error_outcomes),
                    suggested_fix=self._get_error_fix(error_type),
                    actionable_rule=self._get_actionable_rule(error_type),
                    example_trade_ids=','.join(str(o.trade_id) for o in error_outcomes[:5])
                )
                
                pattern.severity_score = min(len(error_outcomes) + int(avg_loss / 2), 10)
                
                db.add(pattern)
                patterns.append(pattern)
        
        if patterns:
            db.commit()
        
        return patterns
    
    async def _analyze_strategy_performance(
        self,
        agent_name: str,
        outcomes: List[TradeOutcome],
        db
    ) -> List[ErrorPattern]:
        """Analyze performance by strategy and update StrategyPerformance table."""
        patterns = []
        
        # Group by strategy and market condition
        strategy_groups = defaultdict(list)
        for outcome in outcomes:
            key = (outcome.strategy_used or "unknown", outcome.market_condition or "unknown")
            strategy_groups[key].append(outcome)
        
        # Update StrategyPerformance records
        for (strategy, market_cond), strat_outcomes in strategy_groups.items():
            if len(strat_outcomes) < 2:
                continue
            
            # Get or create StrategyPerformance record
            perf = db.query(StrategyPerformance).filter(
                StrategyPerformance.agent_name == agent_name,
                StrategyPerformance.strategy_type == strategy,
                StrategyPerformance.market_condition == market_cond
            ).first()
            
            if not perf:
                perf = StrategyPerformance(
                    agent_name=agent_name,
                    strategy_type=strategy,
                    market_condition=market_cond
                )
                db.add(perf)
            
            # Update with new outcomes
            for outcome in strat_outcomes:
                perf.update_with_trade(
                    pnl_amount=outcome.pnl_amount,
                    pnl_percent=outcome.pnl_percent,
                    trade_date=outcome.close_date
                )
            
            # Check if this strategy performs poorly
            if perf.total_trades >= 5 and perf.win_rate < 40:
                # Create error pattern for poor strategy
                signature = ErrorPattern.generate_signature(
                    agent_name, 
                    "strategy_mismatch",
                    f"{strategy}_{market_cond}"
                )
                
                existing = db.query(ErrorPattern).filter(
                    ErrorPattern.pattern_signature == signature
                ).first()
                
                if not existing:
                    losses = [o for o in strat_outcomes if o.outcome_category == OutcomeCategory.LOSS]
                    
                    pattern = ErrorPattern(
                        agent_name=agent_name,
                        pattern_type="strategy_mismatch",
                        pattern_signature=signature,
                        title=f"Poor Performance: {strategy} in {market_cond} markets",
                        description=f"Win rate only {perf.win_rate:.1f}% when using {strategy} strategy in {market_cond} conditions",
                        occurrence_count=len(losses),
                        total_loss_amount=sum(abs(o.pnl_amount) for o in losses),
                        avg_loss_amount=sum(abs(o.pnl_amount) for o in losses) / len(losses) if losses else 0,
                        avg_loss_percent=sum(abs(o.pnl_percent) for o in losses) / len(losses) if losses else 0,
                        first_seen=min(o.close_date for o in strat_outcomes),
                        last_seen=max(o.close_date for o in strat_outcomes),
                        suggested_fix=f"Avoid {strategy} strategy when market is {market_cond}. Consider alternative approaches.",
                        actionable_rule=f"IF strategy=={strategy} AND market_condition=={market_cond} THEN skip trade or use different strategy",
                        severity_score=8 if perf.win_rate < 30 else 6
                    )
                    
                    db.add(pattern)
                    patterns.append(pattern)
        
        if patterns:
            db.commit()
        
        return patterns
    
    async def _analyze_symbol_patterns(
        self,
        agent_name: str,
        outcomes: List[TradeOutcome],
        db
    ) -> List[ErrorPattern]:
        """Detect patterns related to specific symbols."""
        patterns = []
        
        # Get trades with symbols
        symbol_performance = defaultdict(lambda: {"wins": 0, "losses": 0, "total_pnl": 0, "outcomes": []})
        
        for outcome in outcomes:
            # Get associated trade to find symbol
            trade = db.query(Trade).filter(Trade.id == outcome.trade_id).first()
            if trade:
                symbol = trade.symbol
                if outcome.outcome_category == OutcomeCategory.WIN:
                    symbol_performance[symbol]["wins"] += 1
                elif outcome.outcome_category == OutcomeCategory.LOSS:
                    symbol_performance[symbol]["losses"] += 1
                symbol_performance[symbol]["total_pnl"] += outcome.pnl_amount
                symbol_performance[symbol]["outcomes"].append(outcome)
        
        # Find symbols with poor performance
        for symbol, stats in symbol_performance.items():
            total = stats["wins"] + stats["losses"]
            if total >= 3 and stats["losses"] > stats["wins"] * 1.5:  # More losses than wins
                win_rate = (stats["wins"] / total) * 100
                
                signature = ErrorPattern.generate_signature(
                    agent_name,
                    "poor_symbol_selection",
                    symbol
                )
                
                existing = db.query(ErrorPattern).filter(
                    ErrorPattern.pattern_signature == signature
                ).first()
                
                if not existing:
                    pattern = ErrorPattern(
                        agent_name=agent_name,
                        pattern_type="poor_symbol_selection",
                        pattern_signature=signature,
                        title=f"Poor Performance on {symbol}",
                        description=f"Win rate of {win_rate:.1f}% on {symbol} ({stats['wins']} wins vs {stats['losses']} losses)",
                        occurrence_count=stats["losses"],
                        total_loss_amount=abs(min(stats["total_pnl"], 0)),
                        avg_loss_amount=abs(stats["total_pnl"] / total),
                        avg_loss_percent=sum(abs(o.pnl_percent) for o in stats["outcomes"] if o.outcome_category == OutcomeCategory.LOSS) / stats["losses"] if stats["losses"] > 0 else 0,
                        first_seen=min(o.close_date for o in stats["outcomes"]),
                        last_seen=max(o.close_date for o in stats["outcomes"]),
                        suggested_fix=f"Reconsider trading {symbol}. Analyze why this asset underperforms.",
                        actionable_rule=f"IF symbol=={symbol} THEN increase analysis rigor or skip",
                        severity_score=7
                    )
                    
                    db.add(pattern)
                    patterns.append(pattern)
        
        if patterns:
            db.commit()
        
        return patterns
    
    async def _analyze_timing_patterns(
        self,
        agent_name: str,
        outcomes: List[TradeOutcome],
        db
    ) -> List[ErrorPattern]:
        """Detect patterns related to trade timing (quick losses, etc.)."""
        patterns = []
        
        # Find quick losses (held < 4 hours and lost)
        quick_losses = [
            o for o in outcomes
            if o.outcome_category == OutcomeCategory.LOSS 
            and o.hold_duration_hours < 4
            and abs(o.pnl_percent) > 2
        ]
        
        if len(quick_losses) >= 4:
            signature = ErrorPattern.generate_signature(
                agent_name,
                "bad_timing",
                "quick_exits"
            )
            
            existing = db.query(ErrorPattern).filter(
                ErrorPattern.pattern_signature == signature
            ).first()
            
            if not existing:
                avg_loss = sum(abs(o.pnl_percent) for o in quick_losses) / len(quick_losses)
                
                pattern = ErrorPattern(
                    agent_name=agent_name,
                    pattern_type="bad_timing",
                    pattern_signature=signature,
                    title="Frequent Quick Losses",
                    description=f"{len(quick_losses)} trades closed with loss within 4 hours (avg loss: {avg_loss:.1f}%)",
                    occurrence_count=len(quick_losses),
                    total_loss_amount=sum(abs(o.pnl_amount) for o in quick_losses),
                    avg_loss_amount=sum(abs(o.pnl_amount) for o in quick_losses) / len(quick_losses),
                    avg_loss_percent=avg_loss,
                    first_seen=min(o.close_date for o in quick_losses),
                    last_seen=max(o.close_date for o in quick_losses),
                    suggested_fix="Wait for stronger confirmation before entering. Consider using limit orders at better prices.",
                    actionable_rule="IF position negative after 1 hour AND no clear reversal signals THEN exit to minimize loss",
                    severity_score=7
                )
                
                db.add(pattern)
                db.commit()
                patterns.append(pattern)
        
        return patterns
    
    def _get_error_fix(self, error_type: str) -> str:
        """Get suggested fix for error type."""
        fixes = {
            "bad_timing": "Use multiple timeframe confirmation before entry",
            "wrong_sizing": "Calculate position size based on portfolio % and volatility",
            "missed_signals": "Set up alerts for key technical levels",
            "emotional": "Follow predetermined rules, use stop-loss orders",
            "poor_risk_management": "Always set stop-loss at entry, max 2% risk per trade",
            "strategy_mismatch": "Match strategy to current market regime"
        }
        return fixes.get(error_type, "Review and adjust trading criteria")
    
    def _get_actionable_rule(self, error_type: str) -> str:
        """Get actionable rule for error type."""
        rules = {
            "bad_timing": "IF position goes red within 2 hours THEN exit and reassess",
            "wrong_sizing": "IF trade size > 5% portfolio THEN reduce to max 5%",
            "missed_signals": "IF RSI > 70 or < 30 THEN wait for mean reversion",
            "emotional": "IF unrealized gain > 5% THEN take at least 50% profit",
            "poor_risk_management": "IF no stop-loss set THEN do not enter trade",
            "strategy_mismatch": "IF strategy doesn't match market condition THEN skip trade"
        }
        return rules.get(error_type, "IF similar setup appears THEN review past outcomes first")


# Singleton instance
def get_error_pattern_detector() -> ErrorPatternDetector:
    """Get the singleton ErrorPatternDetector instance."""
    return ErrorPatternDetector()
