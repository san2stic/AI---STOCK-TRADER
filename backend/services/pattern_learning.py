"""
Pattern Learning System
Analyzes trade history to automatically extract winning patterns, 
identify losing setups, and generate actionable trading rules.
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import structlog
from database import get_db
from models.database import Trade, TradeStatus
from collections import defaultdict
import statistics

logger = structlog.get_logger()


class TradeClusterAnalyzer:
    """
    Groupe les trades par similitudes pour identifier les patterns récurrents.
    """
    
    def analyze_trade_clusters(
        self,
        agent_name: str,
        lookback_days: int = 90,
        min_cluster_size: int = 3
    ) -> Dict[str, Any]:
        """
        Analyse les clusters de trades similaires.
        
        Returns:
            {
                "winning_clusters": [...],
                "losing_clusters": [...],
                "insights": [...]
            }
        """
        db = next(get_db())
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
            
            trades = db.query(Trade).filter(
                Trade.agent_name == agent_name,
                Trade.created_at >= cutoff_date,
                Trade.status.in_([TradeStatus.CLOSED, TradeStatus.FILLED]),
                Trade.pnl != None
            ).all()
            
            if len(trades) < min_cluster_size:
                return {
                    "winning_clusters": [],
                    "losing_clusters": [],
                    "insights": ["Insufficient trades for cluster analysis"],
                    "total_trades": len(trades)
                }
            
            # Group trades by characteristics
            clusters = self._create_clusters(trades)
            
            # Identify winning vs losing clusters
            winning_clusters = []
            losing_clusters = []
            
            for cluster_key, cluster_trades in clusters.items():
                if len(cluster_trades) < min_cluster_size:
                    continue
                
                win_rate = sum(1 for t in cluster_trades if t.pnl > 0) / len(cluster_trades)
                avg_pnl = statistics.mean([t.pnl for t in cluster_trades])
                
                cluster_info = {
                    "pattern": cluster_key,
                    "trade_count": len(cluster_trades),
                    "win_rate": round(win_rate, 3),
                    "avg_pnl": round(avg_pnl, 2),
                    "total_pnl": round(sum(t.pnl for t in cluster_trades), 2),
                    "symbols": list(set(t.symbol for t in cluster_trades)),
                }
                
                if win_rate >= 0.60 and avg_pnl > 0:
                    winning_clusters.append(cluster_info)
                elif win_rate <= 0.40 or avg_pnl < 0:
                    losing_clusters.append(cluster_info)
            
            # Sort by performance
            winning_clusters.sort(key=lambda x: x["avg_pnl"], reverse=True)
            losing_clusters.sort(key=lambda x: x["avg_pnl"])
            
            # Generate insights
            insights = self._generate_cluster_insights(winning_clusters, losing_clusters)
            
            return {
                "winning_clusters": winning_clusters[:5],  # Top 5
                "losing_clusters": losing_clusters[:5],    # Worst 5
                "insights": insights,
                "total_trades": len(trades),
                "total_clusters": len(clusters)
            }
            
        finally:
            db.close()
    
    def _create_clusters(self, trades: List[Trade]) -> Dict[str, List[Trade]]:
        """Group trades by similar characteristics."""
        clusters = defaultdict(list)
        
        for trade in trades:
            # Create cluster key based on trade characteristics
            # Using reasoning keywords if available
            cluster_key = self._extract_cluster_key(trade)
            clusters[cluster_key].append(trade)
        
        return clusters
    
    def _extract_cluster_key(self, trade: Trade) -> str:
        """Extract pattern key from trade."""
        key_parts = []
        
        # Action type
        key_parts.append(trade.action.value.upper())
        
        # Try to extract pattern from reasoning
        reasoning = (trade.reasoning or "").lower()
        
        if "oversold" in reasoning or "rsi" in reasoning and "low" in reasoning:
            key_parts.append("OVERSOLD_BOUNCE")
        elif "overbought" in reasoning or "rsi" in reasoning and "high" in reasoning:
            key_parts.append("OVERBOUGHT_FADE")
        elif "breakout" in reasoning:
            key_parts.append("BREAKOUT")
        elif "reversal" in reasoning or "bottom" in reasoning:
            key_parts.append("REVERSAL")
        elif "trend" in reasoning or "momentum" in reasoning:
            key_parts.append("TREND_FOLLOW")
        elif "support" in reasoning:
            key_parts.append("SUPPORT_BOUNCE")
        elif "resistance" in reasoning:
            key_parts.append("RESISTANCE_BREAK")
        else:
            key_parts.append("OTHER")
        
        return "_".join(key_parts)
    
    def _generate_cluster_insights(
        self,
        winning_clusters: List[Dict],
        losing_clusters: List[Dict]
    ) -> List[str]:
        """Generate actionable insights from cluster analysis."""
        insights = []
        
        if winning_clusters:
            best = winning_clusters[0]
            insights.append(
                f"✅ Best setup: {best['pattern']} - {best['win_rate']:.0%} win rate, "
                f"avg P&L ${best['avg_pnl']:.2f} over {best['trade_count']} trades"
            )
        
        if losing_clusters:
            worst = losing_clusters[0]
            insights.append(
                f"❌ Worst setup: {worst['pattern']} - {worst['win_rate']:.0%} win rate, "
                f"avg P&L ${worst['avg_pnl']:.2f} - AVOID THIS"
            )
        
        # Compare winning vs losing
        if winning_clusters and losing_clusters:
            winning_patterns = set(c['pattern'] for c in winning_clusters)
            losing_patterns = set(c['pattern'] for c in losing_clusters)
            
            insights.append(
                f"Focus on: {', '.join(list(winning_patterns)[:3])} | "
                f"Avoid: {', '.join(list(losing_patterns)[:3])}"
            )
        
        return insights


class SuccessPatternExtractor:
    """
    Extrait automatiquement les caractéristiques communes des trades gagnants.
    """
    
    def extract_golden_rules(
        self,
        agent_name: str,
        min_trades: int = 15,
        min_win_rate: float = 0.65
    ) -> Dict[str, Any]:
        """
        Extrait les "golden rules" des trades gagnants.
        
        Returns:
            {
                "golden_rules": [...],
                "winning_conditions": {...},
                "recommendations": [...]
            }
        """
        db = next(get_db())
        
        try:
            # Get recent winning trades
            cutoff_date = datetime.utcnow() - timedelta(days=90)
            
            winning_trades = db.query(Trade).filter(
                Trade.agent_name == agent_name,
                Trade.created_at >= cutoff_date,
                Trade.status.in_([TradeStatus.CLOSED, TradeStatus.FILLED]),
                Trade.pnl != None,
                Trade.pnl > 0
            ).all()
            
            if len(winning_trades) < min_trades:
                return {
                    "golden_rules": [],
                    "winning_conditions": {},
                    "recommendations": [f"Need {min_trades - len(winning_trades)} more winning trades for pattern extraction"],
                    "status": "insufficient_data"
                }
            
            # Analyze common characteristics
            common_patterns = self._find_common_patterns(winning_trades)
            
            # Generate golden rules
            golden_rules = self._generate_golden_rules(common_patterns, winning_trades)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(common_patterns)
            
            return {
                "golden_rules": golden_rules,
                "winning_conditions": common_patterns,
                "recommendations": recommendations,
                "sample_size": len(winning_trades),
                "status": "extracted"
            }
            
        finally:
            db.close()
    
    def _find_common_patterns(self, trades: List[Trade]) -> Dict[str, Any]:
        """Find common characteristics in winning trades."""
        patterns = {
            "preferred_symbols": defaultdict(int),
            "preferred_actions": defaultdict(int),
            "common_keywords": defaultdict(int),
            "avg_pnl": statistics.mean([t.pnl for t in trades]),
            "median_pnl": statistics.median([t.pnl for t in trades]),
        }
        
        for trade in trades:
            patterns["preferred_symbols"][trade.symbol] += 1
            patterns["preferred_actions"][trade.action.value] += 1
            
            # Extract keywords from reasoning
            if trade.reasoning:
                keywords = self._extract_keywords(trade.reasoning)
                for keyword in keywords:
                    patterns["common_keywords"][keyword] += 1
        
        # Convert to sorted lists
        patterns["preferred_symbols"] = sorted(
            patterns["preferred_symbols"].items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        patterns["common_keywords"] = sorted(
            patterns["common_keywords"].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return patterns
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract trading-related keywords from text."""
        keywords = []
        text_lower = text.lower()
        
        # Technical indicators
        if "rsi" in text_lower:
            keywords.append("RSI")
        if "macd" in text_lower:
            keywords.append("MACD")
        if "bollinger" in text_lower:
            keywords.append("Bollinger")
        if "sma" in text_lower or "moving average" in text_lower:
            keywords.append("SMA")
        
        # Patterns
        if "oversold" in text_lower:
            keywords.append("Oversold")
        if "overbought" in text_lower:
            keywords.append("Overbought")
        if "breakout" in text_lower:
            keywords.append("Breakout")
        if "reversal" in text_lower:
            keywords.append("Reversal")
        if "support" in text_lower:
            keywords.append("Support")
        if "resistance" in text_lower:
            keywords.append("Resistance")
        
        # Sentiment
        if "bullish" in text_lower:
            keywords.append("Bullish")
        if "bearish" in text_lower:
            keywords.append("Bearish")
        
        return keywords
    
    def _generate_golden_rules(
        self,
        patterns: Dict[str, Any],
        trades: List[Trade]
    ) -> List[str]:
        """Generate actionable golden rules."""
        rules = []
        
        # Symbol-based rules
        if patterns["preferred_symbols"]:
            top_symbol, count = patterns["preferred_symbols"][0]
            if count >= 5:
                rules.append(
                    f"RULE: {top_symbol} is your best performer ({count} winning trades). "
                    f"Prioritize {top_symbol} opportunities."
                )
        
        # Keyword-based rules
        if patterns["common_keywords"]:
            top_keywords = [kw for kw, _ in patterns["common_keywords"][:3]]
            if len(top_keywords) >= 2:
                rules.append(
                    f"RULE: Your winning trades often involve {', '.join(top_keywords)}. "
                    f"Look for setups with these characteristics."
                )
        
        # Performance-based rule
        avg_pnl = patterns["avg_pnl"]
        if avg_pnl > 0:
            rules.append(
                f"RULE: Your winning trades avg ${avg_pnl:.2f}. "
                f"Don't exit too early - let winners run."
            )
        
        return rules
    
    def _generate_recommendations(self, patterns: Dict[str, Any]) -> List[str]:
        """Generate trading recommendations."""
        recommendations = []
        
        if patterns["common_keywords"]:
            top_kw = patterns["common_keywords"][0][0]
            recommendations.append(
                f"Continue using {top_kw}-based strategies - they're working for you"
            )
        
        if patterns["preferred_symbols"]:
            recommendations.append(
                f"Your top symbols: {', '.join([s for s, _ in patterns['preferred_symbols'][:3]])}"
            )
        
        return recommendations


class AdaptiveStrategyAdjuster:
    """
    Ajuste automatiquement les paramètres de trading en fonction des performances.
    """
    
    def suggest_parameter_adjustments(
        self,
        agent_name: str,
        lookback_days: int = 30
    ) -> Dict[str, Any]:
        """
        Suggère des ajustements de paramètres basés sur les performances.
        
        Returns:
            {
                "adjustments": [...],
                "current_performance": {...},
                "recommendations": [...]
            }
        """
        db = next(get_db())
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
            
            trades = db.query(Trade).filter(
                Trade.agent_name == agent_name,
                Trade.created_at >= cutoff_date,
                Trade.status.in_([TradeStatus.CLOSED, TradeStatus.FILLED]),
                Trade.pnl != None
            ).all()
            
            if len(trades) < 10:
                return {
                    "adjustments": [],
                    "current_performance": {},
                    "recommendations": ["Need more trades for adjustment suggestions"],
                    "status": "insufficient_data"
                }
            
            # Analyze current performance
            performance = self._analyze_performance(trades)
            
            # Generate adjustment suggestions
            adjustments = self._generate_adjustments(performance, trades)
            
            # Generate recommendations
            recommendations = self._generate_adjustment_recommendations(performance, adjustments)
            
            return {
                "adjustments": adjustments,
                "current_performance": performance,
                "recommendations": recommendations,
                "status": "analyzed"
            }
            
        finally:
            db.close()
    
    def _analyze_performance(self, trades: List[Trade]) -> Dict[str, Any]:
        """Analyze current trading performance."""
        wins = [t for t in trades if t.pnl > 0]
        losses = [t for t in trades if t.pnl < 0]
        
        return {
            "win_rate": len(wins) / len(trades) if trades else 0,
            "total_trades": len(trades),
            "avg_win": statistics.mean([t.pnl for t in wins]) if wins else 0,
            "avg_loss": statistics.mean([t.pnl for t in losses]) if losses else 0,
            "total_pnl": sum(t.pnl for t in trades),
            "best_trade": max([t.pnl for t in trades]),
            "worst_trade": min([t.pnl for t in trades]),
        }
    
    def _generate_adjustments(
        self,
        performance: Dict[str, Any],
        trades: List[Trade]
    ) -> List[Dict[str, Any]]:
        """Generate parameter adjustment suggestions."""
        adjustments = []
        
        # Win rate adjustments
        if performance["win_rate"] < 0.45:
            adjustments.append({
                "parameter": "entry_criteria",
                "current": "standard",
                "suggested": "stricter",
                "reason": f"Win rate is only {performance['win_rate']:.1%}. Tighten entry criteria."
            })
        elif performance["win_rate"] > 0.70:
            adjustments.append({
                "parameter": "entry_criteria",
                "current": "strict",
                "suggested": "relaxed",
                "reason": f"Win rate is {performance['win_rate']:.1%}. You can afford to take more trades."
            })
        
        # Risk/reward adjustments
        if performance["avg_win"] > 0 and performance["avg_loss"] < 0:
            rr_ratio = abs(performance["avg_win"] / performance["avg_loss"])
            if rr_ratio < 1.5:
                adjustments.append({
                    "parameter": "take_profit_target",
                    "current": "conservative",
                    "suggested": "extended",
                    "reason": f"R:R ratio is only {rr_ratio:.2f}. Let winners run longer."
                })
        
        # Position sizing
        if performance["total_pnl"] < 0:
            adjustments.append({
                "parameter": "position_size",
                "current": "normal",
                "suggested": "reduced",
                "reason": "Overall P&L is negative. Reduce size while reassessing strategy."
            })
        
        return adjustments
    
    def _generate_adjustment_recommendations(
        self,
        performance: Dict[str, Any],
        adjustments: List[Dict]
    ) -> List[str]:
        """Generate human-readable recommendations."""
        recommendations = []
        
        for adj in adjustments:
            recommendations.append(
                f"Consider adjusting {adj['parameter']}: {adj['suggested']} - {adj['reason']}"
            )
        
        return recommendations


# Tool functions

def analyze_trade_patterns(agent_name: str, lookback_days: int = 90) -> Dict[str, Any]:
    """Tool: Analyze trade clusters to find patterns."""
    analyzer = TradeClusterAnalyzer()
    return analyzer.analyze_trade_clusters(agent_name, lookback_days)


def extract_winning_patterns(agent_name: str) -> Dict[str, Any]:
    """Tool: Extract golden rules from winning trades."""
    extractor = SuccessPatternExtractor()
    return extractor.extract_golden_rules(agent_name)


def get_strategy_adjustments(agent_name: str, lookback_days: int = 30) -> Dict[str, Any]:
    """Tool: Get suggested parameter adjustments."""
    adjuster = AdaptiveStrategyAdjuster()
    return adjuster.suggest_parameter_adjustments(agent_name, lookback_days)
