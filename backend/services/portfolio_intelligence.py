"""
Portfolio Intelligence Service.
Provides advanced portfolio analytics including risk analysis, sector exposure,
and optimization suggestions. All calculations use local data.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import structlog
import math
from database import get_db
from models.database import Trade, Portfolio, TradeAction

logger = structlog.get_logger()


class PortfolioIntelligence:
    """Advanced portfolio analysis and optimization."""
    
    def __init__(self, agent_name: str = None):
        """Initialize with optional agent name."""
        self.agent_name = agent_name
    
    async def analyze_portfolio_risk(self, agent_name: str = None) -> Dict[str, Any]:
        """
        Comprehensive portfolio risk analysis.
        
        Returns:
            VaR estimate, concentration analysis, risk score
        """
        try:
            target_agent = agent_name or self.agent_name
            if not target_agent:
                return {"error": "Agent name required"}
            
            with get_db() as db:
                portfolio = db.query(Portfolio).filter(
                    Portfolio.agent_name == target_agent
                ).first()
                
                if not portfolio:
                    return {"error": "Portfolio not found"}
                
                positions = portfolio.positions or {}
                
                if not positions:
                    return {
                        "agent_name": target_agent,
                        "risk_score": 0,
                        "var_estimate": 0,
                        "concentration": {},
                        "interpretation": "No positions - no risk exposure"
                    }
                
                total_value = portfolio.total_value or 0
                cash_percent = (portfolio.cash / total_value * 100) if total_value > 0 else 100
                
                # Concentration analysis
                position_weights = {}
                max_concentration = 0
                
                for symbol, pos in positions.items():
                    value = pos.get("current_value", 0)
                    weight = (value / total_value * 100) if total_value > 0 else 0
                    position_weights[symbol] = round(weight, 2)
                    max_concentration = max(max_concentration, weight)
                
                # Calculate Herfindahl-Hirschman Index (HHI) for concentration
                hhi = sum(w ** 2 for w in position_weights.values()) / 100
                
                # Estimate daily VaR (simplified - 2% average volatility assumption)
                daily_volatility = 0.02
                var_95 = total_value * daily_volatility * 1.645  # 95% confidence
                var_99 = total_value * daily_volatility * 2.326  # 99% confidence
                
                # Risk score (0-100)
                concentration_risk = min(50, max_concentration / 2)  # Max 50 from concentration
                position_count_risk = max(0, 25 - len(positions) * 2.5)  # Diversification benefit
                cash_risk = max(0, 25 - cash_percent / 4)  # Cash buffer benefit
                
                risk_score = concentration_risk + position_count_risk + cash_risk
                risk_score = min(100, max(0, risk_score))
                
                # Risk level
                if risk_score < 25:
                    risk_level = "LOW"
                elif risk_score < 50:
                    risk_level = "MODERATE"
                elif risk_score < 75:
                    risk_level = "HIGH"
                else:
                    risk_level = "EXTREME"
                
                # Recommendations
                recommendations = []
                if max_concentration > 25:
                    recommendations.append(f"Reduce concentration in top holding (currently {max_concentration:.1f}%)")
                if len(positions) < 5:
                    recommendations.append("Consider diversifying across more positions")
                if cash_percent < 10:
                    recommendations.append("Consider maintaining higher cash buffer")
                
                return {
                    "agent_name": target_agent,
                    "risk_score": round(risk_score, 1),
                    "risk_level": risk_level,
                    "total_value": round(total_value, 2),
                    "cash_percent": round(cash_percent, 1),
                    "positions_count": len(positions),
                    "var_95_daily": round(var_95, 2),
                    "var_99_daily": round(var_99, 2),
                    "max_concentration_percent": round(max_concentration, 1),
                    "hhi_score": round(hhi, 2),
                    "position_weights": position_weights,
                    "recommendations": recommendations,
                    "interpretation": f"{risk_level} risk ({risk_score:.0f}/100) with {len(positions)} positions"
                }
                
        except Exception as e:
            logger.error("analyze_portfolio_risk_error", error=str(e))
            return {"error": str(e)}
    
    async def get_sector_exposure(self, agent_name: str = None) -> Dict[str, Any]:
        """
        Analyze portfolio sector exposure.
        
        Returns:
            Sector breakdown and rebalancing suggestions
        """
        try:
            target_agent = agent_name or self.agent_name
            if not target_agent:
                return {"error": "Agent name required"}
            
            # Sector mapping for common symbols
            sector_map = {
                "AAPL": "Technology", "MSFT": "Technology", "GOOGL": "Technology",
                "AMZN": "Consumer Discretionary", "NVDA": "Technology", "META": "Technology",
                "TSLA": "Consumer Discretionary", "JPM": "Financials", "BAC": "Financials",
                "JNJ": "Healthcare", "UNH": "Healthcare", "PFE": "Healthcare",
                "XOM": "Energy", "CVX": "Energy", "VZ": "Communication",
                "KO": "Consumer Staples", "PG": "Consumer Staples",
                "BTCUSDT": "Crypto", "ETHUSDT": "Crypto", "SOLUSDT": "Crypto",
                "BNBUSDT": "Crypto", "ADAUSDT": "Crypto",
            }
            
            with get_db() as db:
                portfolio = db.query(Portfolio).filter(
                    Portfolio.agent_name == target_agent
                ).first()
                
                if not portfolio:
                    return {"error": "Portfolio not found"}
                
                positions = portfolio.positions or {}
                total_value = portfolio.total_value or 0
                
                # Aggregate by sector
                sector_exposure = {}
                unknown_symbols = []
                
                for symbol, pos in positions.items():
                    value = pos.get("current_value", 0)
                    sector = sector_map.get(symbol.upper(), "Unknown")
                    
                    if sector == "Unknown":
                        unknown_symbols.append(symbol)
                    
                    if sector not in sector_exposure:
                        sector_exposure[sector] = {"value": 0, "symbols": []}
                    
                    sector_exposure[sector]["value"] += value
                    sector_exposure[sector]["symbols"].append(symbol)
                
                # Calculate percentages
                for sector, data in sector_exposure.items():
                    data["percent"] = round(data["value"] / total_value * 100, 1) if total_value > 0 else 0
                    data["value"] = round(data["value"], 2)
                
                # Find over/under exposure
                target_weights = {"Technology": 30, "Financials": 15, "Healthcare": 15, 
                                 "Consumer Discretionary": 15, "Crypto": 10}
                
                rebalance_suggestions = []
                for sector, target in target_weights.items():
                    current = sector_exposure.get(sector, {}).get("percent", 0)
                    diff = current - target
                    if abs(diff) > 10:
                        action = "Reduce" if diff > 0 else "Increase"
                        rebalance_suggestions.append(f"{action} {sector} exposure by ~{abs(diff):.0f}%")
                
                return {
                    "agent_name": target_agent,
                    "total_value": round(total_value, 2),
                    "sector_breakdown": sector_exposure,
                    "dominant_sector": max(sector_exposure.items(), key=lambda x: x[1]["value"])[0] if sector_exposure else None,
                    "unknown_symbols": unknown_symbols,
                    "rebalance_suggestions": rebalance_suggestions,
                    "interpretation": f"Portfolio across {len(sector_exposure)} sectors"
                }
                
        except Exception as e:
            logger.error("get_sector_exposure_error", error=str(e))
            return {"error": str(e)}
    
    async def calculate_portfolio_beta(self, agent_name: str = None) -> Dict[str, Any]:
        """
        Calculate portfolio beta relative to market (SPY).
        
        Returns:
            Portfolio beta and volatility comparison
        """
        try:
            from services.data_collector import get_data_collector
            
            target_agent = agent_name or self.agent_name
            if not target_agent:
                return {"error": "Agent name required"}
            
            collector = get_data_collector()
            
            with get_db() as db:
                portfolio = db.query(Portfolio).filter(
                    Portfolio.agent_name == target_agent
                ).first()
                
                if not portfolio:
                    return {"error": "Portfolio not found"}
                
                positions = portfolio.positions or {}
                
                if not positions:
                    return {
                        "agent_name": target_agent,
                        "portfolio_beta": 0,
                        "interpretation": "No positions - beta is 0 (cash only)"
                    }
                
                # Simplified beta estimates for common symbols
                beta_estimates = {
                    "AAPL": 1.2, "MSFT": 1.1, "GOOGL": 1.15, "AMZN": 1.3,
                    "NVDA": 1.8, "META": 1.4, "TSLA": 2.0, "JPM": 1.1,
                    "BAC": 1.3, "JNJ": 0.7, "UNH": 0.9, "PFE": 0.7,
                    "XOM": 1.0, "KO": 0.6, "VZ": 0.5,
                    "BTCUSDT": 2.5, "ETHUSDT": 2.8, "SOLUSDT": 3.0,
                    "SPY": 1.0, "QQQ": 1.2,
                }
                
                total_value = portfolio.total_value or 0
                weighted_beta = 0
                unknown_positions = []
                
                for symbol, pos in positions.items():
                    value = pos.get("current_value", 0)
                    weight = value / total_value if total_value > 0 else 0
                    beta = beta_estimates.get(symbol.upper(), 1.0)
                    
                    if symbol.upper() not in beta_estimates:
                        unknown_positions.append(symbol)
                    
                    weighted_beta += weight * beta
                
                # Account for cash (beta = 0)
                cash_weight = portfolio.cash / total_value if total_value > 0 else 0
                weighted_beta = weighted_beta * (1 - cash_weight)
                
                # Interpretation
                if weighted_beta < 0.8:
                    interpretation = "Defensive portfolio - less volatile than market"
                elif weighted_beta < 1.2:
                    interpretation = "Balanced portfolio - similar volatility to market"
                elif weighted_beta < 1.6:
                    interpretation = "Aggressive portfolio - more volatile than market"
                else:
                    interpretation = "High-beta portfolio - significantly more volatile"
                
                return {
                    "agent_name": target_agent,
                    "portfolio_beta": round(weighted_beta, 2),
                    "cash_weight": round(cash_weight * 100, 1),
                    "positions_count": len(positions),
                    "unknown_betas": unknown_positions,
                    "interpretation": interpretation,
                    "market_correlation": "High" if 0.8 <= weighted_beta <= 1.2 else "Moderate"
                }
                
        except Exception as e:
            logger.error("calculate_portfolio_beta_error", error=str(e))
            return {"error": str(e)}
    
    async def optimize_portfolio_allocation(self, agent_name: str = None) -> Dict[str, Any]:
        """
        Suggest portfolio optimization based on risk/return.
        
        Returns:
            Optimization suggestions and rebalancing actions
        """
        try:
            target_agent = agent_name or self.agent_name
            if not target_agent:
                return {"error": "Agent name required"}
            
            # Get current portfolio analysis
            risk_analysis = await self.analyze_portfolio_risk(target_agent)
            sector_analysis = await self.get_sector_exposure(target_agent)
            beta_analysis = await self.calculate_portfolio_beta(target_agent)
            
            if "error" in risk_analysis:
                return risk_analysis
            
            suggestions = []
            actions = []
            
            # Risk-based suggestions
            risk_score = risk_analysis.get("risk_score", 50)
            if risk_score > 60:
                suggestions.append("Portfolio risk is elevated - consider reducing exposure")
                actions.append({"type": "reduce_risk", "priority": "high"})
            
            # Concentration suggestions
            max_conc = risk_analysis.get("max_concentration_percent", 0)
            if max_conc > 30:
                suggestions.append(f"Top position is {max_conc:.0f}% - consider trimming")
                actions.append({"type": "trim_top_holding", "priority": "medium"})
            
            # Cash buffer suggestions
            cash_pct = risk_analysis.get("cash_percent", 0)
            if cash_pct < 5:
                suggestions.append("Very low cash reserves - consider selling partial positions")
                actions.append({"type": "raise_cash", "priority": "high"})
            elif cash_pct > 30:
                suggestions.append("High cash - consider deploying capital")
                actions.append({"type": "deploy_cash", "priority": "medium"})
            
            # Beta suggestions
            beta = beta_analysis.get("portfolio_beta", 1.0)
            if beta > 1.5:
                suggestions.append("High beta - portfolio will amplify market moves")
                actions.append({"type": "reduce_beta", "priority": "low"})
            
            # Sector suggestions
            sector_suggestions = sector_analysis.get("rebalance_suggestions", [])
            suggestions.extend(sector_suggestions)
            
            # Overall optimization score
            optimization_score = 100 - risk_score + (10 if 0.8 <= beta <= 1.2 else 0) + (10 if 10 <= cash_pct <= 25 else 0)
            optimization_score = min(100, max(0, optimization_score))
            
            return {
                "agent_name": target_agent,
                "optimization_score": round(optimization_score, 1),
                "current_risk_score": round(risk_score, 1),
                "current_beta": round(beta, 2),
                "current_cash_percent": round(cash_pct, 1),
                "suggestions": suggestions,
                "recommended_actions": actions,
                "interpretation": f"Optimization score: {optimization_score:.0f}/100 - {'Well optimized' if optimization_score > 70 else 'Needs attention'}"
            }
            
        except Exception as e:
            logger.error("optimize_portfolio_allocation_error", error=str(e))
            return {"error": str(e)}


# Singleton instance
_portfolio_intelligence: Optional[PortfolioIntelligence] = None


def get_portfolio_intelligence(agent_name: str = None) -> PortfolioIntelligence:
    """Get or create portfolio intelligence instance."""
    global _portfolio_intelligence
    if _portfolio_intelligence is None or agent_name:
        _portfolio_intelligence = PortfolioIntelligence(agent_name)
    return _portfolio_intelligence
