"""
Crew orchestrator - manages multi-agent deliberation sessions.
Coordinates discussion rounds, collects votes, and reaches consensus.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid
import asyncio
import structlog

from crew.agent_communication import AgentCommunication
from crew.consensus_manager import ConsensusManager
from models.crew_models import (
    CrewSession, AgentMessage, CrewVote,
    SessionStatus, MessageType, VoteAction, CrewPerformance,
)
from database import get_db
from config import get_settings
from services.gemini_client import get_gemini_client
from services.decision_parser import get_decision_parser
from services.risk_manager import get_risk_manager
from tools.trading_tools import TRADING_TOOLS

logger = structlog.get_logger()
settings = get_settings()


class CrewOrchestrator:
    """
    Orchestrates deliberation sessions where agents discuss and reach consensus.
    
    Process:
    1. Round 1: Each agent gives initial position
    2. Round 2: Agents debate and respond to each other
    3. Round 3: Final vote and consensus
    4. If deadlock: Mediator makes final decision
    """
    
    def __init__(self, agents: List[Any], ws_manager=None):
        """
        Initialize the crew orchestrator.
        
        Args:
            agents: List of agent instances (BaseAgent subclasses)
            ws_manager: WebSocket manager for broadcasting updates
        """
        self.agents = agents
        self.ws_manager = ws_manager
        self.llm_client = get_gemini_client()
        self.decision_parser = None  # Initialized lazily on first use
        
        # Configuration
        settings = get_settings()
        self.total_rounds = settings.crew_deliberation_rounds
        self.min_consensus_percent = settings.crew_min_consensus_percent
        self.enable_mediator = settings.crew_enable_mediator
        
        logger.info(
            "crew_orchestrator_initialized",
            num_agents=len(agents),
            total_rounds=self.total_rounds,
        )
    
    async def run_deliberation_session(
        self,
        market_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run a complete deliberation session.
        
        Args:
            market_context: Current market data, news, prices
            
        Returns:
            Final decision with full deliberation details
        """
        session_id = f"crew_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        logger.info("crew_session_start", session_id=session_id)
        start_time = datetime.utcnow()
        
        # Initialize communication and consensus systems
        communication = AgentCommunication(session_id)
        consensus = ConsensusManager(session_id)
        
        # Create database session record
        with get_db() as db:
            db_session = CrewSession(
                session_id=session_id,
                market_context=market_context,
                symbols_discussed=list(market_context.get("prices", {}).keys()),
                status=SessionStatus.DELIBERATING,
                total_rounds=self.total_rounds,
            )
            db.add(db_session)
            db.commit()
            db.refresh(db_session)
            session_db_id = db_session.id
        
        # Broadcast session start
        await self._broadcast({
            "type": "crew_session_start",
            "session_id": session_id,
            "agents": [agent.name for agent in self.agents],
        })
        
        try:
            # === ROUND 0: Market Discovery (NEW) ===
            await self._update_session_status(session_db_id, SessionStatus.DELIBERATING, 0)
            await self._broadcast({
                "type": "crew_round_start",
                "session_id": session_id,
                "round": 0,
                "description": "Market Discovery - Exploring available options",
            })
            
            discovery_insights = await self._round_0_market_discovery(
                market_context, communication
            )
            
            # Add discovery insights to market context for subsequent rounds
            market_context["discovery_insights"] = discovery_insights
            
            # === ROUND 1: Initial Positions ===
            await self._update_session_status(session_db_id, SessionStatus.DELIBERATING, 1)
            await self._broadcast({
                "type": "crew_round_start",
                "session_id": session_id,
                "round": 1,
                "description": "Initial positions",
            })
            
            initial_positions = await self._round_1_initial_positions(
                market_context, communication
            )
            
            # === ROUND 2: Deliberation ===
            if self.total_rounds >= 2:
                await self._update_session_status(session_db_id, SessionStatus.DELIBERATING, 2)
                await self._broadcast({
                    "type": "crew_round_start",
                    "session_id": session_id,
                    "round": 2,
                    "description": "Deliberation and debate",
                })
                
            await self._round_2_deliberation(
                    market_context, communication, initial_positions
                )
            
            # === CROSS-CRITIQUE ROUND (NEW) ===
            await self._broadcast({
                "type": "crew_round_start",
                "session_id": session_id,
                "round": "2.3",
                "description": "Cross-Critique - Agents evaluate each other's positions",
            })
            
            await self._cross_critique_round(
                market_context, communication, initial_positions
            )
            
            # === DEVIL'S ADVOCATE ROUND ===
            await self._broadcast({
                "type": "crew_round_start",
                "session_id": session_id,
                "round": "2.5",
                "description": "Devil's Advocate Challenge",
            })
            
            await self._devil_advocate_round(
                market_context, communication, initial_positions
            )
            
            # === ROUND 3: Final Voting ===
            await self._update_session_status(session_db_id, SessionStatus.VOTING, self.total_rounds)
            await self._broadcast({
                "type": "crew_round_start",
                "session_id": session_id,
                "round": self.total_rounds,
                "description": "Final voting",
            })
            
            await self._round_3_voting(
                market_context, communication, consensus
            )
            
            # Calculate consensus
            winning_action, consensus_score, vote_details = consensus.calculate_consensus()
            
            # Check for deadlock
            is_deadlock = consensus.detect_deadlock(consensus_score)
            
            final_decision = winning_action
            mediator_used = False
            mediator_reasoning = None
            
            if is_deadlock and self.enable_mediator:
                # Invoke mediator
                await self._update_session_status(session_db_id, SessionStatus.MEDIATOR_INVOKED, self.total_rounds)
                
                mediator_result = await self._invoke_mediator(
                    market_context, communication, vote_details
                )
                
                final_decision = mediator_result["decision"]
                mediator_reasoning = mediator_result["reasoning"]
                mediator_used = True
                
                logger.info(
                    "mediator_invoked",
                    session_id=session_id,
                    mediator_decision=final_decision,
                )
            
            # Determine final symbol if buy/sell
            final_symbol = None
            final_quantity = None
            
            if final_decision in ["buy", "sell"]:
                final_symbol = consensus.get_symbol_consensus()
                # Calculate safe quantity based on portfolio constraints
                final_quantity = await self._calculate_safe_quantity(
                    final_symbol, final_decision, market_context
                )
            
            # Save everything to database
            communication.save_to_database(session_db_id)
            consensus.save_to_database(session_db_id)
            
            # Update session with final results
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            with get_db() as db:
                db_session = db.query(CrewSession).get(session_db_id)
                db_session.status = SessionStatus.CONSENSUS_REACHED if not is_deadlock else SessionStatus.DEADLOCK
                db_session.final_decision = final_decision
                db_session.final_symbol = final_symbol
                db_session.final_quantity = final_quantity
                db_session.consensus_score = consensus_score
                db_session.total_messages = len(communication.message_cache)
                db_session.mediator_used = mediator_used
                db_session.mediator_reasoning = mediator_reasoning
                db_session.completed_at = end_time
                db_session.duration_seconds = duration
                db.commit()
            
            # Broadcast final result
            await self._broadcast({
                "type": "crew_session_complete",
                "session_id": session_id,
                "final_decision": final_decision,
                "final_symbol": final_symbol,
                "consensus_score": consensus_score,
                "mediator_used": mediator_used,
                "duration_seconds": duration,
            })
            
            logger.info(
                "crew_session_complete",
                session_id=session_id,
                final_decision=final_decision,
                consensus_score=consensus_score,
                duration=duration,
            )
            
            return {
                "session_id": session_id,
                "action": final_decision,
                "symbol": final_symbol,
                "quantity": final_quantity,
                "consensus_score": consensus_score,
                "is_deadlock": is_deadlock,
                "mediator_used": mediator_used,
                "mediator_reasoning": mediator_reasoning,
                "vote_details": vote_details,
                "discussion_analysis": communication.analyze_discussion_sentiment(),
                "duration_seconds": duration,
            }
            
        except Exception as e:
            logger.error(
                "crew_session_error",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            
            # Mark session as failed
            with get_db() as db:
                db_session = db.query(CrewSession).get(session_db_id)
                db_session.status = SessionStatus.DEADLOCK
                db_session.completed_at = datetime.utcnow()
                db.commit()
            
            return {
                "session_id": session_id,
                "action": "hold",
                "error": str(e),
            }
    
    async def _round_1_initial_positions(
        self,
        market_context: Dict[str, Any],
        communication: AgentCommunication,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Round 1: Each agent gives their initial position.
        
        Returns:
            Dictionary mapping agent name to their position
        """
        positions = {}
        
        # Run agents in parallel to get initial positions
        tasks = []
        for agent in self.agents:
            tasks.append(self._get_agent_position(agent, market_context))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and send messages
        for idx, (agent, result) in enumerate(zip(self.agents, results)):
            if isinstance(result, Exception):
                logger.error(
                    "agent_position_error",
                    agent=agent.name,
                    error=str(result),
                )
                continue
            
            # Extract position details
            action = result.get("action", "hold")
            symbol = result.get("symbol")
            confidence = result.get("confidence", 75)
            reasoning = result.get("reasoning", "No reasoning provided")
            
            # Send message
            communication.send_message(
                agent_name=agent.name,
                round_number=1,
                message_type=MessageType.POSITION,
                content=reasoning,
                sequence_number=idx,
                proposed_action=action,
                proposed_symbol=symbol,
                confidence_level=confidence,
            )
            
            positions[agent.name] = result
            
            # Broadcast
            await self._broadcast({
                "type": "agent_position",
                "agent": agent.name,
                "round": 1,
                "action": action,
                "symbol": symbol,
                "confidence": confidence,
                "reasoning": reasoning,
            })
        
        return positions
    
    async def _round_0_market_discovery(
        self,
        market_context: Dict[str, Any],
        communication: AgentCommunication,
    ) -> Dict[str, Any]:
        """
        Round 0: Market Discovery Phase (NEW).
        
        Each agent explores the market using discovery tools:
        - get_available_stocks: See what's tradable
        - get_market_overview: Understand overall conditions
        - get_technical_indicators: Analyze candidates
        - compare_stocks: Evaluate options
        
        Returns:
            Aggregated market intelligence from all agents
        """
        logger.info("crew_round_0_start", phase="market_discovery")
        
        discovery_results = {}
        
        # Prompt each agent to discover market opportunities
        for idx, agent in enumerate(self.agents):
            discovery_prompt = f"""
{agent._build_system_prompt()}

MARKET DISCOVERY PHASE:

You are in Round 0 of crew deliberation. Your task is to EXPLORE the market and identify opportunities.

STEP 1: Use 'get_market_overview' to understand current market conditions
STEP 2: Use 'get_available_stocks' to see what stocks are available (filter by your preferred category)
STEP 3: Use 'compare_stocks' to evaluate 3-5 interesting candidates
STEP 4: Use 'get_technical_indicators' on promising stocks to check RSI, MACD, BOLLINGER

MARKET CONTEXT:
{self._format_market_context(market_context)}

Respond with your findings:
- What are the overall market conditions?
- Which stocks did you discover?
- What technical signals did you observe?
- What opportunities or risks do you see?

Focus on EXPLORATION, not final decision yet.
"""
            
            try:
                # Call agent to explore
                response = await self.llm_client.call_agent(
                    model=agent.model,
                    messages=[{"role": "user", "content": discovery_prompt}],
                    tools=TRADING_TOOLS,
                    temperature=0.7,
                )
                
                content = self.llm_client.get_message_content(response)
                tool_calls = self.llm_client.parse_tool_calls(response) if hasattr(self.llm_client, 'parse_tool_calls') else []
                
                # Store discovery results
                discovery_results[agent.name] = {
                    "findings": content,
                    "tools_used": [tc["name"] for tc in tool_calls],
                    "num_tools_used": len(tool_calls),
                }
                
                # Send discovery message
                communication.send_message(
                    agent_name=agent.name,
                    round_number=0,
                    message_type=MessageType.POSITION,
                    content=content,
                    sequence_number=idx,
                )
                
                # Broadcast discovery
                await self._broadcast({
                    "type": "agent_discovery",
                    "agent": agent.name,
                    "round": 0,
                    "findings": content[:500],  # Truncate for broadcast
                    "tools_used": len(tool_calls),
                })
                
                logger.info(
                    "agent_discovery_complete",
                    agent=agent.name,
                    tools_used=len(tool_calls),
                )
                
            except Exception as e:
                logger.error(
                    "agent_discovery_error",
                    agent=agent.name,
                    error=str(e),
                )
                discovery_results[agent.name] = {
                    "findings": f"Discovery error: {str(e)}",
                    "tools_used": [],
                    "num_tools_used": 0,
                }
        
        # Aggregate discovery insights
        total_tools_used = sum(r["num_tools_used"] for r in discovery_results.values())
        
        logger.info(
            "crew_round_0_complete",
            agents_participated=len(discovery_results),
            total_tools_used=total_tools_used,
        )
        
        return {
            "agents_discoveries": discovery_results,
            "total_tools_used": total_tools_used,
            "discovery_complete": True,
        }
    
    async def _round_2_deliberation(
        self,
        market_context: Dict[str, Any],
        communication: AgentCommunication,
        initial_positions: Dict[str, Dict[str, Any]],
    ):
        """
        Round 2: Agents see others' positions and respond.
        """
        # Each agent responds to the discussion
        for idx, agent in enumerate(self.agents):
            # Format discussion history for this agent
            discussion_text = communication.format_discussion_for_agent(
                agent_name=agent.name,
                round_number=2,
                include_previous_rounds=True,
            )
            
            # Get agent's response
            response = await self._get_agent_response(
                agent, market_context, discussion_text
            )
            
            if isinstance(response, Exception):
                logger.error(
                    "agent_response_error",
                    agent=agent.name,
                    error=str(response),
                )
                continue
            
            # Send message - use the parsed message type
            message_type_str = response.get("message_type", "REBUTTAL")
            try:
                message_type = MessageType(message_type_str.lower())
            except ValueError:
                message_type = MessageType.REBUTTAL
            
            communication.send_message(
                agent_name=agent.name,
                round_number=2,
                message_type=message_type,
                content=response.get("content", ""),
                sequence_number=idx,
                proposed_action=response.get("action"),
                proposed_symbol=response.get("symbol"),
                confidence_level=response.get("confidence"),
            )
            
            # Broadcast
            await self._broadcast({
                "type": "agent_message",
                "agent": agent.name,
                "round": 2,
                "message_type": message_type.value,
                "content": response.get("content"),
            })
    
    async def _devil_advocate_round(
        self,
        market_context: Dict[str, Any],
        communication: AgentCommunication,
        initial_positions: Dict[str, Dict[str, Any]],
    ):
        """
        Devil's Advocate Round: Challenge the emerging consensus.
        
        One agent (randomly selected or most contrarian) must argue against
        the majority position to stress-test the decision.
        """
        logger.info("devil_advocate_round_start")
        
        # Determine dominant position
        position_counts = {"buy": 0, "sell": 0, "hold": 0}
        for agent_name, position in initial_positions.items():
            action = position.get("action", "hold").lower()
            if action in position_counts:
                position_counts[action] += 1
        
        dominant_action = max(position_counts, key=position_counts.get)
        
        # Find agent who disagreed (natural devil's advocate) or pick one
        devil_advocate = None
        for agent_name, position in initial_positions.items():
            if position.get("action", "hold").lower() != dominant_action:
                devil_advocate = next((a for a in self.agents if a.name == agent_name), None)
                break
        
        # If all agreed, pick first agent to play devil's advocate
        if devil_advocate is None:
            devil_advocate = self.agents[0]
        
        # Build devil's advocate prompt
        prompt = f"""
{devil_advocate._build_system_prompt()}

=== DEVIL'S ADVOCATE CHALLENGE ===

You have been selected to play "Devil's Advocate" - your job is to CHALLENGE the majority decision.

CURRENT MAJORITY POSITION: {dominant_action.upper()}
Position breakdown: BUY={position_counts['buy']}, SELL={position_counts['sell']}, HOLD={position_counts['hold']}

MARKET CONTEXT:
{self._format_market_context(market_context)}

Your task:
1. Present the STRONGEST POSSIBLE ARGUMENTS AGAINST {dominant_action.upper()}
2. Identify risks the group may be overlooking
3. Use the advanced tools to find counter-evidence:
   - get_fear_greed_index: Is sentiment too extreme?
   - get_advanced_indicators: Is the technical picture overstretched?
   - get_market_regime: Are we in a regime that favors the opposite action?
4. Be constructive but challenging

IMPORTANT: This is NOT about what you believe, but about stress-testing the group's decision.
Present your devil's advocate argument now.
"""

        try:
            response = await self.llm_client.call_agent(
                model=devil_advocate.model,
                messages=[{"role": "user", "content": prompt}],
                tools=TRADING_TOOLS,
                temperature=0.8,  # Higher temperature for creative counter-arguments
            )
            
            content = self.llm_client.get_message_content(response)
            
            # Send devil's advocate message
            communication.send_message(
                agent_name=f"{devil_advocate.name} (Devil's Advocate)",
                round_number=2,
                message_type=MessageType.REBUTTAL,
                content=content,
                sequence_number=99,  # Special sequence for devil's advocate
            )
            
            # Broadcast
            await self._broadcast({
                "type": "devil_advocate",
                "agent": devil_advocate.name,
                "challenging": dominant_action,
                "argument": content[:500],  # Truncate for broadcast
            })
            
            logger.info(
                "devil_advocate_complete",
                agent=devil_advocate.name,
                challenging=dominant_action,
            )
            
        except Exception as e:
            logger.error(
                "devil_advocate_error",
                agent=devil_advocate.name,
                error=str(e),
            )
    
    async def _cross_critique_round(
        self,
        market_context: Dict[str, Any],
        communication: AgentCommunication,
        initial_positions: Dict[str, Dict[str, Any]],
    ):
        """
        Cross-Critique Round: Each agent evaluates other agents' positions.
        
        This enhances decision quality by:
        - Scoring other agents' reasoning (0-100)
        - Identifying strongest and weakest arguments
        - Highlighting overlooked risks or opportunities
        """
        logger.info("cross_critique_round_start")
        
        for idx, agent in enumerate(self.agents):
            # Get other agents' positions
            other_positions = {
                name: pos for name, pos in initial_positions.items() 
                if name != agent.name
            }
            
            if not other_positions:
                continue
            
            # Format other positions for evaluation (skip error positions)
            valid_positions = {
                name: pos for name, pos in other_positions.items()
                if pos.get('action', '').lower() not in ['error', ''] and pos.get('reasoning')
            }
            
            if not valid_positions:
                logger.warning(
                    "cross_critique_no_valid_positions",
                    agent=agent.name,
                    all_positions_count=len(other_positions),
                )
                continue
            
            positions_text = "\n".join([
                f"📊 {name}: {pos.get('action', 'HOLD').upper()} {pos.get('symbol', '')} (Reasoning: {(pos.get('reasoning') or 'N/A')[:200]}...)"
                for name, pos in valid_positions.items()
            ])
            
            prompt = f"""
{agent._build_system_prompt()}

=== CROSS-CRITIQUE ROUND ===

You are evaluating your fellow agents' positions. Your task is to provide constructive critique.

YOUR POSITION: {initial_positions.get(agent.name, {}).get('action', 'HOLD').upper()}

OTHER AGENTS' POSITIONS:
{positions_text}

For EACH agent, provide:
1. SCORE (0-100): How well-reasoned is their position?
2. STRENGTHS: What are the strongest points in their argument?
3. WEAKNESSES: What are they overlooking or getting wrong?
4. SUGGESTED IMPROVEMENT: What additional analysis or tool should they have used?

Use the advanced tools to verify their claims:
- get_advanced_indicators: Check their technical claims
- get_fear_greed_index: Verify sentiment assertions
- get_market_regime: Confirm market conditions

Be constructive and specific. Your critique helps improve overall decision quality.
"""
            
            try:
                response = await self.llm_client.call_agent(
                    model=agent.model,
                    messages=[{"role": "user", "content": prompt}],
                    tools=TRADING_TOOLS,
                    temperature=0.7,
                )
                
                content = self.llm_client.get_message_content(response)
                
                if not content:
                    logger.warning(
                        "cross_critique_empty_content", 
                        agent=agent.name,
                        raw_response_preview=str(response)[:100]
                    )
                    # Skip sending empty message
                    continue

                # Send critique message
                communication.send_message(
                    agent_name=f"{agent.name} (Critique)",
                    round_number=2,
                    message_type=MessageType.REBUTTAL,
                    content=content,
                    sequence_number=50 + idx,  # Sequence for critique round
                )
                
                # Broadcast
                await self._broadcast({
                    "type": "cross_critique",
                    "agent": agent.name,
                    "critique": content[:400],
                })
                
            except Exception as e:
                logger.error(
                    "cross_critique_error",
                    agent=agent.name,
                    error=str(e),
                )
        
        logger.info("cross_critique_round_complete")
    
    async def _round_3_voting(
        self,
        market_context: Dict[str, Any],
        communication: AgentCommunication,
        consensus: ConsensusManager,
    ):
        """
        Round 3: Final voting.
        """
        # Get final votes from all agents
        tasks = []
        for agent in self.agents:
            discussion_text = communication.format_discussion_for_agent(
                agent_name=agent.name,
                round_number=self.total_rounds,
                include_previous_rounds=True,
            )
            tasks.append(self._get_agent_vote(agent, market_context, discussion_text))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process votes
        for agent, result in zip(self.agents, results):
            if isinstance(result, Exception):
                logger.error("agent_vote_error", agent=agent.name, error=str(result))
                # Default vote: hold
                result = {"action": "hold", "confidence": 50}
            
            vote_action = VoteAction(result.get("action", "hold"))
            
            consensus.add_vote(
                agent_name=agent.name,
                vote_action=vote_action,
                vote_symbol=result.get("symbol"),
                reasoning=result.get("reasoning"),
                confidence_level=result.get("confidence", 100),
            )
            
            # Broadcast
            await self._broadcast({
                "type": "agent_vote",
                "agent": agent.name,
                "vote_action": vote_action.value,
                "symbol": result.get("symbol"),
                "confidence": result.get("confidence"),
            })
    
    async def _get_agent_position(
        self,
        agent: Any,
        market_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Get initial position from an agent."""
        try:
            # Use agent's existing make_decision but extract position without executing
            result = await agent.make_decision(market_context)
            
            # Handle error responses
            if result.get("action") == "error":
                error_msg = result.get("error", "Unknown error occurred")
                logger.warning(
                    "agent_position_returned_error",
                    agent=agent.name,
                    error=error_msg,
                )
                return {
                    "action": "hold",
                    "symbol": None,
                    "reasoning": f"Agent encountered an error: {error_msg}. Defaulting to HOLD.",
                    "confidence": 25,  # Low confidence due to error
                }
            
            return {
                "action": result.get("action", "hold"),
                "symbol": result.get("symbol"),
                "reasoning": result.get("reasoning") or "No detailed reasoning provided",
                "confidence": 75,  # Default confidence
            }
        except Exception as e:
            logger.error(
                "agent_position_exception",
                agent=agent.name,
                error=str(e),
            )
            return {
                "action": "hold",
                "symbol": None,
                "reasoning": f"Exception while getting position: {str(e)}. Defaulting to HOLD.",
                "confidence": 10,  # Very low confidence due to exception
            }
    
    async def _get_agent_response(
        self,
        agent: Any,
        market_context: Dict[str, Any],
        discussion_history: str,
    ) -> Dict[str, Any]:
        """Get agent's response to the discussion."""
        # Build prompt for response
        prompt = f"""
{agent._build_system_prompt()}

You are participating in a crew deliberation with other AI trading agents.

MARKET CONTEXT:
{self._format_market_context(market_context)}

DISCUSSION SO FAR:
{discussion_history}

Respond to the discussion. You can:
- Agree with other agents and explain why
- Present counter-arguments with data
- Propose a compromise position
- Ask questions for clarification

Be respectful but express your true analysis. Provide your response and updated position if any.
"""
        
        try:
            response = await self.llm_client.call_agent(
                model=agent.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            
            content = self.llm_client.get_message_content(response)
            
            # Use intelligent parser to extract structured information
            if self.decision_parser is None:
                self.decision_parser = await get_decision_parser()
            
            parsed = await self.decision_parser.parse_agent_response(content, agent.name)
            
            return parsed
        except Exception as e:
            logger.error("agent_response_error", agent=agent.name, error=str(e))
            return {"content": f"Error: {str(e)}", "action": "hold", "message_type": "POSITION"}
    
    async def _get_agent_vote(
        self,
        agent: Any,
        market_context: Dict[str, Any],
        discussion_history: str,
    ) -> Dict[str, Any]:
        """Get final vote from an agent."""
        prompt = f"""
{agent._build_system_prompt()}

MARKET CONTEXT:
{self._format_market_context(market_context)}

FULL DISCUSSION:
{discussion_history}

After hearing all arguments, cast your final vote: BUY, SELL, or HOLD.
If BUY or SELL, specify which symbol.
Provide your confidence level (0-100%) and brief reasoning.

Format:
Vote: [BUY/SELL/HOLD] [SYMBOL if applicable]
Confidence: [0-100]%
Reasoning: [brief explanation]
"""
        
        try:
            response = await self.llm_client.call_agent(
                model=agent.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
            )
            
            content = self.llm_client.get_message_content(response)
            
            # Use intelligent parser for robust extraction
            if self.decision_parser is None:
                self.decision_parser = await get_decision_parser()
            
            parsed = await self.decision_parser.parse_agent_vote(content, agent.name)
            
            return parsed
        except Exception as e:
            logger.error("agent_vote_error", agent=agent.name, error=str(e))
            return {"action": "hold", "confidence": 50, "reasoning": f"Error: {str(e)}"}
    
    async def _invoke_mediator(
        self,
        market_context: Dict[str, Any],
        communication: AgentCommunication,
        vote_details: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Invoke AI mediator to break deadlock."""
        mediator_model = getattr(settings, 'crew_mediator_model', 'openai/gpt-4-turbo-preview')
        
        discussion_summary = communication.format_discussion_for_agent(
            agent_name="Mediator",
            round_number=999,
            include_previous_rounds=True,
        )
        
        vote_summary = self._format_vote_details(vote_details)
        
        prompt = f"""
You are an impartial AI mediator for a trading agent deliberation that has reached deadlock.

MARKET CONTEXT:
{self._format_market_context(market_context)}

FULL DISCUSSION:
{discussion_summary}

VOTING RESULTS:
{vote_summary}

The agents could not reach consensus. As the mediator, analyze all arguments and make the final decision.
Choose: BUY, SELL, or HOLD (and symbol if applicable).
Provide clear reasoning for your decision.

Format:
Decision: [BUY/SELL/HOLD] [SYMBOL if applicable]
Reasoning: [detailed explanation]
"""
        
        try:
            response = await self.llm_client.call_agent(
                model=mediator_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,  # Lower temperature for mediator
            )
            
            content = self.llm_client.get_message_content(response)
            
            # Use intelligent parser for mediator decision
            if self.decision_parser is None:
                self.decision_parser = await get_decision_parser()
            
            parsed = await self.decision_parser.parse_mediator_decision(content)
            decision = parsed["decision"]
            
            await self._broadcast({
                "type": "mediator_decision",
                "decision": decision,
                "reasoning": content,
            })
            
            return {
                "decision": decision,
                "reasoning": content,
            }
        except Exception as e:
            logger.error("mediator_error", error=str(e))
            return {
                "decision": "hold",
                "reasoning": f"Mediator error: {str(e)}. Defaulting to HOLD.",
            }
    
    def _format_market_context(self, market_context: Dict[str, Any]) -> str:
        """Format market context for prompts."""
        import json
        return json.dumps(market_context, indent=2)
    
    def _format_vote_details(self, vote_details: Dict[str, Any]) -> str:
        """Format vote details for display."""
        lines = []
        lines.append(f"Total votes: {vote_details['total_votes']}")
        lines.append(f"Vote breakdown: {vote_details['vote_counts']}")
        lines.append(f"Winning action: {vote_details['winning_action']}")
        lines.append(f"Consensus: {vote_details['consensus_percent']:.1f}%")
        return "\n".join(lines)
    
    async def _update_session_status(
        self,
        session_db_id: int,
        status: SessionStatus,
        round_number: int,
    ):
        """Update session status in database."""
        with get_db() as db:
            db_session = db.query(CrewSession).get(session_db_id)
            db_session.status = status
            db_session.current_round = round_number
            db.commit()
    
    async def _broadcast(self, message: Dict[str, Any]):
        """Broadcast message via WebSocket if available."""
        if self.ws_manager:
            try:
                await self.ws_manager.broadcast(message)
            except Exception as e:
                logger.warning("broadcast_error", error=str(e))
    
    async def _calculate_safe_quantity(
        self,
        symbol: str,
        action: str,
        market_context: Dict[str, Any],
    ) -> int:
        """
        Calculate safe quantity based on portfolio constraints.
        
        This prevents proposing impossible trades like $880K orders
        on a $104 portfolio.
        
        Args:
            symbol: The trading symbol
            action: "buy" or "sell"
            market_context: Market data including prices
            
        Returns:
            Safe quantity (minimum of 1 if calculation fails for buy,
            or actual position quantity for sell)
        """
        risk_manager = get_risk_manager()
        
        # Get current price from market context
        prices = market_context.get("prices", {})
        price_data = prices.get(symbol, {})
        
        if isinstance(price_data, dict):
            current_price = price_data.get("price", 0) or price_data.get("current", 0)
        else:
            current_price = float(price_data) if price_data else 0
        
        if current_price <= 0:
            logger.warning(
                "cannot_calculate_quantity_no_price",
                symbol=symbol,
                price_data=price_data,
            )
            # Return minimal quantity as fallback
            return 1
        
        # For sell orders, we should check actual positions
        # For now, calculate based on buy constraints (conservative)
        
        # Calculate for a representative agent (use first agent or average)
        max_quantities = []
        
        for agent in self.agents:
            result = risk_manager.calculate_max_quantity(
                agent_name=agent.name,
                symbol=symbol,
                price=current_price,
            )
            max_quantities.append(result["max_quantity"])
        
        if not max_quantities:
            logger.warning("no_agents_for_quantity_calculation")
            return 1
        
        # Use median to avoid outliers affecting the crew decision
        max_quantities.sort()
        median_idx = len(max_quantities) // 2
        safe_quantity = max_quantities[median_idx]
        
        # Ensure at least 1 for a valid trade
        safe_quantity = max(1, safe_quantity)
        
        logger.info(
            "crew_safe_quantity_calculated",
            symbol=symbol,
            action=action,
            current_price=current_price,
            agent_max_quantities=max_quantities,
            final_quantity=safe_quantity,
        )
        
        return safe_quantity

