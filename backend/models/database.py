"""
Database models for the trading system.
Stores trades, decisions, portfolios, and agent reflections.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, 
    Text, JSON, Enum, ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
import enum

from models.base import Base

# Import learning models to register them with SQLAlchemy
# We use string references in relationships to avoid circular imports if needed, 
# but simply importing them here registers them with Base.metadata
from models.trade_outcome import TradeOutcome, OutcomeCategory, ErrorClassification
from models.error_pattern import ErrorPattern
from models.strategy_performance import StrategyPerformance


class TradeAction(str, enum.Enum):
    """Trade action types."""
    BUY = "buy"
    SELL = "sell"


class AssetType(str, enum.Enum):
    """Asset type for trading."""
    STOCK = "stock"
    CRYPTO = "crypto"


class TradeStatus(str, enum.Enum):
    """Trade status types."""
    PENDING = "pending"
    EXECUTED = "executed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Trade(Base):
    """Trade execution records."""
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String(50), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)  # Increased to support crypto pairs
    asset_type = Column(Enum(AssetType), default=AssetType.STOCK, nullable=False, index=True)
    action = Column(Enum(TradeAction), nullable=False)
    quantity = Column(Float, nullable=False)  # Changed to Float for crypto fractional amounts
    price = Column(Float, nullable=True)  # Execution price
    total_value = Column(Float, nullable=True)
    
    status = Column(Enum(TradeStatus), default=TradeStatus.PENDING, index=True)
    reasoning = Column(Text, nullable=True)  # AI's reasoning
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    executed_at = Column(DateTime, nullable=True)
    
    # Risk metrics at trade time
    portfolio_value_before = Column(Float, nullable=True)
    cash_before = Column(Float, nullable=True)
    position_size_percent = Column(Float, nullable=True)
    
    # Results
    error_message = Column(Text, nullable=True)
    
    # Relationship to decision
    decision_id = Column(Integer, ForeignKey("decisions.id"), nullable=True)
    
    __table_args__ = (
        Index("idx_agent_created", "agent_name", "created_at"),
        Index("idx_symbol_created", "symbol", "created_at"),
    )


class Decision(Base):
    """AI agent decision logs with full context."""
    __tablename__ = "decisions"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String(50), nullable=False, index=True)
    
    # Context provided to agent
    market_context = Column(JSON, nullable=True)  # Price data, news, etc.
    portfolio_context = Column(JSON, nullable=True)  # Current holdings
    
    # Agent's response
    raw_response = Column(Text, nullable=True)  # Full AI response
    tool_calls = Column(JSON, nullable=True)  # Parsed function calls
    final_action = Column(String(20), nullable=True)  # buy/sell/hold
    reasoning = Column(Text, nullable=True)
    
    # Execution
    was_executed = Column(Boolean, default=False)
    execution_error = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    trades = relationship("Trade", backref="decision")
    
    __table_args__ = (
        Index("idx_agent_created_dec", "agent_name", "created_at"),
    )


class Portfolio(Base):
    """Current portfolio state per agent."""
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String(50), nullable=False, unique=True, index=True)
    
    # Cash and total value
    cash = Column(Float, nullable=False, default=0.0)
    total_value = Column(Float, nullable=False, default=0.0)  # Cash + positions
    initial_value = Column(Float, nullable=False)
    
    # Positions (JSON: {symbol: {quantity, avg_price, current_value, asset_type}})
    positions = Column(JSON, nullable=True, default=dict)
    
    # Separate tracking for stock and crypto values
    stock_value = Column(Float, default=0.0)
    crypto_value = Column(Float, default=0.0)
    
    # Performance metrics
    total_pnl = Column(Float, default=0.0)
    total_pnl_percent = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    unrealized_pnl = Column(Float, default=0.0)
    
    # Trading stats
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    
    # Risk metrics
    max_drawdown = Column(Float, default=0.0)
    max_drawdown_percent = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, nullable=True)
    
    # API costs
    openrouter_cost_total = Column(Float, default=0.0)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class AgentReflection(Base):
    """Agent self-critique and learning logs."""
    __tablename__ = "agent_reflections"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String(50), nullable=False, index=True)
    
    # Context for reflection
    trades_analyzed = Column(JSON, nullable=True)  # Last N trades
    performance_stats = Column(JSON, nullable=True)
    
    # Agent's reflection
    what_went_well = Column(Text, nullable=True)
    what_went_wrong = Column(Text, nullable=True)
    improvements_planned = Column(Text, nullable=True)
    raw_reflection = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index("idx_agent_created_ref", "agent_name", "created_at"),
    )


class MarketData(Base):
    """Cached market data to reduce API calls."""
    __tablename__ = "market_data"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)  # Support crypto pairs
    data_type = Column(String(50), nullable=False)  # price, historical, news, crypto_price, crypto_historical
    
    data = Column(JSON, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False, index=True)
    
    __table_args__ = (
        UniqueConstraint("symbol", "data_type", name="uq_symbol_data_type"),
        Index("idx_symbol_type_expires", "symbol", "data_type", "expires_at"),
    )


class SystemLog(Base):
    """System-level logs for monitoring."""
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(20), nullable=False, index=True)  # INFO, WARNING, ERROR
    component = Column(String(50), nullable=False, index=True)  # agent, ib_connector, etc.
    message = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index("idx_level_created", "level", "created_at"),
        Index("idx_component_created", "component", "created_at"),
    )


class Watchlist(Base):
    """User or Agent defined watchlist for tracking specific assets."""
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String(50), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    reason = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("agent_name", "symbol", name="uq_agent_symbol"),
    )


class WebSearchResult(Base):
    """Stored web search results for historical tracking."""
    __tablename__ = "web_search_results"

    id = Column(Integer, primary_key=True, index=True)
    query = Column(String(255), nullable=False, index=True)
    results = Column(JSON, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index("idx_query_timestamp", "query", "timestamp"),
    )
