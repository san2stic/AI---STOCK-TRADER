"""
Market Sentiment Analysis Service.
Aggregates sentiment from multiple free sources for trading decisions.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import httpx
import asyncio
import structlog
import re

logger = structlog.get_logger()


class SentimentAnalyzer:
    """
    Analyze market sentiment from multiple free sources:
    - Fear & Greed Index (alternative.me API - no key needed)
    - Simple price momentum sentiment
    - Volume-based sentiment
    """
    
    def __init__(self):
        self.timeout = 15.0
        self._cache = {}
        self._cache_duration_hours = 1  # Cache for 1 hour
    
    async def get_comprehensive_sentiment(
        self, 
        symbol: str = None,
        include_crypto: bool = True
    ) -> Dict[str, Any]:
        """
        Get comprehensive market sentiment analysis.
        
        Returns:
            Dictionary with sentiment scores and interpretation
        """
        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "symbol": symbol,
        }
        
        # Get Fear & Greed Index (crypto-focused but indicative of overall risk appetite)
        if include_crypto:
            result["fear_greed"] = await self.get_fear_greed_index()
        
        # Get price-based sentiment for specific symbol
        if symbol:
            result["price_sentiment"] = await self.get_price_sentiment(symbol)
        
        # Calculate overall sentiment score
        result["overall"] = self._calculate_overall_sentiment(result)
        
        return result
    
    async def get_fear_greed_index(self) -> Dict[str, Any]:
        """
        Get the Fear & Greed Index from alternative.me (FREE, no API key).
        
        Index ranges:
        - 0-24: Extreme Fear (buy signal)
        - 25-44: Fear
        - 45-55: Neutral
        - 56-75: Greed
        - 76-100: Extreme Greed (sell signal)
        """
        cache_key = "fear_greed"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    "https://api.alternative.me/fng/",
                    params={"limit": 1, "format": "json"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("data") and len(data["data"]) > 0:
                        fng_data = data["data"][0]
                        value = int(fng_data.get("value", 50))
                        classification = fng_data.get("value_classification", "Neutral")
                        
                        # Interpret for trading
                        if value <= 24:
                            signal = "strong_buy"
                            interpretation = "Extreme fear - potential buying opportunity"
                        elif value <= 44:
                            signal = "buy"
                            interpretation = "Fear in market - consider accumulating"
                        elif value <= 55:
                            signal = "neutral"
                            interpretation = "Neutral sentiment - wait for clearer signals"
                        elif value <= 75:
                            signal = "sell"
                            interpretation = "Greed building - consider taking profits"
                        else:
                            signal = "strong_sell"
                            interpretation = "Extreme greed - high risk of correction"
                        
                        result = {
                            "value": value,
                            "classification": classification,
                            "signal": signal,
                            "interpretation": interpretation,
                            "timestamp": fng_data.get("timestamp"),
                            "source": "alternative.me",
                        }
                        
                        self._save_to_cache(cache_key, result)
                        return result
                
                return {"error": "Failed to fetch Fear & Greed Index"}
                
        except Exception as e:
            logger.error("fear_greed_error", error=str(e))
            return {"error": str(e)}
    
    async def get_price_sentiment(self, symbol: str) -> Dict[str, Any]:
        """
        Calculate sentiment based on price action and momentum.
        Uses recent price changes to gauge market sentiment.
        """
        try:
            from services.data_collector import get_data_collector
            collector = get_data_collector()
            
            # Get historical data
            historical = await collector.get_historical_data(symbol, "1m")
            
            if not historical or len(historical) < 20:
                return {"error": "Insufficient data"}
            
            closes = [bar.get("close", bar.get("c", 0)) for bar in historical]
            volumes = [bar.get("volume", bar.get("v", 0)) for bar in historical]
            
            current_price = closes[-1]
            
            # Calculate various momentum metrics
            # 7-day return
            if len(closes) >= 7:
                return_7d = ((current_price - closes[-7]) / closes[-7]) * 100
            else:
                return_7d = 0
            
            # 30-day return
            if len(closes) >= 30:
                return_30d = ((current_price - closes[-30]) / closes[-30]) * 100
            else:
                return_30d = 0
            
            # Volume trend (recent vs average)
            avg_volume = sum(volumes) / len(volumes) if volumes else 0
            recent_volume = sum(volumes[-5:]) / 5 if len(volumes) >= 5 else avg_volume
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
            
            # Price vs 20-day SMA
            sma_20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else current_price
            price_vs_sma = ((current_price - sma_20) / sma_20) * 100
            
            # Calculate sentiment score (0-100)
            sentiment_score = 50  # Start neutral
            
            # Adjust based on returns
            if return_7d > 10:
                sentiment_score += 15
            elif return_7d > 5:
                sentiment_score += 10
            elif return_7d > 0:
                sentiment_score += 5
            elif return_7d < -10:
                sentiment_score -= 15
            elif return_7d < -5:
                sentiment_score -= 10
            elif return_7d < 0:
                sentiment_score -= 5
            
            # Adjust based on volume
            if volume_ratio > 1.5:
                sentiment_score += 10 if return_7d > 0 else -10  # High volume confirms trend
            
            # Adjust based on SMA position
            if price_vs_sma > 5:
                sentiment_score += 5
            elif price_vs_sma < -5:
                sentiment_score -= 5
            
            # Clamp to 0-100
            sentiment_score = max(0, min(100, sentiment_score))
            
            # Interpret
            if sentiment_score >= 70:
                signal = "bullish"
                interpretation = "Strong bullish momentum"
            elif sentiment_score >= 55:
                signal = "slightly_bullish"
                interpretation = "Mild bullish sentiment"
            elif sentiment_score >= 45:
                signal = "neutral"
                interpretation = "Neutral price action"
            elif sentiment_score >= 30:
                signal = "slightly_bearish"
                interpretation = "Mild bearish sentiment"
            else:
                signal = "bearish"
                interpretation = "Strong bearish momentum"
            
            return {
                "sentiment_score": sentiment_score,
                "signal": signal,
                "interpretation": interpretation,
                "metrics": {
                    "return_7d": round(return_7d, 2),
                    "return_30d": round(return_30d, 2),
                    "volume_ratio": round(volume_ratio, 2),
                    "price_vs_sma": round(price_vs_sma, 2),
                },
            }
            
        except Exception as e:
            logger.error("price_sentiment_error", symbol=symbol, error=str(e))
            return {"error": str(e)}
    
    async def get_volume_sentiment(self, symbol: str) -> Dict[str, Any]:
        """
        Analyze volume patterns for sentiment signals.
        High volume on up days = bullish, high volume on down days = bearish.
        """
        try:
            from services.data_collector import get_data_collector
            collector = get_data_collector()
            
            historical = await collector.get_historical_data(symbol, "1m")
            
            if not historical or len(historical) < 10:
                return {"error": "Insufficient data"}
            
            # Analyze last 10 days
            recent_data = historical[-10:]
            
            up_volume = 0
            down_volume = 0
            
            for i in range(1, len(recent_data)):
                current_close = recent_data[i].get("close", recent_data[i].get("c", 0))
                prev_close = recent_data[i-1].get("close", recent_data[i-1].get("c", 0))
                volume = recent_data[i].get("volume", recent_data[i].get("v", 0))
                
                if current_close > prev_close:
                    up_volume += volume
                else:
                    down_volume += volume
            
            total_volume = up_volume + down_volume
            
            if total_volume > 0:
                up_ratio = up_volume / total_volume
                down_ratio = down_volume / total_volume
            else:
                up_ratio = down_ratio = 0.5
            
            # Interpret
            if up_ratio > 0.65:
                signal = "accumulation"
                interpretation = "Strong accumulation pattern (buying pressure)"
            elif up_ratio > 0.55:
                signal = "mild_accumulation"
                interpretation = "Mild accumulation (slight buying pressure)"
            elif down_ratio > 0.65:
                signal = "distribution"
                interpretation = "Strong distribution pattern (selling pressure)"
            elif down_ratio > 0.55:
                signal = "mild_distribution"
                interpretation = "Mild distribution (slight selling pressure)"
            else:
                signal = "neutral"
                interpretation = "Balanced volume distribution"
            
            return {
                "signal": signal,
                "interpretation": interpretation,
                "up_volume_ratio": round(up_ratio * 100, 1),
                "down_volume_ratio": round(down_ratio * 100, 1),
            }
            
        except Exception as e:
            logger.error("volume_sentiment_error", symbol=symbol, error=str(e))
            return {"error": str(e)}
    
    def _calculate_overall_sentiment(self, sentiment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall sentiment score from all sources."""
        scores = []
        weights = []
        
        # Fear & Greed (weight: 40%)
        if "fear_greed" in sentiment_data and "value" in sentiment_data["fear_greed"]:
            # Convert to bullish scale (high fear = bullish opportunity)
            fg_value = sentiment_data["fear_greed"]["value"]
            # Invert: low fear/greed value = bullish, high = bearish
            fg_bullish = 100 - fg_value
            scores.append(fg_bullish)
            weights.append(0.4)
        
        # Price sentiment (weight: 60%)
        if "price_sentiment" in sentiment_data and "sentiment_score" in sentiment_data["price_sentiment"]:
            scores.append(sentiment_data["price_sentiment"]["sentiment_score"])
            weights.append(0.6)
        
        if not scores:
            return {"score": 50, "signal": "neutral", "interpretation": "Insufficient data"}
        
        # Weighted average
        total_weight = sum(weights)
        if total_weight > 0:
            overall_score = sum(s * w for s, w in zip(scores, weights)) / total_weight
        else:
            overall_score = 50
        
        # Interpret overall sentiment
        if overall_score >= 70:
            signal = "strong_bullish"
            interpretation = "Strong bullish sentiment across indicators"
        elif overall_score >= 55:
            signal = "bullish"
            interpretation = "Moderately bullish sentiment"
        elif overall_score >= 45:
            signal = "neutral"
            interpretation = "Neutral market sentiment"
        elif overall_score >= 30:
            signal = "bearish"
            interpretation = "Moderately bearish sentiment"
        else:
            signal = "strong_bearish"
            interpretation = "Strong bearish sentiment across indicators"
        
        return {
            "score": round(overall_score, 1),
            "signal": signal,
            "interpretation": interpretation,
        }
    
    def _get_from_cache(self, key: str) -> Optional[Dict]:
        """Get data from cache if not expired."""
        if key in self._cache:
            cached_time, data = self._cache[key]
            if datetime.utcnow() - cached_time < timedelta(hours=self._cache_duration_hours):
                return data
        return None
    
    def _save_to_cache(self, key: str, data: Dict):
        """Save data to cache."""
        self._cache[key] = (datetime.utcnow(), data)


# Singleton instance
_sentiment_analyzer: Optional[SentimentAnalyzer] = None


def get_sentiment_analyzer() -> SentimentAnalyzer:
    """Get or create sentiment analyzer instance."""
    global _sentiment_analyzer
    if _sentiment_analyzer is None:
        _sentiment_analyzer = SentimentAnalyzer()
    return _sentiment_analyzer
