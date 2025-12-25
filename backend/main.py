"""
Main FastAPI application.
Provides REST API, WebSocket streaming, and orchestrates the trading system.
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import List
from sqlalchemy import text
import structlog
import asyncio
from datetime import datetime

from config import get_settings
from database import init_db, get_db
from models.database import Portfolio, Trade, Decision, AgentReflection
from agents.gpt_agent import GPT4Agent
from agents.claude_agent import ClaudeAgent
from agents.grok_agent import GrokAgent
from agents.gemini_agent import GeminiAgent
from agents.deepseek_agent import DeepSeekAgent
from agents.mistral_agent import MistralAgent

logger = structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)
logger = structlog.get_logger()

settings = get_settings()


# WebSocket connections manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass


manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("application_startup", mode=settings.trading_mode)
    
    # Initialize database
    init_db()
    
    # Initialize portfolios for all agents
    _initialize_portfolios()
    
    # Start scheduler
    from scheduler import start_scheduler, TradingOrchestrator
    scheduler = start_scheduler(manager)
    
    # Run initial market analysis if enabled
    if settings.run_analysis_on_startup:
        logger.info("startup_analysis_begin")
        try:
            orchestrator = TradingOrchestrator(manager)
            await orchestrator.run_trading_cycle()
            logger.info("startup_analysis_complete")
        except Exception as e:
            logger.error("startup_analysis_failed", error=str(e), exc_info=True)
            # Don't fail startup if analysis fails
    else:
        logger.info("startup_analysis_disabled")
    
    
    yield
    
    # Shutdown
    logger.info("application_shutdown")
    scheduler.shutdown()


app = FastAPI(
    title="Multi-AI Trading System",
    description="Autonomous trading platform with 6 AI agents",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include crew API routes
from api.crew_routes import router as crew_router
app.include_router(crew_router)

# Include economic calendar API routes
from api.economic_routes import router as economic_router
app.include_router(economic_router, tags=["economic"])

# Include learning analytics API routes
from api.learning_routes import router as learning_router
app.include_router(learning_router, tags=["learning"])

# Include model management API routes
from routes.model_routes import router as model_router
app.include_router(model_router, tags=["models"])


def _initialize_portfolios():
    """Initialize portfolios for all agents if they don't exist."""
    agents = ["gpt4", "claude", "grok", "gemini", "deepseek", "mistral"]
    
    with get_db() as db:
        for agent_key in agents:
            from config import AGENT_CONFIGS
            agent_config = AGENT_CONFIGS[agent_key]
            agent_name = agent_config["name"]
            
            existing = db.query(Portfolio).filter(
                Portfolio.agent_name == agent_name
            ).first()
            
            if not existing:
                portfolio = Portfolio(
                    agent_name=agent_name,
                    cash=settings.initial_capital,
                    total_value=settings.initial_capital,
                    initial_value=settings.initial_capital,
                    positions={},
                )
                db.add(portfolio)
                logger.info(
                    "portfolio_initialized",
                    agent=agent_name,
                    capital=settings.initial_capital,
                )
        
        db.commit()


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Multi-AI Trading System",
        "version": "1.0.0",
        "mode": settings.trading_mode,
        "agents": 6,
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    # Check database
    try:
        with get_db() as db:
            db.execute(text("SELECT 1"))
        db_healthy = True
    except:
        db_healthy = False
    
    # Check OpenRouter
    from services.openrouter import get_openrouter_client
    openrouter = get_openrouter_client()
    openrouter_healthy = await openrouter.healthcheck()
    
    # Check Alpaca (only if live trading)
    alpaca_healthy = True
    if not settings.is_paper_trading():
        from services.alpaca_connector import get_alpaca_connector
        alpaca = get_alpaca_connector()
        alpaca_healthy = await alpaca.healthcheck()
    
    status = "healthy" if all([db_healthy, openrouter_healthy, alpaca_healthy]) else "degraded"
    
    return {
        "status": status,
        "database": db_healthy,
        "openrouter": openrouter_healthy,
        "alpaca": alpaca_healthy,
    }


@app.get("/agents")
async def list_agents():
    """List all agents and their performance."""
    with get_db() as db:
        portfolios = db.query(Portfolio).all()
        
        agents_data = []
        for portfolio in portfolios:
            agents_data.append({
                "name": portfolio.agent_name,
                "cash": portfolio.cash,
                "total_value": portfolio.total_value,
                "pnl": portfolio.total_pnl,
                "pnl_percent": portfolio.total_pnl_percent,
                "total_trades": portfolio.total_trades,
                "winning_trades": portfolio.winning_trades,
                "losing_trades": portfolio.losing_trades,
                "win_rate": (portfolio.winning_trades / (portfolio.total_trades or 1)) * 100,
                "positions_count": len(portfolio.positions or {}),
            })
        
        return {"agents": agents_data}


@app.get("/agents/{agent_name}")
async def get_agent_details(agent_name: str):
    """Get detailed information about a specific agent."""
    with get_db() as db:
        portfolio = db.query(Portfolio).filter(
            Portfolio.agent_name == agent_name
        ).first()
        
        if not portfolio:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Get recent trades
        recent_trades = db.query(Trade).filter(
            Trade.agent_name == agent_name
        ).order_by(Trade.created_at.desc()).limit(20).all()
        
        # Get recent decisions
        recent_decisions = db.query(Decision).filter(
            Decision.agent_name == agent_name
        ).order_by(Decision.created_at.desc()).limit(10).all()
        
        # Get recent reflections
        reflections = db.query(AgentReflection).filter(
            AgentReflection.agent_name == agent_name
        ).order_by(AgentReflection.created_at.desc()).limit(5).all()
        
        return {
            "agent": agent_name,
            "portfolio": {
                "cash": portfolio.cash,
                "total_value": portfolio.total_value,
                "pnl": portfolio.total_pnl,
                "pnl_percent": portfolio.total_pnl_percent,
                "positions": portfolio.positions,
            },
            "stats": {
                "total_trades": portfolio.total_trades,
                "winning_trades": portfolio.winning_trades,
                "losing_trades": portfolio.losing_trades,
                "sharpe_ratio": portfolio.sharpe_ratio,
                "max_drawdown": portfolio.max_drawdown_percent,
            },
            "recent_trades": [
                {
                    "symbol": t.symbol,
                    "action": t.action.value,
                    "quantity": t.quantity,
                    "price": t.price,
                    "executed_at": t.executed_at.isoformat() if t.executed_at else None,
                    "reasoning": t.reasoning,
                }
                for t in recent_trades
            ],
            "recent_decisions": [
                {
                    "action": d.final_action,
                    "reasoning": d.reasoning,
                    "created_at": d.created_at.isoformat(),
                }
                for d in recent_decisions
            ],
            "reflections": [
                {
                    "well": r.what_went_well,
                    "wrong": r.what_went_wrong,
                    "improvements": r.improvements_planned,
                    "created_at": r.created_at.isoformat(),
                }
                for r in reflections
            ],
        }


@app.get("/trades")
async def get_all_trades(limit: int = 50):
    """Get recent trades across all agents."""
    with get_db() as db:
        trades = db.query(Trade).order_by(
            Trade.created_at.desc()
        ).limit(limit).all()
        
        return {
            "trades": [
                {
                    "id": t.id,
                    "agent": t.agent_name,
                    "symbol": t.symbol,
                    "action": t.action.value,
                    "quantity": t.quantity,
                    "price": t.price,
                    "status": t.status.value,
                    "created_at": t.created_at.isoformat(),
                }
                for t in trades
            ]
        }


@app.post("/trading/pause")
async def pause_trading():
    """Pause automatic trading."""
    # TODO: Implement pause logic in scheduler
    return {"status": "paused"}


@app.post("/trading/resume")
async def resume_trading():
    """Resume automatic trading."""
    # TODO: Implement resume logic in scheduler
    return {"status": "resumed"}


@app.post("/agents/{agent_name}/reflect")
async def trigger_reflection(agent_name: str):
    """Manually trigger agent reflection."""
    agent_map = {
        "GPT-4 Holder": GPT4Agent,
        "Claude Équilibré": ClaudeAgent,
        "Grok Sniper": GrokAgent,
        "Gemini Gestionnaire": GeminiAgent,
        "DeepSeek Nerveux": DeepSeekAgent,
        "Mistral Marine": MistralAgent,
    }
    
    agent_class = agent_map.get(agent_name)
    if not agent_class:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent = agent_class()
    result = await agent.reflect()
    
    return result


@app.get("/funds/realtime")
async def get_realtime_funds():
    """Get real-time funds information across all agents."""
    with get_db() as db:
        portfolios = db.query(Portfolio).all()
        
        # Calculate totals
        total_cash = sum(p.cash for p in portfolios)
        total_value = sum(p.total_value for p in portfolios)
        total_stock_value = sum(p.stock_value or 0 for p in portfolios)
        total_crypto_value = sum(p.crypto_value or 0 for p in portfolios)
        total_pnl = sum(p.total_pnl for p in portfolios)
        total_initial = sum(p.initial_value for p in portfolios)
        
        # Calculate overall P&L percentage
        total_pnl_percent = ((total_value - total_initial) / total_initial * 100) if total_initial > 0 else 0
        
        # Get total positions count
        total_positions = sum(len(p.positions or {}) for p in portfolios)
        
        # Get breakdown by agent
        agents_funds = []
        for portfolio in portfolios:
            agents_funds.append({
                "agent_name": portfolio.agent_name,
                "cash": portfolio.cash,
                "total_value": portfolio.total_value,
                "stock_value": portfolio.stock_value or 0,
                "crypto_value": portfolio.crypto_value or 0,
                "pnl": portfolio.total_pnl,
                "pnl_percent": portfolio.total_pnl_percent,
                "positions_count": len(portfolio.positions or {}),
            })
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "totals": {
                "cash": total_cash,
                "total_value": total_value,
                "stock_value": total_stock_value,
                "crypto_value": total_crypto_value,
                "pnl": total_pnl,
                "pnl_percent": total_pnl_percent,
                "positions_count": total_positions,
                "initial_capital": total_initial,
            },
            "agents": agents_funds,
        }


@app.get("/performance/breakdown")
async def get_performance_breakdown():
    """Get performance breakdown by asset type (stocks vs crypto)."""
    with get_db() as db:
        portfolios = db.query(Portfolio).all()
        trades = db.query(Trade).all()
        
        # Calculate stock vs crypto stats
        stock_trades = [t for t in trades if t.asset_type == "stock"]
        crypto_trades = [t for t in trades if t.asset_type == "crypto"]
        
        stock_executed = [t for t in stock_trades if t.status == "executed"]
        crypto_executed = [t for t in crypto_trades if t.status == "executed"]
        
        # Agent performance by asset type
        agents_performance = []
        for portfolio in portfolios:
            agent_stock_trades = [t for t in stock_executed if t.agent_name == portfolio.agent_name]
            agent_crypto_trades = [t for t in crypto_executed if t.agent_name == portfolio.agent_name]
            
            agents_performance.append({
                "agent_name": portfolio.agent_name,
                "stock": {
                    "value": portfolio.stock_value or 0,
                    "trades_count": len(agent_stock_trades),
                },
                "crypto": {
                    "value": portfolio.crypto_value or 0,
                    "trades_count": len(agent_crypto_trades),
                },
                "total_pnl": portfolio.total_pnl,
                "pnl_percent": portfolio.total_pnl_percent,
            })
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "breakdown": {
                "stocks": {
                    "total_value": sum(p.stock_value or 0 for p in portfolios),
                    "total_trades": len(stock_executed),
                    "pending_trades": len([t for t in stock_trades if t.status == "pending"]),
                },
                "crypto": {
                    "total_value": sum(p.crypto_value or 0 for p in portfolios),
                    "total_trades": len(crypto_executed),
                    "pending_trades": len([t for t in crypto_trades if t.status == "pending"]),
                },
            },
            "agents": agents_performance,
        }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
