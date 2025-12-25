"""
Economic calendar service - tracks major economic events.
Uses Alpha Vantage Economic Indicators API.
"""
from datetime import datetime, date, timedelta, time as dt_time
from typing import Optional, List, Dict
from enum import Enum
import structlog
import aiohttp
import asyncio
from functools import lru_cache
import json
from sqlalchemy import and_, or_
from sqlalchemy.exc import IntegrityError
from database import get_db
from models.economic_event import EconomicEvent, EventImpact as DBEventImpact, EventSource
from services.forex_factory_connector import get_forex_factory_connector

logger = structlog.get_logger()


class EventImpact(str, Enum):
    """Economic event impact levels."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class EconomicCalendar:
    """Manages economic calendar and event tracking."""
    
    # Major high-impact economic events (US-focused for now)
    HIGH_IMPACT_INDICATORS = {
        "NONFARM_PAYROLL": {"name": "Non-Farm Payroll (NFP)", "impact": EventImpact.HIGH},
        "CPI": {"name": "Consumer Price Index", "impact": EventImpact.HIGH},
        "FEDERAL_FUNDS_RATE": {"name": "FOMC Rate Decision", "impact": EventImpact.HIGH},
        "GDP": {"name": "GDP Release", "impact": EventImpact.HIGH},
        "RETAIL_SALES": {"name": "Retail Sales", "impact": EventImpact.MEDIUM},
        "UNEMPLOYMENT": {"name": "Unemployment Rate", "impact": EventImpact.HIGH},
        "INFLATION": {"name": "Inflation Rate", "impact": EventImpact.HIGH},
        "CONSUMER_SENTIMENT": {"name": "Consumer Sentiment", "impact": EventImpact.MEDIUM},
        "DURABLES": {"name": "Durable Goods Orders", "impact": EventImpact.MEDIUM},
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize economic calendar.
        
        Args:
            api_key: Alpha Vantage API key
        """
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
        self.cache = {}  # In-memory cache for events
        self.cache_expiry = timedelta(hours=6)  # Cache for 6 hours
        self.db_refresh_threshold = timedelta(hours=24)  # Refresh DB data after 24 hours
        
        if not api_key:
            logger.warning(
                "economic_calendar_disabled",
                reason="No API key provided"
            )
    
    async def _fetch_indicator(
        self,
        function: str,
        interval: str = "monthly"
    ) -> Optional[Dict]:
        """
        Fetch economic indicator data from Alpha Vantage.
        
        Args:
            function: API function name
            interval: Data interval (annual, quarterly, monthly)
        
        Returns:
            Indicator data or None
        """
        if not self.api_key:
            return None
        
        # Check cache
        cache_key = f"{function}_{interval}"
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if datetime.now() - cached_time < self.cache_expiry:
                logger.debug("using_cached_indicator", function=function)
                return cached_data
        
        params = {
            "function": function,
            "apikey": self.api_key,
        }
        
        if interval:
            params["interval"] = interval
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Check for API errors
                        if "Error Message" in data:
                            logger.error(
                                "alphavantage_error",
                                function=function,
                                error=data["Error Message"]
                            )
                            return None
                        
                        if "Note" in data:
                            logger.warning(
                                "alphavantage_rate_limit",
                                function=function,
                                note=data["Note"]
                            )
                            return None
                        
                        # Cache the result
                        self.cache[cache_key] = (data, datetime.now())
                        
                        logger.debug(
                            "indicator_fetched",
                            function=function,
                            interval=interval
                        )
                        
                        return data
                    else:
                        logger.error(
                            "alphavantage_request_failed",
                            function=function,
                            status=response.status
                        )
                        return None
                        
        except Exception as e:
            logger.error(
                "indicator_fetch_error",
                function=function,
                error=str(e)
            )
            return None
    
    async def get_upcoming_events(
        self,
        days_ahead: int = 7,
        min_impact: EventImpact = EventImpact.MEDIUM
    ) -> List[Dict]:
        """
        Get upcoming economic events.
        
        Uses database-first approach:
        1. Query database for events in date range
        2. If data is fresh, return it
        3. If data is missing/stale, fetch from API and update database
        4. Return combined results
        
        Args:
            days_ahead: Number of days to look ahead
            min_impact: Minimum event impact level
        
        Returns:
            List of upcoming events
        """
        today = date.today()
        end_date = today + timedelta(days=days_ahead)
        
        # Try to get events from database first
        db_events = await self._get_events_from_db(today, end_date, min_impact)
        
        # Check if we have fresh data
        if db_events and await self._is_db_data_fresh(today, end_date):
            logger.info(
                "events_from_database",
                count=len(db_events),
                days_ahead=days_ahead,
                min_impact=min_impact.value
            )
            return db_events
        
        # Database is empty or stale, fetch new data from APIs
        # Priority: Forex Factory (free) -> Estimated
        events = await self._fetch_from_free_apis(days_ahead, min_impact)
        
        # Fallback to estimated events if API fails
        if not events:
            logger.warning("api_fetch_failed_using_estimated")
            events = self._get_estimated_events(days_ahead, min_impact)
        
        # Save to database
        if events:
            await self._save_events_to_db(events)
        
        logger.info(
            "events_refreshed",
            count=len(events),
            days_ahead=days_ahead,
            min_impact=min_impact.value,
            source="forex_factory" if events and events[0].get("source") != "estimated" else "estimated"
        )
        
        return events
    
    def _get_estimated_events(
        self,
        days_ahead: int,
        min_impact: EventImpact
    ) -> List[Dict]:
        """
        Get estimated economic event schedule.
        
        This is a simplified version that estimates typical release dates.
        Real production system should use a dedicated calendar API.
        """
        today = date.today()
        events = []
        
        # NFP: First Friday of each month at 8:30 AM EST
        nfp_date = self._get_first_friday_of_month(today)
        if nfp_date and (nfp_date - today).days <= days_ahead:
            events.append({
                "date": nfp_date.isoformat(),
                "time": "08:30:00",
                "timezone": "EST",
                "name": "Non-Farm Payroll (NFP)",
                "indicator": "NONFARM_PAYROLL",
                "impact": EventImpact.HIGH.value,
                "country": "US",
                "description": "Monthly employment change, major market mover"
            })
        
        # CPI: Mid-month (typically 13th-15th)
        cpi_date = self._estimate_monthly_event(today, 13)
        if cpi_date and (cpi_date - today).days <= days_ahead:
            events.append({
                "date": cpi_date.isoformat(),
                "time": "08:30:00",
                "timezone": "EST",
                "name": "Consumer Price Index (CPI)",
                "indicator": "CPI",
                "impact": EventImpact.HIGH.value,
                "country": "US",
                "description": "Inflation measure, impacts Fed policy"
            })
        
        # FOMC: 8 times per year (roughly every 6 weeks)
        # Typical months: Jan, Mar, May, Jun, Jul, Sep, Nov, Dec
        if today.month in [1, 3, 5, 6, 7, 9, 11, 12]:
            fomc_date = self._estimate_monthly_event(today, 20)
            if fomc_date and (fomc_date - today).days <= days_ahead:
                events.append({
                    "date": fomc_date.isoformat(),
                    "time": "14:00:00",
                    "timezone": "EST",
                    "name": "FOMC Rate Decision",
                    "indicator": "FEDERAL_FUNDS_RATE",
                    "impact": EventImpact.HIGH.value,
                    "country": "US",
                    "description": "Federal Reserve interest rate decision"
                })
        
        # Retail Sales: Mid-month
        retail_date = self._estimate_monthly_event(today, 14)
        if retail_date and (retail_date - today).days <= days_ahead:
            if min_impact in [EventImpact.MEDIUM, EventImpact.LOW]:
                events.append({
                    "date": retail_date.isoformat(),
                    "time": "08:30:00",
                    "timezone": "EST",
                    "name": "Retail Sales",
                    "indicator": "RETAIL_SALES",
                    "impact": EventImpact.MEDIUM.value,
                    "country": "US",
                    "description": "Monthly consumer spending indicator"
                })
        
        # Filter by minimum impact
        impact_order = {EventImpact.HIGH: 3, EventImpact.MEDIUM: 2, EventImpact.LOW: 1}
        min_impact_value = impact_order[min_impact]
        
        events = [
            e for e in events 
            if impact_order[EventImpact(e["impact"])] >= min_impact_value
        ]
        
        return events
    
    def _get_first_friday_of_month(self, ref_date: date) -> Optional[date]:
        """Get first Friday of current or next month."""
        # Start from first day of current month
        first_day = date(ref_date.year, ref_date.month, 1)
        
        # Find first Friday
        days_until_friday = (4 - first_day.weekday()) % 7
        first_friday = first_day + timedelta(days=days_until_friday)
        
        # If already passed, get next month's first Friday
        if first_friday < ref_date:
            if ref_date.month == 12:
                next_month = date(ref_date.year + 1, 1, 1)
            else:
                next_month = date(ref_date.year, ref_date.month + 1, 1)
            
            days_until_friday = (4 - next_month.weekday()) % 7
            first_friday = next_month + timedelta(days=days_until_friday)
        
        return first_friday
    
    def _estimate_monthly_event(self, ref_date: date, target_day: int) -> Optional[date]:
        """Estimate a monthly event on a specific day."""
        # Try current month
        try:
            event_date = date(ref_date.year, ref_date.month, target_day)
            if event_date >= ref_date:
                return event_date
        except ValueError:
            pass
        
        # Try next month
        try:
            if ref_date.month == 12:
                event_date = date(ref_date.year + 1, 1, target_day)
            else:
                event_date = date(ref_date.year, ref_date.month + 1, target_day)
            return event_date
        except ValueError:
            return None
    
    async def _fetch_from_free_apis(
        self,
        days_ahead: int,
        min_impact: EventImpact
    ) -> List[Dict]:
        """
        Fetch events from free APIs (Forex Factory).
        
        Args:
            days_ahead: Number of days ahead
            min_impact: Minimum impact level
        
        Returns:
            List of events from APIs
        """
        try:
            # Try Forex Factory first (100% free)
            forex_connector = get_forex_factory_connector()
            events = await forex_connector.fetch_calendar_events(
                days_ahead=days_ahead,
                min_impact=min_impact.value
            )
            
            if events:
                logger.info(
                    "forex_factory_events_fetched",
                    count=len(events)
                )
                return events
            else:
                logger.warning("forex_factory_no_events")
                return []
                
        except Exception as e:
            logger.error(
                "free_api_fetch_error",
                error=str(e)
            )
            return []
    
    async def _get_events_from_db(
        self,
        start_date: date,
        end_date: date,
        min_impact: EventImpact
    ) -> List[Dict]:
        """
        Retrieve events from database for the given date range.
        
        Args:
            start_date: Start date for events
            end_date: End date for events
            min_impact: Minimum impact level
        
        Returns:
            List of event dictionaries
        """
        try:
            with get_db() as db:
                # Map EventImpact to DBEventImpact
                impact_order = {EventImpact.HIGH: 3, EventImpact.MEDIUM: 2, EventImpact.LOW: 1}
                min_impact_value = impact_order[min_impact]
                
                query = db.query(EconomicEvent).filter(
                    and_(
                        EconomicEvent.event_date >= start_date,
                        EconomicEvent.event_date <= end_date
                    )
                )
                
                # Filter by impact level
                if min_impact == EventImpact.HIGH:
                    query = query.filter(EconomicEvent.impact == DBEventImpact.HIGH)
                elif min_impact == EventImpact.MEDIUM:
                    query = query.filter(
                        or_(
                            EconomicEvent.impact == DBEventImpact.HIGH,
                            EconomicEvent.impact == DBEventImpact.MEDIUM
                        )
                    )
                # LOW includes all
                
                events = query.order_by(EconomicEvent.event_date).all()
                
                logger.debug(
                    "db_events_retrieved",
                    count=len(events),
                    start_date=start_date.isoformat(),
                    end_date=end_date.isoformat()
                )
                
                return [event.to_dict() for event in events]
                
        except Exception as e:
            logger.error(
                "db_events_retrieval_error",
                error=str(e),
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat()
            )
            return []
    
    async def _is_db_data_fresh(self, start_date: date, end_date: date) -> bool:
        """
        Check if database has fresh data for the given date range.
        
        Args:
            start_date: Start date
            end_date: End date
        
        Returns:
            True if data is fresh
        """
        try:
            with get_db() as db:
                # Get the oldest updated_at timestamp in the range
                oldest_event = db.query(EconomicEvent).filter(
                    and_(
                        EconomicEvent.event_date >= start_date,
                        EconomicEvent.event_date <= end_date
                    )
                ).order_by(EconomicEvent.updated_at.asc()).first()
                
                if not oldest_event:
                    # No data in database
                    return False
                
                # Check if data is stale
                age = datetime.now() - oldest_event.updated_at
                is_fresh = age < self.db_refresh_threshold
                
                logger.debug(
                    "db_freshness_check",
                    is_fresh=is_fresh,
                    age_hours=age.total_seconds() / 3600
                )
                
                return is_fresh
                
        except Exception as e:
            logger.error("db_freshness_check_error", error=str(e))
            return False
    
    async def _save_events_to_db(self, events: List[Dict]) -> None:
        """
        Save events to database.
        
        Args:
            events: List of event dictionaries
        """
        try:
            with get_db() as db:
                saved_count = 0
                updated_count = 0
                
                for event_data in events:
                    try:
                        # Parse time if present
                        event_time = None
                        if event_data.get("time"):
                            time_str = event_data["time"]
                            # Parse time string like "08:30:00"
                            parts = time_str.split(":")
                            event_time = dt_time(
                                hour=int(parts[0]),
                                minute=int(parts[1]) if len(parts) > 1 else 0,
                                second=int(parts[2]) if len(parts) > 2 else 0
                            )
                        
                        # Check if event already exists
                        existing = db.query(EconomicEvent).filter(
                            and_(
                                EconomicEvent.event_date == datetime.fromisoformat(event_data["date"]).date(),
                                EconomicEvent.indicator == event_data.get("indicator"),
                                EconomicEvent.country == event_data.get("country", "US")
                            )
                        ).first()
                        
                        if existing:
                            # Update existing event
                            existing.name = event_data["name"]
                            existing.event_time = event_time
                            existing.timezone = event_data.get("timezone")
                            existing.impact = DBEventImpact(event_data["impact"])
                            existing.description = event_data.get("description")
                            existing.updated_at = datetime.utcnow()
                            updated_count += 1
                        else:
                            # Create new event
                            new_event = EconomicEvent(
                                event_date=datetime.fromisoformat(event_data["date"]).date(),
                                event_time=event_time,
                                timezone=event_data.get("timezone"),
                                name=event_data["name"],
                                indicator=event_data.get("indicator"),
                                impact=DBEventImpact(event_data["impact"]),
                                country=event_data.get("country", "US"),
                                description=event_data.get("description"),
                                source=EventSource.ESTIMATED
                            )
                            db.add(new_event)
                            saved_count += 1
                            
                    except IntegrityError as ie:
                        # Duplicate event, skip
                        logger.debug("duplicate_event_skipped", event=event_data.get("name"))
                        db.rollback()
                        continue
                    except Exception as e:
                        logger.error(
                            "event_save_error",
                            event=event_data.get("name"),
                            error=str(e)
                        )
                        db.rollback()
                        continue
                
                db.commit()
                
                logger.info(
                    "events_saved_to_db",
                    saved=saved_count,
                    updated=updated_count,
                    total=len(events)
                )
                
        except Exception as e:
            logger.error("db_save_error", error=str(e))
    
    async def has_high_impact_event_today(self) -> bool:
        """
        Check if there's a high-impact event today.
        
        Returns:
            True if high-impact event is scheduled
        """
        events = await self.get_upcoming_events(days_ahead=1, min_impact=EventImpact.HIGH)
        today = date.today().isoformat()
        
        for event in events:
            if event["date"] == today:
                logger.info(
                    "high_impact_event_today",
                    event=event["name"],
                    time=event.get("time")
                )
                return True
        
        return False
    
    async def get_event_window(
        self,
        event_date: date,
        hours_before: int = 2,
        hours_after: int = 1
    ) -> Dict[str, datetime]:
        """
        Get time window around an economic event.
        
        Args:
            event_date: Date of the event
            hours_before: Hours before event to start pause
            hours_after: Hours after event to end pause
        
        Returns:
            Dict with pause_start and pause_end times
        """
        # Assume most events are at 8:30 AM EST
        event_time = datetime.combine(event_date, datetime.min.time()).replace(
            hour=8, minute=30
        )
        
        pause_start = event_time - timedelta(hours=hours_before)
        pause_end = event_time + timedelta(hours=hours_after)
        
        return {
            "pause_start": pause_start,
            "pause_end": pause_end,
            "event_time": event_time,
        }


# Singleton instance
_economic_calendar: Optional[EconomicCalendar] = None


def get_economic_calendar(api_key: Optional[str] = None) -> EconomicCalendar:
    """Get or create economic calendar singleton."""
    global _economic_calendar
    if _economic_calendar is None:
        _economic_calendar = EconomicCalendar(api_key=api_key)
    return _economic_calendar
