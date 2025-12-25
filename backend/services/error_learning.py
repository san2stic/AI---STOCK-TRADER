"""
Error Learning System  
Détecte automatiquement les erreurs récurrentes et génère des règles d'évitement.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import structlog
from database import get_db
from models.database import Trade, TradeStatus
from collections import defaultdict, Counter

logger = structlog.get_logger()


class RecurringErrorDetector:
    """
    Détecte les patterns d'erreur récurrents dans les trades perdants.
    """
    
    def detect_error_patterns(
        self,
        agent_name: str,
        lookback_days: int = 60,
        min_occurrences: int = 3
    ) -> Dict[str, Any]:
        """
        Détecte les erreurs récurrentes.
        
        Returns:
            {
                "error_patterns": [...],
                "total_losses": int,
                "loss_breakdown": {...}
            }
        """
        db = next(get_db())
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
            
            # Get losing trades
            losing_trades = db.query(Trade).filter(
                Trade.agent_name == agent_name,
                Trade.created_at >= cutoff_date,
                Trade.status.in_([TradeStatus.CLOSED, TradeStatus.FILLED]),
                Trade.pnl != None,
                Trade.pnl < 0
            ).all()
            
            if len(losing_trades) < min_occurrences:
                return {
                    "error_patterns": [],
                    "total_losses": len(losing_trades),
                    "loss_breakdown": {},
                    "message": "Not enough losing trades to detect patterns"
                }
            
            # Analyze error patterns
            patterns = self._analyze_error_patterns(losing_trades)
            
            # Filter by minimum occurrences
            significant_patterns = [
                p for p in patterns
                if p["occurrence_count"] >= min_occurrences
            ]
            
            # Sort by severity (frequency × avg loss)
            significant_patterns.sort(
                key=lambda x: x["severity_score"],
                reverse=True
            )
            
            # Loss breakdown
            loss_breakdown = {
                "total_loss": sum(t.pnl for t in losing_trades),
                "avg_loss": sum(t.pnl for t in losing_trades) / len(losing_trades),
                "worst_loss": min(t.pnl for t in losing_trades),
                "loss_count": len(losing_trades),
            }
            
            return {
                "error_patterns": significant_patterns,
                "total_losses": len(losing_trades),
                "loss_breakdown": loss_breakdown,
                "message": f"Found {len(significant_patterns)} recurring error patterns"
            }
            
        finally:
            db.close()
    
    def _analyze_error_patterns(self, trades: List[Trade]) -> List[Dict[str, Any]]:
        """Analyze and categorize error patterns."""
        pattern_groups = defaultdict(list)
        
        for trade in trades:
            # Classify error type from reasoning/context
            error_type = self._classify_error(trade)
            pattern_groups[error_type].append(trade)
        
        patterns = []
        for error_type, error_trades in pattern_groups.items():
            if error_type == "UNKNOWN":
                continue
            
            avg_loss = sum(t.pnl for t in error_trades) / len(error_trades)
            total_loss = sum(t.pnl for t in error_trades)
            severity = len(error_trades) * abs(avg_loss)  # Frequency × magnitude
            
            patterns.append({
                "error_type": error_type,
                "occurrence_count": len(error_trades),
                "avg_loss": round(avg_loss, 2),
                "total_loss": round(total_loss, 2),
                "severity_score": round(severity, 2),
                "affected_symbols": list(set(t.symbol for t in error_trades)),
                "description": self._get_error_description(error_type),
                "avoidance_rule": self._generate_avoidance_rule(error_type, error_trades)
            })
        
        return patterns
    
    def _classify_error(self, trade: Trade) -> str:
        """Classify the type of error from trade data."""
        reasoning = (trade.reasoning or "").lower()
        
        # Common error patterns
        if "fomo" in reasoning or ("high" in reasoning and "already" in reasoning):
            return "CHASING_MOMENTUM"
        
        if "panic" in reasoning or ("fear" in reasoning and "sell" in trade.action.value.lower()):
            return "PANIC_SELLING"
        
        if "revenge" in reasoning or "recover" in reasoning:
            return "REVENGE_TRADING"
        
        if "overbought" in reasoning and "buy" in trade.action.value.lower():
            return "BUYING_OVERBOUGHT"
        
        if "oversold" in reasoning and "sell" in trade.action.value.lower():
            return "SELLING_OVERSOLD"
        
        if "news" in reasoning and trade.pnl < -50:
            return "NEWS_OVERREACTION"
        
        if abs(trade.pnl) > 100:  # Large loss
            return "POOR_RISK_MANAGEMENT"
        
        return "OTHER_ERROR"
    
    def _get_error_description(self, error_type: str) -> str:
        """Get human-readable description of error."""
        descriptions = {
            "CHASING_MOMENTUM": "Buying stocks after they've already moved significantly",
            "PANIC_SELLING": "Selling positions out of fear during normal volatility",
            "REVENGE_TRADING": "Taking impulsive trades to recover losses",
            "BUYING_OVERBOUGHT": "Buying when RSI/indicators show overbought conditions",
            "SELLING_OVERSOLD": "Selling when RSI/indicators show oversold conditions",
            "NEWS_OVERREACTION": "Overreacting to news without proper analysis",
            "POOR_RISK_MANAGEMENT": "Taking positions too large or without stop-loss",
            "OTHER_ERROR": "Unclassified error pattern"
        }
        return descriptions.get(error_type, "Unknown error pattern")
    
    def _generate_avoidance_rule(self, error_type: str, trades: List[Trade]) -> str:
        """Generate specific avoidance rule for this error pattern."""
        rules = {
            "CHASING_MOMENTUM": "AVOID: Trading stocks up >10% in a day without pullback",
            "PANIC_SELLING": "AVOID: Selling during -5% days unless stop-loss hit",
            "REVENGE_TRADING": "RULE: After 2 consecutive losses, pause for 1 hour minimum",
            "BUYING_OVERBOUGHT": "AVOID: Buying when RSI > 75 unless strong catalyst",
            "SELLING_OVERSOLD": "AVOID: Selling when RSI < 25 - wait for bounce",
            "NEWS_OVERREACTION": "RULE: Wait 30 minutes after major news before trading",
            "POOR_RISK_MANAGEMENT": "RULE: Always calculate stop-loss before entry, max 3% risk",
            "OTHER_ERROR": "Review individual trades for specific patterns"
        }
        
        rule = rules.get(error_type, "No specific rule generated")
        
        # Add affected symbols if specific
        if len(trades) >= 3:
            common_symbols = [t.symbol for t in trades]
            symbol_counts = Counter(common_symbols)
            most_common = symbol_counts.most_common(2)
            if most_common[0][1] >= 2:
                symbols = [s for s, _ in most_common]
                rule += f" | Most affected: {', '.join(symbols)}"
        
        return rule


class AvoidanceRuleGenerator:
    """
    Génère et stocke des règles d'évitement automatiques.
    """
    
    def generate_rules(
        self,
        agent_name: str,
        error_patterns: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Génère des règles d'évitement à partir des patterns d'erreur.
        
        Returns:
            List of avoidance rules
        """
        rules = []
        
        for pattern in error_patterns:
            if pattern["severity_score"] > 50:  # High severity
                rules.append({
                    "severity": "HIGH",
                    "rule": pattern["avoidance_rule"],
                    "reason": f"Caused {pattern['occurrence_count']} losses, "
                             f"avg loss ${pattern['avg_loss']:.2f}"
                })
            elif pattern["severity_score"] > 20:  # Medium severity
                rules.append({
                    "severity": "MEDIUM",
                    "rule": pattern["avoidance_rule"],
                    "reason": f"{pattern['occurrence_count']} occurrences"
                })
        
        return rules
    
    def format_rules_for_prompt(self, rules: List[Dict[str, str]]) -> str:
        """Format rules for inclusion in agent prompt."""
        if not rules:
            return ""
        
        formatted = "\n🚫 AVOIDANCE RULES (learned from your losses):\n"
        
        for rule in rules:
            severity_emoji = "🔴" if rule["severity"] == "HIGH" else "🟡"
            formatted += f"{severity_emoji} {rule['rule']}\n   Reason: {rule['reason']}\n"
        
        return formatted


# Tool functions

def detect_recurring_errors(agent_name: str, lookback_days: int = 60) -> Dict[str, Any]:
    """Tool: Detect recurring error patterns in losing trades."""
    detector = RecurringErrorDetector()
    return detector.detect_error_patterns(agent_name, lookback_days)


def get_avoidance_rules(agent_name: str) -> Dict[str, Any]:
    """Tool: Get avoidance rules based on historical errors."""
    # First detect errors
    detector = RecurringErrorDetector()
    error_result = detector.detect_error_patterns(agent_name, lookback_days=90)
    
    # Then generate rules
    generator = AvoidanceRuleGenerator()
    rules = generator.generate_rules(agent_name, error_result.get("error_patterns", []))
    
    return {
        "avoidance_rules": rules,
        "error_patterns": error_result.get("error_patterns", []),
        "total_errors_detected": len(error_result.get("error_patterns", [])),
        "formatted_for_prompt": generator.format_rules_for_prompt(rules)
    }
