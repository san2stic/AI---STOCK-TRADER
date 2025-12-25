"""
Forex Factory News API Connector - 100% FREE
Fetches economic calendar events from Forex Factory's free JSON endpoint.
No API key required.
"""
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict
import structlog
import aiohttp
from models.economic_event import EventImpact, EventSource

logger = structlog.get_logger()


class ForexFactoryConnector:
    """
    Connector for Forex Factory News API.
    
    Free API endpoint: https://nfs.faireconomy.media/ff_calendar_thisweek.json
    
    Features:
    - 100% free, no API key required
    - Weekly economic calendar
    - Event impact levels (High, Medium, Low)
    - Multiple countries (US, EUR, GBP, JPY, etc.)
    - Forecast and previous values
    """
    
    BASE_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    
    # Currency code to country mapping
    CURRENCY_TO_COUNTRY = {
        "USD": "US",
        "EUR": "EU",
        "GBP": "UK",
        "JPY": "JP",
        "CAD": "CA",
        "AUD": "AU",
        "NZD": "NZ",
        "CHF": "CH",
        "CNY": "CN",
    }
    
    def __init__(self):
        """Initialize Forex Factory connector."""
        self.cache = None
        self.cache_time = None
        self.cache_duration = timedelta(hours=1)  # Cache for 1 hour
        
    async def fetch_calendar_events(
        self,
        days_ahead: int = 7,
        min_impact: Optional[str] = None
    ) -> List[Dict]:
        """
        Fetch economic calendar events from Forex Factory.
        
        Args:
            days_ahead: Number of days ahead to fetch events
            min_impact: Minimum impact level (HIGH, MEDIUM, LOW)
        
        Returns:
            List of event dictionaries in standardized format
        """
        # Check cache first
        if self._is_cache_valid():
            logger.debug("using_cached_forex_factory_data")
            # Parse cached raw data first, then filter
            parsed_events = self._parse_events(self.cache)
            return self._filter_events(parsed_events, days_ahead, min_impact)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.BASE_URL,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Cache the raw data
                        self.cache = data
                        self.cache_time = datetime.now()
                        
                        logger.info(
                            "forex_factory_data_fetched",
                            raw_count=len(data) if isinstance(data, list) else 0
                        )
                        
                        # Parse and normalize events
                        events = self._parse_events(data)
                        
                        # Filter by date range and impact
                        filtered_events = self._filter_events(events, days_ahead, min_impact)
                        
                        logger.info(
                            "forex_factory_events_processed",
                            total=len(events),
                            filtered=len(filtered_events)
                        )
                        
                        return filtered_events
                    else:
                        logger.error(
                            "forex_factory_request_failed",
                            status=response.status
                        )
                        return []
                        
        except aiohttp.ClientError as e:
            logger.error(
                "forex_factory_connection_error",
                error=str(e)
            )
            return []
        except Exception as e:
            logger.error(
                "forex_factory_unexpected_error",
                error=str(e),
                error_type=type(e).__name__
            )
            return []
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if self.cache is None or self.cache_time is None:
            return False
        
        age = datetime.now() - self.cache_time
        return age < self.cache_duration
    
    def _parse_events(self, raw_data: List[Dict]) -> List[Dict]:
        """
        Parse raw Forex Factory data into standardized format.
        
        Args:
            raw_data: Raw JSON data from API
        
        Returns:
            List of normalized event dictionaries
        """
        events = []
        
        if not isinstance(raw_data, list):
            logger.warning("forex_factory_invalid_data_format", type=type(raw_data).__name__)
            return events
        
        for item in raw_data:
            try:
                # Parse date and time
                date_str = item.get("date", "")
                if not date_str:
                    continue
                
                # Parse ISO format date with timezone support
                # Handles formats like: "2025-12-26T13:30:00+00:00" or "2025-12-25T08:30:00-05:00"
                try:
                    event_datetime = datetime.fromisoformat(date_str)
                except ValueError:
                    # Fallback: try parsing without timezone info
                    import re
                    # Remove timezone info (e.g., +00:00, -05:00)
                    date_str_clean = re.sub(r'[+-]\d{2}:\d{2}$', '', date_str)
                    event_datetime = datetime.fromisoformat(date_str_clean)
                
                # Determine impact level
                impact_str = item.get("impact", "").upper()
                if "HIGH" in impact_str or impact_str == "3":
                    impact = EventImpact.HIGH
                elif "MEDIUM" in impact_str or "MED" in impact_str or impact_str == "2":
                    impact = EventImpact.MEDIUM
                else:
                    impact = EventImpact.LOW
                
                # Get country from currency code
                currency = item.get("country", "USD")
                country = self.CURRENCY_TO_COUNTRY.get(currency, currency)
                
                # Build standardized event
                event = {
                    "date": event_datetime.date().isoformat(),
                    "time": event_datetime.time().isoformat(),
                    "timezone": "UTC",
                    "name": item.get("title", "Unknown Event"),
                    "indicator": self._generate_indicator(item.get("title", "")),
                    "impact": impact.value,
                    "country": country,
                    "description": f"Forecast: {item.get('forecast', 'N/A')}, Previous: {item.get('previous', 'N/A')}",
                    "source": EventSource.ALPHAVANTAGE.value,  # We'll use a new source later
                    "forecast": item.get("forecast"),
                    "previous": item.get("previous"),
                    "actual": item.get("actual"),
                }
                
                events.append(event)
                
            except Exception as e:
                logger.warning(
                    "forex_factory_event_parse_error",
                    error=str(e),
                    item=item
                )
                continue
        
        return events
    
    def _generate_indicator(self, title: str) -> str:
        """
        Generate indicator code from event title.
        
        Args:
            title: Event title
        
        Returns:
            Indicator code
        """
        # Common economic indicators
        indicators_map = {
            "Non-Farm": "NONFARM_PAYROLL",
            "NFP": "NONFARM_PAYROLL",
            "CPI": "CPI",
            "Consumer Price": "CPI",
            "GDP": "GDP",
            "Retail Sales": "RETAIL_SALES",
            "Unemployment": "UNEMPLOYMENT",
            "FOMC": "FEDERAL_FUNDS_RATE",
            "Interest Rate": "INTEREST_RATE",
            "PMI": "PMI",
            "Inflation": "INFLATION",
        }
        
        title_upper = title.upper()
        for key, value in indicators_map.items():
            if key.upper() in title_upper:
                return value
        
        # Default: use title as indicator
        return title.upper().replace(" ", "_")[:50]
    
    def _filter_events(
        self,
        events: List[Dict],
        days_ahead: int,
        min_impact: Optional[str]
    ) -> List[Dict]:
        """
        Filter events by date range and impact level.
        
        Args:
            events: List of events
            days_ahead: Number of days ahead
            min_impact: Minimum impact level
        
        Returns:
            Filtered events
        """
        today = date.today()
        end_date = today + timedelta(days=days_ahead)
        
        filtered = []
        impact_order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        min_impact_value = impact_order.get(min_impact, 1) if min_impact else 1
        
        for event in events:
            try:
                event_date = date.fromisoformat(event["date"])
                event_impact_value = impact_order.get(event["impact"], 1)
                
                # Filter by date range
                if event_date < today or event_date > end_date:
                    continue
                
                # Filter by impact
                if event_impact_value < min_impact_value:
                    continue
                
                filtered.append(event)
                
            except Exception as e:
                logger.warning("event_filter_error", error=str(e))
                continue
        
        return filtered


# Singleton instance
_forex_factory_connector: Optional[ForexFactoryConnector] = None


def get_forex_factory_connector() -> ForexFactoryConnector:
    """Get or create Forex Factory connector singleton."""
    global _forex_factory_connector
    if _forex_factory_connector is None:
        _forex_factory_connector = ForexFactoryConnector()
    return _forex_factory_connector
