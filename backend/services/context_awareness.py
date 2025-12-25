"""
Advanced Context Awareness System
Provides real-time market context, correlation analysis, and portfolio impact assessment
to help agents make contextually-aware decisions.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import structlog
from database import get_db
from models.database import Trade, Portfolio
import statistics

logger = structlog.get_logger()


class MarketContextAnalyzer:
    """
    Analyse le contexte global du marché pour informer les décisions.
    """
    
    def get_comprehensive_context(
        self,
        agent_name: str
    ) -> Dict[str, Any]:
        """
        Retourne un contexte de marché complet et actionnable.
        
        Returns:
            {
                "market_summary": {...},
                "portfolio_context": {...},
                "trading_conditions": {...},
                "recommendations": [...]
            }
        """
        db = next(get_db())
        
        try:
            # Get portfolio
            portfolio = db.query(Portfolio).filter(
                Portfolio.agent_name == agent_name
            ).first()
            
            # Analyze recent trading activity
            recent_trades = db.query(Trade).filter(
                Trade.agent_name == agent_name,
                Trade.created_at >= datetime.utcnow() - timedelta(days=7)
            ).all()
            
            # Build context
            market_summary = self._build_market_summary(recent_trades)
            portfolio_context = self._build_portfolio_context(portfolio)
            trading_conditions = self._assess_trading_conditions(recent_trades, portfolio)
            recommendations = self._generate_contextual_recommendations(
                market_summary, portfolio_context, trading_conditions
            )
            
            return {
                "market_summary": market_summary,
                "portfolio_context": portfolio_context,
                "trading_conditions": trading_conditions,
                "recommendations": recommendations,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        finally:
            db.close()
    
    def _build_market_summary(self, recent_trades: List) -> Dict[str, Any]:
        """Summarize recent market activity."""
        if not recent_trades:
            return {
                "activity_level": "LOW",
                "most_active_symbols": [],
                "trade_count_7d": 0
            }
        
        # Count trades by symbol
        symbol_counts = {}
        for trade in recent_trades:
            symbol_counts[trade.symbol] = symbol_counts.get(trade.symbol, 0) + 1
        
        most_active = sorted(symbol_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # Determine activity level
        trade_count = len(recent_trades)
        if trade_count >= 15:
            activity_level = "HIGH"
        elif trade_count >= 7:
            activity_level = "MODERATE"
        else:
            activity_level = "LOW"
        
        return {
            "activity_level": activity_level,
            "most_active_symbols": [s for s, _ in most_active],
            "trade_count_7d": trade_count,
            "unique_symbols_traded": len(symbol_counts)
        }
    
    def _build_portfolio_context(self, portfolio) -> Dict[str, Any]:
        """Build portfolio context."""
        if not portfolio:
            return {
                "position_count": 0,
                "cash_percent": 100,
                "concentration_risk": "NONE"
            }
        
        positions = portfolio.positions or []
        total_value = portfolio.cash
        
        # Calculate position values
        position_values = []
        for pos in positions:
            pos_value = pos.get("value", 0)
            total_value += pos_value
            position_values.append(pos_value)
        
        # Cash percentage
        cash_percent = (portfolio.cash / total_value * 100) if total_value > 0 else 100
        
        # Concentration risk
        if position_values:
            max_position_percent = (max(position_values) / total_value * 100) if total_value > 0 else 0
            
            if max_position_percent > 40:
                concentration = "HIGH"
            elif max_position_percent > 25:
                concentration = "MODERATE"
            else:
                concentration = "LOW"
        else:
            concentration = "NONE"
        
        return {
            "position_count": len(positions),
            "cash_percent": round(cash_percent, 1),
            "concentration_risk": concentration,
            "total_value": round(total_value, 2),
            "positions_summary": [
                {"symbol": p.get("symbol"), "value": p.get("value")}
                for p in positions[:5]
            ]
        }
    
    def _assess_trading_conditions(self, recent_trades: List, portfolio) -> Dict[str, Any]:
        """Assess current trading conditions."""
        conditions = {
            "recommended_action": "HOLD",
            "risk_level": "MODERATE",
            "reasons": []
        }
        
        # Check recent performance
        if recent_trades:
            recent_pnls = [t.pnl for t in recent_trades if t.pnl is not None]
            if recent_pnls:
                avg_pnl = statistics.mean(recent_pnls)
                
                if avg_pnl > 50:
                    conditions["recommended_action"] = "CONTINUE"
                    conditions["risk_level"] = "LOW"
                    conditions["reasons"].append("Strong recent performance")
                elif avg_pnl < -50:
                    conditions["recommended_action"] = "REDUCE"
                    conditions["risk_level"] = "HIGH"
                    conditions["reasons"].append("Poor recent performance")
        
        # Check portfolio allocation
        if portfolio:
            positions = portfolio.positions or []
            total_value = portfolio.cash + sum(p.get("value", 0) for p in positions)
            cash_percent = (portfolio.cash / total_value * 100) if total_value > 0 else 100
            
            if cash_percent < 20:
                conditions["reasons"].append("Low cash reserves (<20%)")
                conditions["risk_level"] = "HIGH"
            elif cash_percent > 70:
                conditions["reasons"].append("High cash reserves - underutilized capital")
                conditions["recommended_action"] = "SEEK_OPPORTUNITIES"
        
        return conditions
    
    def _generate_contextual_recommendations(
        self,
        market_summary: Dict,
        portfolio_context: Dict,
        trading_conditions: Dict
    ) -> List[str]:
        """Generate actionable recommendations based on context."""
        recommendations = []
        
        # Activity-based recommendations
        if market_summary["activity_level"] == "LOW":
            recommendations.append("📉 Low trading activity - Be selective, wait for quality setups")
        elif market_summary["activity_level"] == "HIGH":
            recommendations.append("📈 High trading activity - Ensure you're not overtrading")
        
        # Portfolio-based recommendations
        if portfolio_context["cash_percent"] < 20:
            recommendations.append("💰 Low cash (<20%) - Consider taking profits or reducing positions")
        elif portfolio_context["cash_percent"] > 80:
            recommendations.append("💵 High cash (>80%) - Look for entry opportunities")
        
        if portfolio_context["concentration_risk"] == "HIGH":
            recommendations.append("⚠️ High concentration risk - Diversify portfolio")
        
        # Conditions-based recommendations
        if trading_conditions["risk_level"] == "HIGH":
            recommendations.append("🔴 High risk environment - Reduce position sizes")
        
        if not recommendations:
            recommendations.append("✅ Conditions normal - Trade according to your strategy")
        
        return recommendations


class PortfolioCorrelationDetector:
    """
    Détecte les corrélations entre positions du portfolio.
    """
    
    def analyze_portfolio_correlation(
        self,
        agent_name: str,
        new_symbol: str = None
    ) -> Dict[str, Any]:
        """
        Analyse les corrélations dans le portfolio.
        Si new_symbol fourni, évalue l'impact d'ajouter ce symbole.
        
        Returns:
            {
                "correlation_risk": "LOW" | "MODERATE" | "HIGH",
                "correlated_positions": [...],
                "diversification_score": 0-100,
                "recommendation": str
            }
        """
        db = next(get_db())
        
        try:
            portfolio = db.query(Portfolio).filter(
                Portfolio.agent_name == agent_name
            ).first()
            
            if not portfolio or not portfolio.positions:
                return {
                    "correlation_risk": "NONE",
                    "correlated_positions": [],
                    "diversification_score": 100,
                    "recommendation": "Empty portfolio - no correlation risk"
                }
            
            # Get current symbols
            current_symbols = [p.get("symbol") for p in portfolio.positions]
            
            # Analyze correlations (simplified - in reality would use price correlation)
            correlated_groups = self._identify_correlation_groups(current_symbols, new_symbol)
            
            # Calculate diversification score
            diversification_score = self._calculate_diversification_score(
                current_symbols, correlated_groups
            )
            
            # Determine risk level
            if diversification_score >= 70:
                risk_level = "LOW"
            elif diversification_score >= 40:
                risk_level = "MODERATE"
            else:
                risk_level = "HIGH"
            
            # Generate recommendation
            if new_symbol:
                recommendation = self._generate_correlation_recommendation(
                    new_symbol, current_symbols, correlated_groups, risk_level
                )
            else:
                recommendation = f"Portfolio diversification: {diversification_score}/100"
            
            return {
                "correlation_risk": risk_level,
                "correlated_positions": correlated_groups,
                "diversification_score": diversification_score,
                "recommendation": recommendation,
                "current_symbols": current_symbols
            }
            
        finally:
            db.close()
    
    def _identify_correlation_groups(
        self,
        symbols: List[str],
        new_symbol: str = None
    ) -> List[Dict[str, Any]]:
        """Identify groups of correlated symbols (simplified)."""
        # Simplified sector-based correlation
        tech_stocks = ["AAPL", "MSFT", "GOOGL", "META", "NVDA", "AMD", "TSLA"]
        crypto = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]
        finance = ["JPM", "BAC", "GS", "WFC", "C"]
        
        groups = []
        
        # Check tech concentration
        tech_in_portfolio = [s for s in symbols if s in tech_stocks]
        if new_symbol and new_symbol in tech_stocks:
            tech_in_portfolio.append(new_symbol)
        
        if len(tech_in_portfolio) >= 2:
            groups.append({
                "sector": "TECH",
                "symbols": tech_in_portfolio,
                "correlation": "HIGH"
            })
        
        # Check crypto concentration
        crypto_in_portfolio = [s for s in symbols if s in crypto]
        if new_symbol and new_symbol in crypto:
            crypto_in_portfolio.append(new_symbol)
        
        if len(crypto_in_portfolio) >= 2:
            groups.append({
                "sector": "CRYPTO",
                "symbols": crypto_in_portfolio,
                "correlation": "HIGH"
            })
        
        # Check finance concentration
        finance_in_portfolio = [s for s in symbols if s in finance]
        if new_symbol and new_symbol in finance:
            finance_in_portfolio.append(new_symbol)
        
        if len(finance_in_portfolio) >= 2:
            groups.append({
                "sector": "FINANCE",
                "symbols": finance_in_portfolio,
                "correlation": "HIGH"
            })
        
        return groups
    
    def _calculate_diversification_score(
        self,
        symbols: List[str],
        correlated_groups: List[Dict]
    ) -> int:
        """Calculate diversification score 0-100."""
        if not symbols:
            return 100
        
        # Base score
        score = 100
        
        # Penalty for correlation
        for group in correlated_groups:
            group_size = len(group["symbols"])
            # Deduct 15 points per correlated pair
            penalty = (group_size - 1) * 15
            score -= penalty
        
        # Bonus for variety
        if len(symbols) >= 5:
            score += 10
        
        return max(0, min(100, score))
    
    def _generate_correlation_recommendation(
        self,
        new_symbol: str,
        current_symbols: List[str],
        correlated_groups: List[Dict],
        risk_level: str
    ) -> str:
        """Generate recommendation about adding new symbol."""
        # Check if new symbol increases correlation
        for group in correlated_groups:
            if new_symbol in group["symbols"]:
                return (
                    f"⚠️ WARNING: {new_symbol} is highly correlated with existing {group['sector']} "
                    f"positions {group['symbols'][:3]}. Adding it increases concentration risk."
                )
        
        if risk_level == "HIGH":
            return f"✅ {new_symbol} adds diversification to concentrated portfolio"
        else:
            return f"✅ {new_symbol} maintains good portfolio diversification"


# Tool functions

def get_market_context(agent_name: str) -> Dict[str, Any]:
    """Tool: Get comprehensive market context."""
    analyzer = MarketContextAnalyzer()
    return analyzer.get_comprehensive_context(agent_name)


def check_portfolio_correlation(agent_name: str, new_symbol: str = None) -> Dict[str, Any]:
    """Tool: Check portfolio correlation and diversification."""
    detector = PortfolioCorrelationDetector()
    return detector.analyze_portfolio_correlation(agent_name, new_symbol)
