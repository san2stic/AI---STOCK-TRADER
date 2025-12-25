"""
Intelligent decision parsing service using Claude 4.5 Sonnet.
Provides robust extraction of trading decisions, votes, and agent responses.
"""
from typing import Dict, Any, Optional, List
import re
import json
import structlog
from services.gemini_client import get_gemini_client
from services.parsing_cache import get_parsing_cache
from models.crew_models import MessageType
from config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class DecisionParser:
    """
    Intelligent parser for AI agent decisions using Claude 4.5 Sonnet.
    Falls back to regex parsing if Claude API fails.
    """
    
    def __init__(self):
        """Initialize the decision parser."""
        self.llm_client = get_gemini_client()
        self.cache = get_parsing_cache() if settings.parsing_cache_enabled else None
        self.model = settings.claude_parsing_model
        self.enabled = settings.enable_intelligent_parsing
        
        logger.info(
            "decision_parser_initialized",
            intelligent_parsing=self.enabled,
            cache_enabled=settings.parsing_cache_enabled,
            model=self.model,
        )
    
    async def parse_agent_vote(self, content: str, agent_name: str = "") -> Dict[str, Any]:
        """
        Parse an agent's final vote from free-form text.
        
        Extracts:
        - action: buy/sell/hold
        - symbol: stock/crypto symbol (if applicable)
        - confidence: 0-100
        - reasoning: explanation
        
        Args:
            content: The agent's vote response text
            agent_name: Name of the agent (for logging)
            
        Returns:
            Dictionary with parsed vote information
        """
        # Check cache first
        if self.cache:
            cached = self.cache.get(content, "vote")
            if cached:
                logger.debug("vote_parse_cache_hit", agent=agent_name)
                return cached
        
        # Try intelligent parsing if enabled
        if self.enabled:
            try:
                result = await self._parse_vote_with_claude(content, agent_name)
                
                # Cache the result
                if self.cache:
                    self.cache.set(content, "vote", result)
                
                return result
            except Exception as e:
                logger.warning(
                    "claude_parse_vote_failed",
                    agent=agent_name,
                    error=str(e),
                    fallback="regex",
                )
        
        # Fallback to regex parsing
        result = self._parse_vote_with_regex(content)
        
        # Cache even regex results
        if self.cache:
            self.cache.set(content, "vote", result)
        
        return result
    
    async def _parse_vote_with_claude(self, content: str, agent_name: str) -> Dict[str, Any]:
        """
        Parse vote using Claude 4.5 Sonnet for semantic understanding.
        
        Args:
            content: Vote text to parse
            agent_name: Agent name for context
            
        Returns:
            Structured vote data
        """
        prompt = f"""You are a precise data extraction system for trading decisions.

Extract the following information from this agent's vote:

AGENT VOTE:
{content}

Extract and return ONLY a JSON object with these exact fields:
{{
  "action": "buy" | "sell" | "hold",
  "symbol": "STOCK_SYMBOL" or null,
  "confidence": 0-100 (number),
  "reasoning": "brief explanation or quote from vote"
}}

Rules:
- action must be lowercase: "buy", "sell", or "hold"
- symbol should be uppercase ticker (e.g., "AAPL", "BTCUSDT") or null if not specified
- confidence should be a number between 0-100
- reasoning should be concise (max 200 characters)

Return ONLY valid JSON, no markdown or explanation."""

        response = await self.llm_client.call_agent(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,  # Low temperature for consistent extraction
        )
        
        result_text = self.llm_client.get_message_content(response)
        
        # Parse JSON from response
        # Remove markdown code blocks if present
        result_text = result_text.strip()
        if result_text.startswith("```"):
            result_text = re.sub(r'^```(?:json)?\n?', '', result_text)
            result_text = re.sub(r'\n?```$', '', result_text)
        
        parsed = json.loads(result_text)
        
        # Validate and normalize
        result = {
            "action": str(parsed.get("action", "hold")).lower(),
            "symbol": parsed.get("symbol"),
            "confidence": int(parsed.get("confidence", 75)),
            "reasoning": str(parsed.get("reasoning", content[:200])),
        }
        
        # Ensure action is valid
        if result["action"] not in ["buy", "sell", "hold"]:
            result["action"] = "hold"
        
        # Ensure confidence is in range
        result["confidence"] = max(0, min(100, result["confidence"]))
        
        logger.info(
            "claude_vote_parsed",
            agent=agent_name,
            action=result["action"],
            symbol=result["symbol"],
            confidence=result["confidence"],
        )
        
        return result
    
    def _parse_vote_with_regex(self, content: str) -> Dict[str, Any]:
        """
        Fallback regex-based vote parsing.
        
        Args:
            content: Vote text to parse
            
        Returns:
            Structured vote data
        """
        action = "hold"
        symbol = None
        confidence = 75
        
        # Extract action
        if "BUY" in content.upper():
            action = "buy"
        elif "SELL" in content.upper():
            action = "sell"
        
        # Extract symbol (2-5 uppercase letters)
        symbol_match = re.search(r'\b([A-Z]{2,5})\b', content)
        if symbol_match:
            symbol = symbol_match.group(1)
        
        # Extract confidence percentage
        conf_match = re.search(r'(\d+)%', content)
        if conf_match:
            confidence = int(conf_match.group(1))
            confidence = max(0, min(100, confidence))
        
        logger.debug(
            "regex_vote_parsed",
            action=action,
            symbol=symbol,
            confidence=confidence,
        )
        
        return {
            "action": action,
            "symbol": symbol,
            "confidence": confidence,
            "reasoning": content,
        }
    
    async def parse_agent_response(self, content: str, agent_name: str = "") -> Dict[str, Any]:
        """
        Parse an agent's response during deliberation.
        
        Extracts:
        - content: the message
        - action: proposed action (if any)
        - symbol: proposed symbol (if any)
        - confidence: confidence level
        - message_type: POSITION, REBUTTAL, AGREEMENT, COMPROMISE, QUESTION
        - mentioned_agents: list of agent names mentioned
        
        Args:
            content: The agent's response text
            agent_name: Name of the agent
            
        Returns:
            Dictionary with parsed response information
        """
        # Check cache
        if self.cache:
            cached = self.cache.get(content, "response")
            if cached:
                logger.debug("response_parse_cache_hit", agent=agent_name)
                return cached
        
        # Try intelligent parsing
        if self.enabled:
            try:
                result = await self._parse_response_with_claude(content, agent_name)
                
                if self.cache:
                    self.cache.set(content, "response", result)
                
                return result
            except Exception as e:
                logger.warning(
                    "claude_parse_response_failed",
                    agent=agent_name,
                    error=str(e),
                    fallback="regex",
                )
        
        # Fallback
        result = self._parse_response_with_regex(content)
        
        if self.cache:
            self.cache.set(content, "response", result)
        
        return result
    
    async def _parse_response_with_claude(self, content: str, agent_name: str) -> Dict[str, Any]:
        """
        Parse agent response using Claude for semantic understanding.
        
        Args:
            content: Response text
            agent_name: Agent name
            
        Returns:
            Structured response data
        """
        prompt = f"""You are a precise data extraction system for trading agent discussions.

Extract information from this agent's discussion response:

AGENT RESPONSE:
{content}

Extract and return ONLY a JSON object:
{{
  "action": "buy" | "sell" | "hold" | null,
  "symbol": "SYMBOL" or null,
  "confidence": 0-100 or null,
  "message_type": "POSITION" | "REBUTTAL" | "AGREEMENT" | "COMPROMISE" | "QUESTION",
  "sentiment": "bullish" | "bearish" | "neutral",
  "mentioned_agents": ["agent1", "agent2"] or [],
  "key_points": ["point1", "point2"]
}}

Message type definitions:
- POSITION: Initial stance or clear position statement
- REBUTTAL: Disagreement or counter-argument
- AGREEMENT: Supporting another agent's position
- COMPROMISE: Proposing middle ground
- QUESTION: Asking for clarification

Return ONLY valid JSON."""

        response = await self.llm_client.call_agent(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        
        result_text = self.llm_client.get_message_content(response)
        
        # Clean and parse JSON
        result_text = result_text.strip()
        if result_text.startswith("```"):
            result_text = re.sub(r'^```(?:json)?\n?', '', result_text)
            result_text = re.sub(r'\n?```$', '', result_text)
        
        parsed = json.loads(result_text)
        
        result = {
            "content": content,
            "action": str(parsed.get("action")).lower() if parsed.get("action") else None,
            "symbol": parsed.get("symbol"),
            "confidence": int(parsed.get("confidence")) if parsed.get("confidence") else 75,
            "message_type": parsed.get("message_type", "POSITION"),
            "sentiment": parsed.get("sentiment", "neutral"),
            "mentioned_agents": parsed.get("mentioned_agents", []),
            "key_points": parsed.get("key_points", []),
        }
        
        # Validate action
        if result["action"] and result["action"] not in ["buy", "sell", "hold"]:
            result["action"] = None
        
        logger.info(
            "claude_response_parsed",
            agent=agent_name,
            message_type=result["message_type"],
            sentiment=result["sentiment"],
        )
        
        return result
    
    def _parse_response_with_regex(self, content: str) -> Dict[str, Any]:
        """
        Fallback regex-based response parsing.
        
        Args:
            content: Response text
            
        Returns:
            Structured response data
        """
        # Detect message type
        message_type = MessageType.POSITION
        content_lower = content.lower()
        
        if "agree" in content_lower or "support" in content_lower:
            message_type = MessageType.AGREEMENT
        elif "disagree" in content_lower or "counter" in content_lower or "however" in content_lower:
            message_type = MessageType.REBUTTAL
        elif "compromise" in content_lower or "middle" in content_lower:
            message_type = MessageType.COMPROMISE
        elif "?" in content or "question" in content_lower:
            message_type = MessageType.QUESTION
        
        return {
            "content": content,
            "action": None,
            "symbol": None,
            "confidence": 75,
            "message_type": message_type.value,
            "sentiment": "neutral",
            "mentioned_agents": [],
            "key_points": [],
        }
    
    async def parse_mediator_decision(self, content: str) -> Dict[str, Any]:
        """
        Parse the mediator's final decision.
        
        Args:
            content: Mediator's decision text
            
        Returns:
            Dictionary with decision and reasoning
        """
        # Check cache
        if self.cache:
            cached = self.cache.get(content, "mediator")
            if cached:
                logger.debug("mediator_parse_cache_hit")
                return cached
        
        # Try intelligent parsing
        if self.enabled:
            try:
                result = await self._parse_mediator_with_claude(content)
                
                if self.cache:
                    self.cache.set(content, "mediator", result)
                
                return result
            except Exception as e:
                logger.warning(
                    "claude_parse_mediator_failed",
                    error=str(e),
                    fallback="regex",
                )
        
        # Fallback
        result = self._parse_mediator_with_regex(content)
        
        if self.cache:
            self.cache.set(content, "mediator", result)
        
        return result
    
    async def _parse_mediator_with_claude(self, content: str) -> Dict[str, Any]:
        """Parse mediator decision with Claude."""
        prompt = f"""Extract the mediator's final trading decision:

MEDIATOR DECISION:
{content}

Return ONLY a JSON object:
{{
  "decision": "buy" | "sell" | "hold",
  "symbol": "SYMBOL" or null,
  "reasoning": "brief explanation"
}}

Return ONLY valid JSON."""

        response = await self.llm_client.call_agent(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        
        result_text = self.llm_client.get_message_content(response)
        
        # Clean and parse
        result_text = result_text.strip()
        if result_text.startswith("```"):
            result_text = re.sub(r'^```(?:json)?\n?', '', result_text)
            result_text = re.sub(r'\n?```$', '', result_text)
        
        parsed = json.loads(result_text)
        
        return {
            "decision": str(parsed.get("decision", "hold")).lower(),
            "symbol": parsed.get("symbol"),
            "reasoning": str(parsed.get("reasoning", content)),
        }
    
    def _parse_mediator_with_regex(self, content: str) -> Dict[str, Any]:
        """Fallback regex-based mediator parsing."""
        decision = "hold"
        
        if "BUY" in content.upper():
            decision = "buy"
        elif "SELL" in content.upper():
            decision = "sell"
        
        return {
            "decision": decision,
            "symbol": None,
            "reasoning": content,
        }
    
    def get_cache_stats(self) -> Optional[Dict[str, Any]]:
        """Get cache statistics if cache is enabled."""
        if self.cache:
            return self.cache.get_stats()
        return None


# Global parser instance
_global_parser: Optional[DecisionParser] = None


async def get_decision_parser() -> DecisionParser:
    """Get or create the global decision parser instance."""
    global _global_parser
    if _global_parser is None:
        _global_parser = DecisionParser()
        logger.info("decision_parser_instance_created")
    return _global_parser
