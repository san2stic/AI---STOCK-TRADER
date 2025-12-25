"""
Agent communication system for crew deliberation.
Manages message passing, discussion history, and context sharing.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid
import structlog

from models.crew_models import AgentMessage, MessageType
from database import get_db

logger = structlog.get_logger()


class AgentCommunication:
    """
    Handles structured communication between agents during deliberation.
    Manages message routing, history, and context.
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.message_cache: List[Dict[str, Any]] = []
    
    def send_message(
        self,
        agent_name: str,
        round_number: int,
        message_type: MessageType,
        content: str,
        sequence_number: int,
        proposed_action: Optional[str] = None,
        proposed_symbol: Optional[str] = None,
        confidence_level: Optional[float] = None,
        mentioned_agents: Optional[List[str]] = None,
        responding_to_message_id: Optional[str] = None,
    ) -> str:
        """
        Send a message from an agent.
        
        Args:
            agent_name: Name of the sending agent
            round_number: Current deliberation round
            message_type: Type of message (POSITION, REBUTTAL, etc.)
            content: Message content
            sequence_number: Order within the round
            proposed_action: Optional action (buy/sell/hold)
            proposed_symbol: Optional symbol to trade
            confidence_level: Agent's confidence (0-100)
            mentioned_agents: List of agents mentioned in message
            responding_to_message_id: If replying to another message
            
        Returns:
            message_id: Unique identifier for this message
        """
        message_id = f"msg_{uuid.uuid4().hex[:12]}"
        
        # Create message object
        message_data = {
            "message_id": message_id,
            "agent_name": agent_name,
            "round_number": round_number,
            "message_type": message_type.value if isinstance(message_type, MessageType) else message_type,
            "sequence_number": sequence_number,
            "content": content,
            "proposed_action": proposed_action,
            "proposed_symbol": proposed_symbol,
            "confidence_level": confidence_level,
            "mentioned_agents": mentioned_agents or [],
            "responding_to_message_id": responding_to_message_id,
            "created_at": datetime.utcnow(),
        }
        
        # Add to cache
        self.message_cache.append(message_data)
        
        logger.info(
            "agent_message_sent",
            agent=agent_name,
            round=round_number,
            type=message_type.value if isinstance(message_type, MessageType) else message_type,
            message_id=message_id,
        )
        
        return message_id
    
    def get_discussion_history(
        self,
        round_number: Optional[int] = None,
        filter_by_agent: Optional[str] = None,
        message_types: Optional[List[MessageType]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve discussion history with optional filtering.
        
        Args:
            round_number: Filter by specific round (None = all rounds)
            filter_by_agent: Filter by specific agent
            message_types: Filter by message types
            
        Returns:
            List of message dictionaries
        """
        messages = self.message_cache.copy()
        
        # Apply filters
        if round_number is not None:
            messages = [m for m in messages if m["round_number"] == round_number]
        
        if filter_by_agent:
            messages = [m for m in messages if m["agent_name"] == filter_by_agent]
        
        if message_types:
            type_values = [mt.value if isinstance(mt, MessageType) else mt for mt in message_types]
            messages = [m for m in messages if m["message_type"] in type_values]
        
        # Sort by creation time
        messages.sort(key=lambda m: m["created_at"])
        
        return messages
    
    def format_discussion_for_agent(
        self,
        agent_name: str,
        round_number: int,
        include_previous_rounds: bool = True,
    ) -> str:
        """
        Format the discussion history for presentation to an agent.
        
        Args:
            agent_name: The agent who will read this
            round_number: Current round
            include_previous_rounds: Include messages from earlier rounds
            
        Returns:
            Formatted string of the discussion
        """
        # Get relevant messages
        if include_previous_rounds:
            messages = [m for m in self.message_cache if m["round_number"] <= round_number]
        else:
            messages = [m for m in self.message_cache if m["round_number"] == round_number]
        
        if not messages:
            return "No discussion yet."
        
        # Group by round
        rounds_dict: Dict[int, List[Dict]] = {}
        for msg in messages:
            r = msg["round_number"]
            if r not in rounds_dict:
                rounds_dict[r] = []
            rounds_dict[r].append(msg)
        
        # Format output
        formatted_parts = []
        
        for r in sorted(rounds_dict.keys()):
            formatted_parts.append(f"\n=== ROUND {r} ===\n")
            
            for msg in sorted(rounds_dict[r], key=lambda m: m["sequence_number"]):
                msg_type = msg["message_type"].upper()
                sender = msg["agent_name"]
                content = msg["content"]
                
                # Highlight if message mentions this agent
                mentioned = msg.get("mentioned_agents", [])
                mention_flag = " [@YOU]" if agent_name in mentioned else ""
                
                # Add proposed action if present
                action_info = ""
                if msg.get("proposed_action"):
                    action = msg["proposed_action"].upper()
                    symbol = msg.get("proposed_symbol", "")
                    confidence = msg.get("confidence_level", 0)
                    action_info = f" [Proposes: {action} {symbol} - {confidence:.0f}% confidence]"
                
                formatted_parts.append(
                    f"[{msg_type}] {sender}{mention_flag}{action_info}:\n{content}\n"
                )
        
        return "\n".join(formatted_parts)
    
    def get_agent_positions(self, round_number: int = 1) -> Dict[str, Dict[str, Any]]:
        """
        Get all agent positions from a specific round (typically round 1).
        
        Args:
            round_number: Which round to extract positions from
            
        Returns:
            Dictionary mapping agent_name to their position
        """
        positions = {}
        
        for msg in self.message_cache:
            if msg["round_number"] == round_number and msg["message_type"] == MessageType.POSITION.value:
                positions[msg["agent_name"]] = {
                    "action": msg.get("proposed_action"),
                    "symbol": msg.get("proposed_symbol"),
                    "confidence": msg.get("confidence_level"),
                    "reasoning": msg["content"],
                    "message_id": msg["message_id"],
                }
        
        return positions
    
    def save_to_database(self, session_db_id: int):
        """
        Persist all messages to the database.
        
        Args:
            session_db_id: Database ID of the CrewSession
        """
        with get_db() as db:
            for msg_data in self.message_cache:
                # Check if already saved
                existing = db.query(AgentMessage).filter(
                    AgentMessage.message_id == msg_data["message_id"]
                ).first()
                
                if existing:
                    continue
                
                # Create new message record
                db_message = AgentMessage(
                    message_id=msg_data["message_id"],
                    session_id=session_db_id,
                    agent_name=msg_data["agent_name"],
                    round_number=msg_data["round_number"],
                    message_type=msg_data["message_type"],
                    sequence_number=msg_data["sequence_number"],
                    content=msg_data["content"],
                    proposed_action=msg_data.get("proposed_action"),
                    proposed_symbol=msg_data.get("proposed_symbol"),
                    confidence_level=msg_data.get("confidence_level"),
                    mentioned_agents=msg_data.get("mentioned_agents"),
                    responding_to_message_id=msg_data.get("responding_to_message_id"),
                )
                
                db.add(db_message)
            
            db.commit()
            
            logger.info(
                "messages_saved_to_db",
                session_id=self.session_id,
                total_messages=len(self.message_cache),
            )
    
    def analyze_discussion_sentiment(self) -> Dict[str, Any]:
        """
        Analyze the overall sentiment and dynamics of the discussion.
        
        Returns:
            Dictionary with analysis metrics
        """
        if not self.message_cache:
            return {"status": "no_messages"}
        
        # Count message types
        type_counts = {}
        for msg in self.message_cache:
            msg_type = msg["message_type"]
            type_counts[msg_type] = type_counts.get(msg_type, 0) + 1
        
        # Count agreements vs. rebuttals
        agreements = type_counts.get(MessageType.AGREEMENT.value, 0)
        rebuttals = type_counts.get(MessageType.REBUTTAL.value, 0)
        
        # Calculate collaboration score
        total_interactive = agreements + rebuttals
        collaboration_score = (agreements / total_interactive * 100) if total_interactive > 0 else 50
        
        # Get proposed actions distribution
        actions = {}
        for msg in self.message_cache:
            if msg.get("proposed_action"):
                action = msg["proposed_action"]
                actions[action] = actions.get(action, 0) + 1
        
        return {
            "total_messages": len(self.message_cache),
            "message_types": type_counts,
            "agreements": agreements,
            "rebuttals": rebuttals,
            "collaboration_score": collaboration_score,
            "proposed_actions": actions,
            "most_active_agent": max(
                set(m["agent_name"] for m in self.message_cache),
                key=lambda a: sum(1 for m in self.message_cache if m["agent_name"] == a)
            ) if self.message_cache else None,
        }
