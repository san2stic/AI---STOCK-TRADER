"""
Database models for crew collaboration system.
Tracks deliberation sessions, agent messages, and consensus votes.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, 
    Text, JSON, Enum, ForeignKey, Index
)
from sqlalchemy.orm import relationship
import enum

from models.database import Base


class SessionStatus(str, enum.Enum):
    """Crew session status."""
    DELIBERATING = "deliberating"
    VOTING = "voting"
    CONSENSUS_REACHED = "consensus_reached"
    DEADLOCK = "deadlock"
    MEDIATOR_INVOKED = "mediator_invoked"
    COMPLETED = "completed"


class MessageType(str, enum.Enum):
    """Types of messages agents can send."""
    POSITION = "position"  # Initial position statement
    REBUTTAL = "rebuttal"  # Counter-argument
    AGREEMENT = "agreement"  # Supporting another agent
    QUESTION = "question"  # Asking for clarification
    COMPROMISE = "compromise"  # Proposing middle ground
    VOTE = "vote"  # Final vote


class VoteAction(str, enum.Enum):
    """Vote options."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class CrewSession(Base):
    """
    A complete deliberation session by the agent crew.
    Tracks the entire process from initial positions to final consensus.
    """
    __tablename__ = "crew_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(50), unique=True, nullable=False, index=True)
    
    # Context
    market_context = Column(JSON, nullable=False)  # Market data at session time
    symbols_discussed = Column(JSON, nullable=True)  # List of symbols
    
    # Session flow
    status = Column(Enum(SessionStatus), default=SessionStatus.DELIBERATING, index=True)
    current_round = Column(Integer, default=1)
    total_rounds = Column(Integer, default=3)
    
    # Final outcome
    final_decision = Column(String(20), nullable=True)  # buy/sell/hold
    final_symbol = Column(String(10), nullable=True)  # Which symbol to trade
    final_quantity = Column(Integer, nullable=True)
    consensus_score = Column(Float, nullable=True)  # 0-100% strength of consensus
    
    # Metadata
    total_messages = Column(Integer, default=0)
    mediator_used = Column(Boolean, default=False)
    mediator_reasoning = Column(Text, nullable=True)
    
    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    # Relationships
    messages = relationship("AgentMessage", back_populates="session", cascade="all, delete-orphan")
    votes = relationship("CrewVote", back_populates="session", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_session_started", "started_at"),
        Index("idx_session_status", "status", "started_at"),
    )


class AgentMessage(Base):
    """
    Individual messages from agents during deliberation.
    Captures the discussion flow and reasoning.
    """
    __tablename__ = "agent_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String(50), unique=True, nullable=False)
    
    # Session context
    session_id = Column(Integer, ForeignKey("crew_sessions.id"), nullable=False, index=True)
    
    # Message metadata
    agent_name = Column(String(50), nullable=False, index=True)
    round_number = Column(Integer, nullable=False)
    message_type = Column(Enum(MessageType), nullable=False)
    sequence_number = Column(Integer, nullable=False)  # Order within round
    
    # Content
    content = Column(Text, nullable=False)
    mentioned_agents = Column(JSON, nullable=True)  # List of agent names referenced
    responding_to_message_id = Column(String(50), nullable=True)  # Reply to specific message
    
    # Agent confidence
    confidence_level = Column(Float, nullable=True)  # 0-100%
    
    # Proposed action (if any)
    proposed_action = Column(String(20), nullable=True)  # buy/sell/hold
    proposed_symbol = Column(String(10), nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    session = relationship("CrewSession", back_populates="messages")
    
    __table_args__ = (
        Index("idx_message_session_round", "session_id", "round_number"),
        Index("idx_message_agent", "agent_name", "created_at"),
    )


class CrewVote(Base):
    """
    Final votes from each agent in a deliberation session.
    Includes vote weight based on agent performance.
    """
    __tablename__ = "crew_votes"
    
    id = Column(Integer, primary_key=True, index=True)
    vote_id = Column(String(50), unique=True, nullable=False)
    
    # Session context
    session_id = Column(Integer, ForeignKey("crew_sessions.id"), nullable=False, index=True)
    
    # Voter
    agent_name = Column(String(50), nullable=False, index=True)
    
    # Vote details
    vote_action = Column(Enum(VoteAction), nullable=False)
    vote_symbol = Column(String(10), nullable=True)  # Which symbol (if multiple discussed)
    vote_weight = Column(Float, nullable=False, default=1.0)  # Based on performance
    
    # Reasoning
    reasoning = Column(Text, nullable=True)
    confidence_level = Column(Float, nullable=True)  # 0-100%
    
    # Calculated fields
    weighted_score = Column(Float, nullable=True)  # vote_weight * confidence
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("CrewSession", back_populates="votes")
    
    __table_args__ = (
        Index("idx_vote_session", "session_id"),
        Index("idx_vote_agent", "agent_name", "created_at"),
    )


class CrewPerformance(Base):
    """
    Tracks crew-level performance metrics.
    Compares crew decisions vs. hypothetical individual agent performance.
    """
    __tablename__ = "crew_performance"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Time period
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False)
    
    # Session statistics
    total_sessions = Column(Integer, default=0)
    consensus_sessions = Column(Integer, default=0)  # Reached consensus
    deadlock_sessions = Column(Integer, default=0)  # Required mediator
    
    # Consensus metrics
    avg_consensus_score = Column(Float, nullable=True)
    avg_deliberation_time_seconds = Column(Float, nullable=True)
    avg_messages_per_session = Column(Float, nullable=True)
    
    # Trading outcomes
    total_trades_executed = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    total_pnl = Column(Float, default=0.0)
    
    # Agent influence (JSON: {agent_name: influence_score})
    agent_influence_scores = Column(JSON, nullable=True)
    
    # API costs
    total_api_cost = Column(Float, default=0.0)
    avg_cost_per_decision = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_crew_perf_period", "period_start", "period_end"),
    )
