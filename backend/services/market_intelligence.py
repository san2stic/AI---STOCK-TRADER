"""
Market Intelligence Boost
Implements advanced trading concepts: ICT (Inner Circle Trader), Wyckoff, and Elliott Wave.
These are institutional-grade analysis tools used by professional traders.
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger()


class ICTConceptsAnalyzer:
    """
    Analyze ICT (Inner Circle Trader) concepts:
    - Order Blocks (OB): Areas where institutions placed large orders
    - Fair Value Gaps (FVG): Price inefficiencies that tend to get filled
    - Liquidity Zones: Areas where stop-losses cluster
    """
    
    def analyze_ict_structure(
        self,
        symbol: str,
        price_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze ICT market structure.
        
        Returns:
            {
                "order_blocks": [...],
                "fair_value_gaps": [...],
                "liquidity_zones": [...],
                "market_structure": "BULLISH" | "BEARISH" | "RANGING",
                "recommendation": str
            }
        """
        current_price = price_data.get("price", 0)
        high_24h = price_data.get("high_24h", current_price)
        low_24h = price_data.get("low_24h", current_price)
        
        # Identify Order Blocks (simplified - real would use volume profile)
        order_blocks = self._identify_order_blocks(current_price, high_24h, low_24h)
        
        # Identify Fair Value Gaps
        fair_value_gaps = self._identify_fvg(current_price, high_24h, low_24h)
        
        # Identify Liquidity Zones (areas with round numbers + recent highs/lows)
        liquidity_zones = self._identify_liquidity_zones(current_price, high_24h, low_24h)
        
        # Determine market structure
        market_structure = self._determine_market_structure(
            current_price, high_24h, low_24h, order_blocks
        )
        
        # Generate recommendation
        recommendation = self._generate_ict_recommendation(
            market_structure, order_blocks, fair_value_gaps, current_price
        )
        
        return {
            "order_blocks": order_blocks,
            "fair_value_gaps": fair_value_gaps,
            "liquidity_zones": liquidity_zones,
            "market_structure": market_structure,
            "recommendation": recommendation,
            "current_price": current_price
        }
    
    def _identify_order_blocks(
        self,
        current_price: float,
        high: float,
        low: float
    ) -> List[Dict[str, Any]]:
        """Identify institutional order blocks (simplified)."""
        blocks = []
        
        # Bullish Order Block (support zone where institutions bought)
        bullish_ob_price = low * 1.02  # 2% above recent low
        if current_price > bullish_ob_price:
            blocks.append({
                "type": "BULLISH_OB",
                "price_level": round(bullish_ob_price, 2),
                "strength": "HIGH" if (current_price - bullish_ob_price) / current_price > 0.05 else "MODERATE",
                "description": "Bullish Order Block - potential support zone"
            })
        
        # Bearish Order Block (resistance zone where institutions sold)
        bearish_ob_price = high * 0.98  # 2% below recent high
        if current_price < bearish_ob_price:
            blocks.append({
                "type": "BEARISH_OB",
                "price_level": round(bearish_ob_price, 2),
                "strength": "HIGH" if (bearish_ob_price - current_price) / current_price > 0.05 else "MODERATE",
                "description": "Bearish Order Block - potential resistance zone"
            })
        
        return blocks
    
    def _identify_fvg(
        self,
        current_price: float,
        high: float,
        low: float
    ) -> List[Dict[str, Any]]:
        """Identify Fair Value Gaps (price inefficiencies)."""
        gaps = []
        
        # Simplified: FVG is a gap between high/low where price moved quickly
        price_range = high - low
        gap_threshold = price_range * 0.03  # 3% gap
        
        # Bullish FVG (gap below current price that may act as support)
        if current_price - low > gap_threshold:
            fvg_zone = (low, low + gap_threshold)
            gaps.append({
                "type": "BULLISH_FVG",
                "zone": fvg_zone,
                "midpoint": round((fvg_zone[0] + fvg_zone[1]) / 2, 2),
                "description": "Bullish Fair Value Gap - likely to be filled (support)"
            })
        
        # Bearish FVG (gap above current price that may act as resistance)
        if high - current_price > gap_threshold:
            fvg_zone = (high - gap_threshold, high)
            gaps.append({
                "type": "BEARISH_FVG",
                "zone": fvg_zone,
                "midpoint": round((fvg_zone[0] + fvg_zone[1]) / 2, 2),
                "description": "Bearish Fair Value Gap - likely to be filled (resistance)"
            })
        
        return gaps
    
    def _identify_liquidity_zones(
        self,
        current_price: float,
        high: float,
        low: float
    ) -> List[Dict[str, Any]]:
        """Identify liquidity zones (round numbers + swing points)."""
        zones = []
        
        # Round numbers attract liquidity (stop-losses cluster here)
        nearest_round = round(current_price / 10) * 10
        
        zones.append({
            "type": "ROUND_NUMBER",
            "price_level": nearest_round,
            "description": f"Round number liquidity at ${nearest_round}"
        })
        
        # Recent high/low = liquidity (stop-losses placed just above/below)
        zones.append({
            "type": "SWING_HIGH",
            "price_level": round(high, 2),
            "description": "Recent high - stop-losses likely above"
        })
        
        zones.append({
            "type": "SWING_LOW",
            "price_level": round(low, 2),
            "description": "Recent low - stop-losses likely below"
        })
        
        return zones
    
    def _determine_market_structure(
        self,
        current_price: float,
        high: float,
        low: float,
        order_blocks: List
    ) -> str:
        """Determine overall market structure."""
        range_percent = ((high - low) / low) * 100
        
        if range_percent < 3:
            return "RANGING"
        
        # Check position in range
        position_in_range = (current_price - low) / (high - low) if (high - low) > 0 else 0.5
        
        if position_in_range > 0.7:
            return "BULLISH"
        elif position_in_range < 0.3:
            return "BEARISH"
        else:
            return "RANGING"
    
    def _generate_ict_recommendation(
        self,
        structure: str,
        order_blocks: List,
        fvgs: List,
        current_price: float
    ) -> str:
        """Generate ICT-based recommendation."""
        if structure == "BULLISH" and any(ob["type"] == "BULLISH_OB" for ob in order_blocks):
            return f"✅ BULLISH structure with order block support. Look for longs near ${order_blocks[0]['price_level']}"
        elif structure == "BEARISH" and any(ob["type"] == "BEARISH_OB" for ob in order_blocks):
            return f"❌ BEARISH structure with order block resistance. Look for shorts near ${order_blocks[0]['price_level']}"
        elif fvgs:
            fvg = fvgs[0]
            return f"⚠️ Fair Value Gap at ${fvg['midpoint']} - expect price to fill this gap"
        else:
            return "➡️ RANGING market - wait for breakout or reversal"


class WyckoffAnalyzer:
    """
    Analyze Wyckoff accumulation/distribution phases:
    - Phase A: Stopping of prior trend
    - Phase B: Building cause
    - Phase C: Spring (fake-out) or test
    - Phase D: Markup/Markdown begins
    - Phase E: Trend in full effect
    """
    
    def analyze_wyckoff_phase(
        self,
        symbol: str,
        price_history: List[float],
        volume_history: List[float] = None
    ) -> Dict[str, Any]:
        """
        Determine current Wyckoff phase.
        
        Returns:
            {
                "current_phase": "A" | "B" | "C" | "D" | "E",
                "bias": "ACCUMULATION" | "DISTRIBUTION" | "NEUTRAL",
                "recommendation": str,
                "confidence": "LOW" | "MEDIUM" | "HIGH"
            }
        """
        if len(price_history) < 10:
            return {
                "current_phase": "UNKNOWN",
                "bias": "NEUTRAL",
                "recommendation": "Insufficient data for Wyckoff analysis",
                "confidence": "LOW"
            }
        
        # Analyze price action
        recent_prices = price_history[-10:]
        current_price = recent_prices[-1]
        avg_price = sum(recent_prices) / len(recent_prices)
        
        # Calculate volatility
        price_range = max(recent_prices) - min(recent_prices)
        volatility = (price_range / avg_price) * 100
        
        # Determine phase (simplified)
        phase, bias = self._determine_wyckoff_phase(
            recent_prices, volatility, volume_history
        )
        
        # Generate recommendation
        recommendation = self._generate_wyckoff_recommendation(phase, bias, current_price)
        
        # Confidence based on data quality
        confidence = "HIGH" if len(price_history) >= 30 else "MEDIUM"
        
        return {
            "current_phase": phase,
            "bias": bias,
            "recommendation": recommendation,
            "confidence": confidence,
            "current_price": round(current_price, 2)
        }
    
    def _determine_wyckoff_phase(
        self,
        prices: List[float],
        volatility: float,
        volumes: List[float] = None
    ) -> Tuple[str, str]:
        """Determine Wyckoff phase and bias."""
        # Simplified phase detection
        current = prices[-1]
        prev = prices[-5] if len(prices) >= 5 else prices[0]
        
        # Check if consolidating (Phase B/C)
        if volatility < 5:
            # Low volatility = consolidation
            if current > prev:
                return "C", "ACCUMULATION"  # Spring completed, ready to markup
            else:
                return "B", "DISTRIBUTION"  # Building distribution
        
        # Check if trending (Phase D/E)
        elif volatility > 10:
            # High volatility = trending
            if current > prev:
                return "D", "ACCUMULATION"  # Markup beginning
            else:
                return "D", "DISTRIBUTION"  # Markdown beginning
        
        # Medium volatility = Phase A (stopping action)
        else:
            return "A", "NEUTRAL"
    
    def _generate_wyckoff_recommendation(
        self,
        phase: str,
        bias: str,
        current_price: float
    ) -> str:
        """Generate Wyckoff-based recommendation."""
        if phase == "C" and bias == "ACCUMULATION":
            return f"✅ WYCKOFF PHASE C (Accumulation): Spring likely completed. LONG at ${current_price:.2f}"
        elif phase == "D" and bias == "ACCUMULATION":
            return f"🚀 WYCKOFF PHASE D (Accumulation): Markup in progress. Hold longs"
        elif phase == "C" and bias == "DISTRIBUTION":
            return f"❌ WYCKOFF PHASE C (Distribution): UTAD likely. SHORT at ${current_price:.2f}"
        elif phase == "D" and bias == "DISTRIBUTION":
            return f"⬇️ WYCKOFF PHASE D (Distribution): Markdown in progress. Hold shorts"
        elif phase == "B":
            return f"⏳ WYCKOFF PHASE B: Consolidation. Wait for spring/UTAD"
        else:
            return f"➡️ WYCKOFF PHASE A: Stopping action. Wait for direction"


class ElliottWaveDetector:
    """
    Simplified Elliott Wave pattern detection:
    - Identifies 5-wave impulse patterns
    - Identifies ABC corrective patterns
    """
    
    def detect_elliott_wave(
        self,
        symbol: str,
        price_history: List[float]
    ) -> Dict[str, Any]:
        """
        Detect Elliott Wave patterns.
        
        Returns:
            {
                "pattern_detected": "IMPULSE" | "CORRECTIVE" | "NONE",
                "current_wave": 1-5 | "A" | "B" | "C",
                "trend_direction": "UP" | "DOWN" | "SIDEWAYS",
                "recommendation": str
            }
        """
        if len(price_history) < 8:
            return {
                "pattern_detected": "NONE",
                "current_wave": None,
                "trend_direction": "SIDEWAYS",
                "recommendation": "Insufficient price data for Elliott Wave"
            }
        
        # Find pivot points (simplified)
        pivots = self._find_pivots(price_history)
        
        # Detect pattern
        pattern, wave, direction = self._detect_wave_pattern(pivots, price_history)
        
        # Generate recommendation
        recommendation = self._generate_elliott_recommendation(pattern, wave, direction)
        
        return {
            "pattern_detected": pattern,
            "current_wave": wave,
            "trend_direction": direction,
            "recommendation": recommendation,
            "pivot_count": len(pivots)
        }
    
    def _find_pivots(self, prices: List[float], window: int = 3) -> List[Dict]:
        """Find pivot highs and lows."""
        pivots = []
        
        for i in range(window, len(prices) - window):
            # Pivot high
            if all(prices[i] > prices[i-j] for j in range(1, window+1)) and \
               all(prices[i] > prices[i+j] for j in range(1, window+1)):
                pivots.append({"index": i, "price": prices[i], "type": "HIGH"})
            
            # Pivot low
            elif all(prices[i] < prices[i-j] for j in range(1, window+1)) and \
                 all(prices[i] < prices[i+j] for j in range(1, window+1)):
                pivots.append({"index": i, "price": prices[i], "type": "LOW"})
        
        return pivots
    
    def _detect_wave_pattern(
        self,
        pivots: List[Dict],
        prices: List[float]
    ) -> Tuple[str, Any, str]:
        """Detect Elliott Wave pattern from pivots."""
        if len(pivots) < 3:
            return "NONE", None, "SIDEWAYS"
        
        # Simple pattern: alternating highs and lows
        pattern_types = [p["type"] for p in pivots[-5:]]
        
        # Check for impulse pattern (5 waves)
        if len(pattern_types) >= 5:
            # Bullish impulse: LOW-HIGH-LOW-HIGH-LOW-HIGH...
            if pattern_types == ["LOW", "HIGH", "LOW", "HIGH", "LOW"]:
                return "IMPULSE", 5, "UP"
            # Bearish impulse
            elif pattern_types == ["HIGH", "LOW", "HIGH", "LOW", "HIGH"]:
                return "IMPULSE", 5, "DOWN"
        
        # Check for corrective pattern (ABC)
        if len(pattern_types) >= 3:
            recent_3 = pattern_types[-3:]
            if recent_3 == ["HIGH", "LOW", "HIGH"] or recent_3 == ["LOW", "HIGH", "LOW"]:
                return "CORRECTIVE", "C", "SIDEWAYS"
        
        # Trend direction based on recent price action
        if prices[-1] > prices[0]:
            return "NONE", None, "UP"
        elif prices[-1] < prices[0]:
            return "NONE", None, "DOWN"
        else:
            return "NONE", None, "SIDEWAYS"
    
    def _generate_elliott_recommendation(
        self,
        pattern: str,
        wave: Any,
        direction: str
    ) -> str:
        """Generate Elliott Wave recommendation."""
        if pattern == "IMPULSE" and wave == 5:
            if direction == "UP":
                return "⚠️ WAVE 5 (Impulse UP): Nearing exhaustion. Consider taking profits or preparing for correction"
            else:
                return "⚠️ WAVE 5 (Impulse DOWN): Nearing bottom. Consider reversal trades"
        elif pattern == "IMPULSE" and wave in [1, 3]:
            return f"✅ WAVE {wave} (Impulse): Strong trend. Trade with trend"
        elif pattern == "CORRECTIVE":
            return "➡️ CORRECTIVE WAVE: Consolidation. Wait for next impulse wave"
        elif direction == "UP":
            return "📈 Uptrend detected. Look for long opportunities"
        elif direction == "DOWN":
            return "📉 Downtrend detected. Look for short opportunities"
        else:
            return "➡️ Sideways. Wait for clear direction"


# Tool functions

def analyze_ict_concepts(symbol: str, price_data: Dict[str, Any]) -> Dict[str, Any]:
    """Tool: Analyze ICT concepts (Order Blocks, FVG, Liquidity)."""
    analyzer = ICTConceptsAnalyzer()
    return analyzer.analyze_ict_structure(symbol, price_data)


def analyze_wyckoff_phase(symbol: str, price_history: List[float]) -> Dict[str, Any]:
    """Tool: Determine Wyckoff accumulation/distribution phase."""
    analyzer = WyckoffAnalyzer()
    return analyzer.analyze_wyckoff_phase(symbol, price_history)


def detect_elliott_wave_pattern(symbol: str, price_history: List[float]) -> Dict[str, Any]:
    """Tool: Detect Elliott Wave patterns."""
    detector = ElliottWaveDetector()
    return detector.detect_elliott_wave(symbol, price_history)
