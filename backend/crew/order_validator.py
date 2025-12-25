"""
Order Execution Validator - Final safety check before executing trades.
Uses a powerful model (Claude 4.5) to validate crew decisions.
"""
from typing import Dict, Any, Optional
import structlog
from config import get_settings
from services.openrouter import get_openrouter_client

logger = structlog.get_logger()
settings = get_settings()


class OrderValidator:
    """
    Final validation layer before order execution.
    Uses Claude 4.5 to perform sanity checks on crew decisions.
    """
    
    def __init__(self):
        self.openrouter = get_openrouter_client()
        # Use Claude 4.5 or another powerful model for validation
        self.validator_model = getattr(
            settings, 
            'order_validator_model', 
            'anthropic/claude-sonnet-4.5'
        )
        
        logger.info(
            "order_validator_initialized",
            model=self.validator_model,
        )
    
    async def validate_order(
        self,
        crew_decision: Dict[str, Any],
        market_context: Dict[str, Any],
        portfolio_state: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Validate a crew decision before execution.
        
        Args:
            crew_decision: The consensus decision from the crew
            market_context: Current market data
            portfolio_state: Current portfolio state (if available)
            
        Returns:
            Validation result with approved/rejected status and reasoning
        """
        action = crew_decision.get("action", "hold")
        symbol = crew_decision.get("symbol")
        quantity = crew_decision.get("quantity")
        consensus_score = crew_decision.get("consensus_score", 0)
        
        # If HOLD, no validation needed
        if action == "hold":
            return {
                "approved": True,
                "action": "hold",
                "reasoning": "No trade to validate - HOLD position",
                "risk_level": "none",
            }
        
        logger.info(
            "validating_order",
            action=action,
            symbol=symbol,
            quantity=quantity,
            consensus=consensus_score,
        )
        
        # Build validation prompt
        prompt = self._build_validation_prompt(
            crew_decision, 
            market_context, 
            portfolio_state
        )
        
        try:
            # Call Claude 4.5 for validation
            response = await self.openrouter.call_agent(
                model=self.validator_model,
                messages=[
                    {
                        "role": "system",
                        "content": self._build_system_prompt(),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                temperature=0.1,  # Very low temperature for consistent validation
            )
            
            validation_text = self.openrouter.get_message_content(response)
            
            # Parse validation result
            result = self._parse_validation_result(validation_text)
            
            logger.info(
                "order_validation_complete",
                approved=result["approved"],
                risk_level=result.get("risk_level"),
                action=action,
                symbol=symbol,
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "order_validation_error",
                error=str(e),
                action=action,
                symbol=symbol,
            )
            
            # In case of error, reject for safety
            return {
                "approved": False,
                "action": action,
                "symbol": symbol,
                "reasoning": f"Validation failed due to error: {str(e)}",
                "risk_level": "unknown",
                "error": str(e),
            }
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for the validator."""
        return """You are an ORDER EXECUTION VALIDATOR for an AI trading system.

Your CRITICAL MISSION is to perform final safety checks on trading decisions before execution.

You must validate:
1. **Market Hours**: Is the market open? (US market: Mon-Fri 9:30 AM - 4:00 PM EST)
2. **Risk Limits**: Does the order violate position size limits, stop-loss rules, or circuit breakers?
3. **Data Quality**: Is there sufficient data to support this decision?
4. **Execution Feasibility**: Can this order be executed (liquidity, price limits)?
5. **Sanity Check**: Does this decision make sense given the context?

RESPOND IN THIS EXACT FORMAT:

APPROVED: [YES/NO]
RISK_LEVEL: [LOW/MEDIUM/HIGH/CRITICAL]
REASONING: [Clear explanation of your decision]
MODIFICATIONS: [Any suggested modifications, or "None"]

BE CONSERVATIVE. When in doubt, REJECT.
Your job is to prevent costly mistakes, not to maximize trades.
"""
    
    def _build_validation_prompt(
        self,
        crew_decision: Dict[str, Any],
        market_context: Dict[str, Any],
        portfolio_state: Optional[Dict[str, Any]],
    ) -> str:
        """Build the validation prompt."""
        import json
        from datetime import datetime
        
        action = crew_decision.get("action")
        symbol = crew_decision.get("symbol")
        quantity = crew_decision.get("quantity")
        consensus_score = crew_decision.get("consensus_score")
        mediator_used = crew_decision.get("mediator_used")
        
        prompt = f"""
VALIDATE THIS ORDER:

**PROPOSED TRADE:**
- Action: {action.upper()}
- Symbol: {symbol}
- Quantity: {quantity} shares
- Consensus Score: {consensus_score:.1f}%
- Mediator Used: {mediator_used}

**CREW REASONING:**
{crew_decision.get('mediator_reasoning', 'Not provided')}

**MARKET CONTEXT:**
Current Time (UTC): {market_context.get('timestamp', datetime.utcnow().isoformat())}
Prices: {json.dumps(market_context.get('prices', {}), indent=2)}

**PORTFOLIO STATE:**
{json.dumps(portfolio_state, indent=2) if portfolio_state else 'Portfolio data not provided'}

**RISK MANAGEMENT RULES:**
- Maximum position size: {settings.max_trade_percent}% of portfolio
- Stop-loss threshold: {settings.stop_loss_percent}%
- Circuit breaker: {settings.circuit_breaker_percent}% daily loss
- Maximum concurrent positions: {settings.max_positions}

**YOUR TASK:**
Validate this order against all safety criteria. Check:
1. Market hours compliance
2. Risk limit compliance
3. Data sufficiency
4. Execution feasibility
5. Overall sanity

Provide your decision in the required format.
"""
        return prompt
    
    def _parse_validation_result(self, validation_text: str) -> Dict[str, Any]:
        """Parse the validation response."""
        lines = validation_text.strip().split('\n')
        
        result = {
            "approved": False,
            "risk_level": "unknown",
            "reasoning": "",
            "modifications": "None",
            "raw_validation": validation_text,
        }
        
        for line in lines:
            line_upper = line.upper()
            
            if line_upper.startswith("APPROVED:"):
                approved_text = line.split(":", 1)[1].strip().upper()
                result["approved"] = "YES" in approved_text or "TRUE" in approved_text
            
            elif line_upper.startswith("RISK_LEVEL:"):
                risk_text = line.split(":", 1)[1].strip().upper()
                if "LOW" in risk_text:
                    result["risk_level"] = "low"
                elif "MEDIUM" in risk_text:
                    result["risk_level"] = "medium"
                elif "HIGH" in risk_text:
                    result["risk_level"] = "high"
                elif "CRITICAL" in risk_text:
                    result["risk_level"] = "critical"
            
            elif line_upper.startswith("REASONING:"):
                result["reasoning"] = line.split(":", 1)[1].strip()
            
            elif line_upper.startswith("MODIFICATIONS:"):
                result["modifications"] = line.split(":", 1)[1].strip()
        
        # Capture any reasoning text that wasn't captured by the prefix
        if not result["reasoning"]:
            # Look for reasoning in the full text
            reasoning_start = validation_text.find("REASONING:")
            if reasoning_start >= 0:
                result["reasoning"] = validation_text[reasoning_start + 10:].strip()
        
        return result


# Singleton instance
_order_validator: Optional[OrderValidator] = None


def get_order_validator() -> OrderValidator:
    """Get or create the order validator instance."""
    global _order_validator
    if _order_validator is None:
        _order_validator = OrderValidator()
    return _order_validator
