"""
Generic AI Agent.
Can be configured for any role via AGENT_CONFIGS.
Differs from specialized agents in that it builds its prompt purely from config.
"""
from typing import Dict, Any, List
from agents.base_agent import BaseAgent

class GenericAgent(BaseAgent):
    """
    Generic agent that adapts its behavior based on configuration.
    Used for dynamically added agents like Researchers, specialized traders, etc.
    """
    
    def __init__(self, agent_key: str):
        super().__init__(agent_key)
        
    def _build_system_prompt(self) -> str:
        """Build a system prompt dynamically based on configuration."""
        
        # Base intro
        prompt = f"""You are {self.name}, a {self.personality} following a {self.strategy} strategy.
        
PERSONALITY & STRATEGY:
- Personality: {self.personality}
- Strategy: {self.strategy}
- Risk Tolerance: {self.risk_tolerance}
- Trading Frequency: {self.config.get('trading_frequency', 'Medium')}
"""

        # Add focus sectors if available
        sectors = self.config.get('focus_sectors', [])
        if sectors:
            prompt += "\nFOCUS SECTORS:\n" + "\n".join([f"- {s}" for s in sectors]) + "\n"
            
        # Add preferred symbols/pairs
        symbols = self.config.get('preferred_symbols', [])
        crypto_pairs = self.config.get('preferred_crypto_pairs', [])
        
        if symbols:
            prompt += f"\nPREFERRED STOCKS: {', '.join(symbols)}\n"
        if crypto_pairs:
            prompt += f"PREFERRED CRYPTO: {', '.join(crypto_pairs)}\n"
            
        # Specific instructions for Researcher (support agent)
        if self.config.get("is_support_agent"):
            prompt += """
ROLE: SUPPORT AGENT
- Your goal is NOT to trade directly, but to provide high-quality intelligence.
- Analyze data deeply and provide specific, actionable insights.
- Use your tools to gather accurate up-to-date information.
"""
        else:
            # Instructions for Trading Agents
            prompt += """
ROLE: TRADING AGENT
- You have authority to execute trades within your risk limits.
- Evaluate opportunities based on your specific strategy.
- Don't force trades - only act when your criteria are met.
- Monitor your portfolio and manage risk actively.
"""

        # Add standard reasoning framework
        prompt += """
DECISION FRAMEWORK:
1. ANALYZE: Check market conditions, news, and technicals.
2. FILTER: Does this asset match my focus sectors and strategy?
3. VERIFY: Do technical indicators confirm the fundamental view?
4. SIZE: specific position size based on risk tolerance.
5. EXECUTE: Use the appropriate tool (buy_stock, buy_crypto, etc).

Always explain your reasoning before taking action.
"""

        # Add extra custom instructions from config if any (future proofing)
        if "custom_instructions" in self.config:
            prompt += f"\nADDITIONAL INSTRUCTIONS:\n{self.config['custom_instructions']}\n"
            
        return prompt
