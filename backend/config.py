"""
Configuration management for the trading system.
Centralized settings loaded from environment variables.
"""
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator


class Settings(BaseSettings):
    """Main configuration class with validation."""
    
    # Trading mode
    trading_mode: str = Field(default="PAPER", description="PAPER or LIVE")
    initial_capital: float = Field(default=10000.0, ge=100.0)
    
    # OpenRouter API
    openrouter_api_key: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    
    # Alpaca Markets (Free API)
    alpaca_api_key: str
    alpaca_api_secret: str
    alpaca_base_url: str = "https://paper-api.alpaca.markets"  # Paper trading by default
    
    # Binance API (Crypto Trading)
    binance_api_key: str = ""  # Optional, empty = crypto trading disabled
    binance_api_secret: str = ""  # Optional, empty = crypto trading disabled
    binance_testnet: bool = True  # Use testnet for paper trading crypto
    
    # Data sources
    news_api_key: Optional[str] = None
    twitter_api_key: Optional[str] = None
    twitter_api_secret: Optional[str] = None
    twitter_bearer_token: Optional[str] = None
    
    # Database
    database_url: str
    
    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    
    # Risk management
    max_trade_percent: float = Field(default=10.0, ge=1.0, le=50.0)
    stop_loss_percent: float = Field(default=15.0, ge=5.0, le=50.0)
    circuit_breaker_percent: float = Field(default=5.0, ge=1.0, le=20.0)
    max_positions: int = Field(default=10, ge=1, le=50)
    
    # Crypto-specific risk management
    crypto_enabled: bool = True
    crypto_trade_percent: float = Field(default=5.0, ge=1.0, le=25.0)  # Lower than stocks due to volatility
    crypto_stop_loss_percent: float = Field(default=20.0, ge=10.0, le=50.0)  # Higher threshold for volatility
    use_all_binance_pairs: bool = True  # Allow trading all available pairs on Binance
    allowed_crypto_pairs: str = ""  # Optional whitelist, empty = all available pairs
    
    # Market configuration
    
    # Multi-market configuration
    us_market_open_hour: int = 9
    us_market_open_minute: int = 30
    us_market_close_hour: int = 16
    us_market_close_minute: int = 0
    
    europe_market_open_hour: int = 9
    europe_market_open_minute: int = 0
    europe_market_close_hour: int = 17
    europe_market_close_minute: int = 30
    
    asia_market_open_hour: int = 9
    asia_market_open_minute: int = 0
    asia_market_close_hour: int = 15
    asia_market_close_minute: int = 0
    
    active_markets: str = "US,EUROPE"  # Comma-separated: US,EUROPE,ASIA
    market_strategy: str = "ANY"  # ANY or ALL
    
    # Trading configuration
    trading_interval_minutes: int = Field(default=30, ge=5, le=120)
    enable_extended_hours: bool = False
    enforce_market_hours: bool = True  # Set to False to ignore all market hours
    run_analysis_on_startup: bool = False  # Run market analysis when container starts (disabled by default for faster startup)

    # Market calendar & economic events
    enable_holiday_check: bool = True  # Check market holidays before trading
    enable_economic_calendar: bool = True  # Check economic events
    economic_calendar_api_key: str = ""  # Optional: Alpha Vantage API key (works without)
    economic_event_strategy: str = "NORMAL"  # NORMAL, CAUTIOUS, or PAUSE
    high_impact_position_reduction: float = Field(default=0.5, ge=0.0, le=1.0)  # Reduce position sizes by this factor
    pause_before_event_hours: int = Field(default=2, ge=0, le=24)  # Hours to pause before high-impact events
    pause_after_event_hours: int = Field(default=1, ge=0, le=24)  # Hours to pause after high-impact events
    high_impact_events: str = "FOMC,NFP,CPI,GDP,ECB,UNEMPLOYMENT"  # Comma-separated list

    
    
    # Crew configuration
    enable_crew_mode: bool = True
    crew_deliberation_rounds: int = Field(default=2, ge=1, le=3)
    crew_min_consensus_percent: float = Field(default=66.0, ge=50.0, le=100.0)
    crew_enable_mediator: bool = True
    crew_mediator_model: str = "openai/gpt-5.2"
    crew_vote_weighting: str = "PERFORMANCE_BASED"
    crew_max_messages_per_round: int = Field(default=3, ge=1, le=10)
    
    # Order execution validator
    enable_order_validation: bool = True
    order_validator_model: str = "anthropic/claude-4.5-sonnet"
    
    # Intelligent decision parsing (using Claude 4.5 Sonnet)
    enable_intelligent_parsing: bool = True
    claude_parsing_model: str = "anthropic/claude-4.5-sonnet"
    parsing_cache_enabled: bool = True
    parsing_fallback_to_regex: bool = True
    
    # Dynamic model selection
    enable_dynamic_models: bool = False  # Use OpenRouter to select best models
    model_selection_strategy: str = "performance"  # performance or cost_effective
    model_cache_hours: int = Field(default=1, ge=1, le=24)  # Hours to cache model selection
    
    # Agent configuration
    auto_critique_frequency: int = Field(default=5, ge=3, le=20)
    allowed_symbols: str = ""
    
    # Security
    secret_key: str
    admin_password: str = "changeme"
    jwt_expiration_hours: int = 24
    
    # Monitoring
    log_level: str = "INFO"
    structured_logging: bool = True
    
    # Email notifications (optional)
    enable_email_notifications: bool = False
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    notification_email: Optional[str] = None
    
    @validator("trading_mode")
    def validate_trading_mode(cls, v):
        """Ensure trading mode is valid."""
        if v not in ["PAPER", "LIVE"]:
            raise ValueError("trading_mode must be PAPER or LIVE")
        return v
    
    @validator("log_level")
    def validate_log_level(cls, v):
        """Ensure log level is valid."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()
    
    def get_allowed_symbols(self) -> List[str]:
        """Parse allowed symbols into a list."""
        if not self.allowed_symbols:
            return []
        return [s.strip().upper() for s in self.allowed_symbols.split(",")]
    
    def get_allowed_crypto_pairs(self) -> List[str]:
        """Parse allowed crypto pairs into a list."""
        if not self.allowed_crypto_pairs:
            return []
        return [s.strip().upper() for s in self.allowed_crypto_pairs.split(",")]
    
    def is_paper_trading(self) -> bool:
        """Check if system is in paper trading mode."""
        return self.trading_mode == "PAPER"
    
    def has_twitter_access(self) -> bool:
        """Check if Twitter API credentials are configured."""
        return bool(
            self.twitter_api_key 
            and self.twitter_api_secret 
            and self.twitter_bearer_token
        )
    
    model_config = SettingsConfigDict(
        env_file=".env", 
        case_sensitive=False,
        protected_namespaces=('settings_',),
        extra='ignore'
    )


# Agent personality configurations
AGENT_CONFIGS = {
    "gpt4": {
        "name": "GPT-4 Holder",
        "model": "openai/gpt-4o",
        "personality": "Conservative long-term investor",
        "strategy": "Buy & Hold",
        "risk_tolerance": "Medium",
        "trading_frequency": "Low",
        "focus_sectors": ["Technology", "Consumer"],
        "preferred_symbols": ["AAPL", "MSFT", "GOOGL", "NVDA", "AMZN"],
        "preferred_crypto_pairs": ["BTCUSDT", "ETHUSDT"],  # Blue-chip crypto
        "crypto_risk_multiplier": 0.7,  # 70% of normal position size for crypto
        "max_cash_reserve": 0.10,  # Keep max 10% cash
        "min_holding_days": 7,
    },
    "claude": {
        "name": "Claude Équilibré",
        "model": "anthropic/claude-4.5-sonnet",
        "personality": "Prudent diversified portfolio manager",
        "strategy": "Diversification",
        "risk_tolerance": "Low-Medium",
        "trading_frequency": "Medium",
        "focus_sectors": ["Technology", "Finance", "Healthcare"],
        "preferred_symbols": ["AAPL", "JPM", "BAC", "JNJ", "MSFT"],
        "preferred_crypto_pairs": ["BTCUSDT", "ETHUSDT", "BNBUSDT"],  # Diversified major coins
        "crypto_risk_multiplier": 0.6,  # Conservative 60% position size
        "min_cash_reserve": 0.15,  # Keep minimum 15% cash
        "rebalance_frequency_days": 30,
    },
    "grok": {
        "name": "Grok Sniper",
        "model": "x-ai/grok-4",
        "personality": "Aggressive opportunistic trader",
        "strategy": "Momentum & Catalysts",
        "risk_tolerance": "High",
        "trading_frequency": "High",
        "focus_sectors": ["Biotech", "Small Cap", "Volatility"],
        "preferred_symbols": ["MRNA", "PFE", "TSLA"],
        "preferred_crypto_pairs": ["SOLUSDT", "ADAUSDT", "DOGEUSDT"],  # High volatility plays
        "crypto_risk_multiplier": 1.0,  # Full aggressive position size
        "max_position_size": 0.15,  # Max 15% per position (more aggressive)
        "use_twitter": True,
        "min_holding_hours": 4,
    },
    "gemini": {
        "name": "Gemini Gestionnaire",
        "model": "google/gemini-3-pro-preview",
        "personality": "Risk-averse capital preserver",
        "strategy": "Risk Management",
        "risk_tolerance": "Low",
        "trading_frequency": "Low",
        "focus_sectors": ["Large Cap Tech"],
        "preferred_symbols": ["AAPL", "MSFT", "GOOGL", "AMZN", "META"],
        "preferred_crypto_pairs": ["BTCUSDT", "ETHUSDT"],  # Only major coins
        "crypto_risk_multiplier": 0.5,  # Very conservative 50% position size
        "stop_loss_override": 0.10,  # Stricter 10% stop-loss
        "use_technical_analysis": True,
    },
    "deepseek": {
        "name": "DeepSeek Nerveux",
        "model": "deepseek/deepseek-v3.2",
        "personality": "Reactive momentum chaser",
        "strategy": "Sector Rotation",
        "risk_tolerance": "Medium-High",
        "trading_frequency": "High",
        "focus_sectors": ["Trending", "Momentum"],
        "preferred_symbols": ["NVDA", "TSLA", "META"],
        "preferred_crypto_pairs": ["SOLUSDT", "AVAXUSDT", "MATICUSDT"],  # L1 rotation plays
        "crypto_risk_multiplier": 0.8,  # 80% position size for momentum
        "pivot_threshold": 0.15,  # Pivot if sector moves 15%
    },
    "mistral": {
        "name": "Mistral Marine",
        "model": "mistralai/mistral-large-2512",
        "personality": "Persistent active trader with fallbacks",
        "strategy": "Active Trading",
        "risk_tolerance": "Medium",
        "trading_frequency": "Medium",
        "focus_sectors": ["Large Cap", "Mid Cap"],
        "preferred_symbols": ["AAPL", "MSFT", "JPM", "NVDA"],
        "preferred_crypto_pairs": ["BTCUSDT", "ETHUSDT", "ADAUSDT"],  # Balanced approach
        "crypto_risk_multiplier": 0.7,  # 70% position size
        "enable_tool_fallback": True,
    },
    "researcher": {
        "name": "Researcher",
        "model": "anthropic/claude-4.5-sonnet",
        "personality": "Deep analytical researcher focused on macro trends and news",
        "strategy": "Fundamental Analysis",
        "risk_tolerance": "Low",
        "trading_frequency": "Low",
        "focus_sectors": ["Macro", "News", "Earnings"],
        "preferred_symbols": [],
        "crypto_risk_multiplier": 0.0,  # Purely research
        "min_holding_days": 0,
        "is_support_agent": True,  # New flag for non-trading agents
    },
    "risk_manager": {
        "name": "Risk Guardian",
        "model": "anthropic/claude-4.5-sonnet",
        "personality": "Strict risk manager focused on capital preservation",
        "strategy": "Hedging & Protection",
        "risk_tolerance": "Very Low",
        "trading_frequency": "Medium",
        "focus_sectors": ["Volatility", "Inverse ETFs"],
        "preferred_symbols": ["VIX", "SPY"],
        "crypto_risk_multiplier": 0.1,
        "is_support_agent": True,
    },
    "crypto_specialist": {
        "name": "Crypto Zenith",
        "model": "anthropic/claude-4.5-sonnet",
        "personality": "High-frequency crypto arbitrage and momentum trader",
        "strategy": "Crypto Momentum",
        "risk_tolerance": "High",
        "trading_frequency": "Very High",
        "focus_sectors": ["Crypto L1", "DeFi"],
        "preferred_symbols": ["MSTR", "COIN"],
        "preferred_crypto_pairs": ["SOLUSDT", "AVAXUSDT", "SUIUSDT", "NEARUSDT", "PEPEUSDT"],
        "crypto_risk_multiplier": 1.0,  # Full position sizing
        "active_market_types": ["CRYPTO"],  # New: specifically for crypto
    },
}


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
