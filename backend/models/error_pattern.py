"""
Error Pattern Model - Catalogs recurring mistakes across agents.
Enables pattern detection and prevention of repeated errors.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, 
    Text, Index
)
from models.base import Base


class ErrorPattern(Base):
    """Catalog of recurring error patterns for agent learning."""
    __tablename__ = "error_patterns"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String(50), nullable=False, index=True)
    
    # Pattern identification
    pattern_type = Column(String(100), nullable=False, index=True)
    pattern_signature = Column(String(255), nullable=False)  # Hash/key for detecting duplicates
    
    # Description
    title = Column(String(200), nullable=False)  # Short title
    description = Column(Text, nullable=False)  # Detailed explanation
    
    # Statistics
    occurrence_count = Column(Integer, default=1)
    total_loss_amount = Column(Float, default=0.0)
    avg_loss_amount = Column(Float, default=0.0)
    avg_loss_percent = Column(Float, default=0.0)
    
    # Timing
    first_seen = Column(DateTime, nullable=False, index=True)
    last_seen = Column(DateTime, nullable=False, index=True)
    
    # Learning
    suggested_fix = Column(Text, nullable=True)  # AI-generated remediation
    actionable_rule = Column(Text, nullable=True)  # IF-THEN rule to prevent recurrence
    is_resolved = Column(Boolean, default=False)  # Has pattern stopped occurring?
    resolution_date = Column(DateTime, nullable=True)
    
    # Severity (1-10 scale based on frequency and impact)
    severity_score = Column(Integer, default=5)
    
    # Related trades (JSON array of trade IDs showing this pattern)
    example_trade_ids = Column(Text, nullable=True)  # JSON string
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_agent_pattern", "agent_name", "pattern_type"),
        Index("idx_agent_unresolved", "agent_name", "is_resolved"),
    )
    
    def update_occurrence(self, loss_amount: float, loss_percent: float, trade_id: int):
        """Update pattern statistics when it recurs."""
        self.occurrence_count += 1
        self.total_loss_amount += abs(loss_amount)
        self.avg_loss_amount = self.total_loss_amount / self.occurrence_count
        
        # Update average loss percent
        self.avg_loss_percent = (
            (self.avg_loss_percent * (self.occurrence_count - 1) + abs(loss_percent))
            / self.occurrence_count
        )
        
        self.last_seen = datetime.utcnow()
        
        # Update severity: combination of frequency and impact
        frequency_score = min(self.occurrence_count, 10)  # Cap at 10
        impact_score = min(int(self.avg_loss_percent / 2), 10)  # 20% loss = severity 10
        self.severity_score = min((frequency_score + impact_score) // 2, 10)
        
        # Append trade ID to examples (simple comma-separated for now)
        if self.example_trade_ids:
            ids = self.example_trade_ids.split(',')
            if str(trade_id) not in ids:
                ids.append(str(trade_id))
                self.example_trade_ids = ','.join(ids[-10:])  # Keep last 10
        else:
            self.example_trade_ids = str(trade_id)
    
    def mark_resolved(self):
        """Mark pattern as resolved."""
        self.is_resolved = True
        self.resolution_date = datetime.utcnow()
    
    @staticmethod
    def generate_signature(agent_name: str, pattern_type: str, context: str) -> str:
        """Generate unique signature for pattern deduplication."""
        import hashlib
        key = f"{agent_name}:{pattern_type}:{context}"
        return hashlib.md5(key.encode()).hexdigest()[:16]
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "agent_name": self.agent_name,
            "pattern_type": self.pattern_type,
            "title": self.title,
            "description": self.description,
            "occurrence_count": self.occurrence_count,
            "avg_loss_percent": round(self.avg_loss_percent, 2),
            "severity_score": self.severity_score,
            "suggested_fix": self.suggested_fix,
            "actionable_rule": self.actionable_rule,
            "is_resolved": self.is_resolved,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
        }
