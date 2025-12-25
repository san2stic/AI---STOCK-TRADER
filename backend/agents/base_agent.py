"""
Base agent class for all trading AI agents.
Provides common functionality for decision-making, tool execution, and reflection.
Enhanced with Chain-of-Thought reasoning, contextual memory, and lessons learned.
"""
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import json
import structlog
from config import get_settings, AGENT_CONFIGS
from services.vertex_client import get_vertex_client
from tools.trading_tools import TRADING_TOOLS, TradingTools
from models.database import Decision, AgentReflection, Trade, TradeStatus, Portfolio
from database import get_db

logger = structlog.get_logger()
settings = get_settings()


class BaseAgent(ABC):
    """Abstract base class for trading agents."""
    
    def __init__(self, agent_key: str):
        self.agent_key = agent_key
        self.config = AGENT_CONFIGS[agent_key]
        self.name = self.config["name"]
        self.personality = self.config["personality"]
        self.strategy = self.config["strategy"]
        self.risk_tolerance = self.config["risk_tolerance"]
        
        # Vertex AI - force configured model (Claude 3.5 Sonnet)
        # Dynamic selection is disabled in favor of standardized high-performance model
        self.model = self.config["model"]
        self.model_category = "finance"
        
        self.vertex_client = get_vertex_client()
        self.tools = TradingTools(self.name)
        
        logger.info(
            "agent_initialized",
            name=self.name,
            model=self.model,
            provider="vertex_ai",
            strategy=self.strategy,
        )
    
    @abstractmethod
    def _build_system_prompt(self) -> str:
        """Build the system prompt for this agent. Must be implemented by subclasses."""
        pass
    
    async def make_decision(self, market_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make a trading decision based on current market context.
        
        Args:
            market_context: Current market data, news, etc.
            
        Returns:
            Decision result with actions and reasoning
        """
        logger.info(
            "agent_decision_start",
            agent=self.name,
            symbols=list(market_context.get("prices", {}).keys()),
        )
        
        # Get current portfolio
        portfolio = await self._get_portfolio_state()
        
        # Build prompt with context
        messages = [
            {
                "role": "system",
                "content": self._build_system_prompt(),
            },
            {
                "role": "user",
                "content": self._format_context(market_context, portfolio),
            }
        ]
        
        try:
            # Call AI model with function calling tools
            response = await self.vertex_client.call_agent(
                model=self.model,
                messages=messages,
                tools=TRADING_TOOLS,
                temperature=0.7,
            )
            
            # Parse response
            tool_calls = self.vertex_client.parse_tool_calls(response)
            message_content = self.vertex_client.get_message_content(response)
            
            # Log decision
            decision = await self._log_decision(
                market_context=market_context,
                portfolio_context=portfolio,
                raw_response=message_content,
                tool_calls=tool_calls,
            )
            
            # Execute tool calls
            execution_results = []
            for tool_call in tool_calls:
                result = await self.tools.execute_tool(
                    tool_name=tool_call["name"],
                    args=tool_call["args"],
                )
                execution_results.append({
                    "tool": tool_call["name"],
                    "args": tool_call["args"],
                    "result": result,
                })
            
            # Determine final action
            final_action = self._determine_action(tool_calls)
            
            # Update decision log
            with get_db() as db:
                decision.final_action = final_action
                decision.was_executed = len(execution_results) > 0
                db.commit()
            
            logger.info(
                "agent_decision_complete",
                agent=self.name,
                final_action=final_action,
                tools_used=len(tool_calls),
            )
            
            return {
                "agent": self.name,
                "action": final_action,
                "reasoning": message_content,
                "tool_calls": tool_calls,
                "execution_results": execution_results,
            }
            
        except Exception as e:
            logger.error(
                "agent_decision_error",
                agent=self.name,
                error=str(e),
            )
            
            # Log error
            await self._log_decision(
                market_context=market_context,
                portfolio_context=portfolio,
                raw_response="",
                tool_calls=[],
                execution_error=str(e),
            )
            
            return {
                "agent": self.name,
                "action": "error",
                "error": str(e),
            }
    
    async def reflect(self) -> Dict[str, Any]:
        """
        Agent reflects on recent trades and performance.
        Enhanced with advanced metrics and learned rules generation.
        """
        logger.info("agent_reflection_start", agent=self.name)
        
        # Get last N trades
        with get_db() as db:
            recent_trades = db.query(Trade).filter(
                Trade.agent_name == self.name,
                Trade.status == TradeStatus.EXECUTED,
            ).order_by(Trade.executed_at.desc()).limit(20).all()
            
            portfolio = db.query(Portfolio).filter(
                Portfolio.agent_name == self.name
            ).first()
        
        if not recent_trades:
            return {"status": "no_trades", "message": "Not enough trades to reflect"}
        
        # Calculate advanced performance metrics
        performance_metrics = self._calculate_performance_metrics(recent_trades, portfolio)
        
        # Format trades for analysis with P&L info
        trades_summary = []
        for trade in recent_trades:
            trade_info = {
                "symbol": trade.symbol,
                "action": trade.action.value,
                "quantity": trade.quantity,
                "price": trade.price,
                "executed_at": trade.executed_at.isoformat(),
                "reasoning": trade.reasoning[:200] if trade.reasoning else "N/A",
            }
            # Add P&L if available
            if hasattr(trade, 'realized_pnl') and trade.realized_pnl is not None:
                trade_info["pnl"] = trade.realized_pnl
            trades_summary.append(trade_info)
        
        # Build enhanced reflection prompt
        messages = [
            {
                "role": "system",
                "content": f"""You are {self.name}, a {self.personality} trading agent doing self-reflection.
                
Your goal is to analyze your performance honestly and generate ACTIONABLE RULES for improvement.
Be specific, data-driven, and self-critical.""",
            },
            {
                "role": "user",
                "content": f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 PERFORMANCE ANALYSIS FOR {self.name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 OVERALL METRICS:
- Total P&L: ${portfolio.total_pnl:.2f} ({portfolio.total_pnl_percent:.2f}%)
- Win Rate: {performance_metrics['win_rate']:.1f}%
- Total Trades: {portfolio.total_trades}
- Avg Trade P&L: ${performance_metrics['avg_trade_pnl']:.2f}
- Best Trade: ${performance_metrics['best_trade']:.2f}
- Worst Trade: ${performance_metrics['worst_trade']:.2f}

📉 RISK METRICS:
- Max Drawdown: {performance_metrics['max_drawdown']:.1f}%
- Profit Factor: {performance_metrics['profit_factor']:.2f}
- Risk/Reward Ratio: {performance_metrics['risk_reward']:.2f}

📋 RECENT TRADES (Last 20):
{json.dumps(trades_summary[:10], indent=2)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 REFLECTION REQUIRED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Analyze your performance and answer:

1. **WINNERS ANALYSIS**: 
   - What patterns do your winning trades share?
   - What tools/indicators led to good decisions?

2. **LOSERS ANALYSIS**:
   - What went wrong in losing trades?
   - Were there warning signs you ignored?

3. **BEHAVIORAL PATTERNS**:
   - Are you trading too frequently or not enough?
   - Are you respecting your stop-losses?
   - Are you letting winners run or cutting early?

4. **LEARNED RULES** (Most Important!):
   Generate 3-5 specific, actionable rules based on your analysis.
   Format each as: "RULE: [Specific condition] → [Action to take]"
   
   Example: "RULE: When RSI > 80 AND I already have a position → Take partial profits"

5. **ADJUSTMENT PLAN**:
   What specific changes will you make in your next trading session?

Be brutally honest with yourself. Your future performance depends on this reflection.
""",
            }
        ]
        
        try:
            response = await self.vertex_client.call_agent(
                model=self.model,
                messages=messages,
                temperature=0.8,
            )
            
            reflection_text = self.vertex_client.get_message_content(response)
            
            # Parse reflection sections
            went_well = ""
            went_wrong = ""
            improvements = ""
            learned_rules = []
            
            lines = reflection_text.split("\n")
            current_section = None
            
            for line in lines:
                lower = line.lower()
                
                # Extract learned rules (key enhancement)
                if line.strip().startswith("RULE:"):
                    learned_rules.append(line.strip()[5:].strip())
                
                # Section detection
                if "winner" in lower or "well" in lower or "good" in lower:
                    current_section = "well"
                elif "loser" in lower or "wrong" in lower or "mistake" in lower:
                    current_section = "wrong"
                elif "adjustment" in lower or "change" in lower or "improve" in lower:
                    current_section = "improve"
                elif current_section == "well":
                    went_well += line + "\n"
                elif current_section == "wrong":
                    went_wrong += line + "\n"
                elif current_section == "improve":
                    improvements += line + "\n"
            
            # Save reflection with enhanced data
            with get_db() as db:
                reflection = AgentReflection(
                    agent_name=self.name,
                    trades_analyzed=trades_summary,
                    performance_stats={
                        "total_pnl": portfolio.total_pnl,
                        "pnl_percent": portfolio.total_pnl_percent,
                        "win_rate": performance_metrics['win_rate'],
                        "profit_factor": performance_metrics['profit_factor'],
                        "max_drawdown": performance_metrics['max_drawdown'],
                        "avg_trade_pnl": performance_metrics['avg_trade_pnl'],
                        "total_trades_analyzed": len(recent_trades),
                    },
                    what_went_well=went_well.strip(),
                    what_went_wrong=went_wrong.strip(),
                    improvements_planned=improvements.strip() + "\n\nLEARNED RULES:\n" + "\n".join(learned_rules),
                    raw_reflection=reflection_text,
                )
                db.add(reflection)
                db.commit()
            
            logger.info(
                "agent_reflection_complete", 
                agent=self.name,
                rules_learned=len(learned_rules),
            )
            
            return {
                "status": "complete",
                "reflection": reflection_text,
                "learned_rules": learned_rules,
                "performance_metrics": performance_metrics,
            }
            
        except Exception as e:
            logger.error("agent_reflection_error", agent=self.name, error=str(e))
            return {"status": "error", "error": str(e)}
    
    def _calculate_performance_metrics(
        self, 
        trades: List[Any], 
        portfolio: Any
    ) -> Dict[str, float]:
        """Calculate advanced performance metrics from trade history."""
        if not trades or not portfolio:
            return {
                "win_rate": 0, "avg_trade_pnl": 0, "best_trade": 0, 
                "worst_trade": 0, "max_drawdown": 0, "profit_factor": 1,
                "risk_reward": 1,
            }
        
        win_rate = (portfolio.winning_trades / max(portfolio.total_trades, 1)) * 100
        
        # Extract P&L from trades if available
        pnls = []
        for trade in trades:
            if hasattr(trade, 'realized_pnl') and trade.realized_pnl is not None:
                pnls.append(trade.realized_pnl)
        
        if pnls:
            avg_trade_pnl = sum(pnls) / len(pnls)
            best_trade = max(pnls)
            worst_trade = min(pnls)
            
            # Profit factor = gross profit / gross loss
            gains = sum(p for p in pnls if p > 0)
            losses = abs(sum(p for p in pnls if p < 0))
            profit_factor = gains / losses if losses > 0 else (2.0 if gains > 0 else 1.0)
            
            # Risk/Reward = avg win / avg loss
            wins = [p for p in pnls if p > 0]
            losers = [p for p in pnls if p < 0]
            avg_win = sum(wins) / len(wins) if wins else 0
            avg_loss = abs(sum(losers) / len(losers)) if losers else 1
            risk_reward = avg_win / avg_loss if avg_loss > 0 else 1
        else:
            avg_trade_pnl = portfolio.total_pnl / max(portfolio.total_trades, 1)
            best_trade = 0
            worst_trade = 0
            profit_factor = 1
            risk_reward = 1
        
        # Max drawdown from portfolio
        max_drawdown = getattr(portfolio, 'max_drawdown', 0) or 0
        
        return {
            "win_rate": win_rate,
            "avg_trade_pnl": avg_trade_pnl,
            "best_trade": best_trade,
            "worst_trade": worst_trade,
            "max_drawdown": max_drawdown,
            "profit_factor": profit_factor,
            "risk_reward": risk_reward,
        }
    
    async def _get_portfolio_state(self) -> Dict[str, Any]:
        """Get current portfolio state."""
        result = await self.tools.get_portfolio()
        return result
    
    def _get_recent_decisions(self, limit: int = 3) -> List[Dict[str, Any]]:
        """Get recent decisions made by this agent for contextual memory."""
        try:
            with get_db() as db:
                decisions = db.query(Decision).filter(
                    Decision.agent_name == self.name
                ).order_by(Decision.created_at.desc()).limit(limit).all()
                
                return [{
                    "date": d.created_at.strftime("%Y-%m-%d %H:%M"),
                    "action": d.final_action or "analyze",
                    "reasoning_summary": (d.raw_response[:200] + "...") if d.raw_response and len(d.raw_response) > 200 else d.raw_response,
                } for d in decisions]
        except Exception as e:
            logger.warning("failed_to_get_recent_decisions", error=str(e))
            return []
    
    def _get_lessons_learned(self, limit: int = 3) -> List[Dict[str, Any]]:
        """Get lessons learned from past reflections."""
        try:
            with get_db() as db:
                reflections = db.query(AgentReflection).filter(
                    AgentReflection.agent_name == self.name
                ).order_by(AgentReflection.created_at.desc()).limit(limit).all()
                
                lessons = []
                for r in reflections:
                    lesson = {
                        "date": r.created_at.strftime("%Y-%m-%d"),
                        "key_insight": None,
                    }
                    # Extract key actionable insight
                    if r.improvements_planned:
                        lesson["key_insight"] = r.improvements_planned[:150]
                    elif r.what_went_wrong:
                        lesson["key_insight"] = f"Avoid: {r.what_went_wrong[:100]}"
                    elif r.what_went_well:
                        lesson["key_insight"] = f"Continue: {r.what_went_well[:100]}"
                    
                    if lesson["key_insight"]:
                        lessons.append(lesson)
                
                return lessons
        except Exception as e:
            logger.warning("failed_to_get_lessons_learned", error=str(e))
            return []
    
    def _get_error_patterns(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get active error patterns for this agent."""
        try:
            from models.error_pattern import ErrorPattern
            
            with get_db() as db:
                patterns = db.query(ErrorPattern).filter(
                    ErrorPattern.agent_name == self.name,
                    ErrorPattern.is_resolved == False
                ).order_by(ErrorPattern.severity_score.desc()).limit(limit).all()
                
                return [{
                    "pattern_type": p.pattern_type,
                    "title": p.title,
                    "occurrence_count": p.occurrence_count,
                    "avg_loss_percent": p.avg_loss_percent,
                    "severity": p.severity_score,
                    "suggested_fix": p.suggested_fix,
                    "actionable_rule": p.actionable_rule,
                } for p in patterns]
        except Exception as e:
            logger.warning("failed_to_get_error_patterns", error=str(e))
            return []
    
    def _get_strategy_scores(self, market_condition: str = None) -> List[Dict[str, Any]]:
        """Get strategy performance scores for this agent."""
        try:
            from models.strategy_performance import StrategyPerformance
            
            with get_db() as db:
                query = db.query(StrategyPerformance).filter(
                    StrategyPerformance.agent_name == self.name,
                    StrategyPerformance.total_trades >= 3  # Minimum data
                )
                
                # Filter by market condition if provided
                if market_condition:
                    query = query.filter(
                        StrategyPerformance.market_condition == market_condition
                    )
                
                strategies = query.order_by(
                    StrategyPerformance.win_rate.desc()
                ).limit(10).all()
                
                return [{
                    "strategy": s.strategy_type,
                    "market_condition": s.market_condition,
                    "win_rate": s.win_rate,
                    "total_trades": s.total_trades,
                    "avg_pnl": s.avg_pnl_per_trade,
                    "profit_factor": s.profit_factor,
                    "confidence": s.confidence_score,
                    "recommendation": s.get_recommendation_strength(),
                } for s in strategies]
        except Exception as e:
            logger.warning("failed_to_get_strategy_scores", error=str(e))
            return []
    
    def _format_context(
        self, 
        market_context: Dict[str, Any], 
        portfolio: Dict[str, Any]
    ) -> str:
        """Format market and portfolio context with Asset-Specific Chain-of-Thought structure."""
        
        # Get contextual memory
        recent_decisions = self._get_recent_decisions(3)
        lessons_learned = self._get_lessons_learned(2)
        
        # Get error patterns and strategy performance
        error_patterns = self._get_error_patterns(3)
        strategy_scores = self._get_strategy_scores()
        
        # Format lessons section
        lessons_section = ""
        if lessons_learned:
            lessons_section = "\n🧠 LESSONS FROM YOUR PAST EXPERIENCE:\n"
            for lesson in lessons_learned:
                lessons_section += f"  - [{lesson['date']}] {lesson['key_insight']}\n"
        
        # Format error patterns section
        errors_section = ""
        if error_patterns:
            errors_section = "\n⚠️ KNOWN ERROR PATTERNS (AVOID THESE!):\n"
            for pattern in error_patterns:
                errors_section += f"  - {pattern['title']} (occurred {pattern['occurrence_count']}x, avg loss: {pattern['avg_loss_percent']:.1f}%)\n"
                errors_section += f"    ➜ Fix: {pattern['suggested_fix']}\n"
                if pattern['actionable_rule']:
                    errors_section += f"    ➜ Rule: {pattern['actionable_rule']}\n"
        
        # Format strategy performance section
        strategy_section = ""
        if strategy_scores:
            strategy_section = "\n📊 YOUR STRATEGY PERFORMANCE:\n"
            # Show top 3 best and worst
            best_strategies = [s for s in strategy_scores if s['recommendation'] in ['strong_recommend', 'recommend']][:3]
            worst_strategies = [s for s in strategy_scores if s['recommendation'] == 'avoid'][:3]
            
            if best_strategies:
                strategy_section += "  ✅ What Works for You:\n"
                for s in best_strategies:
                    strategy_section += f"    - {s['strategy']} in {s['market_condition']}: {s['win_rate']:.1f}% win rate\n"
            
            if worst_strategies:
                strategy_section += "  ❌ What Doesn't Work:\n"
                for s in worst_strategies:
                    strategy_section += f"    - {s['strategy']} in {s['market_condition']}: {s['win_rate']:.1f}% win rate (AVOID!)\n"
        
        # Format recent decisions
        memory_section = ""
        if recent_decisions:
            memory_section = "\n📝 YOUR RECENT DECISIONS (for context):\n"
            for dec in recent_decisions:
                memory_section += f"  - [{dec['date']}] Action: {dec['action'].upper()}\n"
        
        # Determine Asset Class Context (Stock vs Crypto)
        # We look at valid symbols in market_context or preferred symbols to guess intent
        is_crypto_focus = any("USDT" in s or "BTC" in s or "ETH" in s for s in market_context.get('prices', {}).keys())
        
        if is_crypto_focus:
            asset_specific_instructions = """
**ASSET CLASS: CRYPTOCURRENCY (High Volatility)** 🚨
- **24/7 Market**: Trends can shift overnight. No "market close" safety.
- **Bitcoin Correlation**: ALWAYS check BTC price action. If BTC dumps, alts dump harder.
- **Extreme Volatility**: +/- 10% is normal. Don't panic, but respect stops.
- **Hype vs Utility**: Distinguish between memecoins (gamble) and infrastructure (investment).
"""
        else:
            asset_specific_instructions = """
**ASSET CLASS: STOCKS (Regulated Market)** 🏛️
- **Market Hours**: Liquidity helps during 9:30-16:00 ET. Pre-market is deceptive.
- **Earnings Season**: Check if earnings are approaching. Volatility spikes.
- **Sector Rotation**: Money flows from Tech -> Defensives -> Cyclicals. Identify the flow.
- **Macro Sensitivity**: Fed rates and economic data drive the bus.
"""

        context = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 AGENT: {self.name}
📈 STRATEGY: {self.strategy} | RISK: {self.risk_tolerance}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{errors_section}{strategy_section}
{lessons_section}{memory_section}
━━━━━━━ CURRENT MARKET DATA ━━━━━━━
{json.dumps(market_context.get('prices', {}), indent=2)}

━━━━━━━ RECENT NEWS ━━━━━━━
{json.dumps(market_context.get('news', [])[:5], indent=2)}

━━━━━━━ YOUR PORTFOLIO ━━━━━━━
💰 Cash: ${portfolio.get('cash', 0):.2f}
📈 Total Value: ${portfolio.get('total_value', 0):.2f}
📊 P&L: ${portfolio.get('total_pnl', 0):.2f} ({portfolio.get('total_pnl_percent', 0):.2f}%)
🎯 Win Rate: {(portfolio.get('winning_trades', 0)/(portfolio.get('total_trades') or 1))*100:.1f}%

📁 Positions:
{json.dumps(portfolio.get('positions', []), indent=2)}

━━━━━━━ YOUR WATCHLIST ━━━━━━━
{json.dumps(self._get_agent_watchlist(), indent=2)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 ADVANCED CHAIN-OF-THOUGHT REASONING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{asset_specific_instructions}

You MUST follow this 7-step structured reasoning process:

╔══════════════════════════════════════════════════╗
║ STEP 1: MARKET REGIME IDENTIFICATION 🔍         ║
╚══════════════════════════════════════════════════╝
QUESTION: What is the current market environment?
- Is it BULLISH, BEARISH, or SIDEWAYS?
- What is the Fear & Greed Index? (Extreme values = caution)
- Are we pre/post a major economic event?

TOOLS: `get_market_regime`, `get_fear_greed_index`, `get_economic_events`

⚠️ This determines your ENTIRE approach. Get it right.

╔══════════════════════════════════════════════════╗
║ STEP 2: NEWS & CATALYST SCAN 📰                 ║
╚══════════════════════════════════════════════════╝
QUESTION: Are there any material news or catalysts?
- Breaking news that could move markets?
- Upcoming earnings for my holdings/watchlist?
- Any macro events (Fed, CPI, NFP) within 48hrs?

TOOLS: `search_news`, `search_web`, `get_earnings_calendar`

⛔ ANTI-HALLUCINATION: If you don't know recent news, USE THE TOOL. Never assume.

╔══════════════════════════════════════════════════╗
║ STEP 3: OPPORTUNITY IDENTIFICATION 🎯           ║
╚══════════════════════════════════════════════════╝
QUESTION: What opportunities align with my strategy?
- Check my WATCHLIST first - am I tracking any setups?
- Scan my preferred universe for interesting moves
- Any extreme moves (dips to buy or pumps to fade)?

TOOLS: `manage_watchlist`, `get_available_stocks`, `get_available_crypto_pairs`

🎯 Focus on YOUR edge, not random opportunities.

╔══════════════════════════════════════════════════╗
║ STEP 4: TECHNICAL VALIDATION 📊                 ║
╚══════════════════════════════════════════════════╝
QUESTION: Do the technicals CONFIRM my thesis?
- What does RSI say? Overbought/Oversold?
- Is there trend confirmation (ADX > 25)?
- Any chart patterns (double bottom, breakout)?
- Multi-timeframe alignment?

TOOLS: `get_technical_indicators`, `get_advanced_indicators`, `detect_chart_patterns`, `get_conviction_score`

✅ If technicals conflict with thesis → ABORT or REDUCE SIZE.

╔══════════════════════════════════════════════════╗
║ STEP 5: RISK QUANTIFICATION ⚠️                  ║
╚══════════════════════════════════════════════════╝
QUESTION: What is the EXACT risk of this trade?
- What is my STOP-LOSS level? (Calculate BEFORE entry)
- How much of portfolio am I risking? (Max 2% per trade)
- What is the correlation with existing holdings?
- What is my Risk:Reward ratio? (Must be ≥ 2:1)

TOOLS: `get_optimal_position_size`, `get_correlation_check`, `get_portfolio`

📐 FORMULA: Position Size = (Portfolio × Risk%) / Stop Distance

╔══════════════════════════════════════════════════╗
║ STEP 6: EMOTIONAL CHECK 🧘                      ║
╚══════════════════════════════════════════════════╝
QUESTION: Am I thinking RATIONALLY?
- Am I experiencing FOMO? (Stock up big = dangerous)
- Am I experiencing FEAR? (Selling because scared, not data)
- Am I revenge trading? (Trying to recover losses)
- Would I take this trade with fresh eyes tomorrow?

CHECKLIST:
□ I am NOT chasing a move that already happened
□ I am NOT panic selling due to a red day
□ I am NOT trying to "get back" at the market
□ I would recommend this trade to a colleague

⛔ If ANY answer is NO → DO NOT TRADE. Step away.

╔══════════════════════════════════════════════════╗
║ STEP 7: DECISION & EXECUTION ✅                 ║
╚══════════════════════════════════════════════════╝
After completing steps 1-6, make your decision:

FORMAT YOUR DECISION AS:
```
DECISION: [BUY/SELL/HOLD]
SYMBOL: [TICKER]
QUANTITY: [AMOUNT] (calculated with risk formula)
STOP-LOSS: [PRICE/LEVEL]
TARGET: [PRICE/LEVEL]
RISK:REWARD: [X:Y]
REASONING: [2-3 sentences explaining WHY]
CONFIDENCE: [LOW/MEDIUM/HIGH] with justification
```

If HOLD: Explain what would need to change for you to act.

TOOLS: `buy_stock`, `sell_stock`, `buy_crypto`, `sell_crypto`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎓 META-COGNITION (Quality Check Your Thinking)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Before finalizing, ask yourself:
- Did I skip any steps? (If yes, go back)
- Am I relying on data from tools or assumptions?
- Have I considered what could go WRONG?
- Is my confidence calibrated to my actual edge?
- Would past-me (from reflections above) approve?

QUALITY SCORE YOUR ANALYSIS:
- Used 5+ relevant tools = HIGH quality
- Used 3-4 tools = MEDIUM quality
- Used 0-2 tools = LOW quality → Reconsider trading

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ CRITICAL REMINDERS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- **Personality**: {self.personality}
- Apply lessons from your PAST EXPERIENCE (see errors section above)
- If stock is UP >20% today → 90% chance you're late. WAIT.
- If you're unsure → HOLD is always an option. Cash is a position.
- NEVER guess prices or news. ALWAYS verify with tools.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Now, begin your structured Chain-of-Thought analysis:
"""
        return context
    
    def _get_agent_watchlist(self) -> List[Dict[str, Any]]:
        """Get agent's current watchlist."""
        try:
            with get_db() as db:
                from models.database import Watchlist
                items = db.query(Watchlist).filter(
                    Watchlist.agent_name == self.name
                ).all()
                return [{"symbol": i.symbol, "reason": i.reason} for i in items]
        except Exception as e:
            logger.warning("failed_to_get_watchlist", error=str(e))
            return []
    
    def _determine_action(self, tool_calls: List[Dict]) -> str:
        """Determine the final action from tool calls."""
        if not tool_calls:
            return "hold"
        
        for call in tool_calls:
            if call["name"] == "buy_stock":
                return "buy"
            elif call["name"] == "sell_stock":
                return "sell"
        
        return "analyze"  # Used tools but didn't trade
    
    async def _log_decision(
        self,
        market_context: Dict[str, Any],
        portfolio_context: Dict[str, Any],
        raw_response: str,
        tool_calls: List[Dict],
        execution_error: Optional[str] = None,
    ) -> Decision:
        """Log agent decision to database."""
        with get_db() as db:
            decision = Decision(
                agent_name=self.name,
                market_context=market_context,
                portfolio_context=portfolio_context,
                raw_response=raw_response,
                tool_calls=tool_calls,
                execution_error=execution_error,
            )
            db.add(decision)
            db.commit()
            db.refresh(decision)
            return decision
