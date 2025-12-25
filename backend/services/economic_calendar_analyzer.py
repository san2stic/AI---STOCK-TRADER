"""
Economic Calendar Analyzer - LLM-powered analysis of economic events.
Uses OpenRouter API to provide intelligent insights on market impact.
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import structlog
import json
from services.economic_calendar import get_economic_calendar, EventImpact
from services.openrouter import get_openrouter_client

logger = structlog.get_logger()


class EconomicCalendarAnalyzer:
    """Analyzes economic events using LLM to provide trading insights."""
    
    def __init__(self, model: str = "anthropic/claude-3.5-sonnet"):
        """
        Initialize the analyzer.
        
        Args:
            model: OpenRouter model to use for analysis
        """
        self.model = model
        self.openrouter = get_openrouter_client()
        self.calendar = get_economic_calendar()
        self.cache: Optional[Dict[str, Any]] = None
        self.cache_time: Optional[datetime] = None
        self.cache_ttl = timedelta(hours=6)  # Cache analysis for 6 hours
        
    async def analyze_upcoming_events(
        self,
        days_ahead: int = 7,
        min_impact: EventImpact = EventImpact.MEDIUM,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Analyze upcoming economic events using LLM.
        
        Args:
            days_ahead: Number of days to analyze
            min_impact: Minimum event impact level
            force_refresh: Force refresh cache
        
        Returns:
            Dict containing LLM analysis and recommendations
        """
        # Check cache
        cache_key = f"{days_ahead}_{min_impact.value}"
        if not force_refresh and self._is_cache_valid(cache_key):
            logger.info("using_cached_analysis", cache_key=cache_key)
            return self.cache
        
        # Get upcoming events
        events = await self.calendar.get_upcoming_events(
            days_ahead=days_ahead,
            min_impact=min_impact
        )
        
        if not events:
            logger.warning("no_events_to_analyze")
            return {
                "success": True,
                "analysis": "No significant economic events scheduled in the next {} days.".format(days_ahead),
                "market_outlook": "NEUTRAL",
                "recommended_strategy": "NORMAL",
                "volatility_level": "LOW",
                "events_count": 0,
                "analyzed_at": datetime.now().isoformat()
            }
        
        # Build analysis prompt
        prompt = self._build_analysis_prompt(events, days_ahead)
        
        try:
            # Get LLM analysis
            logger.info(
                "requesting_llm_analysis",
                model=self.model,
                events_count=len(events)
            )
            
            response = await self.openrouter.call_agent(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower temperature for more focused analysis
                max_tokens=1500
            )
            
            # Parse LLM response
            analysis_text = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            if not analysis_text:
                raise ValueError("Empty response from LLM")
            
            # Extract structured data from analysis
            structured_analysis = self._parse_analysis(analysis_text, events)
            
            # Cache the result
            self.cache = structured_analysis
            self.cache_time = datetime.now()
            
            logger.info(
                "analysis_completed",
                events_analyzed=len(events),
                market_outlook=structured_analysis.get("market_outlook"),
                volatility_level=structured_analysis.get("volatility_level")
            )
            
            return structured_analysis
            
        except Exception as e:
            logger.error(
                "analysis_error",
                error=str(e),
                model=self.model
            )
            # Return fallback analysis
            return self._get_fallback_analysis(events)
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for LLM."""
        return """You are an expert financial analyst specializing in economic event analysis and market impact assessment.

Your role is to:
1. Analyze upcoming economic events and their potential market impact
2. Assess volatility levels and market sentiment
3. Provide actionable trading recommendations
4. Identify sectors and assets most likely to be affected

You must respond in a structured JSON format with the following fields:
{
  "summary": "Brief 2-3 sentence overview of the economic landscape",
  "market_outlook": "BULLISH|BEARISH|NEUTRAL|VOLATILE",
  "volatility_level": "HIGH|MEDIUM|LOW",
  "recommended_strategy": "NORMAL|CAUTIOUS|PAUSE|AGGRESSIVE",
  "key_events": ["List of most important upcoming events"],
  "potential_impacts": {
    "stocks": "Impact description for stock market",
    "crypto": "Impact description for crypto market",
    "forex": "Impact description for forex market"
  },
  "affected_sectors": ["List of sectors likely to be affected"],
  "trading_recommendations": [
    "Specific actionable recommendation 1",
    "Specific actionable recommendation 2",
    "Specific actionable recommendation 3"
  ],
  "risk_factors": ["Key risks to watch"]
}

Be precise, data-driven, and actionable in your analysis."""
    
    def _build_analysis_prompt(self, events: List[Dict], days_ahead: int) -> str:
        """Build analysis prompt from events."""
        events_text = "\n\n".join([
            f"**{event.get('name')}**\n"
            f"- Date: {event.get('date')} {event.get('time', 'TBD')}\n"
            f"- Country: {event.get('country')}\n"
            f"- Impact: {event.get('impact')}\n"
            f"- Description: {event.get('description', 'N/A')}\n"
            f"- Forecast: {event.get('forecast', 'N/A')}\n"
            f"- Previous: {event.get('previous', 'N/A')}"
            for event in events
        ])
        
        return f"""Analyze the following economic events scheduled for the next {days_ahead} days:

{events_text}

Current Date: {datetime.now().strftime('%Y-%m-%d')}

Please provide a comprehensive analysis of these events and their potential impact on financial markets (stocks, crypto, forex). Focus on:
1. Overall market sentiment and direction
2. Expected volatility levels
3. Sectors and assets most likely to be affected
4. Specific trading recommendations
5. Key risk factors to monitor

Respond ONLY with valid JSON following the specified format."""
    
    def _parse_analysis(self, analysis_text: str, events: List[Dict]) -> Dict[str, Any]:
        """
        Parse LLM analysis into structured format.
        
        Args:
            analysis_text: Raw LLM response
            events: Original events list
        
        Returns:
            Structured analysis dict
        """
        try:
            # Try to extract JSON from response
            # LLM might wrap JSON in markdown code blocks
            if "```json" in analysis_text:
                json_start = analysis_text.index("```json") + 7
                json_end = analysis_text.index("```", json_start)
                json_text = analysis_text[json_start:json_end].strip()
            elif "```" in analysis_text:
                json_start = analysis_text.index("```") + 3
                json_end = analysis_text.index("```", json_start)
                json_text = analysis_text[json_start:json_end].strip()
            else:
                json_text = analysis_text.strip()
            
            # Parse JSON
            parsed = json.loads(json_text)
            
            # Add metadata
            parsed["success"] = True
            parsed["events_count"] = len(events)
            parsed["analyzed_at"] = datetime.now().isoformat()
            parsed["raw_analysis"] = analysis_text
            parsed["events"] = events[:5]  # Include top 5 events for reference
            
            return parsed
            
        except (json.JSONDecodeError, ValueError, IndexError) as e:
            logger.error("analysis_parse_error", error=str(e))
            # Return analysis with raw text
            return {
                "success": True,
                "summary": analysis_text[:500],  # First 500 chars
                "market_outlook": "NEUTRAL",
                "volatility_level": "MEDIUM",
                "recommended_strategy": "CAUTIOUS",
                "raw_analysis": analysis_text,
                "events_count": len(events),
                "analyzed_at": datetime.now().isoformat(),
                "parse_error": True
            }
    
    def _get_fallback_analysis(self, events: List[Dict]) -> Dict[str, Any]:
        """
        Generate fallback analysis when LLM fails.
        
        Args:
            events: List of events
        
        Returns:
            Basic analysis based on event impact levels
        """
        high_impact_count = sum(1 for e in events if e.get("impact") == "HIGH")
        medium_impact_count = sum(1 for e in events if e.get("impact") == "MEDIUM")
        
        if high_impact_count >= 3:
            volatility = "HIGH"
            strategy = "CAUTIOUS"
            outlook = "VOLATILE"
        elif high_impact_count >= 1:
            volatility = "MEDIUM"
            strategy = "CAUTIOUS"
            outlook = "NEUTRAL"
        elif medium_impact_count >= 3:
            volatility = "MEDIUM"
            strategy = "NORMAL"
            outlook = "NEUTRAL"
        else:
            volatility = "LOW"
            strategy = "NORMAL"
            outlook = "NEUTRAL"
        
        return {
            "success": True,
            "summary": f"Found {len(events)} upcoming economic events ({high_impact_count} high-impact). Analysis service temporarily unavailable.",
            "market_outlook": outlook,
            "volatility_level": volatility,
            "recommended_strategy": strategy,
            "key_events": [e.get("name") for e in events[:5]],
            "events_count": len(events),
            "analyzed_at": datetime.now().isoformat(),
            "fallback": True
        }
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache is still valid."""
        if not self.cache or not self.cache_time:
            return False
        
        age = datetime.now() - self.cache_time
        return age < self.cache_ttl
    
    async def get_high_impact_summary(self) -> Dict[str, Any]:
        """
        Get quick summary of high-impact events (optimized for dashboard).
        
        Returns:
            Quick summary of high-impact events
        """
        events = await self.calendar.get_upcoming_events(
            days_ahead=3,
            min_impact=EventImpact.HIGH
        )
        
        if not events:
            return {
                "has_high_impact": False,
                "count": 0,
                "next_event": None,
                "alert_level": "LOW"
            }
        
        # Check if any event is today or tomorrow
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        
        today_events = [e for e in events if e.get("date") == today.isoformat()]
        tomorrow_events = [e for e in events if e.get("date") == tomorrow.isoformat()]
        
        if today_events:
            alert_level = "CRITICAL"
            next_event = today_events[0]
        elif tomorrow_events:
            alert_level = "HIGH"
            next_event = tomorrow_events[0]
        else:
            alert_level = "MEDIUM"
            next_event = events[0]
        
        return {
            "has_high_impact": True,
            "count": len(events),
            "today_count": len(today_events),
            "tomorrow_count": len(tomorrow_events),
            "next_event": next_event,
            "alert_level": alert_level,
            "events": events[:3]  # Top 3 events
        }


# Singleton instance
_analyzer: Optional[EconomicCalendarAnalyzer] = None


def get_analyzer(model: str = "anthropic/claude-3.5-sonnet") -> EconomicCalendarAnalyzer:
    """Get or create analyzer singleton."""
    global _analyzer
    if _analyzer is None:
        _analyzer = EconomicCalendarAnalyzer(model=model)
    return _analyzer
