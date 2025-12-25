"""
Advanced Multi-Factor Decision Engine
Combines technical indicators, sentiment, market conditions into sophisticated scoring.
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import structlog
from database import get_db
from models.database import Trade, TradeStatus, Decision
import statistics
import math

logger = structlog.get_logger()


class MultiFactorScorer:
    """
    Calcul de score multi-facteurs combinant tous les signaux disponibles.
    Score final: 0-100 (plus élevé = meilleur setup)
    """
    
    def __init__(self):
        self.weights = {
            "technical": 0.35,      # 35% - indicateurs techniques
            "momentum": 0.25,       # 25% - momentum et tendance
            "sentiment": 0.20,      # 20% - sentiment de marché
            "risk_reward": 0.15,    # 15% - ratio risque/rendement
            "confluence": 0.05,     # 5% - bonus de confluence
        }
    
    def calculate_score(
        self,
        symbol: str,
        technical_data: Dict[str, Any],
        market_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calcule le score multi-facteurs complet.
        
        Returns:
            {
                "total_score": 0-100,
                "breakdown": {...},
                "signals": [...],
                "recommendation": "STRONG_BUY" | "BUY" | "NEUTRAL" | "SELL" | "STRONG_SELL"
            }
        """
        scores = {}
        
        # 1. Score technique (RSI, MACD, Bollinger, etc.)
        scores["technical"] = self._calculate_technical_score(technical_data)
        
        # 2. Score de momentum et tendance
        scores["momentum"] = self._calculate_momentum_score(technical_data)
        
        # 3. Score de sentiment
        scores["sentiment"] = self._calculate_sentiment_score(market_context)
        
        # 4. Score risque/rendement
        scores["risk_reward"] = self._calculate_risk_reward_score(technical_data)
        
        # 5. Bonus de confluence (signaux alignés)
        scores["confluence"] = self._calculate_confluence_bonus(technical_data)
        
        # Score total pondéré
        total_score = sum(
            scores[key] * self.weights[key] 
            for key in scores.keys()
        )
        
        # Recommandation basée sur le score
        recommendation = self._get_recommendation(total_score)
        
        # Liste des signaux détectés
        signals = self._extract_signals(technical_data, scores)
        
        return {
            "total_score": round(total_score, 2),
            "breakdown": {k: round(v, 2) for k, v in scores.items()},
            "signals": signals,
            "recommendation": recommendation,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _calculate_technical_score(self, data: Dict[str, Any]) -> float:
        """Score basé sur les indicateurs techniques (0-100)"""
        score = 50.0  # neutral par défaut
        
        # RSI analysis
        rsi = data.get("rsi")
        if rsi:
            if rsi < 30:  # Oversold - bullish
                score += 15
            elif rsi < 40:
                score += 10
            elif rsi > 70:  # Overbought - bearish
                score -= 15
            elif rsi > 60:
                score -= 10
        
        # MACD analysis
        macd = data.get("macd", {})
        if macd:
            macd_line = macd.get("macd")
            signal_line = macd.get("signal")
            if macd_line and signal_line:
                if macd_line > signal_line:  # Bullish
                    score += 10
                else:  # Bearish
                    score -= 10
        
        # Bollinger Bands
        bollinger = data.get("bollinger", {})
        if bollinger:
            price = data.get("current_price")
            lower = bollinger.get("lower")
            upper = bollinger.get("upper")
            middle = bollinger.get("middle")
            
            if price and lower and upper and middle:
                # Prix près de la bande inférieure = bullish
                if price <= lower * 1.02:
                    score += 12
                # Prix près de la bande supérieure = bearish
                elif price >= upper * 0.98:
                    score -= 12
                # Prix au-dessus de la moyenne = légèrement bullish
                elif price > middle:
                    score += 5
                else:
                    score -= 5
        
        # SMA analysis (50 vs 200)
        sma_50 = data.get("sma_50")
        sma_200 = data.get("sma_200")
        if sma_50 and sma_200:
            if sma_50 > sma_200:  # Golden cross territory
                score += 8
            else:  # Death cross territory
                score -= 8
        
        return max(0, min(100, score))
    
    def _calculate_momentum_score(self, data: Dict[str, Any]) -> float:
        """Score basé sur le momentum et la tendance (0-100)"""
        score = 50.0
        
        # Price change (daily, weekly)
        change_1d = data.get("change_1d", 0)
        change_7d = data.get("change_7d", 0)
        
        # Momentum positif fort
        if change_1d > 3 and change_7d > 10:
            score += 20
        elif change_1d > 1 and change_7d > 5:
            score += 10
        # Momentum négatif fort
        elif change_1d < -3 and change_7d < -10:
            score -= 20
        elif change_1d < -1 and change_7d < -5:
            score -= 10
        
        # Volume analysis
        volume_ratio = data.get("volume_ratio", 1.0)  # vs average
        if volume_ratio > 1.5:  # Volume élevé
            # Volume élevé + momentum positif = très bullish
            if change_1d > 0:
                score += 15
            # Volume élevé + momentum négatif = très bearish
            else:
                score -= 15
        
        # ADX (trend strength)
        adx = data.get("adx")
        if adx:
            if adx > 25:  # Tendance forte
                # Si price monte avec tendance forte = bullish
                if change_1d > 0:
                    score += 10
                else:
                    score -= 10
        
        return max(0, min(100, score))
    
    def _calculate_sentiment_score(self, context: Dict[str, Any]) -> float:
        """Score basé sur le sentiment de marché (0-100)"""
        score = 50.0
        
        # Fear & Greed Index
        fear_greed = context.get("fear_greed_index")
        if fear_greed:
            if fear_greed < 25:  # Extreme fear = contrarian buy
                score += 20
            elif fear_greed < 45:  # Fear
                score += 10
            elif fear_greed > 75:  # Extreme greed = contrarian sell
                score -= 20
            elif fear_greed > 55:  # Greed
                score -= 10
        
        # Market regime
        market_regime = context.get("market_regime")
        if market_regime:
            if market_regime == "BULL_MARKET":
                score += 15
            elif market_regime == "BEAR_MARKET":
                score -= 15
            # SIDEWAYS = neutral, no change
        
        # News sentiment
        news_sentiment = context.get("news_sentiment")
        if news_sentiment:
            if news_sentiment > 0.3:  # Positive
                score += 10
            elif news_sentiment < -0.3:  # Negative
                score -= 10
        
        # Economic events impact
        eco_impact = context.get("economic_impact", "LOW")
        if eco_impact == "HIGH":
            # High impact events = reduce score (caution)
            score -= 15
        
        return max(0, min(100, score))
    
    def _calculate_risk_reward_score(self, data: Dict[str, Any]) -> float:
        """Score basé sur le ratio risque/rendement (0-100)"""
        score = 50.0
        
        # Support/Resistance levels
        support = data.get("nearest_support")
        resistance = data.get("nearest_resistance")
        current_price = data.get("current_price")
        
        if support and resistance and current_price:
            # Distance to support (risk)
            downside_risk = (current_price - support) / current_price * 100
            # Distance to resistance (reward)
            upside_potential = (resistance - current_price) / current_price * 100
            
            # Risk/Reward ratio
            if downside_risk > 0:
                rr_ratio = upside_potential / downside_risk
                
                if rr_ratio > 3:  # Excellent R:R (1:3+)
                    score += 25
                elif rr_ratio > 2:  # Good R:R (1:2)
                    score += 15
                elif rr_ratio > 1.5:  # Acceptable R:R
                    score += 5
                elif rr_ratio < 1:  # Poor R:R
                    score -= 20
        
        # Volatility (ATR)
        atr_percent = data.get("atr_percent")
        if atr_percent:
            # Volatilité modérée = meilleur score
            if 1 < atr_percent < 3:
                score += 10
            # Volatilité extrême = risqué
            elif atr_percent > 5:
                score -= 15
        
        return max(0, min(100, score))
    
    def _calculate_confluence_bonus(self, data: Dict[str, Any]) -> float:
        """Bonus quand plusieurs signaux sont alignés (0-100)"""
        bullish_signals = 0
        bearish_signals = 0
        
        # Check RSI
        rsi = data.get("rsi")
        if rsi:
            if rsi < 40:
                bullish_signals += 1
            elif rsi > 60:
                bearish_signals += 1
        
        # Check MACD
        macd = data.get("macd", {})
        if macd.get("macd", 0) > macd.get("signal", 0):
            bullish_signals += 1
        else:
            bearish_signals += 1
        
        # Check price vs SMA
        current_price = data.get("current_price")
        sma_50 = data.get("sma_50")
        if current_price and sma_50:
            if current_price > sma_50:
                bullish_signals += 1
            else:
                bearish_signals += 1
        
        # Check Bollinger position
        bollinger = data.get("bollinger", {})
        if bollinger and current_price:
            if current_price < bollinger.get("lower", float('inf')):
                bullish_signals += 1
            elif current_price > bollinger.get("upper", 0):
                bearish_signals += 1
        
        # Check price change
        if data.get("change_1d", 0) > 0:
            bullish_signals += 1
        else:
            bearish_signals += 1
        
        # Confluence score based on agreement
        total_signals = bullish_signals + bearish_signals
        if total_signals > 0:
            # Strong confluence = beaucoup de signaux dans la même direction
            max_direction = max(bullish_signals, bearish_signals)
            confluence_ratio = max_direction / total_signals
            
            if confluence_ratio >= 0.8:  # 80%+ agreement
                return 100
            elif confluence_ratio >= 0.6:  # 60%+ agreement
                return 60
            else:
                return 20
        
        return 50
    
    def _get_recommendation(self, score: float) -> str:
        """Convertit le score en recommandation"""
        if score >= 75:
            return "STRONG_BUY"
        elif score >= 60:
            return "BUY"
        elif score >= 40:
            return "NEUTRAL"
        elif score >= 25:
            return "SELL"
        else:
            return "STRONG_SELL"
    
    def _extract_signals(self, data: Dict[str, Any], scores: Dict[str, float]) -> List[str]:
        """Extract human-readable signals from the analysis"""
        signals = []
        
        # Technical signals
        rsi = data.get("rsi")
        if rsi:
            if rsi < 30:
                signals.append(f"RSI oversold ({rsi:.1f}) - bullish signal")
            elif rsi > 70:
                signals.append(f"RSI overbought ({rsi:.1f}) - bearish signal")
        
        # MACD signals
        macd = data.get("macd", {})
        if macd.get("macd", 0) > macd.get("signal", 0):
            signals.append("MACD bullish crossover")
        else:
            signals.append("MACD bearish crossover")
        
        # Trend signals
        if scores.get("momentum", 50) > 60:
            signals.append("Strong positive momentum")
        elif scores.get("momentum", 50) < 40:
            signals.append("Strong negative momentum")
        
        # Sentiment signals
        if scores.get("sentiment", 50) > 65:
            signals.append("Bullish market sentiment")
        elif scores.get("sentiment", 50) < 35:
            signals.append("Bearish market sentiment")
        
        # Confluence
        if scores.get("confluence", 50) > 80:
            signals.append("⭐ High signal confluence - strong setup")
        
        return signals


class SignalConfluenceDetector:
    """
    Détecte quand plusieurs indicateurs convergent vers le même signal.
    Plus de confluence = plus de fiabilité.
    """
    
    def analyze_confluence(
        self,
        technical_data: Dict[str, Any],
        market_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyse la confluence des signaux.
        
        Returns:
            {
                "confluence_score": 0-100,
                "direction": "BULLISH" | "BEARISH" | "NEUTRAL",
                "agreeing_indicators": [...],
                "conflicting_indicators": [...],
                "reliability": "HIGH" | "MEDIUM" | "LOW"
            }
        """
        bullish_indicators = []
        bearish_indicators = []
        
        # Analyze each indicator
        self._check_rsi(technical_data, bullish_indicators, bearish_indicators)
        self._check_macd(technical_data, bullish_indicators, bearish_indicators)
        self._check_bollinger(technical_data, bullish_indicators, bearish_indicators)
        self._check_sma(technical_data, bullish_indicators, bearish_indicators)
        self._check_momentum(technical_data, bullish_indicators, bearish_indicators)
        self._check_sentiment(market_context, bullish_indicators, bearish_indicators)
        
        total_indicators = len(bullish_indicators) + len(bearish_indicators)
        
        if total_indicators == 0:
            return {
                "confluence_score": 0,
                "direction": "NEUTRAL",
                "agreeing_indicators": [],
                "conflicting_indicators": [],
                "reliability": "LOW"
            }
        
        # Determine dominant direction
        if len(bullish_indicators) > len(bearish_indicators):
            direction = "BULLISH"
            agreeing = bullish_indicators
            conflicting = bearish_indicators
        elif len(bearish_indicators) > len(bullish_indicators):
            direction = "BEARISH"
            agreeing = bearish_indicators
            conflicting = bullish_indicators
        else:
            direction = "NEUTRAL"
            agreeing = []
            conflicting = bullish_indicators + bearish_indicators
        
        # Calculate confluence score
        if total_indicators > 0:
            confluence_score = (len(agreeing) / total_indicators) * 100
        else:
            confluence_score = 0
        
        # Determine reliability
        if confluence_score >= 75:
            reliability = "HIGH"
        elif confluence_score >= 50:
            reliability = "MEDIUM"
        else:
            reliability = "LOW"
        
        return {
            "confluence_score": round(confluence_score, 2),
            "direction": direction,
            "agreeing_indicators": agreeing,
            "conflicting_indicators": conflicting,
            "reliability": reliability,
            "indicator_count": {
                "bullish": len(bullish_indicators),
                "bearish": len(bearish_indicators),
                "total": total_indicators
            }
        }
    
    def _check_rsi(self, data: Dict, bullish: List, bearish: List):
        rsi = data.get("rsi")
        if rsi:
            if rsi < 40:
                bullish.append(f"RSI({rsi:.1f})")
            elif rsi > 60:
                bearish.append(f"RSI({rsi:.1f})")
    
    def _check_macd(self, data: Dict, bullish: List, bearish: List):
        macd = data.get("macd", {})
        if macd.get("macd") and macd.get("signal"):
            if macd["macd"] > macd["signal"]:
                bullish.append("MACD")
            else:
                bearish.append("MACD")
    
    def _check_bollinger(self, data: Dict, bullish: List, bearish: List):
        bollinger = data.get("bollinger", {})
        price = data.get("current_price")
        if bollinger and price:
            lower = bollinger.get("lower")
            upper = bollinger.get("upper")
            if lower and price <= lower * 1.02:
                bullish.append("Bollinger")
            elif upper and price >= upper * 0.98:
                bearish.append("Bollinger")
    
    def _check_sma(self, data: Dict, bullish: List, bearish: List):
        price = data.get("current_price")
        sma_50 = data.get("sma_50")
        sma_200 = data.get("sma_200")
        
        if price and sma_50:
            if price > sma_50:
                bullish.append("SMA50")
            else:
                bearish.append("SMA50")
        
        if sma_50 and sma_200:
            if sma_50 > sma_200:
                bullish.append("Golden Cross")
            else:
                bearish.append("Death Cross")
    
    def _check_momentum(self, data: Dict, bullish: List, bearish: List):
        change = data.get("change_1d", 0)
        volume_ratio = data.get("volume_ratio", 1.0)
        
        if change > 1 and volume_ratio > 1.2:
            bullish.append("Momentum+Volume")
        elif change < -1 and volume_ratio > 1.2:
            bearish.append("Momentum+Volume")
    
    def _check_sentiment(self, context: Dict, bullish: List, bearish: List):
        fear_greed = context.get("fear_greed_index")
        if fear_greed:
            if fear_greed < 30:
                bullish.append("Extreme Fear")
            elif fear_greed > 70:
                bearish.append("Extreme Greed")


class BayesianDecisionTree:
    """
    Arbre de décision probabiliste qui s'adapte en fonction des résultats passés.
    Utilise le théorème de Bayes pour calculer les probabilités de succès.
    """
    
    def __init__(self):
        self.prior_success_rate = 0.5  # 50% par défaut
    
    def calculate_success_probability(
        self,
        agent_key: str,
        symbol: str,
        action: str,
        market_conditions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calcule la probabilité de succès d'un trade basé sur l'historique.
        
        Returns:
            {
                "success_probability": 0.0-1.0,
                "confidence_level": "HIGH" | "MEDIUM" | "LOW",
                "sample_size": int,
                "recommendation": str
            }
        """
        db = next(get_db())
        
        try:
            # Get historical trades for this agent and similar conditions
            historical_trades = self._get_similar_trades(
                db, agent_key, symbol, action, market_conditions
            )
            
            if len(historical_trades) < 5:
                # Not enough data, use prior
                return {
                    "success_probability": self.prior_success_rate,
                    "confidence_level": "LOW",
                    "sample_size": len(historical_trades),
                    "recommendation": "Insufficient historical data - proceed with caution",
                    "method": "prior"
                }
            
            # Calculate success rate from history
            successful_trades = sum(
                1 for trade in historical_trades
                if trade.pnl and trade.pnl > 0
            )
            
            success_rate = successful_trades / len(historical_trades)
            
            # Bayesian update: combine prior with observed data
            # Using Beta distribution: posterior mean = (α + successes) / (α + β + total)
            # where α and β are prior parameters (we use α=β=1 for uniform prior)
            alpha = beta = 1
            posterior_probability = (alpha + successful_trades) / (
                alpha + beta + len(historical_trades)
            )
            
            # Confidence level based on sample size
            if len(historical_trades) >= 30:
                confidence = "HIGH"
            elif len(historical_trades) >= 15:
                confidence = "MEDIUM"
            else:
                confidence = "LOW"
            
            # Recommendation
            if posterior_probability >= 0.65 and confidence in ["HIGH", "MEDIUM"]:
                recommendation = "Strong historical edge - favorable setup"
            elif posterior_probability >= 0.55:
                recommendation = "Slight positive edge - acceptable risk"
            elif posterior_probability >= 0.45:
                recommendation = "Neutral - no clear edge"
            else:
                recommendation = "Negative historical edge - avoid or reduce size"
            
            return {
                "success_probability": round(posterior_probability, 3),
                "raw_success_rate": round(success_rate, 3),
                "confidence_level": confidence,
                "sample_size": len(historical_trades),
                "successful_trades": successful_trades,
                "recommendation": recommendation,
                "method": "bayesian"
            }
            
        finally:
            db.close()
    
    def _get_similar_trades(
        self,
        db,
        agent_key: str,
        symbol: str,
        action: str,
        market_conditions: Dict[str, Any]
    ) -> List[Trade]:
        """Get similar historical trades"""
        
        # Get trades from the last 90 days for this agent
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        
        query = db.query(Trade).filter(
            Trade.agent_key == agent_key,
            Trade.created_at >= cutoff_date,
            Trade.status.in_([TradeStatus.CLOSED, TradeStatus.FILLED])
        )
        
        # Filter by symbol if specific symbol (not searching for similar)
        if symbol and symbol != "ANY":
            query = query.filter(Trade.symbol == symbol)
        
        # Filter by action
        query = query.filter(Trade.action == action.upper())
        
        trades = query.all()
        
        # TODO: Could add filtering by similar market conditions
        # (e.g., similar RSI, similar market regime, etc.)
        
        return trades


def get_decision_score(symbol: str, technical_data: Dict[str, Any], market_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool function: Get comprehensive decision score for a symbol.
    """
    scorer = MultiFactorScorer()
    return scorer.calculate_score(symbol, technical_data, market_context)


def get_signal_confluence(technical_data: Dict[str, Any], market_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool function: Analyze signal confluence.
    """
    detector = SignalConfluenceDetector()
    return detector.analyze_confluence(technical_data, market_context)


def get_success_probability(
    agent_key: str,
    symbol: str,
    action: str,
    market_conditions: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Tool function: Calculate Bayesian success probability.
    """
    bayesian_tree = BayesianDecisionTree()
    return bayesian_tree.calculate_success_probability(
        agent_key, symbol, action, market_conditions
    )
