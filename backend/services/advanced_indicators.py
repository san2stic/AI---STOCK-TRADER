"""
Advanced Technical Indicators Service.
Provides sophisticated indicators beyond basic RSI/MACD for better AI decision-making.
All calculations use free data - no additional APIs required.
"""
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import structlog
import math

logger = structlog.get_logger()


class AdvancedIndicators:
    """Calculate advanced technical indicators for trading signals."""
    
    def __init__(self, data_collector=None):
        """Initialize with optional data collector for fetching historical data."""
        self._data_collector = data_collector
    
    @property
    def data_collector(self):
        """Lazy load data collector to avoid circular imports."""
        if self._data_collector is None:
            from services.data_collector import get_data_collector
            self._data_collector = get_data_collector()
        return self._data_collector
    
    async def get_all_advanced_indicators(
        self, 
        symbol: str,
        include_multi_timeframe: bool = True
    ) -> Dict[str, Any]:
        """
        Get all advanced indicators for a symbol.
        
        Returns comprehensive analysis including:
        - Fibonacci retracements
        - ADX (trend strength)
        - Stochastic oscillator
        - ATR (volatility)
        - VWAP
        - Multi-timeframe analysis (optional)
        """
        try:
            # Get historical data (3 months for good Fibonacci levels)
            historical = await self.data_collector.get_historical_data(symbol, "3m")
            
            if not historical or len(historical) < 20:
                return {"error": "Insufficient historical data"}
            
            # Extract OHLCV data
            closes = [bar.get("close", bar.get("c", 0)) for bar in historical]
            highs = [bar.get("high", bar.get("h", 0)) for bar in historical]
            lows = [bar.get("low", bar.get("l", 0)) for bar in historical]
            volumes = [bar.get("volume", bar.get("v", 0)) for bar in historical]
            
            result = {
                "symbol": symbol,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            # Calculate all indicators
            result["fibonacci"] = self.calculate_fibonacci_retracements(highs, lows, closes)
            result["adx"] = self.calculate_adx(highs, lows, closes)
            result["stochastic"] = self.calculate_stochastic(highs, lows, closes)
            result["atr"] = self.calculate_atr(highs, lows, closes)
            result["vwap"] = self.calculate_vwap(highs, lows, closes, volumes)
            result["volume_profile"] = self.calculate_volume_profile(closes, volumes)
            result["trend_analysis"] = self.analyze_trend(closes, result["adx"])
            
            # Multi-timeframe analysis
            if include_multi_timeframe:
                result["multi_timeframe"] = await self._analyze_multi_timeframe(symbol)
            
            # Generate trading signals
            result["signals"] = self._generate_signals(result)
            
            return result
            
        except Exception as e:
            logger.error("advanced_indicators_error", symbol=symbol, error=str(e))
            return {"error": str(e)}
    
    def calculate_fibonacci_retracements(
        self, 
        highs: List[float], 
        lows: List[float],
        closes: List[float]
    ) -> Dict[str, Any]:
        """
        Calculate Fibonacci retracement levels.
        Key levels: 0%, 23.6%, 38.2%, 50%, 61.8%, 78.6%, 100%
        """
        if len(highs) < 5:
            return {"error": "Insufficient data"}
        
        # Find swing high and swing low
        period_high = max(highs[-60:]) if len(highs) >= 60 else max(highs)
        period_low = min(lows[-60:]) if len(lows) >= 60 else min(lows)
        current_price = closes[-1]
        
        # Determine trend direction
        is_uptrend = closes[-1] > closes[-20] if len(closes) >= 20 else True
        
        diff = period_high - period_low
        
        # Fibonacci levels
        fib_levels = {
            "0.0": period_high if is_uptrend else period_low,
            "0.236": period_high - (diff * 0.236) if is_uptrend else period_low + (diff * 0.236),
            "0.382": period_high - (diff * 0.382) if is_uptrend else period_low + (diff * 0.382),
            "0.5": period_high - (diff * 0.5) if is_uptrend else period_low + (diff * 0.5),
            "0.618": period_high - (diff * 0.618) if is_uptrend else period_low + (diff * 0.618),
            "0.786": period_high - (diff * 0.786) if is_uptrend else period_low + (diff * 0.786),
            "1.0": period_low if is_uptrend else period_high,
        }
        
        # Find nearest support and resistance
        nearest_support = None
        nearest_resistance = None
        
        for level, price in sorted(fib_levels.items(), key=lambda x: x[1]):
            if price < current_price and (nearest_support is None or price > nearest_support["price"]):
                nearest_support = {"level": level, "price": price}
            elif price > current_price and nearest_resistance is None:
                nearest_resistance = {"level": level, "price": price}
        
        return {
            "levels": fib_levels,
            "period_high": period_high,
            "period_low": period_low,
            "current_price": current_price,
            "trend_direction": "uptrend" if is_uptrend else "downtrend",
            "nearest_support": nearest_support,
            "nearest_resistance": nearest_resistance,
        }
    
    def calculate_adx(
        self, 
        highs: List[float], 
        lows: List[float], 
        closes: List[float],
        period: int = 14
    ) -> Dict[str, Any]:
        """
        Calculate Average Directional Index (ADX).
        
        ADX measures trend strength:
        - 0-25: Weak/No trend
        - 25-50: Strong trend  
        - 50-75: Very strong trend
        - 75-100: Extremely strong trend
        """
        if len(closes) < period + 1:
            return {"error": "Insufficient data"}
        
        # Calculate True Range and Directional Movement
        tr_list = []
        plus_dm_list = []
        minus_dm_list = []
        
        for i in range(1, len(closes)):
            high_diff = highs[i] - highs[i-1]
            low_diff = lows[i-1] - lows[i]
            
            # True Range
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            tr_list.append(tr)
            
            # Directional Movement
            plus_dm = high_diff if high_diff > low_diff and high_diff > 0 else 0
            minus_dm = low_diff if low_diff > high_diff and low_diff > 0 else 0
            
            plus_dm_list.append(plus_dm)
            minus_dm_list.append(minus_dm)
        
        # Smooth the values using Wilder's smoothing
        def wilder_smooth(values: List[float], period: int) -> List[float]:
            smoothed = [sum(values[:period])]
            for i in range(period, len(values)):
                smoothed.append(smoothed[-1] - (smoothed[-1] / period) + values[i])
            return smoothed
        
        atr = wilder_smooth(tr_list, period)
        plus_di_smooth = wilder_smooth(plus_dm_list, period)
        minus_di_smooth = wilder_smooth(minus_dm_list, period)
        
        # Calculate +DI and -DI
        plus_di = [(100 * plus_di_smooth[i] / atr[i]) if atr[i] > 0 else 0 
                   for i in range(len(atr))]
        minus_di = [(100 * minus_di_smooth[i] / atr[i]) if atr[i] > 0 else 0 
                    for i in range(len(atr))]
        
        # Calculate DX
        dx = []
        for i in range(len(plus_di)):
            di_sum = plus_di[i] + minus_di[i]
            if di_sum > 0:
                dx.append(100 * abs(plus_di[i] - minus_di[i]) / di_sum)
            else:
                dx.append(0)
        
        # Calculate ADX
        adx = wilder_smooth(dx, period) if len(dx) >= period else dx
        current_adx = adx[-1] if adx else 0
        
        # Interpret trend strength
        if current_adx < 25:
            trend_strength = "weak"
        elif current_adx < 50:
            trend_strength = "strong"
        elif current_adx < 75:
            trend_strength = "very_strong"
        else:
            trend_strength = "extreme"
        
        # Determine trend direction
        current_plus_di = plus_di[-1] if plus_di else 0
        current_minus_di = minus_di[-1] if minus_di else 0
        trend_direction = "bullish" if current_plus_di > current_minus_di else "bearish"
        
        return {
            "adx": round(current_adx, 2),
            "plus_di": round(current_plus_di, 2),
            "minus_di": round(current_minus_di, 2),
            "trend_strength": trend_strength,
            "trend_direction": trend_direction,
            "interpretation": f"{trend_strength.replace('_', ' ').title()} {trend_direction} trend (ADX: {current_adx:.1f})"
        }
    
    def calculate_stochastic(
        self, 
        highs: List[float], 
        lows: List[float], 
        closes: List[float],
        k_period: int = 14,
        d_period: int = 3
    ) -> Dict[str, Any]:
        """
        Calculate Stochastic Oscillator (%K and %D).
        
        Signals:
        - Overbought: %K > 80
        - Oversold: %K < 20
        - Bullish crossover: %K crosses above %D
        - Bearish crossover: %K crosses below %D
        """
        if len(closes) < k_period:
            return {"error": "Insufficient data"}
        
        k_values = []
        
        for i in range(k_period - 1, len(closes)):
            period_highs = highs[i - k_period + 1:i + 1]
            period_lows = lows[i - k_period + 1:i + 1]
            
            highest_high = max(period_highs)
            lowest_low = min(period_lows)
            
            if highest_high != lowest_low:
                k = 100 * (closes[i] - lowest_low) / (highest_high - lowest_low)
            else:
                k = 50  # Neutral
            
            k_values.append(k)
        
        # Calculate %D (SMA of %K)
        d_values = []
        for i in range(d_period - 1, len(k_values)):
            d = sum(k_values[i - d_period + 1:i + 1]) / d_period
            d_values.append(d)
        
        current_k = k_values[-1] if k_values else 50
        current_d = d_values[-1] if d_values else 50
        prev_k = k_values[-2] if len(k_values) >= 2 else current_k
        prev_d = d_values[-2] if len(d_values) >= 2 else current_d
        
        # Determine signal
        if current_k > 80:
            zone = "overbought"
        elif current_k < 20:
            zone = "oversold"
        else:
            zone = "neutral"
        
        # Check for crossovers
        crossover = None
        if prev_k <= prev_d and current_k > current_d:
            crossover = "bullish"
        elif prev_k >= prev_d and current_k < current_d:
            crossover = "bearish"
        
        return {
            "k": round(current_k, 2),
            "d": round(current_d, 2),
            "zone": zone,
            "crossover": crossover,
            "interpretation": f"Stochastic {zone.upper()}" + (f" with {crossover} crossover" if crossover else "")
        }
    
    def calculate_atr(
        self, 
        highs: List[float], 
        lows: List[float], 
        closes: List[float],
        period: int = 14
    ) -> Dict[str, Any]:
        """
        Calculate Average True Range (ATR).
        Used for volatility measurement and position sizing.
        """
        if len(closes) < period + 1:
            return {"error": "Insufficient data"}
        
        tr_list = []
        
        for i in range(1, len(closes)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            tr_list.append(tr)
        
        # Initial ATR is SMA of first N true ranges
        atr = sum(tr_list[:period]) / period
        
        # Subsequent ATR uses exponential smoothing
        for i in range(period, len(tr_list)):
            atr = ((atr * (period - 1)) + tr_list[i]) / period
        
        current_price = closes[-1]
        atr_percent = (atr / current_price) * 100 if current_price > 0 else 0
        
        # Volatility interpretation
        if atr_percent < 2:
            volatility = "low"
        elif atr_percent < 5:
            volatility = "moderate"
        elif atr_percent < 10:
            volatility = "high"
        else:
            volatility = "extreme"
        
        # Position sizing suggestion (risk 2% of capital)
        # If you risk 2% and want to place stop at 2x ATR, position size = capital * 0.02 / (2 * ATR)
        suggested_stop_distance = atr * 2
        
        return {
            "atr": round(atr, 4),
            "atr_percent": round(atr_percent, 2),
            "volatility": volatility,
            "suggested_stop_distance": round(suggested_stop_distance, 4),
            "period": period,
            "interpretation": f"{volatility.title()} volatility (ATR: {atr_percent:.1f}% of price)"
        }
    
    def calculate_vwap(
        self, 
        highs: List[float], 
        lows: List[float], 
        closes: List[float],
        volumes: List[float]
    ) -> Dict[str, Any]:
        """
        Calculate Volume Weighted Average Price (VWAP).
        Key institutional level - price above VWAP is bullish, below is bearish.
        """
        if len(closes) < 1 or len(volumes) < 1:
            return {"error": "Insufficient data"}
        
        # Typical price
        typical_prices = [(highs[i] + lows[i] + closes[i]) / 3 for i in range(len(closes))]
        
        # VWAP calculation
        cumulative_tpv = 0  # Typical Price * Volume
        cumulative_volume = 0
        
        for i in range(len(typical_prices)):
            cumulative_tpv += typical_prices[i] * volumes[i]
            cumulative_volume += volumes[i]
        
        vwap = cumulative_tpv / cumulative_volume if cumulative_volume > 0 else 0
        current_price = closes[-1]
        
        # Position relative to VWAP
        distance_percent = ((current_price - vwap) / vwap) * 100 if vwap > 0 else 0
        
        if current_price > vwap:
            position = "above"
            bias = "bullish"
        else:
            position = "below"
            bias = "bearish"
        
        return {
            "vwap": round(vwap, 4),
            "current_price": current_price,
            "position": position,
            "distance_percent": round(distance_percent, 2),
            "bias": bias,
            "interpretation": f"Price {position} VWAP ({bias} bias, {abs(distance_percent):.1f}% away)"
        }
    
    def calculate_volume_profile(
        self, 
        closes: List[float], 
        volumes: List[float],
        num_bins: int = 10
    ) -> Dict[str, Any]:
        """
        Calculate Volume Profile - shows price levels with highest trading activity.
        Point of Control (POC) is the price with highest volume - major support/resistance.
        """
        if len(closes) < 5:
            return {"error": "Insufficient data"}
        
        price_min = min(closes)
        price_max = max(closes)
        price_range = price_max - price_min
        
        if price_range == 0:
            return {"error": "No price variation"}
        
        bin_size = price_range / num_bins
        
        # Create volume bins
        bins = {}
        for i in range(num_bins):
            bin_low = price_min + (i * bin_size)
            bin_high = bin_low + bin_size
            bin_mid = (bin_low + bin_high) / 2
            bins[round(bin_mid, 4)] = 0
        
        # Assign volume to bins
        for i in range(len(closes)):
            for bin_mid in bins.keys():
                bin_low = bin_mid - (bin_size / 2)
                bin_high = bin_mid + (bin_size / 2)
                if bin_low <= closes[i] < bin_high:
                    bins[bin_mid] += volumes[i]
                    break
        
        # Find Point of Control (highest volume node)
        poc_price = max(bins, key=bins.get)
        poc_volume = bins[poc_price]
        
        # Find high volume nodes (support/resistance)
        total_volume = sum(bins.values())
        high_volume_nodes = [
            {"price": price, "volume": vol, "volume_percent": (vol / total_volume * 100) if total_volume > 0 else 0}
            for price, vol in sorted(bins.items(), key=lambda x: x[1], reverse=True)[:3]
        ]
        
        current_price = closes[-1]
        
        return {
            "point_of_control": poc_price,
            "poc_volume": poc_volume,
            "high_volume_nodes": high_volume_nodes,
            "current_price": current_price,
            "price_vs_poc": "above" if current_price > poc_price else "below",
            "interpretation": f"POC at {poc_price:.2f} - Major {'support' if current_price > poc_price else 'resistance'}"
        }
    
    def analyze_trend(self, closes: List[float], adx_result: Dict) -> Dict[str, Any]:
        """Comprehensive trend analysis combining multiple indicators."""
        if len(closes) < 50:
            return {"error": "Insufficient data for trend analysis"}
        
        # Moving averages
        sma_20 = sum(closes[-20:]) / 20
        sma_50 = sum(closes[-50:]) / 50
        
        current_price = closes[-1]
        
        # Price position relative to MAs
        above_sma20 = current_price > sma_20
        above_sma50 = current_price > sma_50
        ma_alignment = sma_20 > sma_50  # Golden cross vs death cross
        
        # Determine overall trend
        if above_sma20 and above_sma50 and ma_alignment:
            trend = "strong_uptrend"
        elif above_sma20 and above_sma50:
            trend = "uptrend"
        elif not above_sma20 and not above_sma50 and not ma_alignment:
            trend = "strong_downtrend"
        elif not above_sma20 and not above_sma50:
            trend = "downtrend"
        else:
            trend = "sideways"
        
        # Combine with ADX for confidence
        adx_value = adx_result.get("adx", 0) if isinstance(adx_result, dict) else 0
        
        if adx_value > 25:
            confidence = "high"
        elif adx_value > 15:
            confidence = "medium"
        else:
            confidence = "low"
        
        return {
            "trend": trend,
            "confidence": confidence,
            "sma_20": round(sma_20, 4),
            "sma_50": round(sma_50, 4),
            "above_sma20": above_sma20,
            "above_sma50": above_sma50,
            "ma_alignment": "bullish" if ma_alignment else "bearish",
            "interpretation": f"{trend.replace('_', ' ').title()} with {confidence} confidence"
        }
    
    async def _analyze_multi_timeframe(self, symbol: str) -> Dict[str, Any]:
        """
        Analyze symbol across multiple timeframes.
        Returns alignment score for stronger signals.
        """
        timeframes = ["1d", "1w", "1m"]
        analyses = {}
        bullish_count = 0
        bearish_count = 0
        
        for tf in timeframes:
            try:
                historical = await self.data_collector.get_historical_data(symbol, tf)
                
                if historical and len(historical) >= 20:
                    closes = [bar.get("close", bar.get("c", 0)) for bar in historical]
                    
                    # Simple trend check
                    sma_short = sum(closes[-10:]) / 10
                    sma_long = sum(closes[-20:]) / 20
                    current = closes[-1]
                    
                    if current > sma_short > sma_long:
                        trend = "bullish"
                        bullish_count += 1
                    elif current < sma_short < sma_long:
                        trend = "bearish"
                        bearish_count += 1
                    else:
                        trend = "neutral"
                    
                    analyses[tf] = {
                        "trend": trend,
                        "price": current,
                        "sma_short": round(sma_short, 4),
                        "sma_long": round(sma_long, 4),
                    }
            except Exception as e:
                logger.error("multi_timeframe_error", symbol=symbol, timeframe=tf, error=str(e))
                analyses[tf] = {"error": str(e)}
        
        # Calculate alignment
        total = bullish_count + bearish_count
        if total > 0:
            alignment = "bullish" if bullish_count > bearish_count else "bearish"
            alignment_strength = max(bullish_count, bearish_count) / len(timeframes) * 100
        else:
            alignment = "neutral"
            alignment_strength = 0
        
        return {
            "timeframes": analyses,
            "alignment": alignment,
            "alignment_strength": round(alignment_strength, 1),
            "bullish_count": bullish_count,
            "bearish_count": bearish_count,
            "interpretation": f"{alignment.title()} alignment across {max(bullish_count, bearish_count)}/{len(timeframes)} timeframes"
        }
    
    def _generate_signals(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate trading signals based on all indicators.
        Returns overall bias and confidence score.
        """
        bullish_signals = 0
        bearish_signals = 0
        total_signals = 0
        
        # Check each indicator
        if "adx" in analysis and isinstance(analysis["adx"], dict):
            total_signals += 1
            if analysis["adx"].get("trend_direction") == "bullish":
                bullish_signals += 1
            else:
                bearish_signals += 1
        
        if "stochastic" in analysis and isinstance(analysis["stochastic"], dict):
            total_signals += 1
            zone = analysis["stochastic"].get("zone")
            crossover = analysis["stochastic"].get("crossover")
            if zone == "oversold" or crossover == "bullish":
                bullish_signals += 1
            elif zone == "overbought" or crossover == "bearish":
                bearish_signals += 1
        
        if "vwap" in analysis and isinstance(analysis["vwap"], dict):
            total_signals += 1
            if analysis["vwap"].get("bias") == "bullish":
                bullish_signals += 1
            else:
                bearish_signals += 1
        
        if "trend_analysis" in analysis and isinstance(analysis["trend_analysis"], dict):
            total_signals += 1
            trend = analysis["trend_analysis"].get("trend", "")
            if "uptrend" in trend:
                bullish_signals += 1
            elif "downtrend" in trend:
                bearish_signals += 1
        
        if "multi_timeframe" in analysis and isinstance(analysis["multi_timeframe"], dict):
            total_signals += 1
            if analysis["multi_timeframe"].get("alignment") == "bullish":
                bullish_signals += 1
            elif analysis["multi_timeframe"].get("alignment") == "bearish":
                bearish_signals += 1
        
        # Calculate overall signal
        if total_signals == 0:
            return {"signal": "neutral", "confidence": 0, "bullish": 0, "bearish": 0}
        
        bullish_pct = (bullish_signals / total_signals) * 100
        bearish_pct = (bearish_signals / total_signals) * 100
        
        if bullish_pct >= 70:
            signal = "strong_buy"
        elif bullish_pct >= 50:
            signal = "buy"
        elif bearish_pct >= 70:
            signal = "strong_sell"
        elif bearish_pct >= 50:
            signal = "sell"
        else:
            signal = "neutral"
        
        confidence = max(bullish_pct, bearish_pct)
        
        return {
            "signal": signal,
            "confidence": round(confidence, 1),
            "bullish_signals": bullish_signals,
            "bearish_signals": bearish_signals,
            "total_signals": total_signals,
            "interpretation": f"{signal.replace('_', ' ').upper()} signal with {confidence:.0f}% confidence"
        }


# Singleton instance
_advanced_indicators: AdvancedIndicators = None


def get_advanced_indicators() -> AdvancedIndicators:
    """Get or create advanced indicators instance."""
    global _advanced_indicators
    if _advanced_indicators is None:
        _advanced_indicators = AdvancedIndicators()
    return _advanced_indicators
