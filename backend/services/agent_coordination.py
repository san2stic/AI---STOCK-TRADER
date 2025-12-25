"""
Enhanced Agent Coordination System
Enables multiple agents to collaborate, vote on decisions, and resolve conflicts.
Implements consensus mechanisms for better collective decision-making.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import structlog
from database import get_db
from models.database import Decision
from collections import Counter

logger = structlog.get_logger()


class MultiAgentConsensus:
    """
    Coordonne plusieurs agents pour obtenir un consensus sur les trades.
    """
    
    def get_agent_consensus(
        self,
        symbol: str,
        agent_decisions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyse les décisions de plusieurs agents et retourne un consensus.
        
        Args:
            symbol: Symbol à trader
            agent_decisions: Liste de decisions [{agent: str, action: str, confidence: float, reasoning: str}]
        
        Returns:
            {
                "consensus_action": "BUY" | "SELL" | "HOLD",
                "consensus_strength": 0-100,
                "voting_breakdown": {...},
                "recommendation": str,
                "conflicting_agents": [...]
            }
        """
        if not agent_decisions:
            return {
                "consensus_action": "HOLD",
                "consensus_strength": 0,
                "voting_breakdown": {},
                "recommendation": "No agent decisions available",
                "conflicting_agents": []
            }
        
        # Count votes
        actions = [d.get("action", "HOLD").upper() for d in agent_decisions]
        action_counts = Counter(actions)
        
        # Determine consensus
        total_votes = len(actions)
        most_common_action, max_votes = action_counts.most_common(1)[0]
        
        # Calculate consensus strength (percentage agreement)
        consensus_strength = (max_votes / total_votes) * 100
        
        # Identify conflicting agents
        conflicting = [
            d.get("agent", "Unknown")
            for d in agent_decisions
            if d.get("action", "").upper() != most_common_action
        ]
        
        # Weight by confidence if available
        weighted_action = self._calculate_weighted_action(agent_decisions)
        
        # Generate recommendation
        recommendation = self._generate_consensus_recommendation(
            most_common_action,
            consensus_strength,
            weighted_action,
            conflicting
        )
        
        return {
            "consensus_action": most_common_action,
            "consensus_strength": round(consensus_strength, 1),
            "voting_breakdown": dict(action_counts),
            "weighted_action": weighted_action,
            "recommendation": recommendation,
            "conflicting_agents": conflicting,
            "total_agents": total_votes
        }
    
    def _calculate_weighted_action(self, decisions: List[Dict]) -> str:
        """Calculate action weighted by agent confidence."""
        action_weights = {}
        
        for decision in decisions:
            action = decision.get("action", "HOLD").upper()
            confidence = decision.get("confidence", 50) / 100  # Normalize to 0-1
            
            action_weights[action] = action_weights.get(action, 0) + confidence
        
        if not action_weights:
            return "HOLD"
        
        # Return action with highest weighted score
        return max(action_weights.items(), key=lambda x: x[1])[0]
    
    def _generate_consensus_recommendation(
        self,
        action: str,
        strength: float,
        weighted_action: str,
        conflicting: List[str]
    ) -> str:
        """Generate consensus recommendation."""
        if strength >= 75:
            return f"✅ STRONG CONSENSUS ({strength:.0f}%): {action}. All/most agents agree - high confidence trade."
        elif strength >= 60:
            return f"🟢 MODERATE CONSENSUS ({strength:.0f}%): {action}. Majority agrees but {len(conflicting)} agent(s) disagree."
        elif strength >= 50:
            if weighted_action != action:
                return f"⚠️ WEAK CONSENSUS ({strength:.0f}%): Vote says {action}, but weighted by confidence suggests {weighted_action}. Review carefully."
            return f"🟡 WEAK CONSENSUS ({strength:.0f}%): {action}. Split decision - proceed with caution."
        else:
            return f"❌ NO CONSENSUS ({strength:.0f}%): Agents strongly disagree. HOLD and wait for clearer signals."


class ConflictResolver:
    """
    Résout les conflits lorsque les agents ne sont pas d'accord.
    """
    
    def resolve_conflict(
        self,
        symbol: str,
        conflicting_decisions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Résout un conflit entre agents.
        
        Returns:
            {
                "resolution": "BUY" | "SELL" | "HOLD",
                "resolution_method": str,
                "tiebreaker_used": bool,
                "recommendation": str
            }
        """
        if len(conflicting_decisions) < 2:
            return {
                "resolution": conflicting_decisions[0].get("action", "HOLD") if conflicting_decisions else "HOLD",
                "resolution_method": "single_agent",
                "tiebreaker_used": False,
                "recommendation": "Only one agent opinion available"
            }
        
        # Method 1: Use confidence scores
        resolution, method = self._resolve_by_confidence(conflicting_decisions)
        
        if resolution:
            return {
                "resolution": resolution,
                "resolution_method": method,
                "tiebreaker_used": True,
                "recommendation": f"Conflict resolved using {method}: {resolution}"
            }
        
        # Method 2: Default to HOLD when truly split
        return {
            "resolution": "HOLD",
            "resolution_method": "default_hold",
            "tiebreaker_used": False,
            "recommendation": "Agents equally split - defaulting to HOLD for safety"
        }
    
    def _resolve_by_confidence(
        self,
        decisions: List[Dict]
    ) -> tuple[Optional[str], str]:
        """Resolve by choosing highest confidence decision."""
        # Find decision with highest confidence
        decision_with_conf = [
            (d.get("action", "HOLD"), d.get("confidence", 50))
            for d in decisions
        ]
        
        if not decision_with_conf:
            return None, ""
        
        # Sort by confidence
        sorted_decisions = sorted(decision_with_conf, key=lambda x: x[1], reverse=True)
        
        # Check if top confidence is significantly higher (>10 points)
        if len(sorted_decisions) >= 2:
            top_confidence = sorted_decisions[0][1]
            second_confidence = sorted_decisions[1][1]
            
            if top_confidence - second_confidence >= 10:
                return sorted_decisions[0][0], "highest_confidence"
        
        # If top decision has very high confidence (>80), use it
        if sorted_decisions[0][1] >= 80:
            return sorted_decisions[0][0], "very_high_confidence"
        
        return None, ""


class CollaborativeSignalFilter:
    """
    Filtre collaboratif qui combine les signaux de plusieurs agents.
    """
    
    def filter_collaborative_signals(
        self,
        symbol: str,
        agent_signals: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Combine et filtre les signaux de plusieurs agents.
        
        Args:
            agent_signals: [{agent: str, signal: str, strength: float, reasoning: str}]
        
        Returns:
            {
                "filtered_signal": str,
                "signal_quality": "HIGH" | "MEDIUM" | "LOW",
                "agreeing_agents": [...],
                "recommendation": str
            }
        """
        if not agent_signals:
            return {
                "filtered_signal": "NEUTRAL",
                "signal_quality": "LOW",
                "agreeing_agents": [],
                "recommendation": "No signals to filter"
            }
        
        # Group by signal type
        signal_groups = {}
        for sig in agent_signals:
            signal_type = sig.get("signal", "NEUTRAL")
            if signal_type not in signal_groups:
                signal_groups[signal_type] = []
            signal_groups[signal_type].append(sig)
        
        # Find dominant signal
        dominant_signal = max(signal_groups.items(), key=lambda x: len(x[1]))
        signal_name = dominant_signal[0]
        agreeing_agents = [s.get("agent") for s in dominant_signal[1]]
        
        # Calculate quality based on agreement
        agreement_percent = (len(agreeing_agents) / len(agent_signals)) * 100
        
        if agreement_percent >= 75:
            quality = "HIGH"
        elif agreement_percent >= 50:
            quality = "MEDIUM"
        else:
            quality = "LOW"
        
        # Recommendation
        if quality == "HIGH":
            recommendation = f"✅ HIGH QUALITY: {len(agreeing_agents)}/{len(agent_signals)} agents agree on {signal_name}"
        elif quality == "MEDIUM":
            recommendation = f"🟡 MEDIUM QUALITY: {len(agreeing_agents)}/{len(agent_signals)} agents agree on {signal_name}"
        else:
            recommendation = f"⚠️ LOW QUALITY: Only {len(agreeing_agents)}/{len(agent_signals)} agents agree - signals are noisy"
        
        return {
            "filtered_signal": signal_name,
            "signal_quality": quality,
            "agreeing_agents": agreeing_agents,
            "agreement_percent": round(agreement_percent, 1),
            "recommendation": recommendation
        }


# Tool functions

def get_agent_consensus(symbol: str, agent_decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Tool: Get consensus from multiple agent decisions."""
    coordinator = MultiAgentConsensus()
    return coordinator.get_agent_consensus(symbol, agent_decisions)


def resolve_agent_conflict(symbol: str, conflicting_decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Tool: Resolve conflicts between agents."""
    resolver = ConflictResolver()
    return resolver.resolve_conflict(symbol, conflicting_decisions)


def filter_collaborative_signals(symbol: str, agent_signals: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Tool: Filter and combine signals from multiple agents."""
    filter_obj = CollaborativeSignalFilter()
    return filter_obj.filter_collaborative_signals(symbol, agent_signals)
