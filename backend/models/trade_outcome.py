"""
Trade Outcome Model - Tracks post-trade performance and learning data.
Automatically calculates P&L and classifies errors for agent learning.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, 
    Text, Enum, ForeignKey, Index
)
from models.base import Base
import enum


class OutcomeCategory(str, enum.Enum):
    """Trade outcome categories."""
    WIN = "win"
    LOSS = "loss"
    BREAKEVEN = "breakeven"


class ErrorClassification(str, enum.Enum):
    """Types of trading errors."""
    BAD_TIMING = "bad_timing"  # Entered too early/late
    WRONG_SIZING = "wrong_sizing"  # Position too large/small
    MISSED_SIGNALS = "missed_signals"  # Ignored technical warnings
    EMOTIONAL = "emotional"  # FOMO, panic, revenge trading
    POOR_RISK_MANAGEMENT = "poor_risk_management"  # No stop-loss, etc.
    MARKET_CONDITION = "market_condition"  # External factors
    STRATEGY_MISMATCH = "strategy_mismatch"  # Wrong strategy for conditions
    NO_ERROR = "no_error"  # Clean win or unavoidable loss


class TradeOutcome(Base):
    """Post-trade analysis and performance tracking."""
    __tablename__ = "trade_outcomes"
    
    id = Column(Integer, primary_key=True, index=True)
    trade_id = Column(Integer, ForeignKey("trades.id"), nullable=False, unique=True, index=True)
    
    # Timing and closure
    close_date = Column(DateTime, nullable=False, index=True)
    hold_duration_hours = Column(Float, nullable=False)  # How long position was held
    
    # Performance metrics
    entry_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=False)
    pnl_amount = Column(Float, nullable=False)  # Absolute P&L in dollars
    pnl_percent = Column(Float, nullable=False)  # Percentage return
    
    # Risk metrics during hold
    max_gain_percent = Column(Float, default=0.0)  # Best unrealized gain during hold
    max_loss_percent = Column(Float, default=0.0)  # Worst unrealized loss during hold
    
    # Classification
    outcome_category = Column(Enum(OutcomeCategory), nullable=False, index=True)
    error_classification = Column(Enum(ErrorClassification), nullable=True, index=True)
    
    # Learning data
    error_description = Column(Text, nullable=True)  # Detailed explanation of what went wrong
    lesson_learned = Column(Text, nullable=True)  # Actionable takeaway
    learning_extracted = Column(Boolean, default=False)  # Has feedback been generated?
    
    # Context at time of trade
    market_condition = Column(String(50), nullable=True)  # bullish, bearish, sideways, volatile
    strategy_used = Column(String(100), nullable=True)  # Extracted from trade reasoning
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    analyzed_at = Column(DateTime, nullable=True)  # When AI analysis was performed
    
    __table_args__ = (
        Index("idx_outcome_category", "outcome_category", "close_date"),
        Index("idx_error_class", "error_classification", "close_date"),
    )
    
    def calculate_metrics(self, entry_price: float, close_price: float, quantity: float, hold_hours: float):
        """Calculate all performance metrics."""
        self.entry_price = entry_price
        self.close_price = close_price
        self.hold_duration_hours = hold_hours
        
        # Calculate P&L
        pnl = (close_price - entry_price) * quantity
        pnl_pct = ((close_price - entry_price) / entry_price) * 100
        
        self.pnl_amount = pnl
        self.pnl_percent = pnl_pct
        
        # Categorize outcome
        if pnl_pct > 0.5:
            self.outcome_category = OutcomeCategory.WIN
        elif pnl_pct < -0.5:
            self.outcome_category = OutcomeCategory.LOSS
        else:
            self.outcome_category = OutcomeCategory.BREAKEVEN
        
        return self
    
    def classify_error(self, trade_reasoning: str = None) -> ErrorClassification:
        """
        Heuristic error classification based on outcome metrics.
        Can be enhanced with LLM analysis later.
        """
        if self.outcome_category == OutcomeCategory.WIN:
            self.error_classification = ErrorClassification.NO_ERROR
            return self.error_classification
        
        # Loss with very short hold time suggests bad timing
        if self.hold_duration_hours < 2 and self.pnl_percent < -2:
            self.error_classification = ErrorClassification.BAD_TIMING
            self.error_description = "Position closed quickly with significant loss - possible bad entry timing"
        
        # Large loss suggests sizing or risk management issue
        elif abs(self.pnl_percent) > 10:
            self.error_classification = ErrorClassification.POOR_RISK_MANAGEMENT
            self.error_description = "Large loss exceeds acceptable risk thresholds"
        
        # Had significant unrealized gain but closed at loss - emotional or poor exit
        elif self.max_gain_percent > 5 and self.pnl_percent < 0:
            self.error_classification = ErrorClassification.EMOTIONAL
            self.error_description = f"Failed to take profits at +{self.max_gain_percent:.1f}%, closed at {self.pnl_percent:.1f}%"
        
        # Default to market condition if can't classify
        else:
            self.error_classification = ErrorClassification.MARKET_CONDITION
            self.error_description = "Loss attributed to market conditions"
        
        return self.error_classification
