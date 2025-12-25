"""
Strategy Performance Model - Tracks success rates by strategy and market conditions.
Enables data-driven strategy selection and adaptive trading.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Index, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class StrategyPerformance(Base):
    """Performance tracking by strategy type and market condition."""
    __tablename__ = "strategy_performance"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String(50), nullable=False, index=True)
    
    # Strategy identification
    strategy_type = Column(String(100), nullable=False, index=True)
    # Examples: "momentum", "mean_reversion", "breakout", "value", "swing", "scalping"
    
    # Market condition
    market_condition = Column(String(50), nullable=False, index=True)
    # Examples: "bullish", "bearish", "sideways", "volatile", "low_volatility"
    
    # Performance metrics
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    breakeven_trades = Column(Integer, default=0)
    
    win_rate = Column(Float, default=0.0)  # Percentage
    
    # P&L metrics
    total_pnl = Column(Float, default=0.0)
    avg_pnl_per_trade = Column(Float, default=0.0)
    best_trade = Column(Float, default=0.0)
    worst_trade = Column(Float, default=0.0)
    
    # Risk metrics
    avg_win = Column(Float, default=0.0)
    avg_loss = Column(Float, default=0.0)
    profit_factor = Column(Float, default=1.0)  # Gross profit / Gross loss
    risk_reward_ratio = Column(Float, default=1.0)  # Avg win / Avg loss
    
    # Sharpe ratio (if we have enough data)
    sharpe_ratio = Column(Float, nullable=True)
    
    # Confidence score (0-100) based on sample size and consistency
    confidence_score = Column(Integer, default=0)
    
    # Timestamps
    first_trade_date = Column(DateTime, nullable=True)
    last_trade_date = Column(DateTime, nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint("agent_name", "strategy_type", "market_condition", name="uq_agent_strategy_market"),
        Index("idx_agent_strategy", "agent_name", "strategy_type"),
        Index("idx_strategy_condition", "strategy_type", "market_condition"),
    )
    
    def update_with_trade(self, pnl_amount: float, pnl_percent: float, trade_date: datetime):
        """Update strategy performance with a new trade result."""
        self.total_trades += 1
        
        # Categorize trade
        if pnl_percent > 0.5:
            self.winning_trades += 1
        elif pnl_percent < -0.5:
            self.losing_trades += 1
        else:
            self.breakeven_trades += 1
        
        # Update win rate
        self.win_rate = (self.winning_trades / self.total_trades) * 100
        
        # Update P&L
        self.total_pnl += pnl_amount
        self.avg_pnl_per_trade = self.total_pnl / self.total_trades
        
        if pnl_amount > self.best_trade:
            self.best_trade = pnl_amount
        if pnl_amount < self.worst_trade:
            self.worst_trade = pnl_amount
        
        # Update win/loss averages
        if pnl_amount > 0:
            self.avg_win = (
                (self.avg_win * (self.winning_trades - 1) + pnl_amount) / self.winning_trades
                if self.winning_trades > 0 else 0
            )
        elif pnl_amount < 0:
            self.avg_loss = (
                (self.avg_loss * (self.losing_trades - 1) + abs(pnl_amount)) / self.losing_trades
                if self.losing_trades > 0 else 0
            )
        
        # Calculate risk metrics
        if self.losing_trades > 0 and self.avg_loss > 0:
            gross_profit = self.avg_win * self.winning_trades
            gross_loss = self.avg_loss * self.losing_trades
            self.profit_factor = gross_profit / gross_loss if gross_loss > 0 else 1.0
            self.risk_reward_ratio = self.avg_win / self.avg_loss
        
        # Update dates
        if self.first_trade_date is None:
            self.first_trade_date = trade_date
        self.last_trade_date = trade_date
        
        # Calculate confidence score
        self._calculate_confidence()
    
    def _calculate_confidence(self):
        """
        Calculate confidence score (0-100) based on:
        - Sample size (more trades = higher confidence)
        - Consistency (stable win rate = higher confidence)
        - Recent activity (recent trades = higher confidence)
        """
        # Sample size component (0-50 points)
        sample_score = min(self.total_trades * 2, 50)
        
        # Win rate consistency (0-30 points)
        # Penalize extreme win rates with low sample size
        if self.total_trades < 5:
            consistency_score = 0
        elif 40 <= self.win_rate <= 60:
            consistency_score = 30  # Realistic win rate
        elif 30 <= self.win_rate <= 70:
            consistency_score = 20
        else:
            consistency_score = 10  # Suspicious win rate
        
        # Recency bonus (0-20 points)
        if self.last_trade_date:
            days_since = (datetime.utcnow() - self.last_trade_date).days
            if days_since < 7:
                recency_score = 20
            elif days_since < 30:
                recency_score = 10
            else:
                recency_score = 5
        else:
            recency_score = 0
        
        self.confidence_score = min(sample_score + consistency_score + recency_score, 100)
    
    def get_recommendation_strength(self) -> str:
        """Get recommendation strength based on performance and confidence."""
        if self.confidence_score < 30:
            return "insufficient_data"
        
        if self.win_rate >= 55 and self.profit_factor >= 1.5:
            return "strong_recommend"
        elif self.win_rate >= 50 and self.profit_factor >= 1.2:
            return "recommend"
        elif self.win_rate >= 40:
            return "neutral"
        else:
            return "avoid"
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "strategy_type": self.strategy_type,
            "market_condition": self.market_condition,
            "total_trades": self.total_trades,
            "win_rate": round(self.win_rate, 1),
            "avg_pnl_per_trade": round(self.avg_pnl_per_trade, 2),
            "profit_factor": round(self.profit_factor, 2),
            "risk_reward_ratio": round(self.risk_reward_ratio, 2),
            "confidence_score": self.confidence_score,
            "recommendation": self.get_recommendation_strength(),
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }
