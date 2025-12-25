"""
Trading scheduler - orchestrates agent decisions and executions.
Runs on a schedule during market hours.
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, time, date
import asyncio
import structlog

from config import get_settings, AGENT_CONFIGS
from agents.gpt_agent import GPT4Agent
from agents.claude_agent import ClaudeAgent
from agents.grok_agent import GrokAgent
from agents.gemini_agent import GeminiAgent
from agents.deepseek_agent import DeepSeekAgent
from agents.mistral_agent import MistralAgent
from services.data_collector import get_data_collector
from services.risk_manager import get_risk_manager
from services.market_calendar import get_market_calendar
from services.economic_calendar import get_economic_calendar, EventImpact

logger = structlog.get_logger()
settings = get_settings()


from agents.generic_agent import GenericAgent

# Map legacy keys to specific classes for backward compatibility
AGENT_CLASS_MAP = {
    "gpt4": GPT4Agent,
    "claude": ClaudeAgent,
    "grok": GrokAgent,
    "gemini": GeminiAgent,
    "deepseek": DeepSeekAgent,
    "mistral": MistralAgent,
}

class TradingOrchestrator:
    """Orchestrates trading decisions across all agents."""
    
    def __init__(self, ws_manager=None):
        # Dynamic agent loading
        self.agents = []
        for key in AGENT_CONFIGS.keys():
            if key in AGENT_CLASS_MAP:
                # Use specific class for legacy agents
                self.agents.append(AGENT_CLASS_MAP[key]())
            else:
                # Use GenericAgent for new agents (researcher, risk_manager, etc.)
                self.agents.append(GenericAgent(key))
                
        logger.info("loaded_agents", count=len(self.agents), keys=list(AGENT_CONFIGS.keys()))
        self.data_collector = get_data_collector()
        self.risk_manager = get_risk_manager()
        self.ws_manager = ws_manager
        self.is_trading_active = True
        
        # Initialize market calendar and economic calendar
        self.market_calendar = get_market_calendar()
        self.economic_calendar = get_economic_calendar(
            api_key=settings.economic_calendar_api_key if hasattr(settings, 'economic_calendar_api_key') else None
        )
        
        logger.info(
            "orchestrator_initialized",
            agents=len(self.agents),
            mode=settings.trading_mode,
            holiday_check=settings.enable_holiday_check if hasattr(settings, 'enable_holiday_check') else False,
            economic_check=settings.enable_economic_calendar if hasattr(settings, 'enable_economic_calendar') else False,
        )
    
    async def collect_market_data(self, market_type: str = "STOCK") -> dict:
        """Collect current market data for allowed symbols or crypto pairs."""
        if market_type == "CRYPTO":
            # Collect crypto data
            from services.binance_connector import get_binance_connector
            binance = get_binance_connector()
            
            # Get pairs to track
            if settings.use_all_binance_pairs:
                # Get top pairs by volume (to avoid overwhelming the agents)
                all_pairs = await binance.get_all_tradable_pairs()
                # Use top 20 most common pairs for data collection
                common_pairs = [
                    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
                    "ADAUSDT", "DOGEUSDT", "MATICUSDT", "DOTUSDT", "LTCUSDT",
                    "AVAXUSDT", "LINKUSDT", "ATOMUSDT", "UNIUSDT", "NEARUSDT",
                    "APTUSDT", "ARBUSDT", "OPUSDT", "SUIUSDT", "INJUSDT"
                ]
                pairs = common_pairs
                logger.info("using_common_crypto_pairs", pairs=len(pairs), available=len(all_pairs))
            else:
                # Use configured whitelist
                pairs = settings.get_allowed_crypto_pairs()
                if not pairs:
                    pairs = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
            
            logger.info("collecting_crypto_data", pairs=len(pairs))
            
            from services.binance_connector import get_binance_connector
            binance = get_binance_connector()
            
            prices = {}
            for pair in pairs:
                try:
                    price_data = await binance.get_crypto_price(pair)
                    if price_data:
                        prices[pair] = price_data
                except Exception as e:
                    logger.error("crypto_data_error", pair=pair, error=str(e))
            
            return {
                "prices": prices,
                "news": [],  # Could add crypto news here
                "market_type": "CRYPTO",
                "timestamp": datetime.utcnow().isoformat(),
            }
        else:
            # Collect stock data (original behavior)
            symbols = settings.get_allowed_symbols()
            if not symbols:
                # Default symbols if none specified
                symbols = ["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA"]
            
            # Add Watchlist symbols to collection
            try:
                from database import get_db
                from models.database import Watchlist
                
                with get_db() as db:
                    watchlist_items = db.query(Watchlist.symbol).distinct().all()
                    watchlist_symbols = [item[0] for item in watchlist_items]
                    
                    if watchlist_symbols:
                        logger.info("adding_watchlist_symbols", count=len(watchlist_symbols), symbols=watchlist_symbols)
                        symbols = list(set(symbols + watchlist_symbols))
            except Exception as e:
                logger.error("watchlist_load_error", error=str(e))
            
            logger.info("collecting_market_data", symbols=len(symbols))
            
            prices = {}
            news_all = []
            
            # Collect prices and news for each symbol
            for symbol in symbols:
                try:
                    # Get current price
                    price_data = await self.data_collector.get_current_price(symbol)
                    prices[symbol] = price_data
                    
                    # Get recent news
                    news = await self.data_collector.get_news(symbol, days=3)
                    news_all.extend(news[:2])  # Top 2 articles per symbol
                    
                except Exception as e:
                    logger.error("data_collection_error", symbol=symbol, error=str(e))
            
            return {
                "prices": prices,
                "news": news_all,
                "market_type": "STOCK",
                "timestamp": datetime.utcnow().isoformat(),
            }
    
    async def run_trading_cycle(self):
        """Execute one trading cycle - all agents make decisions."""
        if not self.is_trading_active:
            logger.info("trading_paused", message="Cycle skipped")
            return
        
        # Check trading conditions (holidays, economic events)
        can_trade, trading_mode, reason = await self._check_trading_conditions()
        
        if not can_trade:
            logger.info(
                "trading_blocked",
                reason=reason,
                message="Trading cycle skipped"
            )
            # Broadcast trading pause to frontend
            if self.ws_manager:
                await self.ws_manager.broadcast({
                    "type": "trading_paused",
                    "reason": reason,
                    "timestamp": datetime.utcnow().isoformat(),
                })
            return
        
        # Determine market type (STOCK or CRYPTO)
        market_type = self._get_active_market_type()
        
        logger.info(
            "trading_cycle_start",
            market_type=market_type,
            trading_mode=trading_mode
        )
        
        try:
            # 1. Collect market data based on market type
            market_context = await self.collect_market_data(market_type)
            
            # Broadcast to WebSocket clients
            if self.ws_manager:
                await self.ws_manager.broadcast({
                    "type": "market_data",
                    "data": market_context,
                })
            
            # 2. Check stop-losses before agent decisions
            await self._check_all_stop_losses()
            
            # 3. Run agents - either crew mode or independent mode
            if settings.enable_crew_mode:
                # === CREW MODE ===
                logger.info("running_crew_deliberation")
                
                from crew.crew_orchestrator import CrewOrchestrator
                crew = CrewOrchestrator(self.agents, self.ws_manager)
                
                crew_result = await crew.run_deliberation_session(market_context)
                
                # Broadcast crew result
                if self.ws_manager:
                    await self.ws_manager.broadcast({
                        "type": "crew_decision",
                        "data": crew_result,
                    })
                
                # Validate and execute crew decision if not HOLD
                if crew_result["action"] != "hold" and crew_result.get("symbol"):
                    # Optional: Validate order with Claude 4.5 before execution
                    if settings.enable_order_validation:
                        from crew.order_validator import get_order_validator
                        validator = get_order_validator()
                        
                        # Get portfolio for validation
                        portfolio = await self.data_collector.get_current_price("portfolio") if hasattr(self, 'data_collector') else None
                        
                        validation_result = await validator.validate_order(
                            crew_decision=crew_result,
                            market_context=market_context,
                            portfolio_state=portfolio,
                        )
                        
                        # Broadcast validation result
                        if self.ws_manager:
                            await self.ws_manager.broadcast({
                                "type": "order_validation",
                                "data": validation_result,
                            })
                        
                        logger.info(
                            "order_validation_result",
                            approved=validation_result["approved"],
                            risk_level=validation_result.get("risk_level"),
                            action=crew_result["action"],
                        )
                        
                        # Only execute if approved
                        if validation_result["approved"]:
                            await self._execute_crew_decision(crew_result)
                        else:
                            logger.warning(
                                "order_rejected_by_validator",
                                action=crew_result["action"],
                                symbol=crew_result.get("symbol"),
                                reason=validation_result.get("reasoning"),
                            )
                    else:
                        # Direct execution without validation
                        await self._execute_crew_decision(crew_result)
                
                logger.info(
                    "crew_cycle_complete",
                    action=crew_result["action"],
                    consensus=crew_result.get("consensus_score"),
                )
            else:
                # === INDEPENDENT MODE ===
                logger.info("running_independent_agents")
                
                # Run all agents in parallel (original behavior)
                tasks = []
                for agent in self.agents:
                    tasks.append(agent.make_decision(market_context))
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results and broadcast
                for agent, result in zip(self.agents, results):
                    if isinstance(result, Exception):
                        logger.error(
                            "agent_decision_failed",
                            agent=agent.name,
                            error=str(result),
                        )
                        continue
                    
                    # Broadcast decision to WebSocket
                    if self.ws_manager:
                        await self.ws_manager.broadcast({
                            "type": "agent_decision",
                            "agent": agent.name,
                            "data": result,
                        })
                    
                    logger.info(
                        "agent_cycle_complete",
                        agent=agent.name,
                        action=result.get("action"),
                    )
            
            # 4. Check if any agent needs reflection
            await self._check_reflection_triggers()
            
            # 5. Run learning cycle to process closed trades
            await self._run_learning_cycle()
            
            logger.info("trading_cycle_complete", agents=len(self.agents))
            
        except Exception as e:
            logger.error("trading_cycle_error", error=str(e))
    
    async def _check_all_stop_losses(self):
        """Check stop-loss triggers for all agents."""
        for agent in self.agents:
            positions_to_close = self.risk_manager.check_stop_loss(agent.name)
            
            for position in positions_to_close:
                logger.warning(
                    "stop_loss_auto_sell",
                    agent=agent.name,
                    symbol=position["symbol"],
                    loss_percent=position["loss_percent"],
                )
                
                # Execute automatic sell via tools
                from tools.trading_tools import TradingTools
                tools = TradingTools(agent.name)
                
                result = await tools.sell_stock(
                    symbol=position["symbol"],
                    quantity=position["quantity"],
                )
                
                # Broadcast stop-loss trigger
                if self.ws_manager:
                    await self.ws_manager.broadcast({
                        "type": "stop_loss_triggered",
                        "agent": agent.name,
                        "position": position,
                        "result": result,
                    })
    
    async def _execute_crew_decision(self, crew_result: dict):
        """
        Execute the crew's consensus decision.
        In crew mode, we can either:
        1. Execute for a shared crew portfolio
        2. Execute for all individual agent portfolios
        
        Currently implementing option 2 - all agents follow the crew decision.
        """
        action = crew_result["action"]
        symbol = crew_result.get("symbol")
        quantity = crew_result.get("quantity", 10)
        
        logger.info(
            "executing_crew_decision",
            action=action,
            symbol=symbol,
            quantity=quantity,
        )
        
        from tools.trading_tools import TradingTools
        
        # Execute for each agent (they all follow the crew decision)
        for agent in self.agents:
            tools = TradingTools(agent.name)
            
            try:
                if action == "buy":
                    result = await tools.buy_stock(
                        symbol=symbol,
                        quantity=quantity,
                    )
                elif action == "sell":
                    result = await tools.sell_stock(
                        symbol=symbol,
                        quantity=quantity,
                    )
                
                logger.info(
                    "crew_trade_executed",
                    agent=agent.name,
                    action=action,
                    symbol=symbol,
                    result=result,
                )
            except Exception as e:
                logger.error(
                    "crew_trade_error",
                    agent=agent.name,
                    error=str(e),
                )
    
    async def _check_reflection_triggers(self):
        """Check if agents should reflect based on trade count."""
        from database import get_db
        from models.database import Trade, TradeStatus
        
        for agent in self.agents:
            with get_db() as db:
                # Count trades since last reflection
                from models.database import AgentReflection
                
                last_reflection = db.query(AgentReflection).filter(
                    AgentReflection.agent_name == agent.name
                ).order_by(AgentReflection.created_at.desc()).first()
                
                # Count trades after last reflection
                query = db.query(Trade).filter(
                    Trade.agent_name == agent.name,
                    Trade.status == TradeStatus.EXECUTED,
                )
                
                if last_reflection:
                    query = query.filter(
                        Trade.executed_at > last_reflection.created_at
                    )
                
                trades_count = query.count()
                
                # Trigger reflection if threshold met
                if trades_count >= settings.auto_critique_frequency:
                    logger.info(
                        "triggering_reflection",
                        agent=agent.name,
                        trades_since_last=trades_count,
                    )
                    
                    result = await agent.reflect()
                    
                    # Broadcast reflection
                    if self.ws_manager:
                        await self.ws_manager.broadcast({
                            "type": "agent_reflection",
                            "agent": agent.name,
                            "data": result,
                        })
    
    async def _check_trading_conditions(self) -> tuple[bool, str, str]:
        """
        Check if trading should proceed based on:
        - Market holidays (for stocks only, crypto is 24/7)
        - Economic events
        
        Returns:
            Tuple of (can_trade, trading_mode, reason)
            - can_trade: bool - whether to proceed with trading
            - trading_mode: str - "NORMAL", "CAUTIOUS", or "PAUSE"
            - reason: str - explanation for the decision
        """
        enable_holiday_check = getattr(settings, 'enable_holiday_check', True)
        enable_economic_check = getattr(settings, 'enable_economic_calendar', True)
        economic_strategy = getattr(settings, 'economic_event_strategy', 'NORMAL')
        
        # Determine market type FIRST - crypto markets trade 24/7
        market_type = self._get_active_market_type()
        
        # Crypto markets bypass holiday checks (24/7 trading)
        if market_type == "CRYPTO":
            logger.info(
                "crypto_market_active",
                reason="Crypto markets trade 24/7, bypassing stock market checks"
            )
            # Still check economic events for crypto if enabled
            if enable_economic_check and economic_strategy != "NORMAL":
                has_high_impact = await self.economic_calendar.has_high_impact_event_today()
                if has_high_impact:
                    upcoming_events = await self.economic_calendar.get_upcoming_events(
                        days_ahead=1, 
                        min_impact=EventImpact.HIGH
                    )
                    if upcoming_events:
                        event = upcoming_events[0]
                        if economic_strategy == "CAUTIOUS":
                            return True, "CAUTIOUS", f"High-impact event today: {event['name']} (crypto trading cautiously)"
            
            return True, "NORMAL", "Crypto markets active (24/7)"
        
        # Check market holidays for STOCK markets only
        if enable_holiday_check:
            active_markets = [m.strip().upper() for m in settings.active_markets.split(",")]
            
            for market in active_markets:
                if market == "CRYPTO":
                    continue  # Skip crypto in holiday checks
                
                is_trading_day = self.market_calendar.is_trading_day(market, date.today())
                
                if not is_trading_day:
                    logger.info(
                        "market_holiday_detected",
                        market=market,
                        date=date.today().isoformat(),
                        switching_to_crypto=settings.crypto_enabled
                    )
                    # If crypto is enabled, switch to crypto instead of blocking
                    if settings.crypto_enabled:
                        logger.info("switching_to_crypto_trading", reason=f"{market} market holiday")
                        return True, "NORMAL", f"{market} market closed (holiday), switching to crypto"
                    else:
                        return False, "PAUSED", f"{market} market is closed (holiday)"
        
        # Check economic events
        if enable_economic_check and economic_strategy != "NORMAL":
            has_high_impact = await self.economic_calendar.has_high_impact_event_today()
            
            if has_high_impact:
                upcoming_events = await self.economic_calendar.get_upcoming_events(
                    days_ahead=1, 
                    min_impact=EventImpact.HIGH
                )
                
                if upcoming_events:
                    event = upcoming_events[0]
                    
                    if economic_strategy == "PAUSE":
                        logger.warning(
                            "high_impact_event_pause",
                            event=event["name"],
                            date=event["date"],
                            strategy="PAUSE"
                        )
                        return False, "PAUSED", f"High-impact event today: {event['name']}"
                    
                    elif economic_strategy == "CAUTIOUS":
                        logger.warning(
                            "high_impact_event_cautious",
                            event=event["name"],
                            date=event["date"],
                            strategy="CAUTIOUS"
                        )
                        return True, "CAUTIOUS", f"High-impact event today: {event['name']} (trading cautiously)"
        
        # All clear for normal trading
        return True, "NORMAL", "Normal trading conditions"
    
    def _is_market_hours(self) -> bool:
        """Check if we're currently in market hours for active markets."""
        # If market hours enforcement is disabled, always return True (24/7 trading)
        if not settings.enforce_market_hours:
            logger.debug("market_hours_check_disabled", trading_allowed=True)
            return True
        
        from datetime import datetime, timezone
        import pytz
        
        now_utc = datetime.now(timezone.utc)
        
        # Parse active markets
        active_markets = [m.strip().upper() for m in settings.active_markets.split(",")]
        strategy = settings.market_strategy.upper()
        
        markets_open = []
        
        # Check each active market
        for market in active_markets:
            is_open = False
            
            if market == "US":
                # US Market (EST = UTC-5, EDT = UTC-4)
                # Simplified: using EST always
                est = pytz.timezone('US/Eastern')
                now_est = now_utc.astimezone(est)
                
                is_weekday = now_est.weekday() < 5
                market_start = time(settings.us_market_open_hour, settings.us_market_open_minute)
                market_end = time(settings.us_market_close_hour, settings.us_market_close_minute)
                current_time = now_est.time()
                
                is_open = is_weekday and market_start <= current_time <= market_end
                
                logger.debug(
                    "us_market_check",
                    time_est=now_est.strftime("%H:%M"),
                    is_weekday=is_weekday,
                    is_open=is_open,
                )
            
            elif market == "EUROPE":
                # Europe Market (CET = UTC+1, CEST = UTC+2)
                cet = pytz.timezone('Europe/Paris')
                now_cet = now_utc.astimezone(cet)
                
                is_weekday = now_cet.weekday() < 5
                market_start = time(settings.europe_market_open_hour, settings.europe_market_open_minute)
                market_end = time(settings.europe_market_close_hour, settings.europe_market_close_minute)
                current_time = now_cet.time()
                
                is_open = is_weekday and market_start <= current_time <= market_end
                
                logger.debug(
                    "europe_market_check",
                    time_cet=now_cet.strftime("%H:%M"),
                    is_weekday=is_weekday,
                    is_open=is_open,
                )
            
            elif market == "ASIA":
                # Asia Market (JST = UTC+9)
                jst = pytz.timezone('Asia/Tokyo')
                now_jst = now_utc.astimezone(jst)
                
                is_weekday = now_jst.weekday() < 5
                market_start = time(settings.asia_market_open_hour, settings.asia_market_open_minute)
                market_end = time(settings.asia_market_close_hour, settings.asia_market_close_minute)
                current_time = now_jst.time()
                
                is_open = is_weekday and market_start <= current_time <= market_end
                
                logger.debug(
                    "asia_market_check",
                    time_jst=now_jst.strftime("%H:%M"),
                    is_weekday=is_weekday,
                    is_open=is_open,
                )
            
            if is_open:
                markets_open.append(market)
        
        # Determine if we should trade based on strategy
        if strategy == "ALL":
            # Trade only when ALL active markets are open (overlap)
            should_trade = len(markets_open) == len(active_markets)
        else:  # "ANY"
            # Trade when ANY active market is open
            should_trade = len(markets_open) > 0
        
        logger.info(
            "multi_market_check",
            active_markets=active_markets,
            markets_open=markets_open,
            strategy=strategy,
            trading_allowed=should_trade,
        )
        
        return should_trade
    
    def _get_active_market_type(self) -> str:
        """
        Determine active market type based on stock market hours.
        Returns "STOCK" if stock markets are open, "CRYPTO" if closed.
        Crypto markets trade 24/7.
        """
        # Check for manual override first
        if settings.trading_asset_type_override:
            logger.info("using_manual_market_override", mode=settings.trading_asset_type_override)
            return settings.trading_asset_type_override
            
        # Check if crypto trading is enabled
        if not settings.crypto_enabled:
            return "STOCK"
        
        # Check if any stock market is open
        stock_markets_open = self._is_market_hours()
        
        if stock_markets_open:
            logger.debug("market_type_stock", reason="Stock markets are open")
            return "STOCK"
        else:
            logger.debug("market_type_crypto", reason="Stock markets closed, trading crypto")
            return "CRYPTO"
    
    async def _run_learning_cycle(self):
        """Run automated learning activities: detect closed positions, generate feedback, scan for patterns."""
        try:
            from services.error_tracker import get_error_tracker
            from services.error_pattern_detector import get_error_pattern_detector
            
            error_tracker = get_error_tracker()
            pattern_detector = get_error_pattern_detector()
            
            # Scanfor closed positions and track outcomes
            processed_trades = await error_tracker.scan_closed_positions()
            
            if processed_trades:
                logger.info(
                    "learning_cycle_trades_processed",
                    count=len(processed_trades)
                )
            
            # Periodically scan for error patterns (every 10th cycle or daily)
            # For simplicity, run on every cycle but in production you'd limit this
            for agent in self.agents:
                patterns = await pattern_detector.scan_for_patterns(
                    agent_name=agent.name,
                    lookback_days=30
                )
                
                if patterns:
                    logger.info(
                        "error_patterns_detected",
                        agent=agent.name,
                        pattern_count=len(patterns)
                    )
        
        except Exception as e:
            logger.error("learning_cycle_error", error=str(e))
    
    async def daily_report(self):
        """Generate end-of-day report."""
        logger.info("generating_daily_report")
        
        from database import get_db
        from models.database import Portfolio
        
        with get_db() as db:
            portfolios = db.query(Portfolio).all()
            
            report_data = []
            for portfolio in portfolios:
                report_data.append({
                    "agent": portfolio.agent_name,
                    "total_value": portfolio.total_value,
                    "pnl_percent": portfolio.total_pnl_percent,
                    "trades_today": portfolio.total_trades,  # Simplified
                })
            
            # Broadcast daily report
            if self.ws_manager:
                await self.ws_manager.broadcast({
                    "type": "daily_report",
                    "data": report_data,
                    "timestamp": datetime.utcnow().isoformat(),
                })
            
            logger.info("daily_report_complete", agents=len(report_data))
    
    async def run_position_analysis(self):
        """
        Run position analysis cycle - Position Manager analyzes all open positions.
        This runs every hour independently of the main trading cycle.
        """
        logger.info("position_analysis_start")
        
        try:
            from database import get_db
            from models.database import Portfolio, Trade, TradeStatus
            from tools.trading_tools import TradingTools
            
            with get_db() as db:
                # Get all agents with open positions
                portfolios = db.query(Portfolio).all()
                
                analysis_results = []
                
                for portfolio in portfolios:
                    # Get agent's open positions
                    positions = []
                    for pos in portfolio.positions:
                        # Calculate current P&L for each position
                        current_pnl_percent = pos.get("pnl_percent", 0) if isinstance(pos, dict) else 0
                        
                        positions.append({
                            "symbol": pos.get("symbol") if isinstance(pos, dict) else pos,
                            "quantity": pos.get("quantity", 0) if isinstance(pos, dict) else 0,
                            "avg_price": pos.get("avg_price", 0) if isinstance(pos, dict) else 0,
                            "current_pnl_percent": current_pnl_percent,
                        })
                    
                    # Analyze portfolio health
                    total_positions = len(positions)
                    winning_positions = sum(1 for p in positions if p["current_pnl_percent"] > 0)
                    losing_positions = sum(1 for p in positions if p["current_pnl_percent"] < 0)
                    
                    # Check for positions needing attention (> -10% or > +20%)
                    needs_attention = [
                        p for p in positions 
                        if p["current_pnl_percent"] < -10 or p["current_pnl_percent"] > 20
                    ]
                    
                    analysis = {
                        "agent": portfolio.agent_name,
                        "total_positions": total_positions,
                        "winning": winning_positions,
                        "losing": losing_positions,
                        "portfolio_pnl": portfolio.total_pnl_percent,
                        "needs_attention": needs_attention,
                        "recommendation": self._generate_position_recommendation(
                            portfolio.total_pnl_percent, 
                            winning_positions, 
                            losing_positions,
                            needs_attention
                        ),
                    }
                    
                    analysis_results.append(analysis)
                    
                    logger.info(
                        "position_analysis_agent",
                        agent=portfolio.agent_name,
                        positions=total_positions,
                        winning=winning_positions,
                        losing=losing_positions,
                        attention_needed=len(needs_attention),
                    )
                
                # Broadcast position analysis to WebSocket clients
                if self.ws_manager:
                    await self.ws_manager.broadcast({
                        "type": "position_analysis",
                        "data": analysis_results,
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                
                logger.info("position_analysis_complete", agents=len(analysis_results))
                
        except Exception as e:
            logger.error("position_analysis_error", error=str(e))
    
    def _generate_position_recommendation(self, portfolio_pnl: float, winning: int, losing: int, needs_attention: list) -> str:
        """Generate recommendation based on position analysis."""
        recommendations = []
        
        # Overall portfolio health
        if portfolio_pnl < -5:
            recommendations.append("CAUTION: Portfolio down significantly. Consider reducing exposure.")
        elif portfolio_pnl > 15:
            recommendations.append("Strong performance. Consider taking partial profits.")
        
        # Position balance
        total = winning + losing
        if total > 0:
            win_rate = winning / total
            if win_rate < 0.4:
                recommendations.append(f"Low win rate ({win_rate:.0%}). Review entry strategy.")
        
        # Positions needing attention
        for pos in needs_attention:
            if pos["current_pnl_percent"] < -10:
                recommendations.append(f"{pos['symbol']}: Down {abs(pos['current_pnl_percent']):.1f}%. Review stop-loss.")
            elif pos["current_pnl_percent"] > 20:
                recommendations.append(f"{pos['symbol']}: Up {pos['current_pnl_percent']:.1f}%. Consider profit-taking.")
        
        return " | ".join(recommendations) if recommendations else "All positions healthy. No action needed."


def start_scheduler(ws_manager=None) -> AsyncIOScheduler:
    """Start the trading scheduler."""
    orchestrator = TradingOrchestrator(ws_manager)
    scheduler = AsyncIOScheduler()
    
    # Pre-market warmup (9:25 AM EST = 2:25 PM UTC)
    scheduler.add_job(
        lambda: logger.info("pre_market_warmup"),
        CronTrigger(hour=14, minute=25, timezone="UTC"),
        id="pre_market",
    )
    
    # Trading cycle every N minutes during market hours
    # Run every interval specified in settings
    interval = settings.trading_interval_minutes
    
    # For simplicity, run hourly between 2:30 PM and 9:00 PM UTC (market hours EST)
    # Run 24/7 to support crypto trading
    # The orchestrator will check if stock markets are open and switch to crypto if not
    
    # Handle intervals >= 60 minutes (use hours instead of minutes)
    if interval >= 60:
        hours = interval // 60
        # Use hourly cron expression (e.g., every 4 hours = hour=*/4, minute=0)
        scheduler.add_job(
            orchestrator.run_trading_cycle,
            CronTrigger(minute=0, hour=f"*/{hours}", timezone="UTC"),
            id="trading_cycle",
        )
        logger.info(
            "trading_cycle_scheduled_hourly",
            interval_hours=hours,
        )
    else:
        # Use minute-based interval for < 60 minutes
        scheduler.add_job(
            orchestrator.run_trading_cycle,
            CronTrigger(minute=f"*/{interval}", timezone="UTC"),
            id="trading_cycle",
        )
        logger.info(
            "trading_cycle_scheduled_minutes",
            interval_minutes=interval,
        )
    
    # End of day report (9:00 PM UTC = 4:00 PM EST)
    scheduler.add_job(
        orchestrator.daily_report,
        CronTrigger(hour=21, minute=0, timezone="UTC"),
        id="daily_report",
    )
    
    # Position analysis cycle (runs independently of trading cycle)
    position_interval = getattr(settings, 'position_analysis_interval_minutes', 60)
    
    # Handle intervals >= 60 minutes (use hours instead of minutes)
    if position_interval >= 60:
        hours = position_interval // 60
        # Use hourly cron expression (e.g., every 1 hour = minute=0)
        scheduler.add_job(
            orchestrator.run_position_analysis,
            CronTrigger(minute=0, hour=f"*/{hours}", timezone="UTC"),
            id="position_analysis",
        )
        logger.info(
            "position_analysis_scheduled_hourly",
            interval_hours=hours,
        )
    else:
        # Use minute-based interval for < 60 minutes
        scheduler.add_job(
            orchestrator.run_position_analysis,
            CronTrigger(minute=f"*/{position_interval}", timezone="UTC"),
            id="position_analysis",
        )
        logger.info(
            "position_analysis_scheduled_minutes",
            interval_minutes=position_interval,
        )
    
    scheduler.start()
    
    logger.info(
        "scheduler_started", 
        trading_interval_minutes=interval,
        position_analysis_interval_minutes=position_interval
    )
    
    return scheduler
