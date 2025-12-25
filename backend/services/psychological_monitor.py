"""
Psychological Edge System
Protects against emotional trading by detecting FOMO, FUD, revenge trading,
and implementing circuit breakers for losing streaks.
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import structlog
from database import get_db
from models.database import Trade, TradeStatus, Portfolio

logger = structlog.get_logger()


class FOMOFUDDetector:
    """
    Détecte les trades émotionnels (FOMO/FUD) avant qu'ils ne soient exécutés.
    """
    
    def detect_emotional_trade(
        self,
        agent_name: str,
        symbol: str,
        action: str,
        reasoning: str = ""
    ) -> Dict[str, Any]:
        """
        Détecte si un trade proposé est motivé par l'émotion.
        
        Returns:
            {
                "is_emotional": bool,
                "emotion_type": "FOMO" | "FUD" | "REVENGE" | "NONE",
                "should_block": bool,
                "warning_message": str
            }
        """
        db = next(get_db())
        
        try:
            # Check for FOMO indicators
            fomo_detected, fomo_reason = self._detect_fomo(db, agent_name, symbol, action, reasoning)
            
            # Check for FUD indicators  
            fud_detected, fud_reason = self._detect_fud(db, agent_name, symbol, action, reasoning)
            
            # Check for revenge trading
            revenge_detected, revenge_reason = self._detect_revenge_trading(db, agent_name)
            
            # Determine emotion type and severity
            if revenge_detected:
                return {
                    "is_emotional": True,
                    "emotion_type": "REVENGE",
                    "should_block": True,  # Always block revenge trading
                    "warning_message": f"🚨 REVENGE TRADING DETECTED: {revenge_reason} - TRADE BLOCKED",
                    "details": revenge_reason
                }
            elif fomo_detected:
                return {
                    "is_emotional": True,
                    "emotion_type": "FOMO",
                    "should_block": True,
                    "warning_message": f"⚠️ FOMO DETECTED: {fomo_reason} - TRADE BLOCKED",
                    "details": fomo_reason
                }
            elif fud_detected:
                return {
                    "is_emotional": True,
                    "emotion_type": "FUD",
                    "should_block": True,
                    "warning_message": f"⚠️ FUD/PANIC DETECTED: {fud_reason} - TRADE BLOCKED",
                    "details": fud_reason
                }
            else:
                return {
                    "is_emotional": False,
                    "emotion_type": "NONE",
                    "should_block": False,
                    "warning_message": "Trade appears rational",
                    "details": "No emotional indicators detected"
                }
                
        finally:
            db.close()
    
    def _detect_fomo(
        self,
        db,
        agent_name: str,
        symbol: str,
        action: str,
        reasoning: str
    ) -> Tuple[bool, str]:
        """Detect Fear Of Missing Out indicators."""
        
        # FOMO keywords in reasoning
        reasoning_lower = reasoning.lower()
        fomo_keywords = ["fomo", "don't want to miss", "everyone is buying", "trending", "going to moon"]
        
        if any(keyword in reasoning_lower for keyword in fomo_keywords):
            return True, "FOMO keywords detected in reasoning"
        
        # Check if buying after big move
        if action.upper() == "BUY":
            # Get recent price movement from trades
            recent_trades = db.query(Trade).filter(
                Trade.symbol == symbol,
                Trade.created_at >= datetime.utcnow() - timedelta(hours=24)
            ).all()
            
            # If multiple recent buys on same symbol = possible FOMO
            recent_buys_same_symbol = db.query(Trade).filter(
                Trade.agent_name == agent_name,
                Trade.symbol == symbol,
                Trade.action.in_(["buy", "BUY"]),
                Trade.created_at >= datetime.utcnow() - timedelta(hours=4)
            ).count()
            
            if recent_buys_same_symbol >= 2:
                return True, f"Trying to buy {symbol} again within 4 hours - possible FOMO chasing"
        
        return False, ""
    
    def _detect_fud(
        self,
        db,
        agent_name: str,
        symbol: str,
        action: str,
        reasoning: str
    ) -> Tuple[bool, str]:
        """Detect Fear, Uncertainty, Doubt indicators."""
        
        # FUD keywords
        reasoning_lower = reasoning.lower()
        fud_keywords = ["panic", "scared", "fear", "crash", "emergency", "worried"]
        
        if any(keyword in reasoning_lower for keyword in fud_keywords):
            return True, "Panic/fear keywords detected in reasoning"
        
        # Selling during normal volatility
        if action.upper() == "SELL":
            # Check if there was a recent buy that's now being panic sold
            recent_buy = db.query(Trade).filter(
                Trade.agent_name == agent_name,
                Trade.symbol == symbol,
                Trade.action.in_(["buy", "BUY"]),
                Trade.created_at >= datetime.utcnow() - timedelta(hours=24),
                Trade.status == TradeStatus.FILLED
            ).first()
            
            if recent_buy:
                # Selling within 24h of buying = possible panic
                return True, f"Trying to sell {symbol} within 24h of buying - possible panic selling"
        
        return False, ""
    
    def _detect_revenge_trading(self, db, agent_name: str) -> Tuple[bool, str]:
        """Detect revenge trading patterns."""
        
        # Get last 3 trades
        recent_trades = db.query(Trade).filter(
            Trade.agent_name == agent_name,
            Trade.created_at >= datetime.utcnow() - timedelta(hours=6),
            Trade.status.in_([TradeStatus.CLOSED, TradeStatus.FILLED]),
            Trade.pnl != None
        ).order_by(Trade.created_at.desc()).limit(3).all()
        
        if len(recent_trades) >= 2:
            # Check if last trade was a loss
            last_trade = recent_trades[0]
            if last_trade.pnl < 0:
                # Check how quickly trying to trade again
                time_since_loss = datetime.utcnow() - last_trade.created_at
                
                if time_since_loss < timedelta(minutes=30):
                    return True, f"Trading again within 30 min of ${last_trade.pnl:.2f} loss - REVENGE TRADING"
        
        # Check for rapid fire trades after loss
        if len(recent_trades) >= 3:
            if all(t.pnl < 0 for t in recent_trades[:2]):
                return True, "Two consecutive losses detected - emotional state likely compromised"
        
        return False, ""


class RevengeTradePrevent:
    """
    Prévient le revenge trading en imposant des cooldowns après pertes.
    """
    
    def check_cooldown_required(
        self,
        agent_name: str
    ) -> Dict[str, Any]:
        """
        Vérifie si un cooldown est requis avant de trader.
        
        Returns:
            {
                "cooldown_active": bool,
                "cooldown_ends_at": datetime | None,
                "reason": str,
                "minutes_remaining": int
            }
        """
        db = next(get_db())
        
        try:
            # Get recent losing trades
            recent_losses = db.query(Trade).filter(
                Trade.agent_name == agent_name,
                Trade.created_at >= datetime.utcnow() - timedelta(hours=12),
                Trade.status.in_([TradeStatus.CLOSED, TradeStatus.FILLED]),
                Trade.pnl != None,
                Trade.pnl < 0
            ).order_by(Trade.created_at.desc()).all()
            
            if not recent_losses:
                return {
                    "cooldown_active": False,
                    "cooldown_ends_at": None,
                    "reason": "No recent losses",
                    "minutes_remaining": 0
                }
            
            # Count consecutive losses
            consecutive_losses = 0
            for trade in recent_losses:
                if trade.pnl < 0:
                    consecutive_losses += 1
                else:
                    break
            
            # Determine cooldown duration based on consecutive losses
            cooldown_minutes = 0
            
            if consecutive_losses >= 5:
                cooldown_minutes = 1440  # 24 hours
            elif consecutive_losses >= 3:
                cooldown_minutes = 60  # 1 hour
            elif consecutive_losses >= 2:
                cooldown_minutes = 30  # 30 minutes
            
            if cooldown_minutes > 0:
                last_loss_time = recent_losses[0].created_at
                cooldown_ends_at = last_loss_time + timedelta(minutes=cooldown_minutes)
                
                if datetime.utcnow() < cooldown_ends_at:
                    minutes_remaining = int((cooldown_ends_at - datetime.utcnow()).total_seconds() / 60)
                    
                    return {
                        "cooldown_active": True,
                        "cooldown_ends_at": cooldown_ends_at.isoformat(),
                        "reason": f"Cooldown after {consecutive_losses} consecutive losses",
                        "minutes_remaining": minutes_remaining,
                        "consecutive_losses": consecutive_losses
                    }
            
            return {
                "cooldown_active": False,
                "cooldown_ends_at": None,
                "reason": "Cooldown period ended",
                "minutes_remaining": 0
            }
            
        finally:
            db.close()


class DrawdownEmotionalControl:
    """
    Contrôle émotionnel durant les périodes de drawdown.
    """
    
    def get_drawdown_controls(
        self,
        agent_name: str
    ) -> Dict[str, Any]:
        """
        Retourne les contrôles à appliquer basés sur le drawdown actuel.
        
        Returns:
            {
                "current_drawdown_percent": float,
                "position_size_multiplier": float,
                "should_pause_trading": bool,
                "control_level": "NONE" | "REDUCE" | "PAUSE",
                "message": str
            }
        """
        db = next(get_db())
        
        try:
            # Get portfolio
            portfolio = db.query(Portfolio).filter(
                Portfolio.agent_name == agent_name
            ).first()
            
            if not portfolio:
                return {
                    "current_drawdown_percent": 0,
                    "position_size_multiplier": 1.0,
                    "should_pause_trading": False,
                    "control_level": "NONE",
                    "message": "No portfolio found"
                }
            
            # Calculate drawdown
            initial_capital = 10000  # Assuming initial capital
            current_value = portfolio.cash + sum(p.get("value", 0) for p in portfolio.positions or [])
            drawdown_percent = ((initial_capital - current_value) / initial_capital) * 100
            
            # Determine control level
            if drawdown_percent >= 20:
                return {
                    "current_drawdown_percent": round(drawdown_percent, 2),
                    "position_size_multiplier": 0.0,
                    "should_pause_trading": True,
                    "control_level": "PAUSE",
                    "message": f"🛑 TRADING PAUSED: {drawdown_percent:.1f}% drawdown. Reassess strategy before resuming."
                }
            elif drawdown_percent >= 10:
                return {
                    "current_drawdown_percent": round(drawdown_percent, 2),
                    "position_size_multiplier": 0.5,
                    "should_pause_trading": False,
                    "control_level": "REDUCE",
                    "message": f"⚠️ REDUCE SIZE: {drawdown_percent:.1f}% drawdown. Position sizes reduced to 50%."
                }
            else:
                return {
                    "current_drawdown_percent": round(drawdown_percent, 2),
                    "position_size_multiplier": 1.0,
                    "should_pause_trading": False,
                    "control_level": "NONE",
                    "message": f"✅ Normal operation: {drawdown_percent:.1f}% drawdown."
                }
                
        finally:
            db.close()


class LossStreakCircuitBreaker:
    """
    Disjoncteur qui force une pause après des séries de pertes.
    """
    
    def check_circuit_breaker(
        self,
        agent_name: str
    ) -> Dict[str, Any]:
        """
        Vérifie si le circuit breaker doit s'activer.
        
        Returns:
            {
                "breaker_active": bool,
                "consecutive_losses": int,
                "forced_pause_minutes": int,
                "message": str
            }
        """
        db = next(get_db())
        
        try:
            # Get recent trades
            recent_trades = db.query(Trade).filter(
                Trade.agent_name == agent_name,
                Trade.created_at >= datetime.utcnow() - timedelta(days=1),
                Trade.status.in_([TradeStatus.CLOSED, TradeStatus.FILLED]),
                Trade.pnl != None
            ).order_by(Trade.created_at.desc()).limit(10).all()
            
            # Count consecutive losses from most recent
            consecutive_losses = 0
            for trade in recent_trades:
                if trade.pnl < 0:
                    consecutive_losses += 1
                else:
                    break
            
            # Circuit breaker thresholds
            if consecutive_losses >= 5:
                return {
                    "breaker_active": True,
                    "consecutive_losses": consecutive_losses,
                    "forced_pause_minutes": 1440,  # 24 hours
                    "message": f"🔴 CIRCUIT BREAKER: {consecutive_losses} consecutive losses. FORCED PAUSE 24 HOURS. "
                               f"Analyze what's wrong before resuming.",
                    "severity": "CRITICAL"
                }
            elif consecutive_losses >= 3:
                return {
                    "breaker_active": True,
                    "consecutive_losses": consecutive_losses,
                    "forced_pause_minutes": 60,  # 1 hour
                    "message": f"🟡 CIRCUIT BREAKER: {consecutive_losses} consecutive losses. Pause 1 hour minimum.",
                    "severity": "WARNING"
                }
            else:
                return {
                    "breaker_active": False,
                    "consecutive_losses": consecutive_losses,
                    "forced_pause_minutes": 0,
                    "message": f"✅ No circuit breaker. {consecutive_losses} consecutive losses (threshold: 3)",
                    "severity": "NORMAL"
                }
                
        finally:
            db.close()


# Tool functions

def detect_emotional_trade(
    agent_name: str,
    symbol: str,
    action: str,
    reasoning: str = ""
) -> Dict[str, Any]:
    """Tool: Detect if a proposed trade is emotionally motivated."""
    detector = FOMOFUDDetector()
    return detector.detect_emotional_trade(agent_name, symbol, action, reasoning)


def check_trading_cooldown(agent_name: str) -> Dict[str, Any]:
    """Tool: Check if trading cooldown is active after losses."""
    preventer = RevengeTradePrevent()
    return preventer.check_cooldown_required(agent_name)


def check_drawdown_controls(agent_name: str) -> Dict[str, Any]:
    """Tool: Get position size controls based on current drawdown."""
    controller = DrawdownEmotionalControl()
    return controller.get_drawdown_controls(agent_name)


def check_circuit_breaker(agent_name: str) -> Dict[str, Any]:
    """Tool: Check if circuit breaker is active due to loss streak."""
    breaker = LossStreakCircuitBreaker()
    return breaker.check_circuit_breaker(agent_name)
