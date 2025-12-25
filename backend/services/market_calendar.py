"""
Market calendar service - checks trading days and holidays.
Supports US, European, and Asian markets.
"""
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict
import structlog
from functools import lru_cache

try:
    import pandas_market_calendars as mcal
    CALENDARS_AVAILABLE = True
except ImportError:
    CALENDARS_AVAILABLE = False
    structlog.get_logger().warning(
        "pandas_market_calendars not installed",
        message="Market holiday checking will be disabled"
    )

logger = structlog.get_logger()


class MarketCalendar:
    """Manages market calendars and trading day verification."""
    
    # Map our market names to pandas_market_calendars exchange names
    CALENDAR_MAPPING = {
        "US": "NYSE",  # New York Stock Exchange
        "EUROPE": "LSE",  # London Stock Exchange (representative)
        "ASIA": "XTKS",  # Tokyo Stock Exchange
    }
    
    def __init__(self):
        """Initialize market calendars."""
        self.calendars = {}
        
        if not CALENDARS_AVAILABLE:
            logger.warning("market_calendars_disabled", reason="Library not installed")
            return
        
        # Load calendars for each market
        for market, exchange_code in self.CALENDAR_MAPPING.items():
            try:
                self.calendars[market] = mcal.get_calendar(exchange_code)
                logger.info("calendar_loaded", market=market, exchange=exchange_code)
            except Exception as e:
                logger.error(
                    "calendar_load_failed",
                    market=market,
                    exchange=exchange_code,
                    error=str(e)
                )
    
    def is_trading_day(self, market: str, check_date: Optional[date] = None) -> bool:
        """
        Check if a given date is a trading day for the specified market.
        
        Args:
            market: Market code (US, EUROPE, ASIA)
            check_date: Date to check (default: today)
        
        Returns:
            True if market is open, False if closed (holiday/weekend)
        """
        if not CALENDARS_AVAILABLE:
            # Fallback: just check if it's a weekday
            check_date = check_date or date.today()
            is_weekday = check_date.weekday() < 5
            logger.debug(
                "trading_day_check_fallback",
                market=market,
                date=check_date,
                is_weekday=is_weekday
            )
            return is_weekday
        
        market = market.upper()
        if market not in self.calendars:
            logger.warning("unknown_market", market=market)
            return True  # Default to allow trading
        
        check_date = check_date or date.today()
        calendar = self.calendars[market]
        
        try:
            # Get valid trading days for this date
            schedule = calendar.schedule(
                start_date=check_date,
                end_date=check_date
            )
            
            is_open = len(schedule) > 0
            
            logger.debug(
                "trading_day_check",
                market=market,
                date=check_date.isoformat(),
                is_open=is_open
            )
            
            return is_open
            
        except Exception as e:
            logger.error(
                "trading_day_check_error",
                market=market,
                date=check_date,
                error=str(e)
            )
            return True  # Default to allow trading on error
    
    def get_next_trading_day(
        self, 
        market: str, 
        from_date: Optional[date] = None
    ) -> Optional[date]:
        """
        Get the next trading day after the specified date.
        
        Args:
            market: Market code (US, EUROPE, ASIA)
            from_date: Start date (default: today)
        
        Returns:
            Next trading day, or None if error
        """
        if not CALENDARS_AVAILABLE:
            # Fallback: find next weekday
            from_date = from_date or date.today()
            next_day = from_date + timedelta(days=1)
            while next_day.weekday() >= 5:  # Skip weekends
                next_day += timedelta(days=1)
            return next_day
        
        market = market.upper()
        if market not in self.calendars:
            logger.warning("unknown_market", market=market)
            return None
        
        from_date = from_date or date.today()
        calendar = self.calendars[market]
        
        try:
            # Get next 10 days of schedule
            end_date = from_date + timedelta(days=10)
            schedule = calendar.schedule(
                start_date=from_date + timedelta(days=1),
                end_date=end_date
            )
            
            if len(schedule) > 0:
                next_trading_day = schedule.index[0].date()
                logger.debug(
                    "next_trading_day",
                    market=market,
                    from_date=from_date.isoformat(),
                    next_day=next_trading_day.isoformat()
                )
                return next_trading_day
            
            return None
            
        except Exception as e:
            logger.error(
                "next_trading_day_error",
                market=market,
                from_date=from_date,
                error=str(e)
            )
            return None
    
    def get_market_schedule(
        self,
        market: str,
        start_date: Optional[date] = None,
        days_ahead: int = 30
    ) -> List[Dict]:
        """
        Get market schedule (open/close times) for upcoming days.
        
        Args:
            market: Market code (US, EUROPE, ASIA)
            start_date: Start date (default: today)
            days_ahead: Number of days to fetch
        
        Returns:
            List of trading days with open/close times
        """
        if not CALENDARS_AVAILABLE:
            logger.warning("schedule_unavailable", reason="Library not installed")
            return []
        
        market = market.upper()
        if market not in self.calendars:
            logger.warning("unknown_market", market=market)
            return []
        
        start_date = start_date or date.today()
        end_date = start_date + timedelta(days=days_ahead)
        calendar = self.calendars[market]
        
        try:
            schedule = calendar.schedule(
                start_date=start_date,
                end_date=end_date
            )
            
            result = []
            for idx, row in schedule.iterrows():
                result.append({
                    "date": idx.date().isoformat(),
                    "market_open": row['market_open'].isoformat(),
                    "market_close": row['market_close'].isoformat(),
                    "market": market,
                })
            
            logger.info(
                "market_schedule_retrieved",
                market=market,
                days_found=len(result),
                start=start_date.isoformat(),
                end=end_date.isoformat()
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "market_schedule_error",
                market=market,
                error=str(e)
            )
            return []
    
    def get_upcoming_holidays(
        self,
        market: str,
        days_ahead: int = 90
    ) -> List[Dict]:
        """
        Get upcoming market holidays.
        
        Args:
            market: Market code (US, EUROPE, ASIA)
            days_ahead: Number of days to look ahead
        
        Returns:
            List of holiday dates with names
        """
        if not CALENDARS_AVAILABLE:
            logger.warning("holidays_unavailable", reason="Library not installed")
            return []
        
        market = market.upper()
        if market not in self.calendars:
            logger.warning("unknown_market", market=market)
            return []
        
        start_date = date.today()
        end_date = start_date + timedelta(days=days_ahead)
        calendar = self.calendars[market]
        
        try:
            # Get all holidays in range
            # Try different approaches as the API varies
            result = []
            
            try:
                # Method 1: Try calling holidays() with date range
                holidays_list = calendar.holidays().holidays(
                    start=start_date,
                    end=end_date,
                    return_name=True
                )
                
                for holiday_date, holiday_name in holidays_list.items():
                    # Convert to date if it's a Timestamp
                    if hasattr(holiday_date, 'date'):
                        holiday_date = holiday_date.date()
                    
                    result.append({
                        "date": holiday_date.isoformat() if hasattr(holiday_date, 'isoformat') else str(holiday_date),
                        "market": market,
                        "name": str(holiday_name) if holiday_name else "Market Holiday"
                    })
            except (AttributeError, TypeError):
                # Fallback: just return empty list
                logger.warning("holidays_method_unavailable", market=market)
            

            
            logger.info(
                "holidays_retrieved",
                market=market,
                count=len(result),
                days_ahead=days_ahead
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "holidays_retrieval_error",
                market=market,
                error=str(e)
            )
            return []


# Singleton instance
_market_calendar: Optional[MarketCalendar] = None


def get_market_calendar() -> MarketCalendar:
    """Get or create market calendar singleton."""
    global _market_calendar
    if _market_calendar is None:
        _market_calendar = MarketCalendar()
    return _market_calendar
