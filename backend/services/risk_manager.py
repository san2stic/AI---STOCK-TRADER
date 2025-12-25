"""Risk management and trade validation."""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from config import get_settings, AGENT_CONFIGS
from models.database import Portfolio, Trade, TradeStatus, TradeAction
from database import get_db
import structlog

logger = structlog.get_logger()
settings = get_settings()


class RiskManager:
    """Centralized risk management for all trading operations."""
    
    def validate_trade(
        self,
        agent_name: str,
        symbol: str,
        action: str,
        quantity: float,
        price: float,
        portfolio: Portfolio,
    ) -> Dict[str, Any]:
        """
        Validate if a trade meets risk parameters.
        
        Returns:
            {"allowed": bool, "reason": str}
        """
        # Get agent config
        agent_key = agent_name.replace(" ", "").lower()
        # Extract key from agent name (e.g., "GPT-4 Holder" -> "gpt4")
        for key in AGENT_CONFIGS.keys():
            if key in agent_key:
                agent_key = key
                break
        
        agent_config = AGENT_CONFIGS.get(agent_key, {})
        
        # Calculate trade value
        trade_value = price * quantity
        
        # Check 1: Circuit breaker - daily loss limit
        if self._check_circuit_breaker(agent_name):
            return {
                "allowed": False,
                "reason": f"Circuit breaker active: daily loss exceeds {settings.circuit_breaker_percent}%"
            }
        
        # Check 2: Maximum position size
        max_percent = settings.max_trade_percent / 100
        agent_max = agent_config.get("max_position_size", max_percent)
        
        if action.upper() == "BUY":
            max_value = portfolio.total_value * agent_max
            if trade_value > max_value:
                return {
                    "allowed": False,
                    "reason": f"Trade size ${trade_value:.2f} exceeds max ${max_value:.2f} ({agent_max*100:.1f}% of portfolio)"
                }
        
        # Check 3: Maximum concurrent positions
        if action.upper() == "BUY":
            current_positions = len(portfolio.positions or {})
            if current_positions >= settings.max_positions:
                return {
                    "allowed": False,
                    "reason": f"Maximum positions ({settings.max_positions}) reached"
                }
        
        # Check 4: Minimum cash reserve (for certain agents)
        min_cash = agent_config.get("min_cash_reserve", 0)
        if action.upper() == "BUY" and min_cash > 0:
            cash_after = portfolio.cash - trade_value
            min_required = portfolio.total_value * min_cash
            if cash_after < min_required:
                return {
                    "allowed": False,
                    "reason": f"Trade would violate minimum cash reserve of {min_cash*100:.1f}%"
                }
        
        # Check 5: Agent-specific holding period
        min_holding_days = agent_config.get("min_holding_days", 0)
        if action.upper() == "SELL" and min_holding_days > 0:
            # Check when position was opened
            with get_db() as db:
                last_buy = db.query(Trade).filter(
                    Trade.agent_name == agent_name,
                    Trade.symbol == symbol,
                    Trade.action == "buy",
                    Trade.status == TradeStatus.EXECUTED,
                ).order_by(Trade.executed_at.desc()).first()
                
                if last_buy:
                    days_held = (datetime.utcnow() - last_buy.executed_at).days
                    if days_held < min_holding_days:
                        return {
                            "allowed": False,
                            "reason": f"Minimum holding period is {min_holding_days} days (held {days_held} days)"
                        }
        
        return {"allowed": True, "reason": "Trade validated"}
    
    def _check_circuit_breaker(self, agent_name: str) -> bool:
        """Check if circuit breaker is active for agent."""
        with get_db() as db:
            portfolio = db.query(Portfolio).filter(
                Portfolio.agent_name == agent_name
            ).first()
            
            if not portfolio:
                return False
            
            # Get today's trades
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0)
            trades_today = db.query(Trade).filter(
                Trade.agent_name == agent_name,
                Trade.created_at >= today_start,
                Trade.status == TradeStatus.EXECUTED,
            ).all()
            
            # Calculate daily P&L
            daily_pnl = 0
            for trade in trades_today:
                if trade.action == TradeAction.SELL:
                    # This is simplified - in production would need proper P&L calc
                    daily_pnl += (trade.price - trade.portfolio_value_before) * trade.quantity
            
            loss_percent = (daily_pnl / portfolio.total_value) * 100
            is_active = loss_percent < -settings.circuit_breaker_percent
            
            if is_active:
                logger.warning(
                    "circuit_breaker_active",
                    agent=agent_name,
                    daily_loss_percent=loss_percent,
                )
            
            return is_active
    
    def calculate_max_quantity(
        self,
        agent_name: str,
        symbol: str,
        price: float,
    ) -> Dict[str, Any]:
        """
        Calculate maximum safe quantity for a trade based on portfolio constraints.
        
        This is used for PRE-VALIDATION before crew deliberation to prevent
        proposing impossible trades.
        
        Args:
            agent_name: Name of the agent
            symbol: Trading symbol
            price: Current price per share/unit
            
        Returns:
            {"max_quantity": float, "max_value": float, "portfolio_value": float, "reason": str}
        """
        if price <= 0:
            return {
                "max_quantity": 0,
                "max_value": 0,
                "portfolio_value": 0,
                "reason": "Invalid price (zero or negative)",
            }
        
        with get_db() as db:
            portfolio = db.query(Portfolio).filter(
                Portfolio.agent_name == agent_name
            ).first()
            
            if not portfolio:
                # No portfolio found - use initial capital as fallback
                portfolio_value = settings.initial_capital
                cash = portfolio_value
                logger.warning(
                    "no_portfolio_found_using_default",
                    agent=agent_name,
                    default_capital=portfolio_value,
                )
            else:
                portfolio_value = portfolio.total_value
                cash = portfolio.cash
        
        # Get agent-specific config
        agent_key = agent_name.replace(" ", "").lower()
        for key in AGENT_CONFIGS.keys():
            if key in agent_key:
                agent_key = key
                break
        
        agent_config = AGENT_CONFIGS.get(agent_key, {})
        
        # Calculate max position value based on settings and agent config
        max_percent = settings.max_trade_percent / 100
        agent_max = agent_config.get("max_position_size", max_percent)
        
        # Use the more restrictive of the two
        effective_max_percent = min(max_percent, agent_max)
        
        # For crypto, apply additional multiplier
        if symbol.endswith("USDT") or symbol.endswith("BUSD"):
            crypto_multiplier = agent_config.get("crypto_risk_multiplier", 1.0)
            effective_max_percent *= crypto_multiplier
        
        # Calculate max trade value
        max_trade_value = portfolio_value * effective_max_percent
        
        # Also can't spend more than available cash
        max_trade_value = min(max_trade_value, cash)
        
        # Calculate max quantity (fractional shares supported)
        max_quantity = max_trade_value / price
        
        # Ensure at least 0 (never negative)
        max_quantity = max(0.0, max_quantity)
        
        logger.info(
            "calculated_max_quantity",
            agent=agent_name,
            symbol=symbol,
            price=price,
            portfolio_value=portfolio_value,
            max_percent=effective_max_percent * 100,
            max_trade_value=max_trade_value,
            max_quantity=max_quantity,
        )
        
        return {
            "max_quantity": max_quantity,
            "max_value": max_trade_value,
            "portfolio_value": portfolio_value,
            "reason": f"Max {effective_max_percent*100:.1f}% of ${portfolio_value:.2f} portfolio = ${max_trade_value:.2f}",
        }
    
    def check_stop_loss(self, agent_name: str) -> list[Dict[str, Any]]:
        """
        Check all positions for stop-loss triggers.
        
        Returns:
            List of positions to auto-sell
        """
        positions_to_close = []
        
        with get_db() as db:
            portfolio = db.query(Portfolio).filter(
                Portfolio.agent_name == agent_name
            ).first()
            
            if not portfolio or not portfolio.positions:
                return positions_to_close
            
            # Get agent-specific stop-loss
            agent_key = agent_name.replace(" ", "").lower()
            for key in AGENT_CONFIGS.keys():
                if key in agent_key:
                    agent_key = key
                    break
            
            agent_config = AGENT_CONFIGS.get(agent_key, {})
            stop_loss_pct = agent_config.get(
                "stop_loss_override",
                settings.stop_loss_percent / 100
            )
            
            # Check each position
            from services.data_collector import get_data_collector
            import asyncio
            collector = get_data_collector()
            
            for symbol, position in portfolio.positions.items():
                # Get current price
                price_data = asyncio.run(collector.get_current_price(symbol))
                current_price = price_data.get("price")
                
                if not current_price:
                    continue
                
                # Calculate loss
                loss_pct = (current_price - position["avg_price"]) / position["avg_price"]
                
                if loss_pct <= -stop_loss_pct:
                    positions_to_close.append({
                        "symbol": symbol,
                        "quantity": position["quantity"],
                        "avg_price": position["avg_price"],
                        "current_price": current_price,
                        "loss_percent": loss_pct * 100,
                        "reason": f"Stop-loss triggered at {loss_pct*100:.1f}%",
                    })
                    
                    logger.warning(
                        "stop_loss_triggered",
                        agent=agent_name,
                        symbol=symbol,
                        loss_percent=loss_pct * 100,
                    )
        
        return positions_to_close


# Singleton
_risk_manager: Optional[RiskManager] = None


def get_risk_manager() -> RiskManager:
    """Get risk manager instance."""
    global _risk_manager
    if _risk_manager is None:
        _risk_manager = RiskManager()
    return _risk_manager
