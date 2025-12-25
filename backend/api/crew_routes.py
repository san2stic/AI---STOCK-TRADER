"""
API endpoints for crew collaboration features.
"""
from fastapi import APIRouter, HTTPException
from typing import List, Optional
from datetime import datetime
import structlog

from database import get_db
from config import get_settings

logger = structlog.get_logger()
router = APIRouter(prefix="/api/crew", tags=["crew"])


@router.get("/sessions")
async def get_crew_sessions(limit: int = 20):
    """List recent crew deliberation sessions."""
    with get_db() as db:
        from models.crew_models import CrewSession
        
        sessions = db.query(CrewSession).order_by(
            CrewSession.started_at.desc()
        ).limit(limit).all()
        
        return {
            "sessions": [
                {
                    "session_id": s.session_id,
                    "status": s.status.value if s.status else None,
                    "final_decision": s.final_decision,
                    "final_symbol": s.final_symbol,
                    "consensus_score": s.consensus_score,
                    "total_messages": s.total_messages,
                    "mediator_used": s.mediator_used,
                    "started_at": s.started_at.isoformat() if s.started_at else None,
                    "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                    "duration_seconds": s.duration_seconds,
                }
                for s in sessions
            ]
        }


@router.get("/sessions/{session_id}")
async def get_session_details(session_id: str):
    """Get detailed information about a specific crew session."""
    with get_db() as db:
        from models.crew_models import CrewSession, AgentMessage, CrewVote
        
        session = db.query(CrewSession).filter(
            CrewSession.session_id == session_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get all messages
        messages = db.query(AgentMessage).filter(
            AgentMessage.session_id == session.id
        ).order_by(AgentMessage.round_number, AgentMessage.sequence_number).all()
        
        # Get all votes
        votes = db.query(CrewVote).filter(
            CrewVote.session_id == session.id
        ).all()
        
        return {
            "session": {
                "session_id": session.session_id,
                "status": session.status.value if session.status else None,
                "final_decision": session.final_decision,
                "final_symbol": session.final_symbol,
                "consensus_score": session.consensus_score,
                "market_context": session.market_context,
                "symbols_discussed": session.symbols_discussed,
                "total_rounds": session.total_rounds,
                "mediator_used": session.mediator_used,
                "mediator_reasoning": session.mediator_reasoning,
                "started_at": session.started_at.isoformat() if session.started_at else None,
                "completed_at": session.completed_at.isoformat() if session.completed_at else None,
                "duration_seconds": session.duration_seconds,
            },
            "messages": [
                {
                    "message_id": m.message_id,
                    "agent_name": m.agent_name,
                    "round_number": m.round_number,
                    "message_type": m.message_type.value if m.message_type else None,
                    "content": m.content,
                    "proposed_action": m.proposed_action,
                    "proposed_symbol": m.proposed_symbol,
                    "confidence_level": m.confidence_level,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in messages
            ],
            "votes": [
                {
                    "vote_id": v.vote_id,
                    "agent_name": v.agent_name,
                    "vote_action": v.vote_action.value if v.vote_action else None,
                    "vote_symbol": v.vote_symbol,
                    "vote_weight": v.vote_weight,
                    "confidence_level": v.confidence_level,
                    "reasoning": v.reasoning,
                    "weighted_score": v.weighted_score,
                }
                for v in votes
            ],
        }


@router.get("/analytics")
async def get_crew_analytics():
    """Get crew performance analytics and statistics."""
    with get_db() as db:
        from models.crew_models import CrewSession, CrewVote, AgentMessage
        from sqlalchemy import func
        
        # Basic session statistics
        total_sessions = db.query(func.count(CrewSession.id)).scalar() or 0
        
        consensus_sessions = db.query(func.count(CrewSession.id)).filter(
            CrewSession.consensus_score >= 66
        ).scalar() or 0
        
        avg_consensus = db.query(func.avg(CrewSession.consensus_score)).scalar() or 0
        avg_duration = db.query(func.avg(CrewSession.duration_seconds)).scalar() or 0
        avg_messages = db.query(func.avg(CrewSession.total_messages)).scalar() or 0
        
        mediator_count = db.query(func.count(CrewSession.id)).filter(
            CrewSession.mediator_used == True
        ).scalar() or 0
        
        # Most active agents (by message count)
        agent_message_counts = db.query(
            AgentMessage.agent_name,
            func.count(AgentMessage.id).label('message_count')
        ).group_by(AgentMessage.agent_name).all()
        
        # Vote distribution
        vote_distribution = db.query(
            CrewVote.vote_action,
            func.count(CrewVote.id).label('count')
        ).group_by(CrewVote.vote_action).all()
        
        return {
            "total_sessions": total_sessions,
            "consensus_rate": (consensus_sessions / max(total_sessions, 1)) * 100,
            "avg_consensus_score": avg_consensus,
            "avg_duration_seconds": avg_duration,
            "avg_messages_per_session": avg_messages,
            "mediator_invocations": mediator_count,
            "mediator_rate": (mediator_count / max(total_sessions, 1)) * 100,
            "agent_activity": {
                agent: count for agent, count in agent_message_counts
            },
            "vote_distribution": {
                str(action): count for action, count in vote_distribution
            },
        }


@router.post("/test-deliberation")
async def test_deliberation(symbols: Optional[List[str]] = None):
    """Trigger a test deliberation session."""
    settings = get_settings()
    
    if not settings.enable_crew_mode:
        raise HTTPException(
            status_code=400,
            detail="Crew mode is not enabled"
        )
    
    # Create test market context
    test_symbols = symbols or ["AAPL", "NVDA"]
    
    from services.data_collector import get_data_collector
    data_collector = get_data_collector()
    
    market_context = {
        "prices": {},
        "news": [],
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    for symbol in test_symbols:
        try:
            price_data = await data_collector.get_current_price(symbol)
            market_context["prices"][symbol] = price_data
        except Exception as e:
            logger.warning(f"Failed to get price for {symbol}: {e}")
    
    # Create agents
    from agents.gpt_agent import GPT4Agent
    from agents.claude_agent import ClaudeAgent
    from agents.grok_agent import GrokAgent
    from agents.gemini_agent import GeminiAgent
    from agents.deepseek_agent import DeepSeekAgent
    from agents.mistral_agent import MistralAgent
    
    agents = [
        GPT4Agent(),
        ClaudeAgent(),
        GrokAgent(),
        GeminiAgent(),
        DeepSeekAgent(),
        MistralAgent(),
    ]
    
    # Run deliberation
    from crew.crew_orchestrator import CrewOrchestrator
    crew = CrewOrchestrator(agents, None)
    
    result = await crew.run_deliberation_session(market_context)
    
    return {
        "status": "success",
        "session_id": result.get("session_id"),
        "result": result,
    }
