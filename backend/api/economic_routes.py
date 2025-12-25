"""
Economic calendar API routes.
Provides endpoints to fetch and refresh economic events.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Optional
from datetime import date
import structlog
from services.economic_calendar import get_economic_calendar, EventImpact

logger = structlog.get_logger()
router = APIRouter(prefix="/api", tags=["economic"])


@router.get("/economic-events")
async def get_economic_events(
    days_ahead: int = Query(7, ge=1, le=30, description="Number of days ahead to fetch"),
    min_impact: str = Query("MEDIUM", regex="^(HIGH|MEDIUM|LOW)$", description="Minimum impact level")
) -> Dict:
    """
    Get upcoming economic events from database and free APIs.
    
    Args:
        days_ahead: Number of days ahead (1-30)
        min_impact: Minimum impact level (HIGH, MEDIUM, LOW)
    
    Returns:
        Dict with events list, count, and metadata
    """
    try:
        # Parse impact level
        impact = EventImpact(min_impact)
        
        # Get calendar service
        calendar = get_economic_calendar()
        
        # Fetch events
        events = await calendar.get_upcoming_events(
            days_ahead=days_ahead,
            min_impact=impact
        )
        
        logger.info(
            "api_economic_events_fetched",
            count=len(events),
            days_ahead=days_ahead,
            min_impact=min_impact
        )
        
        return {
            "success": True,
            "events": events,
            "count": len(events),
            "days_ahead": days_ahead,
            "min_impact": min_impact,
            "source": "database" if events and events[0].get("source") != "forex_factory" else "forex_factory"
        }
        
    except ValueError as e:
        logger.error("invalid_impact_level", error=str(e))
        raise HTTPException(status_code=400, detail=f"Invalid impact level: {min_impact}")
    except Exception as e:
        logger.error("economic_events_fetch_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch economic events")


@router.post("/economic-events/refresh")
async def refresh_economic_events(
    days_ahead: int = Query(7, ge=1, le=30, description="Number of days ahead to refresh"),
    force: bool = Query(False, description="Force refresh even if data is fresh")
) -> Dict:
    """
    Manually trigger economic calendar refresh from free APIs.
    
    Args:
        days_ahead: Number of days ahead to refresh (1-30)
        force: Force refresh even if data is fresh
    
    Returns:
        Dict with refresh status and event count
    """
    try:
        from services.forex_factory_connector import get_forex_factory_connector
        
        logger.info(
            "manual_calendar_refresh_triggered",
            days_ahead=days_ahead,
            force=force
        )
        
        # Fetch from Forex Factory
        forex_connector = get_forex_factory_connector()
        
        # Clear cache if force refresh
        if force:
            forex_connector.cache = None
            forex_connector.cache_time = None
        
        # Fetch events (all impact levels for refresh)
        events = await forex_connector.fetch_calendar_events(
            days_ahead=days_ahead,
            min_impact="LOW"  # Get all events
        )
        
        if not events:
            logger.warning("refresh_no_events_found")
            return {
                "success": True,
                "message": "No events found from API",
                "count": 0,
                "source": "forex_factory"
            }
        
        # Save to database
        calendar = get_economic_calendar()
        await calendar._save_events_to_db(events)
        
        logger.info(
            "calendar_refreshed",
            count=len(events),
            source="forex_factory"
        )
        
        return {
            "success": True,
            "message": f"Successfully refreshed {len(events)} events",
            "count": len(events),
            "source": "forex_factory",
            "days_ahead": days_ahead
        }
        
    except Exception as e:
        logger.error("calendar_refresh_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to refresh calendar: {str(e)}")


@router.get("/economic-events/upcoming-high-impact")
async def get_upcoming_high_impact() -> Dict:
    """
    Get only upcoming high-impact events (next 3 days).
    Optimized endpoint for dashboard widgets.
    
    Returns:
        Dict with high-impact events
    """
    try:
        calendar = get_economic_calendar()
        events = await calendar.get_upcoming_events(
            days_ahead=3,
            min_impact=EventImpact.HIGH
        )
        
        # Check if any event is today
        today_str = date.today().isoformat()
        has_event_today = any(e["date"] == today_str for e in events)
        
        return {
            "success": True,
            "events": events,
            "count": len(events),
            "has_event_today": has_event_today,
            "next_event": events[0] if events else None
        }
        
    except Exception as e:
        logger.error("high_impact_events_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch high-impact events")


@router.get("/economic-events/analysis")
async def get_economic_analysis(
    days_ahead: int = Query(7, ge=1, le=30, description="Number of days ahead to analyze"),
    min_impact: str = Query("MEDIUM", regex="^(HIGH|MEDIUM|LOW)$", description="Minimum impact level"),
    force_refresh: bool = Query(False, description="Force refresh analysis cache")
) -> Dict:
    """
    Get LLM-powered analysis of upcoming economic events.
    
    Args:
        days_ahead: Number of days ahead (1-30)
        min_impact: Minimum impact level (HIGH, MEDIUM, LOW)
        force_refresh: Force refresh cache
    
    Returns:
        Dict with comprehensive economic analysis and trading recommendations
    """
    try:
        from services.economic_calendar_analyzer import get_analyzer
        
        # Parse impact level
        impact = EventImpact(min_impact)
        
        # Get analyzer
        analyzer = get_analyzer()
        
        # Get analysis
        analysis = await analyzer.analyze_upcoming_events(
            days_ahead=days_ahead,
            min_impact=impact,
            force_refresh=force_refresh
        )
        
        logger.info(
            "api_economic_analysis_fetched",
            days_ahead=days_ahead,
            min_impact=min_impact,
            market_outlook=analysis.get("market_outlook")
        )
        
        return analysis
        
    except ValueError as e:
        logger.error("invalid_impact_level", error=str(e))
        raise HTTPException(status_code=400, detail=f"Invalid impact level: {min_impact}")
    except Exception as e:
        logger.error("economic_analysis_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to analyze events: {str(e)}")


@router.post("/economic-events/analysis/refresh")
async def refresh_economic_analysis(
    days_ahead: int = Query(7, ge=1, le=30, description="Number of days ahead to analyze")
) -> Dict:
    """
    Force refresh economic calendar analysis.
    
    Args:
        days_ahead: Number of days ahead to analyze
    
    Returns:
        Fresh analysis
    """
    try:
        from services.economic_calendar_analyzer import get_analyzer
        
        logger.info("manual_analysis_refresh_triggered", days_ahead=days_ahead)
        
        # Get analyzer and force refresh
        analyzer = get_analyzer()
        analysis = await analyzer.analyze_upcoming_events(
            days_ahead=days_ahead,
            min_impact=EventImpact.MEDIUM,
            force_refresh=True
        )
        
        logger.info("analysis_refreshed", market_outlook=analysis.get("market_outlook"))
        
        return {
            "success": True,
            "message": "Analysis refreshed successfully",
            "analysis": analysis
        }
        
    except Exception as e:
        logger.error("analysis_refresh_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to refresh analysis: {str(e)}")


@router.get("/economic-events/summary")
async def get_high_impact_summary() -> Dict:
    """
    Get quick summary of high-impact events for dashboard.
    Optimized for crew agents to quickly assess economic risks.
    
    Returns:
        Quick summary with alert level
    """
    try:
        from services.economic_calendar_analyzer import get_analyzer
        
        analyzer = get_analyzer()
        summary = await analyzer.get_high_impact_summary()
        
        return summary
        
    except Exception as e:
        logger.error("high_impact_summary_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch summary")
