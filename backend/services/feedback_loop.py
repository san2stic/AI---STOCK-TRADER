"""
Feedback Loop Service - Generates structured learning feedback for agents.
Uses LLM to analyze trade outcomes and create actionable lessons.
"""
import structlog
from typing import Dict, Any, Optional
from datetime import datetime

from models.database import Trade, Decision
from models.trade_outcome import TradeOutcome, OutcomeCategory
from models.database import AgentReflection
from database import get_db
from services.openrouter import get_openrouter_client
from config import AGENT_CONFIGS

logger = structlog.get_logger()


class FeedbackLoop:
    """
    Automated feedback generation for agent learning.
    Analyzes completed trades and generates actionable lessons.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FeedbackLoop, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.openrouter = get_openrouter_client()
            logger.info("feedback_loop_initialized")
    
    async def generate_trade_feedback(
        self, 
        trade_id: int, 
        outcome: TradeOutcome
    ) -> Optional[str]:
        """
        Generate structured feedback for a completed trade.
        Uses the agent's own LLM to analyze what went wrong/right.
        
        Returns feedback text that will be stored as a lesson.
        """
        try:
            with get_db() as db:
                trade = db.query(Trade).filter(Trade.id == trade_id).first()
                
                if not trade:
                    logger.warning("trade_not_found_for_feedback", trade_id=trade_id)
                    return None
                
                # Get the decision context
                decision = None
                if trade.decision_id:
                    decision = db.query(Decision).filter(
                        Decision.id == trade.decision_id
                    ).first()
                
                # Prepare trade analysis data
                trade_data = {
                    "symbol": trade.symbol,
                    "action": trade.action.value,
                    "quantity": trade.quantity,
                    "entry_price": outcome.entry_price,
                    "close_price": outcome.close_price,
                    "pnl_percent": outcome.pnl_percent,
                    "pnl_amount": outcome.pnl_amount,
                    "hold_duration_hours": outcome.hold_duration_hours,
                    "outcome": outcome.outcome_category.value,
                    "error_type": outcome.error_classification.value if outcome.error_classification else None,
                    "reasoning": trade.reasoning,
                    "market_condition": outcome.market_condition,
                    "strategy": outcome.strategy_used,
                }
                
                # Get agent config
                agent_name = trade.agent_name
                agent_config = None
                for key, config in AGENT_CONFIGS.items():
                    if config["name"] == agent_name:
                        agent_config = config
                        break
                
                if not agent_config:
                    logger.warning("agent_config_not_found", agent_name=agent_name)
                    return None
                
                # Generate feedback using LLM
                feedback = await self._analyze_with_llm(
                    agent_name=agent_name,
                    agent_model=agent_config["model"],
                    trade_data=trade_data,
                    decision_context=decision
                )
                
                if feedback:
                    # Store feedback as lesson
                    await self.store_feedback_as_lesson(agent_name, feedback, trade_data)
                    
                    # Mark outcome as analyzed
                    outcome.learning_extracted = True
                    db.commit()
                    
                    logger.info(
                        "feedback_generated",
                        trade_id=trade_id,
                        agent_name=agent_name,
                        outcome=outcome.outcome_category.value
                    )
                
                return feedback
                
        except Exception as e:
            logger.error("generate_trade_feedback_error", error=str(e))
            return None
    
    async def _analyze_with_llm(
        self,
        agent_name: str,
        agent_model: str,
        trade_data: Dict[str, Any],
        decision_context: Optional[Decision]
    ) -> Optional[str]:
        """Use agent's LLM to analyze the trade outcome."""
        try:
            # Build analysis prompt
            outcome_emoji = "✅" if trade_data["outcome"] == "win" else "❌" if trade_data["outcome"] == "loss" else "➖"
            
            prompt = f"""
You are {agent_name}, analyzing one of your completed trades for learning purposes.

{outcome_emoji} TRADE OUTCOME ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Symbol: {trade_data['symbol']}
Action: {trade_data['action'].upper()}
Entry Price: ${trade_data['entry_price']:.2f}
Close Price: ${trade_data['close_price']:.2f}
P&L: {trade_data['pnl_percent']:.2f}% (${trade_data['pnl_amount']:.2f})
Hold Duration: {trade_data['hold_duration_hours']:.1f} hours
Outcome: {trade_data['outcome'].upper()}
Strategy Used: {trade_data['strategy'] or 'Unknown'}
Market Condition: {trade_data['market_condition'] or 'Unknown'}

YOUR ORIGINAL REASONING:
{trade_data['reasoning'] or 'No reasoning recorded'}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REFLECTION REQUIRED:

1. **What Happened**: Briefly explain the outcome in 1-2 sentences.

2. **Root Cause Analysis**:
   - If LOSS: What specifically went wrong? Was it timing, analysis, risk management, or external factors?
   - If WIN: What specific factors led to success? Can you replicate this?

3. **Lesson Learned** (Most Important!):
   Write ONE clear, actionable lesson in this format:
   "LESSON: [Specific situation/condition] → [Action I will take]"
   
   Example: "LESSON: When entering momentum trades, if price drops >2% within first hour → Exit immediately rather than hoping for recovery"

4. **Future Action**:
   What will you do differently next time you see a similar setup?

Be honest and specific. Your future performance depends on learning from this.
"""
            
            messages = [
                {"role": "system", "content": f"You are {agent_name}, reflecting on your trading performance."},
                {"role": "user", "content": prompt}
            ]
            
            response = await self.openrouter.call_agent(
                model=agent_model,
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            feedback = self.openrouter.get_message_content(response)
            return feedback
            
        except Exception as e:
            logger.error("analyze_with_llm_error", error=str(e))
            return None
    
    async def store_feedback_as_lesson(
        self,
        agent_name: str,
        feedback: str,
        trade_data: Dict[str, Any]
    ) -> bool:
        """Store generated feedback as an AgentReflection for future reference."""
        try:
            with get_db() as db:
                # Extract lesson from feedback
                lesson = self._extract_lesson(feedback)
                
                reflection = AgentReflection(
                    agent_name=agent_name,
                    trades_analyzed=[trade_data],
                    performance_stats={
                        "single_trade_pnl": trade_data["pnl_percent"],
                        "outcome": trade_data["outcome"],
                        "strategy": trade_data["strategy"],
                    },
                    what_went_well="" if trade_data["outcome"] == "loss" else feedback,
                    what_went_wrong=feedback if trade_data["outcome"] == "loss" else "",
                    improvements_planned=lesson or feedback,
                    raw_reflection=feedback
                )
                
                db.add(reflection)
                db.commit()
                
                logger.info(
                    "feedback_stored_as_lesson",
                    agent_name=agent_name,
                    has_lesson=bool(lesson)
                )
                
                return True
                
        except Exception as e:
            logger.error("store_feedback_error", error=str(e))
            return False
    
    def _extract_lesson(self, feedback: str) -> Optional[str]:
        """Extract the LESSON line from feedback."""
        lines = feedback.split('\n')
        for line in lines:
            if line.strip().startswith("LESSON:"):
                return line.strip()
        return None
    
    async def trigger_on_position_close(self, trade_id: int) -> bool:
        """
        Hook to trigger feedback generation when a position closes.
        Can be called from trade execution or monitoring systems.
        """
        try:
            from services.error_tracker import get_error_tracker
            
            error_tracker = get_error_tracker()
            
            # First track the outcome
            outcome_id = await error_tracker.track_trade_outcome(trade_id)
            
            if not outcome_id:
                return False
            
            # Get the outcome
            with get_db() as db:
                outcome = db.query(TradeOutcome).filter(
                    TradeOutcome.id == outcome_id
                ).first()
                
                if outcome and not outcome.learning_extracted:
                    # Generate feedback
                    await self.generate_trade_feedback(trade_id, outcome)
                    return True
            
            return False
            
        except Exception as e:
            logger.error("trigger_on_position_close_error", error=str(e))
            return False


# Singleton instance
def get_feedback_loop() -> FeedbackLoop:
    """Get the singleton FeedbackLoop instance."""
    return FeedbackLoop()
