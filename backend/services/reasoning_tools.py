"""
Reasoning Tools Service.
Provides structured reasoning capabilities for trade thesis evaluation,
scenario comparison, and risk/reward analysis.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import structlog
import math

logger = structlog.get_logger()


class ReasoningTools:
    """Provides advanced reasoning and analysis tools for trading decisions."""
    
    def __init__(self, agent_name: str = None):
        """Initialize with optional agent name."""
        self.agent_name = agent_name
    
    async def evaluate_trade_thesis(
        self, 
        symbol: str,
        thesis: str,
        action: str = "buy"
    ) -> Dict[str, Any]:
        """
        Evaluate a trading thesis with structured analysis.
        
        Args:
            symbol: Stock or crypto symbol
            thesis: The trading thesis to evaluate
            action: Proposed action (buy/sell)
        
        Returns:
            Structured evaluation with pros, cons, and conviction score
        """
        try:
            from services.data_collector import get_data_collector
            from services.advanced_indicators import get_advanced_indicators
            from services.sentiment_analyzer import get_sentiment_analyzer
            
            collector = get_data_collector()
            indicators = get_advanced_indicators()
            sentiment = get_sentiment_analyzer()
            
            symbol = symbol.upper()
            
            # Gather supporting data
            advanced_data = await indicators.get_all_advanced_indicators(symbol, include_multi_timeframe=True)
            sentiment_data = await sentiment.get_comprehensive_sentiment(symbol)
            
            pros = []
            cons = []
            
            # Analyze technical alignment
            if "signals" in advanced_data:
                signal = advanced_data["signals"].get("signal", "neutral")
                confidence = advanced_data["signals"].get("confidence", 50)
                
                if action == "buy":
                    if signal in ["buy", "strong_buy"]:
                        pros.append(f"Technical signals support buying ({confidence:.0f}% confidence)")
                    elif signal in ["sell", "strong_sell"]:
                        cons.append(f"Technical signals oppose buying ({confidence:.0f}% bearish)")
                else:
                    if signal in ["sell", "strong_sell"]:
                        pros.append(f"Technical signals support selling ({confidence:.0f}% confidence)")
                    elif signal in ["buy", "strong_buy"]:
                        cons.append(f"Technical signals oppose selling ({confidence:.0f}% bullish)")
            
            # Analyze trend
            if "trend_analysis" in advanced_data:
                trend = advanced_data["trend_analysis"].get("trend", "sideways")
                if action == "buy" and "uptrend" in trend:
                    pros.append(f"Price in {trend} - favorable for buying")
                elif action == "buy" and "downtrend" in trend:
                    cons.append(f"Price in {trend} - buying against trend")
                elif action == "sell" and "downtrend" in trend:
                    pros.append(f"Price in {trend} - favorable for selling")
            
            # Analyze sentiment
            if sentiment_data and "overall_sentiment" in sentiment_data:
                sent_score = sentiment_data.get("overall_sentiment", {}).get("score", 50)
                if action == "buy" and sent_score < 30:
                    cons.append(f"Market sentiment is very fearful ({sent_score})")
                elif action == "buy" and sent_score > 70:
                    cons.append(f"Market sentiment may be overextended ({sent_score})")
                elif action == "buy" and 40 <= sent_score <= 60:
                    pros.append("Market sentiment is neutral - good entry potential")
            
            # Check volatility
            if "atr" in advanced_data:
                vol = advanced_data["atr"].get("volatility", "moderate")
                if vol in ["high", "extreme"]:
                    cons.append(f"Volatility is {vol} - increased risk")
                elif vol == "low":
                    pros.append("Volatility is low - stable price action")
            
            # Multi-timeframe alignment
            if "multi_timeframe" in advanced_data:
                mtf = advanced_data["multi_timeframe"]
                alignment = mtf.get("alignment", "neutral")
                strength = mtf.get("alignment_strength", 0)
                
                if action == "buy" and alignment == "bullish" and strength > 60:
                    pros.append(f"Multi-timeframe alignment supports buying ({strength:.0f}%)")
                elif action == "sell" and alignment == "bearish" and strength > 60:
                    pros.append(f"Multi-timeframe alignment supports selling ({strength:.0f}%)")
                elif alignment != ("bullish" if action == "buy" else "bearish"):
                    cons.append(f"Multi-timeframe alignment is {alignment}")
            
            # Calculate conviction score
            base_score = 50
            pro_weight = len(pros) * 10
            con_weight = len(cons) * 10
            
            conviction_score = base_score + pro_weight - con_weight
            conviction_score = max(0, min(100, conviction_score))
            
            # Decision recommendation
            if conviction_score >= 70:
                recommendation = "STRONG" + (" BUY" if action == "buy" else " SELL")
            elif conviction_score >= 55:
                recommendation = "MODERATE" + (" BUY" if action == "buy" else " SELL")
            elif conviction_score >= 45:
                recommendation = "WEAK" + (" BUY" if action == "buy" else " SELL")
            else:
                recommendation = "DO NOT " + action.upper()
            
            return {
                "symbol": symbol,
                "thesis": thesis[:200],
                "action_proposed": action,
                "pros": pros,
                "cons": cons,
                "conviction_score": round(conviction_score, 1),
                "recommendation": recommendation,
                "pro_count": len(pros),
                "con_count": len(cons),
                "interpretation": f"{recommendation} ({conviction_score:.0f}/100 conviction)"
            }
            
        except Exception as e:
            logger.error("evaluate_trade_thesis_error", error=str(e))
            return {"error": str(e)}
    
    async def compare_scenarios(self, symbol: str) -> Dict[str, Any]:
        """
        Compare bull, bear, and neutral scenarios for a symbol.
        
        Returns:
            Scenario probabilities and target prices
        """
        try:
            from services.data_collector import get_data_collector
            from services.advanced_indicators import get_advanced_indicators
            
            collector = get_data_collector()
            indicators = get_advanced_indicators()
            
            symbol = symbol.upper()
            
            # Get current data
            price_data = await collector.get_current_price(symbol)
            advanced_data = await indicators.get_all_advanced_indicators(symbol)
            support_resistance = await indicators.get_support_resistance_levels(symbol)
            
            current_price = price_data.get("price", 0)
            
            if not current_price:
                return {"error": "Could not get current price"}
            
            # Get support/resistance for targets
            nearest_resistance = support_resistance.get("nearest_resistance", {})
            nearest_support = support_resistance.get("nearest_support", {})
            
            resistance_price = nearest_resistance.get("price", current_price * 1.1) if nearest_resistance else current_price * 1.1
            support_price = nearest_support.get("price", current_price * 0.9) if nearest_support else current_price * 0.9
            
            # Calculate ATR for realistic moves
            atr = 0
            if "atr" in advanced_data:
                atr = advanced_data["atr"].get("atr", 0)
            
            # Bull scenario
            bull_target = resistance_price if resistance_price > current_price else current_price * 1.15
            bull_upside = ((bull_target - current_price) / current_price) * 100
            
            # Bear scenario  
            bear_target = support_price if support_price < current_price else current_price * 0.85
            bear_downside = ((current_price - bear_target) / current_price) * 100
            
            # Neutral scenario
            neutral_range_low = current_price * 0.97
            neutral_range_high = current_price * 1.03
            
            # Estimate probabilities based on technical signals
            bull_prob = 33
            bear_prob = 33
            neutral_prob = 34
            
            if "signals" in advanced_data:
                signal = advanced_data["signals"].get("signal", "neutral")
                confidence = advanced_data["signals"].get("confidence", 50)
                
                if signal in ["buy", "strong_buy"]:
                    bull_prob = 40 + (confidence - 50) / 2
                    bear_prob = 30 - (confidence - 50) / 3
                    neutral_prob = 100 - bull_prob - bear_prob
                elif signal in ["sell", "strong_sell"]:
                    bear_prob = 40 + (confidence - 50) / 2
                    bull_prob = 30 - (confidence - 50) / 3
                    neutral_prob = 100 - bull_prob - bear_prob
            
            # Normalize probabilities
            total = bull_prob + bear_prob + neutral_prob
            bull_prob = round(bull_prob / total * 100, 1)
            bear_prob = round(bear_prob / total * 100, 1)
            neutral_prob = round(100 - bull_prob - bear_prob, 1)
            
            scenarios = {
                "bull": {
                    "probability": bull_prob,
                    "target_price": round(bull_target, 2),
                    "potential_return": round(bull_upside, 1),
                    "description": f"Price rallies to resistance at ${bull_target:.2f}"
                },
                "bear": {
                    "probability": bear_prob,
                    "target_price": round(bear_target, 2),
                    "potential_loss": round(bear_downside, 1),
                    "description": f"Price drops to support at ${bear_target:.2f}"
                },
                "neutral": {
                    "probability": neutral_prob,
                    "range_low": round(neutral_range_low, 2),
                    "range_high": round(neutral_range_high, 2),
                    "description": f"Price consolidates between ${neutral_range_low:.2f}-${neutral_range_high:.2f}"
                }
            }
            
            # Most likely scenario
            most_likely = max(scenarios.items(), key=lambda x: x[1]["probability"])
            
            return {
                "symbol": symbol,
                "current_price": current_price,
                "scenarios": scenarios,
                "most_likely_scenario": most_likely[0],
                "risk_reward_ratio": round(bull_upside / bear_downside, 2) if bear_downside > 0 else 0,
                "interpretation": f"Most likely: {most_likely[0]} scenario ({most_likely[1]['probability']}%)"
            }
            
        except Exception as e:
            logger.error("compare_scenarios_error", error=str(e))
            return {"error": str(e)}
    
    async def get_risk_reward_analysis(self, symbol: str, entry_price: float = None) -> Dict[str, Any]:
        """
        Calculate detailed risk/reward analysis for a trade.
        
        Returns:
            Optimal stop loss, take profit levels, R:R ratio
        """
        try:
            from services.data_collector import get_data_collector
            from services.advanced_indicators import get_advanced_indicators
            
            collector = get_data_collector()
            indicators = get_advanced_indicators()
            
            symbol = symbol.upper()
            
            # Get current data
            if entry_price is None:
                price_data = await collector.get_current_price(symbol)
                entry_price = price_data.get("price", 0)
            
            if not entry_price:
                return {"error": "Could not determine entry price"}
            
            advanced_data = await indicators.get_all_advanced_indicators(symbol)
            support_resistance = await indicators.get_support_resistance_levels(symbol)
            
            # Get ATR for stop calculation
            atr = 0
            if "atr" in advanced_data:
                atr = advanced_data["atr"].get("atr", entry_price * 0.02)
            
            # Calculate stop loss levels
            stop_1atr = entry_price - atr
            stop_2atr = entry_price - (2 * atr)
            stop_percent = (atr / entry_price) * 100
            
            # Get nearest support for contextual stop
            nearest_support = support_resistance.get("nearest_support", {})
            support_stop = nearest_support.get("price", stop_2atr) if nearest_support else stop_2atr
            
            # Calculate take profit levels (R multiples)
            risk_amount = entry_price - stop_2atr
            
            tp_1r = entry_price + risk_amount
            tp_2r = entry_price + (2 * risk_amount)
            tp_3r = entry_price + (3 * risk_amount)
            
            # Get nearest resistance for contextual target
            nearest_resistance = support_resistance.get("nearest_resistance", {})
            resistance_target = nearest_resistance.get("price", tp_2r) if nearest_resistance else tp_2r
            
            # Calculate actual R:R based on resistance
            potential_profit = resistance_target - entry_price
            potential_loss = entry_price - stop_2atr
            risk_reward_ratio = potential_profit / potential_loss if potential_loss > 0 else 0
            
            # Trade quality assessment
            if risk_reward_ratio >= 3:
                trade_quality = "EXCELLENT"
            elif risk_reward_ratio >= 2:
                trade_quality = "GOOD"
            elif risk_reward_ratio >= 1.5:
                trade_quality = "ACCEPTABLE"
            else:
                trade_quality = "POOR"
            
            return {
                "symbol": symbol,
                "entry_price": round(entry_price, 2),
                "stop_loss": {
                    "tight_1atr": round(stop_1atr, 2),
                    "standard_2atr": round(stop_2atr, 2),
                    "support_based": round(support_stop, 2),
                    "recommended": round(max(stop_2atr, support_stop * 0.995), 2),
                },
                "take_profit": {
                    "tp_1r": round(tp_1r, 2),
                    "tp_2r": round(tp_2r, 2),
                    "tp_3r": round(tp_3r, 2),
                    "resistance_based": round(resistance_target, 2),
                },
                "atr": round(atr, 2),
                "atr_percent": round(stop_percent, 2),
                "risk_reward_ratio": round(risk_reward_ratio, 2),
                "trade_quality": trade_quality,
                "potential_profit_percent": round((potential_profit / entry_price) * 100, 2),
                "potential_loss_percent": round((potential_loss / entry_price) * 100, 2),
                "interpretation": f"{trade_quality} trade setup with {risk_reward_ratio:.1f}:1 R:R ratio"
            }
            
        except Exception as e:
            logger.error("get_risk_reward_analysis_error", error=str(e))
            return {"error": str(e)}
    
    async def detect_market_anomaly(self, symbol: str) -> Dict[str, Any]:
        """
        Detect unusual market activity or anomalies.
        
        Returns:
            Volume spikes, price gaps, unusual patterns
        """
        try:
            from services.data_collector import get_data_collector
            
            collector = get_data_collector()
            symbol = symbol.upper()
            
            # Get historical data
            historical = await collector.get_historical_data(symbol, "1m")
            
            if not historical or len(historical) < 20:
                return {"error": "Insufficient historical data"}
            
            closes = [bar.get("close", bar.get("c", 0)) for bar in historical]
            volumes = [bar.get("volume", bar.get("v", 0)) for bar in historical]
            highs = [bar.get("high", bar.get("h", 0)) for bar in historical]
            lows = [bar.get("low", bar.get("l", 0)) for bar in historical]
            
            anomalies = []
            
            # Volume spike detection
            avg_volume = sum(volumes[-20:-1]) / 19 if len(volumes) > 20 else sum(volumes) / len(volumes)
            current_volume = volumes[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
            
            if volume_ratio > 2.5:
                anomalies.append({
                    "type": "volume_spike",
                    "severity": "high" if volume_ratio > 4 else "medium",
                    "description": f"Volume is {volume_ratio:.1f}x average - unusual activity",
                    "value": round(volume_ratio, 2)
                })
            
            # Price gap detection
            if len(closes) >= 2:
                gap_percent = ((highs[-1] - closes[-2]) / closes[-2]) * 100 if closes[-2] != 0 else 0
                if abs(gap_percent) > 2:
                    anomalies.append({
                        "type": "price_gap",
                        "severity": "high" if abs(gap_percent) > 5 else "medium",
                        "description": f"Price gapped {'up' if gap_percent > 0 else 'down'} {abs(gap_percent):.1f}%",
                        "value": round(gap_percent, 2)
                    })
            
            # Unusual daily range
            current_range = (highs[-1] - lows[-1]) / closes[-1] * 100 if closes[-1] > 0 else 0
            avg_range = sum((highs[i] - lows[i]) / closes[i] * 100 for i in range(-20, -1)) / 19 if len(closes) > 20 else current_range
            range_ratio = current_range / avg_range if avg_range > 0 else 1
            
            if range_ratio > 2:
                anomalies.append({
                    "type": "unusual_range",
                    "severity": "high" if range_ratio > 3 else "medium",
                    "description": f"Daily range is {range_ratio:.1f}x normal - high volatility",
                    "value": round(range_ratio, 2)
                })
            
            # Price acceleration detection
            if len(closes) >= 5:
                recent_change = ((closes[-1] - closes[-5]) / closes[-5]) * 100 if closes[-5] != 0 else 0
                if abs(recent_change) > 10:
                    anomalies.append({
                        "type": "price_acceleration",
                        "severity": "high" if abs(recent_change) > 15 else "medium",
                        "description": f"Price moved {recent_change:.1f}% in 5 days - momentum event",
                        "value": round(recent_change, 2)
                    })
            
            # Overall anomaly score
            anomaly_score = len(anomalies) * 25
            for a in anomalies:
                if a["severity"] == "high":
                    anomaly_score += 15
            
            anomaly_score = min(100, anomaly_score)
            
            return {
                "symbol": symbol,
                "current_price": closes[-1],
                "anomalies": anomalies,
                "anomaly_count": len(anomalies),
                "anomaly_score": anomaly_score,
                "requires_attention": anomaly_score > 50,
                "volume_ratio": round(volume_ratio, 2),
                "interpretation": f"{'⚠️ ATTENTION REQUIRED' if anomaly_score > 50 else 'Normal'} - {len(anomalies)} anomalies detected"
            }
            
        except Exception as e:
            logger.error("detect_market_anomaly_error", error=str(e))
            return {"error": str(e)}


# Singleton instance
_reasoning_tools: Optional[ReasoningTools] = None


def get_reasoning_tools(agent_name: str = None) -> ReasoningTools:
    """Get or create reasoning tools instance."""
    global _reasoning_tools
    if _reasoning_tools is None or agent_name:
        _reasoning_tools = ReasoningTools(agent_name)
    return _reasoning_tools
