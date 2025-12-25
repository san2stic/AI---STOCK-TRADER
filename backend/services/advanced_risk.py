"""
Advanced Risk Management System
Implements Kelly Criterion, Sharpe Ratio optimization, adaptive position sizing,
and volatility-based stop-loss systems.
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import structlog
from database import get_db
from models.database import Trade, TradeStatus, Portfolio
import math
import statistics

logger = structlog.get_logger()


class KellyCriterionCalculator:
    """
    Calcule la fraction optimale du capital à risquer selon le Kelly Criterion.
    Formule: f* = (bp - q) / b
    où b = ratio win/loss moyen, p = probabilité de gain, q = probabilité de perte
    """
    
    def calculate_kelly_fraction(
        self,
        agent_name: str,
        symbol: str = None,
        lookback_days: int = 90
    ) -> Dict[str, Any]:
        """
        Calcule la fraction Kelly optimale.
        
        Returns:
            {
                "kelly_fraction": 0.0-1.0,
                "adjusted_fraction": 0.0-0.5,  # Kelly conservateur (half-Kelly)
                "win_rate": float,
                "avg_win": float,
                "avg_loss": float,
                "recommendation": str
            }
        """
        db = next(get_db())
        
        try:
            # Get historical trades
            cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
            
            query = db.query(Trade).filter(
                Trade.agent_name == agent_name,
                Trade.created_at >= cutoff_date,
                Trade.status.in_([TradeStatus.CLOSED, TradeStatus.FILLED]),
                Trade.pnl != None
            )
            
            if symbol:
                query = query.filter(Trade.symbol == symbol)
            
            trades = query.all()
            
            if len(trades) < 10:
                return {
                    "kelly_fraction": 0.02,  # Default conservative 2%
                    "adjusted_fraction": 0.02,
                    "win_rate": 0.5,
                    "avg_win": 0,
                    "avg_loss": 0,
                    "sample_size": len(trades),
                    "recommendation": "Insufficient data - using conservative 2% default",
                    "status": "insufficient_data"
                }
            
            # Calculate win rate and average P&L
            wins = [t.pnl for t in trades if t.pnl > 0]
            losses = [abs(t.pnl) for t in trades if t.pnl < 0]
            
            if not wins or not losses:
                return {
                    "kelly_fraction": 0.02,
                    "adjusted_fraction": 0.02,
                    "win_rate": len(wins) / len(trades) if trades else 0.5,
                    "avg_win": statistics.mean(wins) if wins else 0,
                    "avg_loss": statistics.mean(losses) if losses else 1,
                    "sample_size": len(trades),
                    "recommendation": "No complete win/loss distribution - using conservative default",
                    "status": "incomplete_distribution"
                }
            
            # Calculate parameters
            win_rate = len(wins) / len(trades)
            loss_rate = 1 - win_rate
            avg_win = statistics.mean(wins)
            avg_loss = statistics.mean(losses)
            
            # Win/Loss ratio (b in Kelly formula)
            b = avg_win / avg_loss if avg_loss > 0 else 1
            
            # Kelly Criterion: f* = (bp - q) / b
            # where p = win_rate, q = loss_rate
            kelly_fraction = (b * win_rate - loss_rate) / b
            
            # Clamp to reasonable bounds [0, 1]
            kelly_fraction = max(0, min(1, kelly_fraction))
            
            # Half-Kelly for conservative approach (reduce risk of ruin)
            adjusted_fraction = kelly_fraction * 0.5
            
            # Further cap at 25% max (never risk more than 25% of portfolio on a single trade)
            adjusted_fraction = min(adjusted_fraction, 0.25)
            
            # Recommendation
            if adjusted_fraction >= 0.15:
                recommendation = f"Strong edge detected ({win_rate:.1%} win rate, {b:.2f}x W/L ratio). Suggested size: {adjusted_fraction:.1%} of portfolio."
            elif adjusted_fraction >= 0.08:
                recommendation = f"Moderate edge. Suggested size: {adjusted_fraction:.1%} of portfolio."
            elif adjusted_fraction >= 0.03:
                recommendation = f"Slight edge. Conservative size: {adjusted_fraction:.1%} of portfolio."
            else:
                recommendation = f"Weak or no edge. Minimal size: {adjusted_fraction:.1%} of portfolio or avoid trading."
            
            return {
                "kelly_fraction": round(kelly_fraction, 4),
                "adjusted_fraction": round(adjusted_fraction, 4),
                "win_rate": round(win_rate, 4),
                "loss_rate": round(loss_rate, 4),
                "avg_win": round(avg_win, 2),
                "avg_loss": round(avg_loss, 2),
                "win_loss_ratio": round(b, 2),
                "sample_size": len(trades),
                "recommendation": recommendation,
                "status": "calculated"
            }
            
        finally:
            db.close()


class DynamicSharpeOptimizer:
    """
    Optimise les positions pour maximiser le Sharpe Ratio.
    Sharpe = (Return - RiskFreeRate) / Volatility
    """
    
    def calculate_sharpe_ratio(
        self,
        agent_name: str,
        lookback_days: int = 30
    ) -> Dict[str, Any]:
        """
        Calcule le Sharpe ratio actuel et recommande des ajustements.
        
        Returns:
            {
                "sharpe_ratio": float,
                "annualized_return": float,
                "annualized_volatility": float,
                "recommendation": str,
                "position_adjustment": "increase" | "maintain" | "decrease"
            }
        """
        db = next(get_db())
        
        try:
            # Get daily P&L over lookback period
            cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
            
            trades = db.query(Trade).filter(
                Trade.agent_name == agent_name,
                Trade.created_at >= cutoff_date,
                Trade.status.in_([TradeStatus.CLOSED, TradeStatus.FILLED]),
                Trade.pnl != None
            ).order_by(Trade.created_at).all()
            
            if len(trades) < 5:
                return {
                    "sharpe_ratio": 0,
                    "annualized_return": 0,
                    "annualized_volatility": 0,
                    "recommendation": "Insufficient trades for Sharpe calculation",
                    "position_adjustment": "maintain",
                    "status": "insufficient_data"
                }
            
            # Calculate daily returns
            pnls = [t.pnl for t in trades]
            
            # Mean return per trade
            mean_pnl = statistics.mean(pnls)
            
            # Volatility (standard deviation)
            volatility = statistics.stdev(pnls) if len(pnls) > 1 else 1
            
            # Sharpe ratio (assuming risk-free rate = 0 for simplicity)
            # In real scenario, subtract risk-free rate from mean return
            if volatility > 0:
                sharpe_ratio = mean_pnl / volatility
            else:
                sharpe_ratio = 0
            
            # Annualize (assuming ~252 trading days per year)
            trades_per_day = len(trades) / lookback_days
            annualized_return = mean_pnl * trades_per_day * 252
            annualized_volatility = volatility * math.sqrt(trades_per_day * 252)
            
            # Recommendation based on Sharpe
            if sharpe_ratio > 2.0:
                recommendation = "Excellent Sharpe ratio (>2.0). Strong risk-adjusted returns. Consider increasing position sizes."
                position_adjustment = "increase"
            elif sharpe_ratio > 1.0:
                recommendation = "Good Sharpe ratio (1.0-2.0). Acceptable risk-adjusted returns. Maintain current approach."
                position_adjustment = "maintain"
            elif sharpe_ratio > 0.5:
                recommendation = "Moderate Sharpe ratio (0.5-1.0). Room for improvement. Consider refining strategy."
                position_adjustment = "maintain"
            else:
                recommendation = "Low Sharpe ratio (<0.5). Poor risk-adjusted returns. Reduce size or reassess strategy."
                position_adjustment = "decrease"
            
            return {
                "sharpe_ratio": round(sharpe_ratio, 2),
                "mean_pnl_per_trade": round(mean_pnl, 2),
                "volatility_per_trade": round(volatility, 2),
                "annualized_return": round(annualized_return, 2),
                "annualized_volatility": round(annualized_volatility, 2),
                "recommendation": recommendation,
                "position_adjustment": position_adjustment,
                "sample_size": len(trades),
                "lookback_days": lookback_days,
                "status": "calculated"
            }
            
        finally:
            db.close()


class AdaptivePositionSizer:
    """
    Dimensionnement adaptatif combinant Kelly, ATR, volatility et Sharpe.
    """
    
    def __init__(self):
        self.kelly_calc = KellyCriterionCalculator()
        self.sharpe_opt = DynamicSharpeOptimizer()
    
    def calculate_optimal_size(
        self,
        agent_name: str,
        symbol: str,
        current_price: float,
        portfolio_value: float,
        atr_percent: float = None,
        market_volatility: str = "NORMAL"
    ) -> Dict[str, Any]:
        """
        Calcule la taille de position optimale en combinant plusieurs facteurs.
        
        Args:
            agent_name: Nom de l'agent
            symbol: Symbol à trader
            current_price: Prix actuel
            portfolio_value: Valeur totale du portfolio
            atr_percent: ATR en % du prix (volatility measure)
            market_volatility: "LOW", "NORMAL", "HIGH", "EXTREME"
        
        Returns:
            {
                "suggested_quantity": int,
                "suggested_investment": float,
                "percent_of_portfolio": float,
                "kelly_component": float,
                "sharpe_adjustment": float,
                "volatility_adjustment": float,
                "reasoning": str
            }
        """
        # 1. Get Kelly fraction
        kelly_result = self.kelly_calc.calculate_kelly_fraction(agent_name, symbol)
        kelly_fraction = kelly_result.get("adjusted_fraction", 0.02)
        
        # 2. Get Sharpe adjustment
        sharpe_result = self.sharpe_opt.calculate_sharpe_ratio(agent_name)
        sharpe_adjustment = 1.0
        
        if sharpe_result["position_adjustment"] == "increase":
            sharpe_adjustment = 1.2  # Increase by 20%
        elif sharpe_result["position_adjustment"] == "decrease":
            sharpe_adjustment = 0.6  # Decrease by 40%
        
        # 3. Volatility adjustment
        volatility_adjustment = 1.0
        
        if market_volatility == "EXTREME":
            volatility_adjustment = 0.4  # Reduce to 40% in extreme volatility
        elif market_volatility == "HIGH":
            volatility_adjustment = 0.7  # Reduce to 70% in high volatility
        elif market_volatility == "LOW":
            volatility_adjustment = 1.2  # Increase to 120% in low volatility
        
        # ATR-based volatility adjustment
        if atr_percent:
            if atr_percent > 5:  # Very high volatility
                volatility_adjustment *= 0.6
            elif atr_percent > 3:
                volatility_adjustment *= 0.8
            elif atr_percent < 1:  # Very low volatility
                volatility_adjustment *= 1.1
        
        # 4. Combine all factors
        final_fraction = kelly_fraction * sharpe_adjustment * volatility_adjustment
        
        # Cap at 20% max (safety limit)
        final_fraction = min(final_fraction, 0.20)
        
        # Calculate investment amount
        suggested_investment = portfolio_value * final_fraction
        
        # Calculate quantity
        if current_price > 0:
            suggested_quantity = int(suggested_investment / current_price)
        else:
            suggested_quantity = 0
        
        # Ensure at least 1 share if investment > 0
        if suggested_investment > current_price and suggested_quantity == 0:
            suggested_quantity = 1
        
        # Reasoning
        reasoning_parts = []
        reasoning_parts.append(f"Kelly Criterion suggests {kelly_fraction:.1%} of portfolio")
        
        if sharpe_adjustment > 1:
            reasoning_parts.append(f"Sharpe ratio is strong (+{(sharpe_adjustment-1)*100:.0f}% boost)")
        elif sharpe_adjustment < 1:
            reasoning_parts.append(f"Sharpe ratio is weak ({(1-sharpe_adjustment)*100:.0f}% reduction)")
        
        if volatility_adjustment < 1:
            reasoning_parts.append(f"Volatility is high ({(1-volatility_adjustment)*100:.0f}% reduction)")
        elif volatility_adjustment > 1:
            reasoning_parts.append(f"Volatility is low (+{(volatility_adjustment-1)*100:.0f}% boost)")
        
        reasoning_parts.append(f"Final allocation: {final_fraction:.1%} of portfolio")
        
        return {
            "suggested_quantity": suggested_quantity,
            "suggested_investment": round(suggested_investment, 2),
            "percent_of_portfolio": round(final_fraction * 100, 2),
            "kelly_component": round(kelly_fraction, 4),
            "sharpe_adjustment": round(sharpe_adjustment, 2),
            "volatility_adjustment": round(volatility_adjustment, 2),
            "final_fraction": round(final_fraction, 4),
            "reasoning": " | ".join(reasoning_parts),
            "kelly_details": kelly_result,
            "sharpe_details": sharpe_result
        }


class VolatilityBasedStopLoss:
    """
    Stop-loss dynamiques basés sur l'ATR.
    """
    
    def calculate_stop_loss(
        self,
        entry_price: float,
        atr: float,
        direction: str = "long",
        atr_multiplier: float = 2.0,
        trailing: bool = True
    ) -> Dict[str, Any]:
        """
        Calcule le stop-loss basé sur ATR.
        
        Args:
            entry_price: Prix d'entrée
            atr: Average True Range
            direction: "long" ou "short"
            atr_multiplier: Multiplicateur ATR (2.0 = stop à 2x ATR)
            trailing: Si True, inclut trailing stop logic
        
        Returns:
            {
                "stop_loss_price": float,
                "stop_distance_percent": float,
                "risk_per_share": float,
                "trailing_stop_enabled": bool,
                "recommendation": str
            }
        """
        if direction.lower() == "long":
            # For long: stop below entry
            stop_loss_price = entry_price - (atr * atr_multiplier)
            risk_per_share = atr * atr_multiplier
        else:
            # For short: stop above entry
            stop_loss_price = entry_price + (atr * atr_multiplier)
            risk_per_share = atr * atr_multiplier
        
        # Calculate stop distance as percentage
        stop_distance_percent = (risk_per_share / entry_price) * 100
        
        # Trailing stop logic
        if trailing:
            # Trailing stop: once price moves favorably by 1 ATR, move stop to breakeven
            # once price moves by 2 ATR, move stop to +1 ATR profit
            breakeven_trigger = entry_price + atr if direction == "long" else entry_price - atr
            profit_trigger = entry_price + (2 * atr) if direction == "long" else entry_price - (2 * atr)
            
            trailing_info = {
                "breakeven_trigger": round(breakeven_trigger, 2),
                "profit_lock_trigger": round(profit_trigger, 2),
                "enabled": True
            }
        else:
            trailing_info = {"enabled": False}
        
        # Recommendation
        if stop_distance_percent > 10:
            recommendation = f"WARNING: Stop distance is {stop_distance_percent:.1f}% - very wide. Consider reducing position size."
        elif stop_distance_percent > 5:
            recommendation = f"Stop distance is {stop_distance_percent:.1f}% - acceptable for volatile assets."
        else:
            recommendation = f"Stop distance is {stop_distance_percent:.1f}% - good risk management."
        
        return {
            "stop_loss_price": round(stop_loss_price, 2),
            "stop_distance_percent": round(stop_distance_percent, 2),
            "risk_per_share": round(risk_per_share, 2),
            "atr": round(atr, 2),
            "atr_multiplier": atr_multiplier,
            "trailing_stop_enabled": trailing,
            "trailing_info": trailing_info,
            "recommendation": recommendation
        }


# Tool functions for integration

def calculate_kelly_position_size(agent_name: str, symbol: str = None) -> Dict[str, Any]:
    """Tool: Calculate optimal position size using Kelly Criterion."""
    calc = KellyCriterionCalculator()
    return calc.calculate_kelly_fraction(agent_name, symbol)


def calculate_sharpe_ratio(agent_name: str, lookback_days: int = 30) -> Dict[str, Any]:
    """Tool: Calculate Sharpe ratio for performance evaluation."""
    optimizer = DynamicSharpeOptimizer()
    return optimizer.calculate_sharpe_ratio(agent_name, lookback_days)


def get_adaptive_position_size(
    agent_name: str,
    symbol: str,
    current_price: float,
    portfolio_value: float,
    atr_percent: float = None,
    market_volatility: str = "NORMAL"
) -> Dict[str, Any]:
    """Tool: Get optimal position size combining Kelly, Sharpe, and volatility."""
    sizer = AdaptivePositionSizer()
    return sizer.calculate_optimal_size(
        agent_name, symbol, current_price, portfolio_value, atr_percent, market_volatility
    )


def calculate_dynamic_stop_loss(
    entry_price: float,
    atr: float,
    direction: str = "long",
    atr_multiplier: float = 2.0
) -> Dict[str, Any]:
    """Tool: Calculate volatility-based stop-loss."""
    calculator = VolatilityBasedStopLoss()
    return calculator.calculate_stop_loss(entry_price, atr, direction, atr_multiplier, trailing=True)
