"""
Database model for economic calendar events.
Stores events from Alpha Vantage and other sources to reduce API calls.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Date, Time, DateTime, 
    Text, Enum, Index
)
from sqlalchemy.ext.declarative import declarative_base
from models.database import Base
import enum


class EventImpact(str, enum.Enum):
    """Economic event impact levels."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class EventSource(str, enum.Enum):
    """Source of economic event data."""
    ALPHAVANTAGE = "alphavantage"
    ESTIMATED = "estimated"
    MANUAL = "manual"


class EconomicEvent(Base):
    """Economic calendar events - persisted to reduce API calls."""
    __tablename__ = "economic_events"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Event details
    event_date = Column(Date, nullable=False, index=True)
    event_time = Column(Time, nullable=True)
    timezone = Column(String(10), nullable=True)  # e.g., "EST", "UTC"
    
    name = Column(String(200), nullable=False)
    indicator = Column(String(50), nullable=True, index=True)  # e.g., "NONFARM_PAYROLL"
    impact = Column(Enum(EventImpact), nullable=False, index=True)
    country = Column(String(10), nullable=False, default="US")
    description = Column(Text, nullable=True)
    
    # Metadata
    source = Column(Enum(EventSource), nullable=False, default=EventSource.ESTIMATED)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True)
    
    __table_args__ = (
        # Composite index for common query patterns
        Index("idx_event_date_impact", "event_date", "impact"),
        Index("idx_event_date_country", "event_date", "country"),
        # Unique constraint to prevent duplicate events
        Index("idx_unique_event", "event_date", "event_time", "indicator", "country", unique=True),
    )
    
    def to_dict(self):
        """Convert to dictionary format compatible with economic_calendar service."""
        return {
            "date": self.event_date.isoformat(),
            "time": self.event_time.isoformat() if self.event_time else None,
            "timezone": self.timezone,
            "name": self.name,
            "indicator": self.indicator,
            "impact": self.impact.value,
            "country": self.country,
            "description": self.description,
            "source": self.source.value,
        }
