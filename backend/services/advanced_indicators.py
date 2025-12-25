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


    # ========== NEW PHASE 1 METHODS ==========
    
    async def get_support_resistance_levels(self, symbol: str, lookback_days: int = 60) -> Dict[str, Any]:
        """
        Detect key support and resistance levels automatically.
        Uses pivot points, price clusters, and volume profile.
        """
        try:
            historical = await self.data_collector.get_historical_data(symbol, "3m")
            
            if not historical or len(historical) < 20:
                return {"error": "Insufficient historical data"}
            
            # Limit to lookback period
            data = historical[-lookback_days:] if len(historical) >= lookback_days else historical
            
            closes = [bar.get("close", bar.get("c", 0)) for bar in data]
            highs = [bar.get("high", bar.get("h", 0)) for bar in data]
            lows = [bar.get("low", bar.get("l", 0)) for bar in data]
            volumes = [bar.get("volume", bar.get("v", 0)) for bar in data]
            
            current_price = closes[-1]
            
            # Method 1: Pivot Points (most recent period)
            recent_high = max(highs[-20:])
            recent_low = min(lows[-20:])
            recent_close = closes[-1]
            pivot = (recent_high + recent_low + recent_close) / 3
            
            r1 = 2 * pivot - recent_low
            r2 = pivot + (recent_high - recent_low)
            r3 = recent_high + 2 * (pivot - recent_low)
            s1 = 2 * pivot - recent_high
            s2 = pivot - (recent_high - recent_low)
            s3 = recent_low - 2 * (recent_high - pivot)
            
            # Method 2: Price clusters (where price spent most time)
            price_min = min(lows)
            price_max = max(highs)
            price_range = price_max - price_min
            num_bins = 20
            bin_size = price_range / num_bins if price_range > 0 else 1
            
            clusters = {}
            for i in range(len(closes)):
                bin_idx = int((closes[i] - price_min) / bin_size) if bin_size > 0 else 0
                bin_idx = min(bin_idx, num_bins - 1)  # Clamp
                bin_price = price_min + (bin_idx + 0.5) * bin_size
                clusters[round(bin_price, 2)] = clusters.get(round(bin_price, 2), 0) + volumes[i]
            
            # Find top 5 volume clusters
            sorted_clusters = sorted(clusters.items(), key=lambda x: x[1], reverse=True)[:5]
            volume_levels = [{"price": p, "strength": "high" if v > sum(volumes) * 0.1 else "medium"} 
                            for p, v in sorted_clusters]
            
            # Method 3: Historical swing highs/lows
            swing_highs = []
            swing_lows = []
            
            for i in range(2, len(highs) - 2):
                if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                    swing_highs.append(highs[i])
                if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                    swing_lows.append(lows[i])
            
            # Compile support/resistance levels
            resistances = []
            supports = []
            
            for level in [r1, r2, r3] + swing_highs[-3:]:
                if level > current_price:
                    resistances.append({
                        "price": round(level, 2),
                        "distance_percent": round((level - current_price) / current_price * 100, 2),
                        "strength": "strong" if level in [r1, r2] else "moderate"
                    })
            
            for level in [s1, s2, s3] + swing_lows[-3:]:
                if level < current_price:
                    supports.append({
                        "price": round(level, 2),
                        "distance_percent": round((current_price - level) / current_price * 100, 2),
                        "strength": "strong" if level in [s1, s2] else "moderate"
                    })
            
            # Sort by distance
            resistances.sort(key=lambda x: x["distance_percent"])
            supports.sort(key=lambda x: x["distance_percent"])
            
            return {
                "symbol": symbol,
                "current_price": current_price,
                "pivot": round(pivot, 2),
                "resistances": resistances[:5],
                "supports": supports[:5],
                "volume_clusters": volume_levels,
                "nearest_resistance": resistances[0] if resistances else None,
                "nearest_support": supports[0] if supports else None,
                "interpretation": f"Key support at {supports[0]['price'] if supports else 'N/A'}, resistance at {resistances[0]['price'] if resistances else 'N/A'}"
            }
            
        except Exception as e:
            logger.error("support_resistance_error", symbol=symbol, error=str(e))
            return {"error": str(e)}
    
    async def analyze_volatility_regime(self, symbol: str) -> Dict[str, Any]:
        """
        Classify current volatility regime: LOW, NORMAL, HIGH, EXTREME.
        Provides position sizing recommendations based on regime.
        """
        try:
            historical = await self.data_collector.get_historical_data(symbol, "3m")
            
            if not historical or len(historical) < 60:
                return {"error": "Insufficient historical data (need 60+ days)"}
            
            closes = [bar.get("close", bar.get("c", 0)) for bar in historical]
            highs = [bar.get("high", bar.get("h", 0)) for bar in historical]
            lows = [bar.get("low", bar.get("l", 0)) for bar in historical]
            
            # Calculate daily returns
            returns = [(closes[i] - closes[i-1]) / closes[i-1] * 100 for i in range(1, len(closes))]
            
            # Current ATR (14-period)
            atr_current = self.calculate_atr(highs[-20:], lows[-20:], closes[-20:], period=14)
            current_atr_pct = atr_current.get("atr_percent", 0)
            
            # Historical ATR comparison (20, 60 day lookback)
            atr_20d = self.calculate_atr(highs[-25:-5], lows[-25:-5], closes[-25:-5], period=14)
            atr_60d = self.calculate_atr(highs[-65:-5], lows[-65:-5], closes[-65:-5], period=14)
            
            atr_20d_pct = atr_20d.get("atr_percent", current_atr_pct)
            atr_60d_pct = atr_60d.get("atr_percent", current_atr_pct)
            
            # Historical volatility (standard deviation of returns)
            mean_return = sum(returns) / len(returns)
            variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
            historical_vol = math.sqrt(variance) * math.sqrt(252)  # Annualized
            
            # Recent volatility (last 20 days)
            recent_returns = returns[-20:]
            mean_recent = sum(recent_returns) / len(recent_returns)
            variance_recent = sum((r - mean_recent) ** 2 for r in recent_returns) / len(recent_returns)
            recent_vol = math.sqrt(variance_recent) * math.sqrt(252)
            
            # Volatility ratio (current vs historical)
            vol_ratio = recent_vol / historical_vol if historical_vol > 0 else 1
            
            # Classify regime
            if vol_ratio < 0.7:
                regime = "LOW"
                position_multiplier = 1.25
                recommendation = "Volatility compressed - consider larger positions, watch for breakout"
            elif vol_ratio < 1.2:
                regime = "NORMAL"
                position_multiplier = 1.0
                recommendation = "Normal volatility - standard position sizing"
            elif vol_ratio < 1.8:
                regime = "HIGH"
                position_multiplier = 0.7
                recommendation = "Elevated volatility - reduce position sizes, widen stops"
            else:
                regime = "EXTREME"
                position_multiplier = 0.4
                recommendation = "Extreme volatility - minimal positions, consider cash"
            
            # Volatility trend
            if current_atr_pct > atr_20d_pct * 1.1:
                vol_trend = "expanding"
            elif current_atr_pct < atr_20d_pct * 0.9:
                vol_trend = "contracting"
            else:
                vol_trend = "stable"
            
            return {
                "symbol": symbol,
                "regime": regime,
                "vol_ratio": round(vol_ratio, 2),
                "current_atr_percent": round(current_atr_pct, 2),
                "historical_volatility": round(historical_vol, 2),
                "recent_volatility": round(recent_vol, 2),
                "volatility_trend": vol_trend,
                "position_multiplier": position_multiplier,
                "recommendation": recommendation,
                "interpretation": f"{regime} volatility regime ({vol_trend}), suggest {position_multiplier}x normal sizing"
            }
            
        except Exception as e:
            logger.error("volatility_regime_error", symbol=symbol, error=str(e))
            return {"error": str(e)}
    
    async def get_momentum_divergence(self, symbol: str) -> Dict[str, Any]:
        """
        Detect divergences between price and RSI/MACD.
        Bullish divergence: Price makes lower low, RSI makes higher low
        Bearish divergence: Price makes higher high, RSI makes lower high
        """
        try:
            historical = await self.data_collector.get_historical_data(symbol, "3m")
            
            if not historical or len(historical) < 30:
                return {"error": "Insufficient historical data"}
            
            closes = [bar.get("close", bar.get("c", 0)) for bar in historical]
            
            # Calculate RSI
            gains = []
            losses = []
            for i in range(1, len(closes)):
                change = closes[i] - closes[i-1]
                gains.append(change if change > 0 else 0)
                losses.append(-change if change < 0 else 0)
            
            period = 14
            avg_gain = sum(gains[:period]) / period
            avg_loss = sum(losses[:period]) / period
            
            rsi_values = []
            for i in range(period, len(gains)):
                avg_gain = (avg_gain * (period - 1) + gains[i]) / period
                avg_loss = (avg_loss * (period - 1) + losses[i]) / period
                rs = avg_gain / avg_loss if avg_loss > 0 else 100
                rsi = 100 - (100 / (1 + rs))
                rsi_values.append(rsi)
            
            # Find price swing lows and highs (last 20 periods)
            lookback = min(20, len(rsi_values))
            recent_closes = closes[-lookback:]
            recent_rsi = rsi_values[-lookback:]
            
            # Find local minima/maxima
            price_lows = []
            price_highs = []
            rsi_lows = []
            rsi_highs = []
            
            for i in range(1, len(recent_closes) - 1):
                if recent_closes[i] < recent_closes[i-1] and recent_closes[i] < recent_closes[i+1]:
                    price_lows.append((i, recent_closes[i]))
                    rsi_lows.append((i, recent_rsi[i]))
                if recent_closes[i] > recent_closes[i-1] and recent_closes[i] > recent_closes[i+1]:
                    price_highs.append((i, recent_closes[i]))
                    rsi_highs.append((i, recent_rsi[i]))
            
            divergences = []
            
            # Check for bullish divergence (at lows)
            if len(price_lows) >= 2:
                last_low = price_lows[-1]
                prev_low = price_lows[-2]
                
                # Price lower low, RSI higher low
                if last_low[1] < prev_low[1]:  # Price made lower low
                    last_rsi_low = rsi_lows[-1][1] if rsi_lows else recent_rsi[-1]
                    prev_rsi_low = rsi_lows[-2][1] if len(rsi_lows) >= 2 else recent_rsi[0]
                    
                    if last_rsi_low > prev_rsi_low:  # RSI made higher low
                        divergences.append({
                            "type": "bullish",
                            "strength": "strong" if (last_rsi_low - prev_rsi_low) > 5 else "moderate",
                            "description": "Price lower low but RSI higher low - potential reversal up"
                        })
            
            # Check for bearish divergence (at highs)
            if len(price_highs) >= 2:
                last_high = price_highs[-1]
                prev_high = price_highs[-2]
                
                # Price higher high, RSI lower high
                if last_high[1] > prev_high[1]:  # Price made higher high
                    last_rsi_high = rsi_highs[-1][1] if rsi_highs else recent_rsi[-1]
                    prev_rsi_high = rsi_highs[-2][1] if len(rsi_highs) >= 2 else recent_rsi[0]
                    
                    if last_rsi_high < prev_rsi_high:  # RSI made lower high
                        divergences.append({
                            "type": "bearish",
                            "strength": "strong" if (prev_rsi_high - last_rsi_high) > 5 else "moderate",
                            "description": "Price higher high but RSI lower high - potential reversal down"
                        })
            
            current_rsi = rsi_values[-1] if rsi_values else 50
            
            # Hidden divergences (trend continuation)
            if len(price_lows) >= 2 and len(rsi_lows) >= 2:
                if price_lows[-1][1] > price_lows[-2][1] and rsi_lows[-1][1] < rsi_lows[-2][1]:
                    divergences.append({
                        "type": "hidden_bullish",
                        "strength": "moderate",
                        "description": "Hidden bullish - uptrend continuation likely"
                    })
            
            if len(price_highs) >= 2 and len(rsi_highs) >= 2:
                if price_highs[-1][1] < price_highs[-2][1] and rsi_highs[-1][1] > rsi_highs[-2][1]:
                    divergences.append({
                        "type": "hidden_bearish",
                        "strength": "moderate",
                        "description": "Hidden bearish - downtrend continuation likely"
                    })
            
            overall_signal = "neutral"
            if divergences:
                bullish_count = sum(1 for d in divergences if "bullish" in d["type"])
                bearish_count = sum(1 for d in divergences if "bearish" in d["type"])
                if bullish_count > bearish_count:
                    overall_signal = "bullish"
                elif bearish_count > bullish_count:
                    overall_signal = "bearish"
            
            return {
                "symbol": symbol,
                "current_rsi": round(current_rsi, 2),
                "divergences": divergences,
                "divergence_count": len(divergences),
                "overall_signal": overall_signal,
                "has_divergence": len(divergences) > 0,
                "interpretation": divergences[0]["description"] if divergences else "No significant divergences detected"
            }
            
        except Exception as e:
            logger.error("momentum_divergence_error", symbol=symbol, error=str(e))
            return {"error": str(e)}
    
    async def analyze_price_structure(self, symbol: str) -> Dict[str, Any]:
        """
        Analyze price structure: Higher Highs/Lows (uptrend) or Lower Highs/Lows (downtrend).
        Identifies trend health and potential reversal points.
        """
        try:
            historical = await self.data_collector.get_historical_data(symbol, "3m")
            
            if not historical or len(historical) < 30:
                return {"error": "Insufficient historical data"}
            
            closes = [bar.get("close", bar.get("c", 0)) for bar in historical]
            highs = [bar.get("high", bar.get("h", 0)) for bar in historical]
            lows = [bar.get("low", bar.get("l", 0)) for bar in historical]
            
            # Find swing highs and lows
            swing_highs = []
            swing_lows = []
            
            for i in range(2, len(highs) - 2):
                if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                    swing_highs.append({"index": i, "price": highs[i]})
                if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                    swing_lows.append({"index": i, "price": lows[i]})
            
            # Analyze recent swings (last 4-5)
            recent_highs = swing_highs[-5:] if len(swing_highs) >= 5 else swing_highs
            recent_lows = swing_lows[-5:] if len(swing_lows) >= 5 else swing_lows
            
            # Count Higher Highs vs Lower Highs
            hh_count = 0  # Higher Highs
            lh_count = 0  # Lower Highs
            for i in range(1, len(recent_highs)):
                if recent_highs[i]["price"] > recent_highs[i-1]["price"]:
                    hh_count += 1
                else:
                    lh_count += 1
            
            # Count Higher Lows vs Lower Lows
            hl_count = 0  # Higher Lows
            ll_count = 0  # Lower Lows
            for i in range(1, len(recent_lows)):
                if recent_lows[i]["price"] > recent_lows[i-1]["price"]:
                    hl_count += 1
                else:
                    ll_count += 1
            
            # Determine structure
            if hh_count > lh_count and hl_count > ll_count:
                structure = "uptrend"
                health = "healthy" if hh_count >= 2 and hl_count >= 2 else "developing"
                bias = "bullish"
            elif lh_count > hh_count and ll_count > hl_count:
                structure = "downtrend"
                health = "healthy" if lh_count >= 2 and ll_count >= 2 else "developing"
                bias = "bearish"
            elif hh_count > lh_count and ll_count > hl_count:
                structure = "diverging"
                health = "uncertain"
                bias = "neutral"
            elif lh_count > hh_count and hl_count > ll_count:
                structure = "converging"
                health = "uncertain"
                bias = "neutral"
            else:
                structure = "ranging"
                health = "stable"
                bias = "neutral"
            
            # Detect potential break of structure
            current_price = closes[-1]
            last_swing_low = recent_lows[-1]["price"] if recent_lows else None
            last_swing_high = recent_highs[-1]["price"] if recent_highs else None
            
            bos_signal = None
            if structure == "uptrend" and last_swing_low and current_price < last_swing_low:
                bos_signal = {"type": "bearish_bos", "description": "Break of Structure - uptrend may be ending"}
            elif structure == "downtrend" and last_swing_high and current_price > last_swing_high:
                bos_signal = {"type": "bullish_bos", "description": "Break of Structure - downtrend may be ending"}
            
            return {
                "symbol": symbol,
                "current_price": current_price,
                "structure": structure,
                "trend_health": health,
                "bias": bias,
                "higher_highs": hh_count,
                "lower_highs": lh_count,
                "higher_lows": hl_count,
                "lower_lows": ll_count,
                "last_swing_high": last_swing_high,
                "last_swing_low": last_swing_low,
                "recent_highs": recent_highs[-3:],
                "recent_lows": recent_lows[-3:],
                "break_of_structure": bos_signal,
                "interpretation": f"{structure.title()} structure ({health}) with {bias} bias"
            }
            
        except Exception as e:
            logger.error("price_structure_error", symbol=symbol, error=str(e))
            return {"error": str(e)}


# Singleton instance
_advanced_indicators: AdvancedIndicators = None


def get_advanced_indicators() -> AdvancedIndicators:
    """Get or create advanced indicators instance."""
    global _advanced_indicators
    if _advanced_indicators is None:
        _advanced_indicators = AdvancedIndicators()
    return _advanced_indicators
