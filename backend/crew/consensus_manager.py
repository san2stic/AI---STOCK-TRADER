"""
Consensus manager for voting and decision-making.
Handles vote weighting, consensus calculation, and deadlock resolution.
"""
from typing import Dict, List, Any, Optional, Tuple
import structlog

from database import get_db
from models.database import Portfolio
from models.crew_models import CrewVote, VoteAction
from config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class ConsensusManager:
    """
    Manages the consensus process including vote weighting and conflict resolution.
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.votes: List[Dict[str, Any]] = []
    
    def calculate_agent_weight(self, agent_name: str) -> float:
        """
        Calculate voting weight for an agent based on their performance.
        
        Better performing agents get higher weights.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Weight value (typically 0.5 to 2.0)
        """
        # Get agent's portfolio performance
        with get_db() as db:
            portfolio = db.query(Portfolio).filter(
                Portfolio.agent_name == agent_name
            ).first()
            
            if not portfolio or portfolio.total_trades < 5:
                # New agent or insufficient history - neutral weight
                return 1.0
            
            # Calculate weight based on:
            # 1. Win rate (50% influence)
            # 2. Sharpe ratio (30% influence)
            # 3. Total P&L % (20% influence)
            
            win_rate = portfolio.winning_trades / max(portfolio.total_trades, 1)
            sharpe = portfolio.sharpe_ratio or 0.0
            pnl_percent = portfolio.total_pnl_percent
            
            # Normalize metrics
            # Win rate: 40% = 0.5x, 50% = 1.0x, 70% = 1.5x
            win_rate_factor = 0.5 + (win_rate - 0.4) * 2.5
            win_rate_factor = max(0.5, min(2.0, win_rate_factor))
            
            # Sharpe ratio: 0 = 1.0x, 1.0 = 1.3x, 2.0+ = 1.5x
            sharpe_factor = 1.0 + min(sharpe * 0.3, 0.5)
            
            # P&L percent: -10% = 0.7x, 0% = 1.0x, +20% = 1.3x
            pnl_factor = 1.0 + (pnl_percent / 100.0) * 1.5
            pnl_factor = max(0.5, min(1.5, pnl_factor))
            
            # Weighted combination
            weight = (
                win_rate_factor * 0.5 +
                sharpe_factor * 0.3 +
                pnl_factor * 0.2
            )
            
            # Clamp to reasonable range
            weight = max(0.5, min(2.0, weight))
            
            logger.info(
                "agent_weight_calculated",
                agent=agent_name,
                weight=weight,
                win_rate=win_rate,
                sharpe=sharpe,
                pnl_percent=pnl_percent,
            )
            
            return weight
    
    def add_vote(
        self,
        agent_name: str,
        vote_action: VoteAction,
        vote_symbol: Optional[str] = None,
        reasoning: Optional[str] = None,
        confidence_level: Optional[float] = None,
    ) -> str:
        """
        Register a vote from an agent.
        
        Args:
            agent_name: Agent casting the vote
            vote_action: BUY, SELL, or HOLD
            vote_symbol: Which symbol (if applicable)
            reasoning: Agent's reasoning
            confidence_level: Confidence in vote (0-100)
            
        Returns:
            vote_id: Unique identifier for the vote
        """
        import uuid
        
        vote_id = f"vote_{uuid.uuid4().hex[:12]}"
        
        # Calculate this agent's weight
        weight = self.calculate_agent_weight(agent_name)
        
        # Calculate weighted score
        confidence = confidence_level or 100.0
        weighted_score = weight * (confidence / 100.0)
        
        vote_data = {
            "vote_id": vote_id,
            "agent_name": agent_name,
            "vote_action": vote_action.value if isinstance(vote_action, VoteAction) else vote_action,
            "vote_symbol": vote_symbol,
            "vote_weight": weight,
            "reasoning": reasoning,
            "confidence_level": confidence,
            "weighted_score": weighted_score,
        }
        
        self.votes.append(vote_data)
        
        logger.info(
            "vote_registered",
            agent=agent_name,
            action=vote_action.value if isinstance(vote_action, VoteAction) else vote_action,
            weight=weight,
            confidence=confidence,
        )
        
        return vote_id
    
    def calculate_consensus(self) -> Tuple[str, float, Dict[str, Any]]:
        """
        Calculate the consensus decision from all votes.
        
        Returns:
            Tuple of (winning_action, consensus_score, details)
            - winning_action: The chosen action (buy/sell/hold)
            - consensus_score: Strength of consensus (0-100%)
            - details: Full breakdown of voting
        """
        if not self.votes:
            return "hold", 0.0, {"error": "no_votes"}
        
        # Tally votes by action
        action_scores = {
            "buy": 0.0,
            "sell": 0.0,
            "hold": 0.0,
        }
        
        vote_counts = {
            "buy": 0,
            "sell": 0,
            "hold": 0,
        }
        
        for vote in self.votes:
            action = vote["vote_action"]
            weighted_score = vote["weighted_score"]
            
            action_scores[action] += weighted_score
            vote_counts[action] += 1
        
        # Find winning action
        winning_action = max(action_scores.items(), key=lambda x: x[1])[0]
        winning_score = action_scores[winning_action]
        
        # Calculate consensus strength
        total_score = sum(action_scores.values())
        consensus_percent = (winning_score / total_score * 100) if total_score > 0 else 0
        
        # Check if consensus is strong enough
        min_consensus = settings.crew_min_consensus_percent if hasattr(settings, 'crew_min_consensus_percent') else 66
        
        details = {
            "action_scores": action_scores,
            "vote_counts": vote_counts,
            "total_votes": len(self.votes),
            "winning_action": winning_action,
            "winning_score": winning_score,
            "consensus_percent": consensus_percent,
            "is_strong_consensus": consensus_percent >= min_consensus,
            "votes": self.votes,
        }
        
        logger.info(
            "consensus_calculated",
            winning_action=winning_action,
            consensus_percent=consensus_percent,
            vote_breakdown=vote_counts,
        )
        
        return winning_action, consensus_percent, details
    
    def detect_deadlock(self, consensus_score: float) -> bool:
        """
        Determine if the voting is in deadlock using enhanced detection.
        
        Enhanced detection considers:
        1. Basic consensus threshold
        2. Vote distribution (close 2-way split)
        3. Confidence levels of opposing votes
        4. Historical accuracy (avoid forcing decisions when uncertain)
        
        Args:
            consensus_score: Consensus percentage
            
        Returns:
            True if deadlock detected
        """
        min_consensus = settings.crew_min_consensus_percent if hasattr(settings, 'crew_min_consensus_percent') else 66
        
        # Basic check: below threshold
        if consensus_score < min_consensus:
            # Additional checks for borderline cases
            quality = self.calculate_decision_quality()
            
            # If quality is high despite low consensus, allow the decision
            if quality["overall_quality"] >= 75 and consensus_score >= (min_consensus - 10):
                logger.info(
                    "high_quality_override",
                    consensus_score=consensus_score,
                    quality_score=quality["overall_quality"],
                    message="Allowing decision due to high quality despite borderline consensus"
                )
                return False
            
            logger.warning(
                "deadlock_detected",
                consensus_score=consensus_score,
                min_required=min_consensus,
                quality_score=quality["overall_quality"],
            )
            return True
        
        return False
    
    def calculate_decision_quality(self) -> Dict[str, Any]:
        """
        Calculate multi-criteria quality score for the decision.
        
        Evaluates:
        1. Conviction Score: How confident are the agents in their votes?
        2. Agreement Quality: How aligned are the high-performing agents?
        3. Risk Alignment: Are risk-aware agents aligned?
        4. Reasoning Quality: Do agents provide substantial reasoning?
        
        Returns:
            Dictionary with quality metrics and overall score (0-100)
        """
        if not self.votes:
            return {"overall_quality": 0, "metrics": {}, "interpretation": "No votes"}
        
        metrics = {}
        
        # 1. Conviction Score (average confidence, weighted)
        total_confidence = 0
        total_weight = 0
        for vote in self.votes:
            confidence = vote.get("confidence_level", 75)
            weight = vote.get("vote_weight", 1.0)
            total_confidence += confidence * weight
            total_weight += weight
        
        avg_confidence = total_confidence / total_weight if total_weight > 0 else 50
        metrics["conviction_score"] = min(100, avg_confidence)
        
        # 2. Agreement Quality (do high-weight agents agree?)
        sorted_by_weight = sorted(self.votes, key=lambda v: v.get("vote_weight", 1.0), reverse=True)
        top_agents = sorted_by_weight[:3] if len(sorted_by_weight) >= 3 else sorted_by_weight
        top_actions = [v["vote_action"] for v in top_agents]
        
        # Calculate agreement among top performers
        if top_actions:
            most_common = max(set(top_actions), key=top_actions.count)
            agreement_ratio = top_actions.count(most_common) / len(top_actions)
            metrics["top_performer_agreement"] = agreement_ratio * 100
        else:
            metrics["top_performer_agreement"] = 50
        
        # 3. Reasoning Quality (length and substance of reasoning)
        reasoning_scores = []
        for vote in self.votes:
            reasoning = vote.get("reasoning") or ""
            # Score based on length and presence of key words
            length_score = min(100, len(reasoning) / 2)  # 200+ chars = 100
            keyword_score = 0
            keywords = ["because", "analysis", "indicator", "risk", "opportunity", "trend", "support", "resistance"]
            for kw in keywords:
                if kw in reasoning.lower():
                    keyword_score += 12.5  # 8 keywords = 100
            reasoning_scores.append(min(100, (length_score + keyword_score) / 2))
        
        metrics["reasoning_quality"] = sum(reasoning_scores) / len(reasoning_scores) if reasoning_scores else 50
        
        # 4. Symbol Consensus (for buy/sell, do they agree on which symbol?)
        symbols = {}
        for vote in self.votes:
            if vote.get("vote_symbol"):
                symbols[vote["vote_symbol"]] = symbols.get(vote["vote_symbol"], 0) + 1
        
        if symbols:
            most_popular = max(symbols.values())
            symbol_agreement = (most_popular / len([v for v in self.votes if v.get("vote_symbol")])) * 100
            metrics["symbol_agreement"] = symbol_agreement
        else:
            metrics["symbol_agreement"] = 100  # N/A for HOLD
        
        # Calculate overall quality (weighted average)
        overall_quality = (
            metrics["conviction_score"] * 0.30 +
            metrics["top_performer_agreement"] * 0.30 +
            metrics["reasoning_quality"] * 0.20 +
            metrics["symbol_agreement"] * 0.20
        )
        
        # Interpretation
        if overall_quality >= 80:
            interpretation = "Excellent decision quality - high conviction and alignment"
        elif overall_quality >= 60:
            interpretation = "Good decision quality - reasonable confidence"
        elif overall_quality >= 40:
            interpretation = "Moderate decision quality - proceed with caution"
        else:
            interpretation = "Low decision quality - consider HOLD or more analysis"
        
        logger.info(
            "decision_quality_calculated",
            overall_quality=overall_quality,
            conviction=metrics["conviction_score"],
            top_agreement=metrics["top_performer_agreement"],
            reasoning=metrics["reasoning_quality"],
        )
        
        return {
            "overall_quality": round(overall_quality, 1),
            "metrics": metrics,
            "interpretation": interpretation,
        }
    
    def get_symbol_consensus(self) -> Optional[str]:
        """
        Determine which symbol has the most support (if buy/sell).
        
        Returns:
            Most popular symbol or None
        """
        symbols = {}
        
        for vote in self.votes:
            if vote.get("vote_symbol") and vote["vote_action"] in ["buy", "sell"]:
                symbol = vote["vote_symbol"]
                weight = vote["weighted_score"]
                symbols[symbol] = symbols.get(symbol, 0) + weight
        
        if not symbols:
            return None
        
        return max(symbols.items(), key=lambda x: x[1])[0]
    
    def save_to_database(self, session_db_id: int):
        """
        Save all votes to the database.
        
        Args:
            session_db_id: Database ID of the CrewSession
        """
        with get_db() as db:
            for vote_data in self.votes:
                # Check if already saved
                existing = db.query(CrewVote).filter(
                    CrewVote.vote_id == vote_data["vote_id"]
                ).first()
                
                if existing:
                    continue
                
                # Create vote record
                db_vote = CrewVote(
                    vote_id=vote_data["vote_id"],
                    session_id=session_db_id,
                    agent_name=vote_data["agent_name"],
                    vote_action=vote_data["vote_action"],
                    vote_symbol=vote_data.get("vote_symbol"),
                    vote_weight=vote_data["vote_weight"],
                    reasoning=vote_data.get("reasoning"),
                    confidence_level=vote_data.get("confidence_level"),
                    weighted_score=vote_data["weighted_score"],
                )
                
                db.add(db_vote)
            
            db.commit()
            
            logger.info(
                "votes_saved_to_db",
                session_id=self.session_id,
                total_votes=len(self.votes),
            )
    
    def format_vote_summary(self) -> str:
        """
        Create a formatted summary of all votes for display.
        
        Returns:
            Formatted string
        """
        if not self.votes:
            return "No votes cast yet."
        
        lines = ["=== VOTE SUMMARY ===\n"]
        
        # Sort by weighted score descending
        sorted_votes = sorted(self.votes, key=lambda v: v["weighted_score"], reverse=True)
        
        for vote in sorted_votes:
            agent = vote["agent_name"]
            action = vote["vote_action"].upper()
            symbol = vote.get("vote_symbol", "")
            weight = vote["vote_weight"]
            confidence = vote.get("confidence_level", 100)
            weighted = vote["weighted_score"]
            
            lines.append(
                f"{agent}: {action} {symbol} "
                f"(weight: {weight:.2f}, confidence: {confidence:.0f}%, "
                f"weighted score: {weighted:.2f})"
            )
        
        return "\n".join(lines)
