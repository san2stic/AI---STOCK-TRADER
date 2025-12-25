"""
Chart Pattern Detection Service.
Detects classic chart patterns for enhanced technical analysis.
All calculations use existing price data - no additional APIs required.
"""
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import structlog
import math

logger = structlog.get_logger()


class PatternDetector:
    """
    Detect classic chart patterns in price data.
    
    Supported Patterns:
    - Head and Shoulders (bearish reversal)
    - Inverse Head and Shoulders (bullish reversal)
    - Double Top (bearish reversal)
    - Double Bottom (bullish reversal)
    - Triangle (Ascending, Descending, Symmetric)
    - Golden Cross / Death Cross
    - Cup and Handle (bullish continuation)
    """
    
    def __init__(self, data_collector=None):
        """Initialize with optional data collector."""
        self._data_collector = data_collector
    
    @property
    def data_collector(self):
        """Lazy load data collector to avoid circular imports."""
        if self._data_collector is None:
            from services.data_collector import get_data_collector
            self._data_collector = get_data_collector()
        return self._data_collector
    
    async def detect_all_patterns(
        self, 
        symbol: str,
        lookback_days: int = 60
    ) -> Dict[str, Any]:
        """
        Detect all patterns for a symbol.
        
        Returns:
            Dictionary with detected patterns and trading signals
        """
        try:
            # Get historical data
            historical = await self.data_collector.get_historical_data(symbol, "3m")
            
            if not historical or len(historical) < 30:
                return {"error": "Insufficient historical data", "patterns": []}
            
            # Extract price data
            closes = [bar.get("close", bar.get("c", 0)) for bar in historical]
            highs = [bar.get("high", bar.get("h", 0)) for bar in historical]
            lows = [bar.get("low", bar.get("l", 0)) for bar in historical]
            
            detected_patterns = []
            
            # Detect various patterns
            head_shoulders = self._detect_head_shoulders(highs, lows, closes)
            if head_shoulders["detected"]:
                detected_patterns.append(head_shoulders)
            
            inverse_hs = self._detect_inverse_head_shoulders(highs, lows, closes)
            if inverse_hs["detected"]:
                detected_patterns.append(inverse_hs)
            
            double_top = self._detect_double_top(highs, closes)
            if double_top["detected"]:
                detected_patterns.append(double_top)
            
            double_bottom = self._detect_double_bottom(lows, closes)
            if double_bottom["detected"]:
                detected_patterns.append(double_bottom)
            
            triangle = self._detect_triangle(highs, lows, closes)
            if triangle["detected"]:
                detected_patterns.append(triangle)
            
            cross = self._detect_ma_cross(closes)
            if cross["detected"]:
                detected_patterns.append(cross)
            
            # Generate overall assessment
            bullish_count = sum(1 for p in detected_patterns if p.get("bias") == "bullish")
            bearish_count = sum(1 for p in detected_patterns if p.get("bias") == "bearish")
            
            if bullish_count > bearish_count:
                overall_bias = "bullish"
            elif bearish_count > bullish_count:
                overall_bias = "bearish"
            else:
                overall_bias = "neutral"
            
            return {
                "symbol": symbol,
                "timestamp": datetime.utcnow().isoformat(),
                "patterns_detected": len(detected_patterns),
                "patterns": detected_patterns,
                "overall_bias": overall_bias,
                "bullish_patterns": bullish_count,
                "bearish_patterns": bearish_count,
                "interpretation": self._generate_interpretation(detected_patterns, overall_bias),
            }
            
        except Exception as e:
            logger.error("pattern_detection_error", symbol=symbol, error=str(e))
            return {"error": str(e), "patterns": []}
    
    def _detect_head_shoulders(
        self, 
        highs: List[float], 
        lows: List[float], 
        closes: List[float]
    ) -> Dict[str, Any]:
        """
        Detect Head and Shoulders pattern (bearish reversal).
        
        Pattern: Left shoulder (high), Head (higher high), Right shoulder (high ~= left)
        """
        if len(highs) < 30:
            return {"detected": False}
        
        # Look for peaks in recent data
        peaks = self._find_peaks(highs[-60:])
        
        if len(peaks) < 3:
            return {"detected": False}
        
        # Check for H&S formation (last 3 peaks)
        recent_peaks = peaks[-3:]
        left_shoulder = recent_peaks[0]
        head = recent_peaks[1]
        right_shoulder = recent_peaks[2]
        
        # Head must be highest
        if not (head["value"] > left_shoulder["value"] and head["value"] > right_shoulder["value"]):
            return {"detected": False}
        
        # Shoulders should be roughly equal (within 5%)
        shoulder_diff = abs(left_shoulder["value"] - right_shoulder["value"]) / left_shoulder["value"]
        if shoulder_diff > 0.05:
            return {"detected": False}
        
        # Calculate neckline and target
        neckline = min(
            min(lows[left_shoulder["index"]:head["index"]]),
            min(lows[head["index"]:right_shoulder["index"]])
        )
        
        pattern_height = head["value"] - neckline
        target = neckline - pattern_height  # Measured move
        
        current_price = closes[-1]
        
        return {
            "detected": True,
            "pattern_name": "Head and Shoulders",
            "type": "reversal",
            "bias": "bearish",
            "confidence": 75 - (shoulder_diff * 500),  # Higher confidence if shoulders are equal
            "key_levels": {
                "left_shoulder": left_shoulder["value"],
                "head": head["value"],
                "right_shoulder": right_shoulder["value"],
                "neckline": neckline,
                "target": target,
            },
            "current_price": current_price,
            "signal": "SELL" if current_price < neckline else "WATCH",
            "interpretation": f"Head & Shoulders detected. Neckline at {neckline:.2f}. Break below confirms bearish target {target:.2f}",
        }
    
    def _detect_inverse_head_shoulders(
        self, 
        highs: List[float], 
        lows: List[float], 
        closes: List[float]
    ) -> Dict[str, Any]:
        """Detect Inverse Head and Shoulders (bullish reversal)."""
        if len(lows) < 30:
            return {"detected": False}
        
        # Look for troughs in recent data
        troughs = self._find_troughs(lows[-60:])
        
        if len(troughs) < 3:
            return {"detected": False}
        
        recent_troughs = troughs[-3:]
        left_shoulder = recent_troughs[0]
        head = recent_troughs[1]
        right_shoulder = recent_troughs[2]
        
        # Head must be lowest
        if not (head["value"] < left_shoulder["value"] and head["value"] < right_shoulder["value"]):
            return {"detected": False}
        
        # Shoulders roughly equal
        shoulder_diff = abs(left_shoulder["value"] - right_shoulder["value"]) / left_shoulder["value"]
        if shoulder_diff > 0.05:
            return {"detected": False}
        
        # Calculate neckline and target
        neckline = max(
            max(highs[left_shoulder["index"]:head["index"]]) if left_shoulder["index"] < head["index"] else highs[left_shoulder["index"]],
            max(highs[head["index"]:right_shoulder["index"]]) if head["index"] < right_shoulder["index"] else highs[head["index"]]
        )
        
        pattern_height = neckline - head["value"]
        target = neckline + pattern_height
        
        current_price = closes[-1]
        
        return {
            "detected": True,
            "pattern_name": "Inverse Head and Shoulders",
            "type": "reversal",
            "bias": "bullish",
            "confidence": 75 - (shoulder_diff * 500),
            "key_levels": {
                "left_shoulder": left_shoulder["value"],
                "head": head["value"],
                "right_shoulder": right_shoulder["value"],
                "neckline": neckline,
                "target": target,
            },
            "current_price": current_price,
            "signal": "BUY" if current_price > neckline else "WATCH",
            "interpretation": f"Inverse H&S detected. Neckline at {neckline:.2f}. Break above confirms bullish target {target:.2f}",
        }
    
    def _detect_double_top(self, highs: List[float], closes: List[float]) -> Dict[str, Any]:
        """Detect Double Top pattern (bearish reversal)."""
        if len(highs) < 20:
            return {"detected": False}
        
        peaks = self._find_peaks(highs[-40:])
        
        if len(peaks) < 2:
            return {"detected": False}
        
        # Check last two peaks
        peak1 = peaks[-2]
        peak2 = peaks[-1]
        
        # Peaks should be roughly equal (within 2%)
        peak_diff = abs(peak1["value"] - peak2["value"]) / peak1["value"]
        if peak_diff > 0.02:
            return {"detected": False}
        
        # Should be separated by at least 5 bars
        if peak2["index"] - peak1["index"] < 5:
            return {"detected": False}
        
        # Find support (trough between peaks)
        min_between = min(highs[peak1["index"]:peak2["index"]])
        
        current_price = closes[-1]
        target = min_between - (peak1["value"] - min_between)
        
        return {
            "detected": True,
            "pattern_name": "Double Top",
            "type": "reversal",
            "bias": "bearish",
            "confidence": 80 - (peak_diff * 1000),
            "key_levels": {
                "top1": peak1["value"],
                "top2": peak2["value"],
                "support": min_between,
                "target": target,
            },
            "current_price": current_price,
            "signal": "SELL" if current_price < min_between else "WATCH",
            "interpretation": f"Double Top at {peak1['value']:.2f}. Support at {min_between:.2f}. Break confirms {target:.2f}",
        }
    
    def _detect_double_bottom(self, lows: List[float], closes: List[float]) -> Dict[str, Any]:
        """Detect Double Bottom pattern (bullish reversal)."""
        if len(lows) < 20:
            return {"detected": False}
        
        troughs = self._find_troughs(lows[-40:])
        
        if len(troughs) < 2:
            return {"detected": False}
        
        trough1 = troughs[-2]
        trough2 = troughs[-1]
        
        # Troughs should be roughly equal (within 2%)
        trough_diff = abs(trough1["value"] - trough2["value"]) / trough1["value"]
        if trough_diff > 0.02:
            return {"detected": False}
        
        if trough2["index"] - trough1["index"] < 5:
            return {"detected": False}
        
        # Find resistance (peak between troughs)
        max_between = max(lows[trough1["index"]:trough2["index"]])
        
        current_price = closes[-1]
        target = max_between + (max_between - trough1["value"])
        
        return {
            "detected": True,
            "pattern_name": "Double Bottom",
            "type": "reversal",
            "bias": "bullish",
            "confidence": 80 - (trough_diff * 1000),
            "key_levels": {
                "bottom1": trough1["value"],
                "bottom2": trough2["value"],
                "resistance": max_between,
                "target": target,
            },
            "current_price": current_price,
            "signal": "BUY" if current_price > max_between else "WATCH",
            "interpretation": f"Double Bottom at {trough1['value']:.2f}. Resistance at {max_between:.2f}. Break confirms {target:.2f}",
        }
    
    def _detect_triangle(
        self, 
        highs: List[float], 
        lows: List[float], 
        closes: List[float]
    ) -> Dict[str, Any]:
        """Detect Triangle patterns (Ascending, Descending, Symmetric)."""
        if len(highs) < 20:
            return {"detected": False}
        
        # Calculate trendlines using linear regression
        recent_highs = highs[-20:]
        recent_lows = lows[-20:]
        
        high_slope = self._calculate_slope(recent_highs)
        low_slope = self._calculate_slope(recent_lows)
        
        # Check for converging trendlines
        if high_slope > 0 and low_slope > 0:
            return {"detected": False}  # Both rising = not a triangle
        if high_slope < 0 and low_slope < 0:
            return {"detected": False}  # Both falling = not a triangle
        
        # Determine triangle type
        if abs(high_slope) < 0.001 and low_slope > 0:
            pattern_type = "Ascending Triangle"
            bias = "bullish"
        elif high_slope < 0 and abs(low_slope) < 0.001:
            pattern_type = "Descending Triangle"
            bias = "bearish"
        elif high_slope < 0 and low_slope > 0:
            pattern_type = "Symmetric Triangle"
            bias = "neutral"  # Can break either way
        else:
            return {"detected": False}
        
        current_price = closes[-1]
        
        return {
            "detected": True,
            "pattern_name": pattern_type,
            "type": "continuation",
            "bias": bias,
            "confidence": 70,
            "key_levels": {
                "upper_trendline_slope": high_slope,
                "lower_trendline_slope": low_slope,
                "current_high": max(recent_highs[-5:]),
                "current_low": min(recent_lows[-5:]),
            },
            "current_price": current_price,
            "signal": "WATCH",
            "interpretation": f"{pattern_type} forming. Watch for breakout direction.",
        }
    
    def _detect_ma_cross(self, closes: List[float]) -> Dict[str, Any]:
        """Detect Golden Cross / Death Cross patterns."""
        if len(closes) < 200:
            return {"detected": False}
        
        # Calculate SMAs
        sma_50 = sum(closes[-50:]) / 50
        sma_200 = sum(closes[-200:]) / 200
        
        prev_sma_50 = sum(closes[-51:-1]) / 50
        prev_sma_200 = sum(closes[-201:-1]) / 200
        
        # Check for crossover
        if prev_sma_50 <= prev_sma_200 and sma_50 > sma_200:
            return {
                "detected": True,
                "pattern_name": "Golden Cross",
                "type": "trend",
                "bias": "bullish",
                "confidence": 80,
                "key_levels": {
                    "sma_50": sma_50,
                    "sma_200": sma_200,
                },
                "current_price": closes[-1],
                "signal": "BUY",
                "interpretation": "Golden Cross - 50 SMA crossed above 200 SMA. Strong bullish signal.",
            }
        
        if prev_sma_50 >= prev_sma_200 and sma_50 < sma_200:
            return {
                "detected": True,
                "pattern_name": "Death Cross",
                "type": "trend",
                "bias": "bearish",
                "confidence": 80,
                "key_levels": {
                    "sma_50": sma_50,
                    "sma_200": sma_200,
                },
                "current_price": closes[-1],
                "signal": "SELL",
                "interpretation": "Death Cross - 50 SMA crossed below 200 SMA. Strong bearish signal.",
            }
        
        return {"detected": False}
    
    def _find_peaks(self, data: List[float], min_distance: int = 3) -> List[Dict]:
        """Find local peaks in data."""
        peaks = []
        for i in range(min_distance, len(data) - min_distance):
            is_peak = all(data[i] > data[i-j] for j in range(1, min_distance+1))
            is_peak = is_peak and all(data[i] > data[i+j] for j in range(1, min_distance+1))
            if is_peak:
                peaks.append({"index": i, "value": data[i]})
        return peaks
    
    def _find_troughs(self, data: List[float], min_distance: int = 3) -> List[Dict]:
        """Find local troughs in data."""
        troughs = []
        for i in range(min_distance, len(data) - min_distance):
            is_trough = all(data[i] < data[i-j] for j in range(1, min_distance+1))
            is_trough = is_trough and all(data[i] < data[i+j] for j in range(1, min_distance+1))
            if is_trough:
                troughs.append({"index": i, "value": data[i]})
        return troughs
    
    def _calculate_slope(self, data: List[float]) -> float:
        """Calculate linear regression slope."""
        n = len(data)
        if n < 2:
            return 0
        
        x_mean = (n - 1) / 2
        y_mean = sum(data) / n
        
        numerator = sum((i - x_mean) * (data[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        return numerator / denominator if denominator != 0 else 0
    
    def _generate_interpretation(
        self, 
        patterns: List[Dict], 
        overall_bias: str
    ) -> str:
        """Generate human-readable interpretation of detected patterns."""
        if not patterns:
            return "No significant chart patterns detected."
        
        pattern_names = [p["pattern_name"] for p in patterns]
        signals = [p.get("signal", "WATCH") for p in patterns]
        
        interpretation = f"Detected {len(patterns)} pattern(s): {', '.join(pattern_names)}. "
        
        buy_signals = signals.count("BUY")
        sell_signals = signals.count("SELL")
        
        if buy_signals > sell_signals:
            interpretation += f"Pattern analysis suggests BULLISH bias with {buy_signals} buy signal(s)."
        elif sell_signals > buy_signals:
            interpretation += f"Pattern analysis suggests BEARISH bias with {sell_signals} sell signal(s)."
        else:
            interpretation += "Mixed signals - wait for confirmation."
        
        return interpretation


# Singleton instance
_pattern_detector: Optional[PatternDetector] = None


def get_pattern_detector() -> PatternDetector:
    """Get or create pattern detector instance."""
    global _pattern_detector
    if _pattern_detector is None:
        _pattern_detector = PatternDetector()
    return _pattern_detector
