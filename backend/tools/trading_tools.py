"""
Trading tools available to AI agents via function calling.
Implements get_stock_price, buy_stock, sell_stock, etc.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import structlog
from config import get_settings
from models.database import Trade, TradeAction, TradeStatus, Portfolio
from database import get_db

logger = structlog.get_logger()
settings = get_settings()


# Tool definitions for function calling
TRADING_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_stock_price",
            "description": "Get the current price of a stock symbol",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock symbol (e.g., AAPL, MSFT)",
                    }
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_historical_data",
            "description": "Get historical price data for a stock",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock symbol",
                    },
                    "period": {
                        "type": "string",
                        "enum": ["1d", "1w", "1m", "3m"],
                        "description": "Time period for historical data",
                    },
                },
                "required": ["symbol", "period"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_news",
            "description": "Search recent news articles about a company",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock symbol (deprecated, use symbols list for multiple)",
                    },
                    "symbols": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of stock symbols to search news for",
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days to search back",
                        "default": 7,
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "manage_watchlist",
            "description": "Add or remove symbols from your personal watchlist for continuous tracking.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["add", "remove", "list"],
                        "description": "Action to perform",
                    },
                    "symbol": {
                        "type": "string",
                        "description": "Stock or crypto symbol to add/remove",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for adding to watchlist",
                    },
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_twitter",
            "description": "Search Twitter/X for sentiment about a stock (Grok agent only)",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g., $AAPL, company name)",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buy_stock",
            "description": "Execute a buy order for a stock",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock symbol to buy",
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "Number of shares to buy",
                        "minimum": 1,
                    },
                },
                "required": ["symbol", "quantity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sell_stock",
            "description": "Execute a sell order for a stock you own",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock symbol to sell",
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "Number of shares to sell",
                        "minimum": 1,
                    },
                },
                "required": ["symbol", "quantity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_portfolio",
            "description": "Get current portfolio state including cash and positions",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_available_stocks",
            "description": "List all tradable stocks available on the market",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["tech", "finance", "healthcare", "all"],
                        "description": "Filter by sector category",
                        "default": "all",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of stocks to return",
                        "default": 50,
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_market_overview",
            "description": "Get overview of major market indices and sector performance",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_technical_indicators",
            "description": "Calculate technical indicators like RSI, MACD, Bollinger Bands for a stock",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock symbol",
                    },
                    "indicators": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["RSI", "MACD", "BOLLINGER", "SMA"]
                        },
                        "description": "List of indicators to calculate",
                    },
                },
                "required": ["symbol", "indicators"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_stocks",
            "description": "Compare multiple stocks side-by-side with key metrics",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbols": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of stock symbols to compare",
                    },
                    "metrics": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["price", "change", "volume", "RSI"]
                        },
                        "description": "Metrics to include in comparison",
                        "default": ["price", "change"],
                    },
                },
                "required": ["symbols"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_earnings_calendar",
            "description": "Get upcoming earnings announcements for companies",
            "parameters": {
                "type": "object",
                "properties": {
                    "days_ahead": {
                        "type": "integer",
                        "description": "Number of days to look ahead",
                        "default": 14,
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_crypto_price",
            "description": "Get the current price of a cryptocurrency pair",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Crypto trading pair (e.g., BTCUSDT, ETHUSDT)",
                    }
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buy_crypto",
            "description": "Execute a buy order for cryptocurrency",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Crypto trading pair to buy (e.g., BTCUSDT)",
                    },
                    "quantity": {
                        "type": "number",
                        "description": "Amount of cryptocurrency to buy (can be fractional)",
                        "minimum": 0.0001,
                    },
                },
                "required": ["symbol", "quantity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sell_crypto",
            "description": "Execute a sell order for cryptocurrency you own",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Crypto trading pair to sell (e.g., BTCUSDT)",
                    },
                    "quantity": {
                        "type": "number",
                        "description": "Amount of cryptocurrency to sell (can be fractional)",
                        "minimum": 0.0001,
                    },
                },
                "required": ["symbol", "quantity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_available_crypto_pairs",
            "description": "List all available cryptocurrency pairs tradable on Binance",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of pairs to return (default: 50)",
                        "default": 50,
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_market_calendar",
            "description": "Get upcoming market holidays and trading days for stock markets",
            "parameters": {
                "type": "object",
                "properties": {
                    "market": {
                        "type": "string",
                        "enum": ["US", "EUROPE", "ASIA"],
                        "description": "Market to check (US, EUROPE, or ASIA)",
                        "default": "US",
                    },
                    "days_ahead": {
                        "type": "integer",
                        "description": "Number of days to look ahead",
                        "default": 30,
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_economic_events",
            "description": "Get upcoming economic events and their expected market impact (NFP, FOMC, CPI, etc.)",
            "parameters": {
                "type": "object",
                "properties": {
                    "days_ahead": {
                        "type": "integer",
                        "description": "Number of days to look ahead",
                        "default": 7,
                    },
                    "min_impact": {
                        "type": "string",
                        "enum": ["LOW", "MEDIUM", "HIGH"],
                        "description": "Minimum event impact level to include",
                        "default": "MEDIUM",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_economic_calendar_analysis",
            "description": "Get LLM-powered analysis of upcoming economic events with market outlook, volatility assessment, and trading recommendations. Use this to understand economic risks and adjust trading strategy accordingly.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days_ahead": {
                        "type": "integer",
                        "description": "Number of days to analyze ahead",
                        "default": 7,
                    },
                },
            },
        },
    },
    # ========== NEW ADVANCED INTELLIGENCE TOOLS ==========
    {
        "type": "function",
        "function": {
            "name": "get_advanced_indicators",
            "description": "Get advanced technical indicators including Fibonacci retracements, ADX (trend strength), Stochastic oscillator, ATR (volatility), VWAP, Volume Profile, and multi-timeframe analysis. Use this for sophisticated technical analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock or crypto symbol to analyze",
                    },
                    "include_multi_timeframe": {
                        "type": "boolean",
                        "description": "Include analysis across multiple timeframes (1D, 1W, 1M)",
                        "default": True,
                    },
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_market_sentiment",
            "description": "Get comprehensive market sentiment analysis including Fear & Greed Index, price momentum sentiment, and volume analysis. High fear = potential buying opportunity, high greed = potential selling opportunity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Optional symbol for specific sentiment analysis",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_fear_greed_index",
            "description": "Get the current Fear & Greed Index (0-100). Extreme Fear (0-24) = buying opportunity, Extreme Greed (76-100) = caution/selling opportunity. Key contrarian indicator.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_market_regime",
            "description": "Detect current market regime (bull market, bear market, or sideways/ranging). Helps adapt trading strategy to market conditions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Symbol to analyze for regime detection",
                        "default": "SPY",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_crypto_funding_rates",
            "description": "Get current funding rates for crypto perpetual futures. Positive = longs paying shorts (bullish sentiment may be overextended), Negative = shorts paying longs (bearish sentiment may be overextended).",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Crypto pair (e.g., BTCUSDT)",
                    },
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_crypto_order_book",
            "description": "Get order book depth analysis for crypto. Shows major support/resistance levels from actual orders, bid/ask imbalance, and whale wall detection.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Crypto pair (e.g., BTCUSDT)",
                    },
                    "depth": {
                        "type": "integer",
                        "description": "Number of order book levels to analyze",
                        "default": 20,
                    },
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_optimal_position_size",
            "description": "Calculate optimal position size based on ATR volatility, account risk (2%), and current market conditions. Returns recommended quantity and stop-loss level.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Symbol to calculate position size for",
                    },
                    "risk_percent": {
                        "type": "number",
                        "description": "Percentage of portfolio to risk (default 2%)",
                        "default": 2.0,
                    },
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_correlation_check",
            "description": "Check correlation between a symbol and current portfolio holdings. Helps avoid over-concentration in correlated assets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Symbol to check correlation for",
                    },
                },
                "required": ["symbol"],
            },
        },
    },
    # ========== NEW PHASE 3 INTELLIGENCE TOOLS ==========
    {
        "type": "function",
        "function": {
            "name": "detect_chart_patterns",
            "description": "Detect classic chart patterns like Head & Shoulders, Double Top/Bottom, Triangles, Golden/Death Cross. Returns pattern type, bias (bullish/bearish), confidence level, and key price levels.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Symbol to analyze for chart patterns",
                    },
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_conviction_score",
            "description": "Calculate a comprehensive conviction score (0-100) combining all technical indicators, sentiment, pattern detection, and multi-timeframe alignment. Higher scores indicate stronger trading signals.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Symbol to calculate conviction score for",
                    },
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web for general information, news, or specific topics using DuckDuckGo. Use this tool when you need information not covered by specific stock/crypto tools.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        },
    },
    # ========== NEW PHASE 1: ADVANCED LOCAL ANALYSIS ==========
    {
        "type": "function",
        "function": {
            "name": "get_support_resistance_levels",
            "description": "Automatically detect key support and resistance levels using pivot points, price clusters, volume profile, and swing highs/lows. Essential for entry/exit planning and stop-loss placement.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock or crypto symbol to analyze",
                    },
                    "lookback_days": {
                        "type": "integer",
                        "description": "Number of days to look back for analysis",
                        "default": 60,
                    },
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_volatility_regime",
            "description": "Classify current volatility regime as LOW, NORMAL, HIGH, or EXTREME. Returns position sizing recommendations based on regime. Helps adapt strategy to market conditions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Symbol to analyze volatility for",
                    },
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_momentum_divergence",
            "description": "Detect bullish/bearish divergences between price and RSI. Bullish divergence (potential reversal up): price makes lower low but RSI makes higher low. Powerful contrarian signal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Symbol to check for divergences",
                    },
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_price_structure",
            "description": "Analyze price structure for Higher Highs/Lows (uptrend) or Lower Highs/Lows (downtrend). Detects trend health, break of structure signals, and potential reversal points.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Symbol to analyze price structure for",
                    },
                },
                "required": ["symbol"],
            },
        },
    },
    # ========== NEW PHASE 2: MEMORY AND LEARNING ==========
    {
        "type": "function",
        "function": {
            "name": "recall_similar_trades",
            "description": "Recall similar trades from your history. Find past trades by symbol, action type, or market condition to learn from previous decisions and outcomes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Filter by specific symbol (optional)",
                    },
                    "action": {
                        "type": "string",
                        "enum": ["buy", "sell"],
                        "description": "Filter by action type (optional)",
                    },
                    "lookback_days": {
                        "type": "integer",
                        "description": "Number of days to look back",
                        "default": 90,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum trades to return",
                        "default": 10,
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_agent_performance_history",
            "description": "Get your performance history across different symbols and conditions. Shows win rates, P&L, and activity breakdown.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lookback_days": {
                        "type": "integer",
                        "description": "Number of days to analyze",
                        "default": 30,
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_market_regime_history",
            "description": "Get historical market regime analysis (bull/bear/sideways) over time. Useful for understanding market cycles and adapting strategy.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lookback_days": {
                        "type": "integer",
                        "description": "Number of days to analyze",
                        "default": 60,
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "record_trade_insight",
            "description": "Record an important trading insight for future reference. Use this to document observations, patterns, or learnings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Related symbol or 'MARKET' for general insights",
                    },
                    "insight_type": {
                        "type": "string",
                        "enum": ["technical", "fundamental", "sentiment", "pattern"],
                        "description": "Type of insight",
                    },
                    "content": {
                        "type": "string",
                        "description": "The insight content (max 500 chars)",
                    },
                    "importance": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Importance level",
                        "default": "medium",
                    },
                },
                "required": ["symbol", "insight_type", "content"],
            },
        },
    },
    # ========== NEW PHASE 3: PORTFOLIO INTELLIGENCE ==========
    {
        "type": "function",
        "function": {
            "name": "analyze_portfolio_risk",
            "description": "Get comprehensive portfolio risk analysis including VaR estimate, concentration risk, and risk score (0-100). Essential for understanding overall exposure.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_sector_exposure",
            "description": "Analyze portfolio sector exposure with breakdown by Technology, Finance, Healthcare, Crypto, etc. Includes rebalancing suggestions.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_portfolio_beta",
            "description": "Calculate portfolio beta relative to market (SPY). Beta > 1 means more volatile than market, < 1 means less volatile.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "optimize_portfolio_allocation",
            "description": "Get portfolio optimization suggestions based on risk, sector exposure, and beta. Returns actionable recommendations.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    # ========== NEW PHASE 4: ADVANCED REASONING ==========
    {
        "type": "function",
        "function": {
            "name": "evaluate_trade_thesis",
            "description": "Evaluate a trading thesis with structured pros/cons analysis. Returns conviction score and recommendation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock or crypto symbol",
                    },
                    "thesis": {
                        "type": "string",
                        "description": "Your trading thesis to evaluate",
                    },
                    "action": {
                        "type": "string",
                        "enum": ["buy", "sell"],
                        "description": "Proposed action",
                        "default": "buy",
                    },
                },
                "required": ["symbol", "thesis"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_scenarios",
            "description": "Compare bull, bear, and neutral scenarios with probabilities and target prices. Helps assess upside vs downside.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Symbol to analyze scenarios for",
                    },
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_risk_reward_analysis",
            "description": "Calculate optimal stop loss, take profit levels (1R, 2R, 3R), and risk/reward ratio. Essential for trade planning.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Symbol to analyze",
                    },
                    "entry_price": {
                        "type": "number",
                        "description": "Optional entry price (uses current price if not specified)",
                    },
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "detect_market_anomaly",
            "description": "Detect unusual market activity: volume spikes, price gaps, unusual ranges. Returns anomaly score and alerts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Symbol to check for anomalies",
                    },
                },
                "required": ["symbol"],
            },
        },
    },
    # ========== NEW PHASE 1: ADVANCED DECISION ENGINE ==========
    {
        "type": "function",
        "function": {
            "name": "get_decision_score",
            "description": "Get comprehensive multi-factor decision score (0-100) combining technical indicators, momentum, sentiment, risk/reward, and signal confluence. Use this before making any trading decision. Scores 75+: Strong Buy, 60-75: Buy, 40-60: Neutral, 25-40: Sell, <25: Strong Sell.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock or crypto symbol to analyze",
                    },
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_signal_confluence",
            "description": "Analyze confluence of trading signals - when multiple indicators agree, reliability increases. Returns confluence score, direction (bullish/bearish/neutral), agreeing vs conflicting indicators, and reliability rating.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Symbol to analyze",
                    },
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_success_probability",
            "description": "Calculate Bayesian probability of trade success based on your historical performance in similar conditions. Returns success probability, confidence level, and recommendation. High probability + high confidence = strong edge.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Symbol to trade",
                    },
                    "action": {
                        "type": "string",
                        "enum": ["buy", "sell"],
                        "description": "Proposed action",
                    },
                },
                "required": ["symbol", "action"],
            },
        },
    },
    # ========== NEW PHASE 7: PSYCHOLOGICAL EDGE ==========
    {
        "type": "function",
        "function": {
            "name": "detect_emotional_trade",
            "description": "Detect if a proposed trade is emotionally motivated (FOMO/FUD/REVENGE). CRITICAL: Use this BEFORE every trade to avoid emotional mistakes. Returns warning and blocks irrational trades.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Symbol you're considering trading",
                    },
                    "action": {
                        "type": "string",
                        "enum": ["buy", "sell"],
                        "description": "Action you're considering",
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Your reasoning for the trade",
                    },
                },
                "required": ["symbol", "action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_trading_cooldown",
            "description": "Check if you're in a mandatory cooldown period after losses. After 2+ consecutive losses, cooldowns are enforced to prevent revenge trading. ALWAYS check this before trading.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_drawdown_controls",
            "description": "Get current drawdown-based controls. Returns position size multiplier (0.0-1.0) and pause status. >10% drawdown = reduced sizing, >20% = trading paused.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_circuit_breaker",
            "description": "Check if circuit breaker is active from loss streak. 3+ consecutive losses = 1hr pause, 5+ losses = 24hr pause. Essential safety mechanism.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    # ========== NEW PHASE 2: PATTERN LEARNING & MEMORY ==========
    {
        "type": "function",
        "function": {
            "name": "analyze_trade_patterns",
            "description": "Analyze your trade history to discover winning and losing patterns. Returns clusters of similar trades with win rates and P&L. Use this to identify what setups work best for you.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lookback_days": {
                        "type": "integer",
                        "description": "Days of history to analyze",
                        "default": 90,
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "extract_winning_patterns",
            "description": "Extract 'golden rules' from your winning trades. Returns common characteristics, preferred symbols, and actionable rules. Learn what makes your winners successful.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "detect_recurring_errors",
            "description": "Detect recurring mistakes in your losing trades. Identifies error patterns like FOMO, panic selling, revenge trading. Essential for avoiding repeated mistakes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lookback_days": {
                        "type": "integer",
                        "description": "Days to analyze for errors",
                        "default": 60,
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_avoidance_rules",
            "description": "Get specific avoidance rules generated from your historical errors. Returns rules like 'AVOID buying when RSI > 75' based on YOUR specific losing patterns.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_strategy_adjustments",
            "description": "Get suggested strategy parameter adjustments based on recent performance. Returns recommendations like 'tighten entry criteria' or 'let winners run longer'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lookback_days": {
                        "type": "integer",
                        "description": "Days to analyze",
                        "default": 30,
                    },
                },
            },
        },
    },
    # ========== NEW PHASE 3: ADVANCED RISK MANAGEMENT ==========
    {
        "type": "function",
        "function": {
            "name": "calculate_kelly_position_size",
            "description": "Calculate optimal position size using Kelly Criterion based on your historical win rate and win/loss ratio. Returns the mathematically optimal fraction of portfolio to risk. Use this for scientific position sizing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Optional symbol to filter historical performance for",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_sharpe_ratio",
            "description": "Calculate your Sharpe ratio (risk-adjusted returns). Sharpe > 2.0 = excellent, 1.0-2.0 = good, 0.5-1.0 = moderate, <0.5 = poor. Returns recommendation on whether to increase, maintain, or decrease position sizes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lookback_days": {
                        "type": "integer",
                        "description": "Number of days to analyze",
                        "default": 30,
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_adaptive_position_size",
            "description": "Get optimal position size combining Kelly Criterion, Sharpe ratio, and market volatility. This is the BEST tool for position sizing - it adapts to your performance and market conditions automatically.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Symbol to trade",
                    },
                    "current_price": {
                        "type": "number",
                        "description": "Current price of the asset",
                    },
                    "portfolio_value": {
                        "type": "number",
                        "description": "Total portfolio value",
                    },
                    "atr_percent": {
                        "type": "number",
                        "description": "ATR as percentage of price (optional)",
                    },
                    "market_volatility": {
                        "type": "string",
                        "enum": ["LOW", "NORMAL", "HIGH", "EXTREME"],
                        "description": "Current market volatility level",
                        "default": "NORMAL",
                    },
                },
                "required": ["symbol", "current_price", "portfolio_value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_dynamic_stop_loss",
            "description": "Calculate volatility-based stop-loss using ATR. Returns stop price, risk per share, and enables trailing stop logic. Essential for risk management - ALWAYS calculate stop-loss BEFORE entering a trade.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entry_price": {
                        "type": "number",
                        "description": "Your entry price",
                    },
                    "atr": {
                        "type": "number",
                        "description": "Average True Range",
                    },
                    "direction": {
                        "type": "string",
                        "enum": ["long", "short"],
                        "description": "Trade direction",
                        "default": "long",
                    },
                    "atr_multiplier": {
                        "type": "number",
                        "description": "ATR multiplier for stop distance (default 2.0)",
                        "default": 2.0,
                    },
                },
                "required": ["entry_price", "atr"],
            },
        },
    },
]


class TradingTools:
    """Implementation of trading tools for AI agents."""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        
    async def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a trading tool by name.
        
        Returns:
            Tool execution result
        """
        logger.info(
            "tool_execution",
            agent=self.agent_name,
            tool=tool_name,
            args=args,
        )
        
        # Route to appropriate handler
        handlers = {
            "get_stock_price": self.get_stock_price,
            "get_historical_data": self.get_historical_data,
            "get_historical_data": self.get_historical_data,
            "search_news": self.search_news,
            "manage_watchlist": self.manage_watchlist,
            "search_web": self.search_web,
            "search_twitter": self.search_twitter,
            "buy_stock": self.buy_stock,
            "sell_stock": self.sell_stock,
            "get_portfolio": self.get_portfolio,
            "get_available_stocks": self.get_available_stocks,
            "get_market_overview": self.get_market_overview,
            "get_technical_indicators": self.get_technical_indicators,
            "compare_stocks": self.compare_stocks,
            "get_earnings_calendar": self.get_earnings_calendar,
            "get_crypto_price": self.get_crypto_price,
            "buy_crypto": self.buy_crypto,
            "sell_crypto": self.sell_crypto,
            "get_available_crypto_pairs": self.get_available_crypto_pairs,
            "get_market_calendar": self.get_market_calendar,
            "get_economic_events": self.get_economic_events,
            "get_economic_calendar_analysis": self.get_economic_calendar_analysis,
            # NEW ADVANCED INTELLIGENCE TOOLS
            "get_advanced_indicators": self.get_advanced_indicators,
            "get_market_sentiment": self.get_market_sentiment,
            "get_fear_greed_index": self.get_fear_greed_index,
            "get_market_regime": self.get_market_regime,
            "get_crypto_funding_rates": self.get_crypto_funding_rates,
            "get_crypto_order_book": self.get_crypto_order_book,
            "get_optimal_position_size": self.get_optimal_position_size,
            "get_correlation_check": self.get_correlation_check,
            # NEW PHASE 3 INTELLIGENCE TOOLS
            "detect_chart_patterns": self.detect_chart_patterns,
            "get_conviction_score": self.get_conviction_score,
            # NEW PHASE 1: ADVANCED LOCAL ANALYSIS
            "get_support_resistance_levels": self.get_support_resistance_levels,
            "analyze_volatility_regime": self.analyze_volatility_regime,
            "get_momentum_divergence": self.get_momentum_divergence,
            "analyze_price_structure": self.analyze_price_structure,
            # NEW PHASE 2: MEMORY AND LEARNING
            "recall_similar_trades": self.recall_similar_trades,
            "get_agent_performance_history": self.get_agent_performance_history,
            "get_market_regime_history": self.get_market_regime_history,
            "record_trade_insight": self.record_trade_insight,
            # NEW PHASE 3: PORTFOLIO INTELLIGENCE
            "analyze_portfolio_risk": self.analyze_portfolio_risk,
            "get_sector_exposure": self.get_sector_exposure,
            "calculate_portfolio_beta": self.calculate_portfolio_beta,
            "optimize_portfolio_allocation": self.optimize_portfolio_allocation,
            # NEW PHASE 4: ADVANCED REASONING
            "evaluate_trade_thesis": self.evaluate_trade_thesis,
            "compare_scenarios": self.compare_scenarios,
            "get_risk_reward_analysis": self.get_risk_reward_analysis,
            "detect_market_anomaly": self.detect_market_anomaly,
            # NEW PHASE 1: ADVANCED DECISION ENGINE
            "get_decision_score": self.get_decision_score,
            "get_signal_confluence": self.get_signal_confluence,
            "get_success_probability": self.get_success_probability,
            # NEW PHASE 7: PSYCHOLOGICAL EDGE
            "detect_emotional_trade": self.detect_emotional_trade,
            "check_trading_cooldown": self.check_trading_cooldown,
            "check_drawdown_controls": self.check_drawdown_controls,
            "check_circuit_breaker": self.check_circuit_breaker,
            # NEW PHASE 2: PATTERN LEARNING & MEMORY
            "analyze_trade_patterns": self.analyze_trade_patterns,
            "extract_winning_patterns": self.extract_winning_patterns,
            "detect_recurring_errors": self.detect_recurring_errors,
            "get_avoidance_rules": self.get_avoidance_rules,
            "get_strategy_adjustments": self.get_strategy_adjustments,
            # NEW PHASE 3: ADVANCED RISK MANAGEMENT
            "calculate_kelly_position_size": self.calculate_kelly_position_size,
            "calculate_sharpe_ratio": self.calculate_sharpe_ratio,
            "get_adaptive_position_size": self.get_adaptive_position_size,
            "calculate_dynamic_stop_loss": self.calculate_dynamic_stop_loss,
        }
        
        handler = handlers.get(tool_name)
        if not handler:
            return {"error": f"Unknown tool: {tool_name}"}
        
        try:
            result = await handler(**args)
            logger.info(
                "tool_success",
                agent=self.agent_name,
                tool=tool_name,
            )
            return result
        except Exception as e:
            logger.error(
                "tool_error",
                agent=self.agent_name,
                tool=tool_name,
                error=str(e),
            )
            return {"error": str(e)}
    
    async def get_stock_price(self, symbol: str) -> Dict[str, Any]:
        """Get current stock price."""
        from services.data_collector import get_data_collector
        
        symbol = symbol.upper()
        collector = get_data_collector()
        price_data = await collector.get_current_price(symbol)
        
        return {
            "symbol": symbol,
            "price": price_data.get("price"),
            "change": price_data.get("change"),
            "change_percent": price_data.get("change_percent"),
            "volume": price_data.get("volume"),
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    async def get_historical_data(self, symbol: str, period: str) -> Dict[str, Any]:
        """Get historical price data."""
        from services.data_collector import get_data_collector
        
        symbol = symbol.upper()
        collector = get_data_collector()
        historical = await collector.get_historical_data(symbol, period)
        
        return {
            "symbol": symbol,
            "period": period,
            "data": historical,
        }
    
    async def search_news(self, symbol: str = None, symbols: List[str] = None, days: int = 7) -> Dict[str, Any]:
        """Search news for one or more symbols."""
        from services.data_collector import get_data_collector
        
        collector = get_data_collector()
        
        targets = []
        if symbols:
            targets.extend(symbols)
        if symbol and symbol not in targets:
            targets.append(symbol)
            
        if not targets:
            return {"error": "No symbol provided"}
            
        results = {}
        for target in targets:
            target = target.upper()
            try:
                news = await collector.get_news(target, days)
                results[target] = news[:5]  # Limit per symbol
            except Exception as e:
                logger.error("news_search_error", symbol=target, error=str(e))
                results[target] = []
        
        return {
            "requested_symbols": targets,
            "results": results,
        }

    async def manage_watchlist(self, action: str, symbol: str = None, reason: str = None) -> Dict[str, Any]:
        """Manage agent's watchlist."""
        from models.database import Watchlist
        from database import get_db
        from sqlalchemy.exc import IntegrityError
        
        action = action.lower()
        
        if action == "list":
            with get_db() as db:
                items = db.query(Watchlist).filter(
                    Watchlist.agent_name == self.agent_name
                ).all()
                return {
                    "watchlist": [{"symbol": i.symbol, "reason": i.reason, "added": i.created_at.isoformat()} for i in items]
                }
                
        if not symbol:
            return {"error": "Symbol required for add/remove actions"}
            
        symbol = symbol.upper()
        
        try:
            with get_db() as db:
                if action == "add":
                    # Check if exists
                    exists = db.query(Watchlist).filter(
                        Watchlist.agent_name == self.agent_name,
                        Watchlist.symbol == symbol
                    ).first()
                    
                    if exists:
                        return {"status": "exists", "message": f"{symbol} already in watchlist"}
                        
                    item = Watchlist(
                        agent_name=self.agent_name, 
                        symbol=symbol, 
                        reason=reason
                    )
                    db.add(item)
                    db.commit()
                    return {"status": "added", "symbol": symbol}
                    
                elif action == "remove":
                    db.query(Watchlist).filter(
                        Watchlist.agent_name == self.agent_name,
                        Watchlist.symbol == symbol
                    ).delete()
                    db.commit()
                    return {"status": "removed", "symbol": symbol}
                    
        except Exception as e:
            return {"error": str(e)}
            
        return {"error": f"Unknown action: {action}"}
    
    async def search_twitter(self, query: str) -> Dict[str, Any]:
        """Search Twitter (Grok agent only)."""
        # Only allow for Grok agent
        if "grok" not in self.agent_name.lower():
            return {"error": "Twitter search is only available to Grok agent"}
        
        if not settings.has_twitter_access():
            return {"error": "Twitter API not configured"}
        
        from services.data_collector import get_data_collector
        
        collector = get_data_collector()
        tweets = await collector.search_twitter(query)
        
        return {
            "query": query,
            "tweets": tweets[:20],  # Limit to 20
        }

    async def search_web(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """Search the web using SerpAPI (Google) with fallback to DuckDuckGo, and store results."""
        from models.database import WebSearchResult
        formatted_results = []
        source_used = "unknown"

        # 1. Try SerpAPI first if configured
        if settings.serpapi_api_key:
            try:
                from serpapi import GoogleSearch
                source_used = "serpapi"
                
                params = {
                    "q": query,
                    "api_key": settings.serpapi_api_key,
                    "num": max_results
                }
                
                # Execute search (GoogleSearch is synchronous)
                search = GoogleSearch(params)
                results_dict = search.get_dict()
                
                organic_results = results_dict.get("organic_results", [])
                
                for r in organic_results:
                    formatted_results.append({
                        "title": r.get("title"),
                        "link": r.get("link"),
                        "snippet": r.get("snippet"),
                        "date": r.get("date"),
                        "source": r.get("source"),
                        "position": r.get("position")
                    })
                    
            except Exception as e:
                logger.warning("serpapi_search_failed", query=query, error=str(e))
                # Fallthrough to DuckDuckGo
                pass
        
        # 2. Fallback to DuckDuckGo if SerpAPI failed or not configured
        if not formatted_results:
            try:
                from duckduckgo_search import DDGS
                source_used = "duckduckgo"
                
                # specific exception catching for DDGs
                try:
                    # DDGS is synchronous but fast
                    with DDGS() as ddgs:
                        # text() returns an iterator
                        ddg_results = list(ddgs.text(query, max_results=max_results))
                        
                        for i, r in enumerate(ddg_results):
                            formatted_results.append({
                                "title": r.get("title"),
                                "link": r.get("href"),
                                "snippet": r.get("body"),
                                "date": None, # DDG sometimes provides this but inconsistent
                                "source": "DuckDuckGo",
                                "position": i + 1
                            })
                            
                except Exception as e:
                     logger.error("duckduckgo_search_failed", query=query, error=str(e))
                     return {"error": f"All search methods failed. Last error: {str(e)}"}
                     
            except ImportError:
                 return {"error": "duckduckgo_search not installed and SerpAPI failed/not configured."}

        # 3. Store in DB (if we have results)
        if formatted_results:
            try:
                with get_db() as db:
                    search_record = WebSearchResult(
                        query=query,
                        results=formatted_results
                    )
                    db.add(search_record)
                    db.commit()
            except Exception as e:
                logger.error("db_save_search_error", query=query, error=str(e))
            
        return {
            "query": query,
            "count": len(formatted_results),
            "source": source_used,
            "results": formatted_results,
        }
    
    async def buy_stock(self, symbol: str, quantity: float) -> Dict[str, Any]:
        """Execute buy order."""
        from services.risk_manager import get_risk_manager
        from services.alpaca_connector import get_alpaca_connector
        
        symbol = symbol.upper()
        
        # Validate symbol is allowed
        allowed = settings.get_allowed_symbols()
        if allowed and symbol not in allowed:
            return {"error": f"Symbol {symbol} not in allowed list"}
        
        # Get current portfolio
        with get_db() as db:
            portfolio = db.query(Portfolio).filter(
                Portfolio.agent_name == self.agent_name
            ).first()
            
            if not portfolio:
                return {"error": "Portfolio not found"}
            
            # Get current price
            from services.data_collector import get_data_collector
            collector = get_data_collector()
            price_data = await collector.get_current_price(symbol)
            price = price_data.get("price")
            
            if not price:
                return {"error": "Could not get current price"}
            
            total_cost = price * quantity
            
            # Risk validation
            risk_mgr = get_risk_manager()
            validation = risk_mgr.validate_trade(
                agent_name=self.agent_name,
                symbol=symbol,
                action="buy",
                quantity=quantity,
                price=price,
                portfolio=portfolio,
            )
            
            if not validation["allowed"]:
                return {"error": validation["reason"]}
            
            # Check cash available
            if portfolio.cash < total_cost:
                return {
                    "error": f"Insufficient cash. Need ${total_cost:.2f}, have ${portfolio.cash:.2f}"
                }
            
            # Execute trade
            alpaca = get_alpaca_connector()
            execution = await alpaca.place_order(
                symbol=symbol,
                action="BUY",
                quantity=quantity,
            )
            
            if execution.get("status") == "filled":
                # Update portfolio
                positions = portfolio.positions or {}
                if symbol in positions:
                    # Average cost
                    existing = positions[symbol]
                    total_qty = existing["quantity"] + quantity
                    avg_price = (
                        (existing["quantity"] * existing["avg_price"]) +
                        (quantity * price)
                    ) / total_qty
                    positions[symbol] = {
                        "quantity": total_qty,
                        "avg_price": avg_price,
                    }
                else:
                    positions[symbol] = {
                        "quantity": quantity,
                        "avg_price": price,
                    }
                
                portfolio.cash -= total_cost
                portfolio.positions = positions
                portfolio.total_trades += 1
                
                # Log trade
                trade = Trade(
                    agent_name=self.agent_name,
                    symbol=symbol,
                    action=TradeAction.BUY,
                    quantity=quantity,
                    price=price,
                    total_value=total_cost,
                    status=TradeStatus.EXECUTED,
                    executed_at=datetime.utcnow(),
                    portfolio_value_before=portfolio.total_value,
                    cash_before=portfolio.cash + total_cost,
                )
                db.add(trade)
                db.commit()
                
                logger.info(
                    "trade_executed",
                    agent=self.agent_name,
                    action="BUY",
                    symbol=symbol,
                    quantity=quantity,
                    price=price,
                )
                
                return {
                    "status": "success",
                    "action": "BUY",
                    "symbol": symbol,
                    "quantity": quantity,
                    "price": price,
                    "total_cost": total_cost,
                    "cash_remaining": portfolio.cash,
                }
            else:
                return {"error": f"Trade failed: {execution.get('error')}"}
    
    async def sell_stock(self, symbol: str, quantity: float) -> Dict[str, Any]:
        """Execute sell order."""
        from services.alpaca_connector import get_alpaca_connector
        
        symbol = symbol.upper()
        
        with get_db() as db:
            portfolio = db.query(Portfolio).filter(
                Portfolio.agent_name == self.agent_name
            ).first()
            
            if not portfolio:
                return {"error": "Portfolio not found"}
            
            # Check if we own the stock
            positions = portfolio.positions or {}
            if symbol not in positions:
                return {"error": f"You don't own {symbol}"}
            
            position = positions[symbol]
            if position["quantity"] < quantity:
                return {
                    "error": f"Insufficient shares. Own {position['quantity']}, trying to sell {quantity}"
                }
            
            # Get current price
            from services.data_collector import get_data_collector
            collector = get_data_collector()
            price_data = await collector.get_current_price(symbol)
            price = price_data.get("price")
            
            if not price:
                return {"error": "Could not get current price"}
            
            total_proceeds = price * quantity
            
            # Execute trade
            alpaca = get_alpaca_connector()
            execution = await alpaca.place_order(
                symbol=symbol,
                action="SELL",
                quantity=quantity,
            )
            
            if execution.get("status") == "filled":
                # Update portfolio
                position["quantity"] -= quantity
                if position["quantity"] == 0:
                    del positions[symbol]
                else:
                    positions[symbol] = position
                
                portfolio.cash += total_proceeds
                portfolio.positions = positions
                portfolio.total_trades += 1
                
                # Calculate P&L
                cost_basis = position["avg_price"] * quantity
                pnl = total_proceeds - cost_basis
                portfolio.realized_pnl += pnl
                
                if pnl > 0:
                    portfolio.winning_trades += 1
                else:
                    portfolio.losing_trades += 1
                
                # Log trade
                trade = Trade(
                    agent_name=self.agent_name,
                    symbol=symbol,
                    action=TradeAction.SELL,
                    quantity=quantity,
                    price=price,
                    total_value=total_proceeds,
                    status=TradeStatus.EXECUTED,
                    executed_at=datetime.utcnow(),
                    portfolio_value_before=portfolio.total_value,
                    cash_before=portfolio.cash - total_proceeds,
                )
                db.add(trade)
                db.commit()
                
                logger.info(
                    "trade_executed",
                    agent=self.agent_name,
                    action="SELL",
                    symbol=symbol,
                    quantity=quantity,
                    price=price,
                    pnl=pnl,
                )
                
                return {
                    "status": "success",
                    "action": "SELL",
                    "symbol": symbol,
                    "quantity": quantity,
                    "price": price,
                    "total_proceeds": total_proceeds,
                    "pnl": pnl,
                    "cash_total": portfolio.cash,
                }
            else:
                return {"error": f"Trade failed: {execution.get('error')}"}
    
    async def get_portfolio(self) -> Dict[str, Any]:
        """Get current portfolio state."""
        with get_db() as db:
            portfolio = db.query(Portfolio).filter(
                Portfolio.agent_name == self.agent_name
            ).first()
            
            if not portfolio:
                return {"error": "Portfolio not found"}
            
            # Calculate current value of positions
            from services.data_collector import get_data_collector
            collector = get_data_collector()
            
            positions_value = 0
            positions_detail = []
            
            for symbol, pos in (portfolio.positions or {}).items():
                price_data = await collector.get_current_price(symbol)
                current_price = price_data.get("price", pos["avg_price"])
                value = current_price * pos["quantity"]
                pnl = (current_price - pos["avg_price"]) * pos["quantity"]
                
                positions_value += value
                positions_detail.append({
                    "symbol": symbol,
                    "quantity": pos["quantity"],
                    "avg_price": pos["avg_price"],
                    "current_price": current_price,
                    "value": value,
                    "pnl": pnl,
                    "pnl_percent": (pnl / (pos["avg_price"] * pos["quantity"])) * 100,
                })
            
            total_value = portfolio.cash + positions_value
            total_pnl = total_value - portfolio.initial_value
            total_pnl_percent = (total_pnl / portfolio.initial_value) * 100
            
            # Update portfolio
            portfolio.total_value = total_value
            portfolio.total_pnl = total_pnl
            portfolio.total_pnl_percent = total_pnl_percent
            portfolio.unrealized_pnl = positions_value - sum(
                p["avg_price"] * p["quantity"] 
                for p in (portfolio.positions or {}).values()
            )
            db.commit()
            
            return {
                "agent": self.agent_name,
                "cash": portfolio.cash,
                "positions_value": positions_value,
                "total_value": total_value,
                "initial_value": portfolio.initial_value,
                "total_pnl": total_pnl,
                "total_pnl_percent": total_pnl_percent,
                "realized_pnl": portfolio.realized_pnl,
                "unrealized_pnl": portfolio.unrealized_pnl,
                "positions": positions_detail,
                "total_trades": portfolio.total_trades,
                "winning_trades": portfolio.winning_trades,
                "losing_trades": portfolio.losing_trades,
            }
    
    async def get_available_stocks(
        self,
        category: str = "all",
        limit: int = 50
    ) -> Dict[str, Any]:
        """Get list of all tradable stocks."""
        from services.data_collector import get_data_collector
        
        collector = get_data_collector()
        
        # Get assets from collector
        category_filter = None if category == "all" else category
        assets = await collector.get_all_tradable_assets(category=category_filter)
        
        # Limit results
        limited_assets = assets[:limit]
        
        return {
            "category": category,
            "count": len(limited_assets),
            "total_available": len(assets),
            "stocks": limited_assets,
        }
    
    async def get_market_overview(self) -> Dict[str, Any]:
        """Get overview of major market indices and sectors."""
        from services.data_collector import get_data_collector
        
        collector = get_data_collector()
        
        # Get index prices
        indices = await collector.get_index_prices()
        
        # Get sector representatives
        sectors = {
            "Technology": "AAPL",
            "Finance": "JPM",
            "Healthcare": "JNJ",
        }
        
        sector_performance = {}
        for sector_name, symbol in sectors.items():
            price_data = await collector.get_current_price(symbol)
            sector_performance[sector_name] = {
                "representative": symbol,
                "change_percent": price_data.get("change_percent"),
            }
        
        return {
            "indices": indices,
            "sectors": sector_performance,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    async def get_technical_indicators(
        self,
        symbol: str,
        indicators: List[str]
    ) -> Dict[str, Any]:
        """Calculate technical indicators for a stock."""
        from services.data_collector import get_data_collector
        
        symbol = symbol.upper()
        collector = get_data_collector()
        
        result = await collector.calculate_technical_indicators(symbol, indicators)
        
        return result
    
    async def compare_stocks(
        self,
        symbols: List[str],
        metrics: List[str] = None
    ) -> Dict[str, Any]:
        """Compare multiple stocks with specified metrics."""
        from services.data_collector import get_data_collector
        
        if metrics is None:
            metrics = ["price", "change"]
        
        collector = get_data_collector()
        comparison = []
        
        for symbol in symbols:
            symbol = symbol.upper()
            stock_data = {"symbol": symbol}
            
            # Get price data
            price_data = await collector.get_current_price(symbol)
            
            if "price" in metrics:
                stock_data["price"] = price_data.get("price")
            
            if "change" in metrics:
                stock_data["change"] = price_data.get("change")
                stock_data["change_percent"] = price_data.get("change_percent")
            
            if "volume" in metrics:
                stock_data["volume"] = price_data.get("volume")
            
            # Calculate RSI if requested
            if "RSI" in metrics:
                indicators = await collector.calculate_technical_indicators(
                    symbol,
                    ["RSI"]
                )
                stock_data["RSI"] = indicators.get("indicators", {}).get("RSI", {}).get("value")
            
            comparison.append(stock_data)
        
        return {
            "comparison": comparison,
            "metrics": metrics,
            "count": len(comparison),
        }
    
    async def get_earnings_calendar(self, days_ahead: int = 14) -> Dict[str, Any]:
        """Get upcoming earnings announcements."""
        # Mock data for now - real implementation would require paid API
        from datetime import datetime, timedelta
        import random
        
        companies = [
            {"symbol": "AAPL", "name": "Apple Inc"},
            {"symbol": "MSFT", "name": "Microsoft Corp"},
            {"symbol": "GOOGL", "name": "Alphabet Inc"},
            {"symbol": "AMZN", "name": "Amazon.com Inc"},
            {"symbol": "META", "name": "Meta Platforms Inc"},
        ]
        
        calendar = []
        for i in range(min(5, days_ahead)):
            company = random.choice(companies)
            earnings_date = datetime.now() + timedelta(days=random.randint(1, days_ahead))
            
            calendar.append({
                "symbol": company["symbol"],
                "name": company["name"],
                "earnings_date": earnings_date.strftime("%Y-%m-%d"),
                "estimate_eps": round(random.uniform(1.0, 5.0), 2),
                "is_mock": True,
            })
        
        # Sort by date
        calendar.sort(key=lambda x: x["earnings_date"])
        
        return {
            "upcoming_earnings": calendar,
            "days_ahead": days_ahead,
            "count": len(calendar),
            "note": "Mock data - real earnings calendar requires premium API",
        }

    # ===== CRYPTO TRADING METHODS =====
    
    async def get_crypto_price(self, symbol: str):
        """Get current cryptocurrency price."""
        from services.binance_connector import get_binance_connector
        
        symbol = symbol.upper()
        binance = get_binance_connector()
        price_data = await binance.get_crypto_price(symbol)
        
        if not price_data:
            return {"error": f"Could not get price for {symbol}"}
        
        return {
            "symbol": symbol,
            "price": price_data.get("price"),
            "change": price_data.get("change"),
            "change_percent": price_data.get("change_percent"),
            "volume": price_data.get("volume"),
            "high_24h": price_data.get("high_24h"),
            "low_24h": price_data.get("low_24h"),
            "bid": price_data.get("bid"),
            "ask": price_data.get("ask"),
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    async def buy_crypto(self, symbol: str, quantity: float):
        """Execute buy order for cryptocurrency."""
        from services.binance_connector import get_binance_connector
        
        symbol = symbol.upper()
        
        # Validate symbol is allowed (only if whitelist is configured)
        if not settings.use_all_binance_pairs:
            allowed = settings.get_allowed_crypto_pairs()
            if allowed and symbol not in allowed:
                return {"error": f"Crypto pair {symbol} not in allowed list"}
        
        with get_db() as db:
            portfolio = db.query(Portfolio).filter(
                Portfolio.agent_name == self.agent_name
            ).first()
            
            if not portfolio:
                return {"error": "Portfolio not found"}
            
            # Get current price
            binance = get_binance_connector()
            price_data = await binance.get_crypto_price(symbol)
            price = price_data.get("price") if price_data else None
            
            if not price:
                return {"error": "Could not get current price"}
            
            total_cost = price * quantity
            
            if portfolio.cash < total_cost:
                return {
                    "error": f"Insufficient cash. Need ${total_cost:.2f}, have ${portfolio.cash:.2f}"
                }
            
            # Execute trade
            execution = await binance.place_order(
                symbol=symbol,
                action="BUY",
                quantity=quantity,
            )
            
            if execution.get("status") == "filled":
                # Update portfolio
                positions = portfolio.positions or {}
                if symbol in positions:
                    existing = positions[symbol]
                    total_qty = existing["quantity"] + quantity
                    avg_price = (
                        (existing["quantity"] * existing["avg_price"]) +
                        (quantity * price)
                    ) / total_qty
                    positions[symbol] = {
                        "quantity": total_qty,
                        "avg_price": avg_price,
                        "asset_type": "CRYPTO",
                    }
                else:
                    positions[symbol] = {
                        "quantity": quantity,
                        "avg_price": price,
                        "asset_type": "CRYPTO",
                    }
                
                portfolio.cash -= total_cost
                portfolio.positions = positions
                portfolio.total_trades += 1
                
                # Log trade
                trade = Trade(
                    agent_name=self.agent_name,
                    symbol=symbol,
                    asset_type=AssetType.CRYPTO,
                    action=TradeAction.BUY,
                    quantity=quantity,
                    price=price,
                    total_value=total_cost,
                    status=TradeStatus.EXECUTED,
                    executed_at=datetime.utcnow(),
                    portfolio_value_before=portfolio.total_value,
                    cash_before=portfolio.cash + total_cost,
                )
                db.add(trade)
                db.commit()
                
                logger.info(
                    "crypto_trade_executed",
                    agent=self.agent_name,
                    action="BUY",
                    symbol=symbol,
                    quantity=quantity,
                    price=price,
                )
                
                return {
                    "status": "success",
                    "action": "BUY",
                    "symbol": symbol,
                    "quantity": quantity,
                    "price": price,
                    "total_cost": total_cost,
                    "cash_remaining": portfolio.cash,
                    "asset_type": "CRYPTO",
                }
            else:
                return {"error": f"Trade failed: {execution.get('error')}"}
    
    async def sell_crypto(self, symbol: str, quantity: float):
        """Execute sell order for cryptocurrency."""
        from services.binance_connector import get_binance_connector
        
        symbol = symbol.upper()
        
        with get_db() as db:
            portfolio = db.query(Portfolio).filter(
                Portfolio.agent_name == self.agent_name
            ).first()
            
            if not portfolio:
                return {"error": "Portfolio not found"}
            
            # Check if we own the crypto
            positions = portfolio.positions or {}
            if symbol not in positions:
                return {"error": f"You don't own {symbol}"}
            
            position = positions[symbol]
            
            if position.get("asset_type") != "CRYPTO":
                return {"error": f"{symbol} is not a crypto position, use sell_stock instead"}
            
            if position["quantity"] < quantity:
                return {
                    "error": f"Insufficient {symbol}. Own {position['quantity']}, trying to sell {quantity}"
                }
            
            # Get current price
            binance = get_binance_connector()
            price_data = await binance.get_crypto_price(symbol)
            price = price_data.get("price") if price_data else None
            
            if not price:
                return {"error": "Could not get current price"}
            
            total_proceeds = price * quantity
            
            # Execute trade
            execution = await binance.place_order(
                symbol=symbol,
                action="SELL",
                quantity=quantity,
            )
            
            if execution.get("status") == "filled":
                # Update portfolio
                position["quantity"] -= quantity
                if position["quantity"] <= 0.0001:
                    del positions[symbol]
                else:
                    positions[symbol] = position
                
                portfolio.cash += total_proceeds
                portfolio.positions = positions
                portfolio.total_trades += 1
                
                # Calculate P&L
                cost_basis = position["avg_price"] * quantity
                pnl = total_proceeds - cost_basis
                portfolio.realized_pnl += pnl
                
                if pnl > 0:
                    portfolio.winning_trades += 1
                else:
                    portfolio.losing_trades += 1
                
                # Log trade
                trade = Trade(
                    agent_name=self.agent_name,
                    symbol=symbol,
                    asset_type=AssetType.CRYPTO,
                    action=TradeAction.SELL,
                    quantity=quantity,
                    price=price,
                    total_value=total_proceeds,
                    status=TradeStatus.EXECUTED,
                    executed_at=datetime.utcnow(),
                    portfolio_value_before=portfolio.total_value,
                    cash_before=portfolio.cash - total_proceeds,
                )
                db.add(trade)
                db.commit()
                
                logger.info(
                    "crypto_trade_executed",
                    agent=self.agent_name,
                    action="SELL",
                    symbol=symbol,
                    quantity=quantity,
                    price=price,
                    pnl=pnl,
                )
                
                return {
                    "status": "success",
                    "action": "SELL",
                    "symbol": symbol,
                    "quantity": quantity,
                    "price": price,
                    "total_proceeds": total_proceeds,
                    "pnl": pnl,
                    "cash_total": portfolio.cash,
                    "asset_type": "CRYPTO",
                }
            else:
                return {"error": f"Trade failed: {execution.get('error')}"}
    
    async def get_available_crypto_pairs(self, limit: int = 50):
        """Get list of all tradable cryptocurrency pairs on Binance."""
        from services.binance_connector import get_binance_connector
        
        binance = get_binance_connector()
        all_pairs = await binance.get_all_tradable_pairs()
        
        # Limit results
        limited_pairs = all_pairs[:limit]
        
        return {
            "available_pairs": [p['symbol'] for p in limited_pairs],
            "count": len(limited_pairs),
            "total_available": len(all_pairs),
            "note": f"Showing top {limit} of {len(all_pairs)} tradable USDT pairs on Binance",
        }

    
    async def get_market_calendar(
        self,
        market: str = "US",
        days_ahead: int = 30
    ) -> Dict[str, Any]:
        """Get market calendar with upcoming holidays and trading days."""
        from services.market_calendar import get_market_calendar
        from datetime import date
        
        market = market.upper()
        calendar = get_market_calendar()
        
        try:
            # Get trading schedule
            schedule = calendar.get_market_schedule(
                market=market,
                start_date=date.today(),
                days_ahead=days_ahead
            )
            
            # Get upcoming holidays
            holidays = calendar.get_upcoming_holidays(
                market=market,
                days_ahead=days_ahead
            )
            
            # Check if today is a trading day
            is_trading_today = calendar.is_trading_day(market, date.today())
            
            # Get next trading day
            next_trading_day = calendar.get_next_trading_day(market, date.today())
            
            return {
                "market": market,
                "is_trading_today": is_trading_today,
                "next_trading_day": next_trading_day.isoformat() if next_trading_day else None,
                "trading_days": schedule,
                "holidays": holidays,
                "days_ahead": days_ahead,
            }
        except Exception as e:
            logger.error(
                "get_market_calendar_error",
                market=market,
                error=str(e)
            )
            return {"error": str(e)}
    
    async def get_economic_events(
        self,
        days_ahead: int = 7,
        min_impact: str = "MEDIUM"
    ) -> Dict[str, Any]:
        """Get upcoming economic events with market impact assessment."""
        try:
            from services.economic_calendar import get_economic_calendar, EventImpact
            
            calendar = get_economic_calendar(
                api_key=settings.economic_calendar_api_key if hasattr(settings, 'economic_calendar_api_key') else None
            )
            
            # Convert string to EventImpact enum
            try:
                impact_level = EventImpact(min_impact.upper())
            except ValueError:
                impact_level = EventImpact.MEDIUM
            
            # Get upcoming events
            events = await calendar.get_upcoming_events(
                days_ahead=days_ahead,
                min_impact=impact_level
            )
            
            # Check if there's a high-impact event today
            high_impact_today = await calendar.has_high_impact_event_today()
            
            return {
                "events": events,
                "count": len(events),
                "high_impact_today": high_impact_today,
                "days_ahead": days_ahead,
                "min_impact": min_impact,
            }
        except Exception as e:
            logger.error(
                "get_economic_events_error",
                error=str(e)
            )
            
            # Fallback: Use simple estimation logic if service fails
            logger.info("using_fallback_economic_events")
            fallback_events = self._get_fallback_economic_events(days_ahead, min_impact)
            
            return {
                "events": fallback_events,
                "count": len(fallback_events),
                "high_impact_today": any(e.get("impact") == "HIGH" and e.get("date") == datetime.now().date().isoformat() for e in fallback_events),
                "days_ahead": days_ahead,
                "min_impact": min_impact,
                "note": "Data from fallback estimation (service unavailable)"
            }

    def _get_fallback_economic_events(self, days_ahead: int, min_impact: str) -> List[Dict]:
        """Fallback estimation of economic events when service is unavailable."""
        from datetime import date, timedelta
        
        today = date.today()
        events = []
        min_impact = min_impact.upper()
        
        # Helper to check if date in range
        def in_range(d):
            return 0 <= (d - today).days <= days_ahead
            
        def get_first_friday(year, month):
            d = date(year, month, 1)
            while d.weekday() != 4:  # 4 is Friday
                d += timedelta(days=1)
            return d
            
        # NFP (First Friday)
        # Check current and next month
        for m_offset in [0, 1]:
            m = today.month + m_offset
            y = today.year
            if m > 12:
                m -= 12
                y += 1
            
            nfp_date = get_first_friday(y, m)
            if in_range(nfp_date):
                events.append({
                    "date": nfp_date.isoformat(),
                    "name": "Non-Farm Payroll (NFP)",
                    "impact": "HIGH",
                    "description": "Estimated NFP date"
                })
        
        # CPI (13th of month approx)
        for m_offset in [0, 1]:
            m = today.month + m_offset
            y = today.year
            if m > 12:
                m -= 12
                y += 1
            
            try:
                cpi_date = date(y, m, 13)
                if in_range(cpi_date):
                    events.append({
                        "date": cpi_date.isoformat(),
                        "name": "Consumer Price Index (CPI)",
                        "impact": "HIGH",
                        "description": "Estimated CPI date"
                    })
            except ValueError: pass
            
        # Filter by impact
        impact_score = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        min_score = impact_score.get(min_impact, 2)
        
        filtered = [e for e in events if impact_score.get(e["impact"], 1) >= min_score]
        filtered.sort(key=lambda x: x["date"])
        
        return filtered
    
    async def get_economic_calendar_analysis(
        self,
        days_ahead: int = 7
    ) -> Dict[str, Any]:
        """
        Get LLM-powered analysis of upcoming economic events.
        
        Args:
            days_ahead: Number of days to analyze ahead
            
        Returns:
            Dict containing analysis, market outlook, volatility assessment,
            and trading recommendations
        """
        try:
            from services.economic_calendar_analyzer import get_analyzer
            from services.economic_calendar import EventImpact
            
            analyzer = get_analyzer()
            
            # Get comprehensive analysis
            analysis = await analyzer.analyze_upcoming_events(
                days_ahead=days_ahead,
                min_impact=EventImpact.MEDIUM,
                force_refresh=False
            )
            
            return {
                "success": analysis.get("success", True),
                "summary": analysis.get("summary", ""),
                "market_outlook": analysis.get("market_outlook", "NEUTRAL"),
                "volatility_level": analysis.get("volatility_level", "MEDIUM"),
                "recommended_strategy": analysis.get("recommended_strategy", "NORMAL"),
                "key_events": analysis.get("key_events", []),
                "potential_impacts": analysis.get("potential_impacts", {}),
                "affected_sectors": analysis.get("affected_sectors", []),
                "trading_recommendations": analysis.get("trading_recommendations", []),
                "risk_factors": analysis.get("risk_factors", []),
                "events_count": analysis.get("events_count", 0),
                "analyzed_at": analysis.get("analyzed_at"),
            }
            
        except Exception as e:
            logger.error(
                "get_economic_calendar_analysis_error",
                error=str(e),
                days_ahead=days_ahead
            )
            
            # Provide fallback analysis based on basic event data
            try:
                fallback_events = self._get_fallback_economic_events(days_ahead, "MEDIUM")
                high_impact_count = sum(1 for e in fallback_events if e.get("impact") == "HIGH")
                
                if high_impact_count >= 3:
                    volatility = "HIGH"
                    strategy = "CAUTIOUS"
                    outlook = "VOLATILE"
                elif high_impact_count >= 1:
                    volatility = "MEDIUM" 
                    strategy = "CAUTIOUS"
                    outlook = "NEUTRAL"
                else:
                    volatility = "LOW"
                    strategy = "NORMAL"
                    outlook = "NEUTRAL"
                
                return {
                    "success": True,
                    "summary": f"Found {len(fallback_events)} estimated economic events ({high_impact_count} high-impact). Analysis service unavailable.",
                    "market_outlook": outlook,
                    "volatility_level": volatility,
                    "recommended_strategy": strategy,
                    "key_events": [e.get("name") for e in fallback_events[:5]],
                    "events_count": len(fallback_events),
                    "note": "Fallback estimation (LLM analysis unavailable)",
                }
            except Exception as fallback_error:
                logger.error("fallback_analysis_error", error=str(fallback_error))
                return {
                    "success": False,
                    "error": str(e),
                    "summary": "Economic calendar analysis temporarily unavailable",
                    "market_outlook": "NEUTRAL",
                    "volatility_level": "MEDIUM",
                    "recommended_strategy": "CAUTIOUS",
                }
    
    # ========== NEW ADVANCED INTELLIGENCE TOOLS ==========
    
    async def get_advanced_indicators(
        self,
        symbol: str,
        include_multi_timeframe: bool = True
    ) -> Dict[str, Any]:
        """Get advanced technical indicators for sophisticated analysis."""
        from services.advanced_indicators import get_advanced_indicators
        
        symbol = symbol.upper()
        indicators = get_advanced_indicators()
        
        try:
            result = await indicators.get_all_advanced_indicators(
                symbol=symbol,
                include_multi_timeframe=include_multi_timeframe
            )
            return result
        except Exception as e:
            logger.error(
                "get_advanced_indicators_error",
                symbol=symbol,
                error=str(e)
            )
            return {"error": str(e)}
    
    async def get_market_sentiment(
        self,
        symbol: str = None
    ) -> Dict[str, Any]:
        """Get comprehensive market sentiment analysis."""
        from services.sentiment_analyzer import get_sentiment_analyzer
        
        analyzer = get_sentiment_analyzer()
        
        try:
            result = await analyzer.get_comprehensive_sentiment(
                symbol=symbol.upper() if symbol else None,
                include_crypto=True
            )
            return result
        except Exception as e:
            logger.error(
                "get_market_sentiment_error",
                symbol=symbol,
                error=str(e)
            )
            return {"error": str(e)}
    
    async def get_fear_greed_index(self) -> Dict[str, Any]:
        """Get the Fear & Greed Index."""
        from services.sentiment_analyzer import get_sentiment_analyzer
        
        analyzer = get_sentiment_analyzer()
        
        try:
            result = await analyzer.get_fear_greed_index()
            return result
        except Exception as e:
            logger.error(
                "get_fear_greed_error",
                error=str(e)
            )
            return {"error": str(e)}
    
    async def get_market_regime(
        self,
        symbol: str = "SPY"
    ) -> Dict[str, Any]:
        """Detect current market regime (bull/bear/sideways)."""
        symbol = symbol.upper()
        
        try:
            from services.advanced_indicators import get_advanced_indicators
            indicators = get_advanced_indicators()
            
            result = await indicators.get_all_advanced_indicators(
                symbol=symbol,
                include_multi_timeframe=True
            )
            
            if "error" in result:
                # If advanced indicators fail, try a simpler fallback if possible
                # e.g. using get_stock_price directly if get_data_collector works
                return result
            
            # Extract regime from trend analysis
            trend_analysis = result.get("trend_analysis", {})
            adx_data = result.get("adx", {})
            
            trend = trend_analysis.get("trend", "sideways")
            confidence = trend_analysis.get("confidence", "low")
            adx_value = adx_data.get("adx", 0)
            
            # Determine regime
            if "uptrend" in trend:
                regime = "bull_market"
                recommendation = "Favor long positions, buy dips"
            elif "downtrend" in trend:
                regime = "bear_market"
                recommendation = "Be cautious, consider defensive positions or cash"
            else:
                regime = "sideways"
                recommendation = "Range trading strategies, wait for breakout"
            
            return {
                "regime": regime,
                "trend": trend,
                "confidence": confidence,
                "adx": adx_value,
                "recommendation": recommendation,
                "symbol": symbol,
            }
        except Exception as e:
            logger.error(
                "get_market_regime_error",
                symbol=symbol,
                error=str(e)
            )
            return {"error": f"Market regime analysis unavailable: {str(e)}"}
    
    async def get_crypto_funding_rates(
        self,
        symbol: str
    ) -> Dict[str, Any]:
        """Get funding rates for crypto perpetual futures."""
        from services.binance_connector import get_binance_connector
        
        symbol = symbol.upper()
        binance = get_binance_connector()
        
        try:
            result = await binance.get_funding_rate(symbol)
            return result
        except Exception as e:
            logger.error(
                "get_funding_rates_error",
                symbol=symbol,
                error=str(e)
            )
            return {"error": str(e)}
    
    async def get_crypto_order_book(
        self,
        symbol: str,
        depth: int = 20
    ) -> Dict[str, Any]:
        """Get order book depth analysis for crypto."""
        from services.binance_connector import get_binance_connector
        
        symbol = symbol.upper()
        binance = get_binance_connector()
        
        try:
            result = await binance.get_order_book_analysis(symbol, depth)
            return result
        except Exception as e:
            logger.error(
                "get_order_book_error",
                symbol=symbol,
                error=str(e)
            )
            return {"error": str(e)}
    
    async def get_optimal_position_size(
        self,
        symbol: str,
        risk_percent: float = 2.0
    ) -> Dict[str, Any]:
        """Calculate optimal position size based on ATR and risk."""
        from services.advanced_indicators import get_advanced_indicators
        
        symbol = symbol.upper()
        
        try:
            # Get portfolio value
            with get_db() as db:
                portfolio = db.query(Portfolio).filter(
                    Portfolio.agent_name == self.agent_name
                ).first()
                
                if not portfolio:
                    return {"error": "Portfolio not found"}
                
                portfolio_value = portfolio.total_value
            
            # Get ATR for volatility-based sizing
            indicators = get_advanced_indicators()
            result = await indicators.get_all_advanced_indicators(symbol)
            
            if "error" in result:
                return result
            
            atr_data = result.get("atr", {})
            atr = atr_data.get("atr", 0)
            current_price = result.get("fibonacci", {}).get("current_price", 0)
            
            if not atr or not current_price:
                return {"error": "Could not calculate ATR or get current price"}
            
            # Calculate position size
            # Risk per trade = portfolio_value * risk_percent / 100
            # Stop distance = 2 * ATR
            # Position size = Risk per trade / Stop distance
            
            risk_amount = portfolio_value * (risk_percent / 100)
            stop_distance = atr * 2
            
            if stop_distance > 0:
                optimal_quantity = risk_amount / stop_distance
                position_value = optimal_quantity * current_price
            else:
                optimal_quantity = 0
                position_value = 0
            
            # Ensure we don't exceed max position size
            max_position_value = portfolio_value * 0.10  # Max 10% per position
            if position_value > max_position_value:
                optimal_quantity = max_position_value / current_price
                position_value = max_position_value
            
            return {
                "symbol": symbol,
                "current_price": current_price,
                "atr": atr,
                "volatility": atr_data.get("volatility", "unknown"),
                "risk_percent": risk_percent,
                "risk_amount": round(risk_amount, 2),
                "stop_distance": round(stop_distance, 4),
                "suggested_stop_price": round(current_price - stop_distance, 4),
                "optimal_quantity": round(optimal_quantity, 4),
                "position_value": round(position_value, 2),
                "portfolio_value": round(portfolio_value, 2),
            }
        except Exception as e:
            logger.error(
                "get_optimal_position_size_error",
                symbol=symbol,
                error=str(e)
            )
            return {"error": str(e)}
    
    async def get_correlation_check(
        self,
        symbol: str
    ) -> Dict[str, Any]:
        """Check correlation between symbol and current portfolio holdings."""
        from services.data_collector import get_data_collector
        
        symbol = symbol.upper()
        collector = get_data_collector()
        
        try:
            # Get portfolio holdings
            with get_db() as db:
                portfolio = db.query(Portfolio).filter(
                    Portfolio.agent_name == self.agent_name
                ).first()
                
                if not portfolio or not portfolio.positions:
                    return {
                        "symbol": symbol,
                        "correlation_risk": "low",
                        "message": "No existing positions to check correlation against",
                    }
                
                holdings = list(portfolio.positions.keys())
            
            # Get historical data for correlation calculation
            new_symbol_data = await collector.get_historical_data(symbol, "1m")
            
            if not new_symbol_data or len(new_symbol_data) < 20:
                return {"error": "Insufficient data for correlation analysis"}
            
            new_closes = [bar.get("close", bar.get("c", 0)) for bar in new_symbol_data[-30:]]
            
            correlations = {}
            high_correlation_count = 0
            
            for holding in holdings[:5]:  # Check top 5 holdings
                holding_data = await collector.get_historical_data(holding, "1m")
                
                if holding_data and len(holding_data) >= 20:
                    holding_closes = [bar.get("close", bar.get("c", 0)) for bar in holding_data[-30:]]
                    
                    # Simple correlation calculation
                    min_len = min(len(new_closes), len(holding_closes))
                    if min_len >= 10:
                        # Normalize returns
                        new_returns = [(new_closes[i] - new_closes[i-1]) / new_closes[i-1] 
                                      for i in range(1, min_len)]
                        holding_returns = [(holding_closes[i] - holding_closes[i-1]) / holding_closes[i-1] 
                                          for i in range(1, min_len)]
                        
                        # Simple correlation (Pearson)
                        mean_new = sum(new_returns) / len(new_returns)
                        mean_holding = sum(holding_returns) / len(holding_returns)
                        
                        numerator = sum((new_returns[i] - mean_new) * (holding_returns[i] - mean_holding) 
                                       for i in range(len(new_returns)))
                        
                        std_new = (sum((x - mean_new) ** 2 for x in new_returns) / len(new_returns)) ** 0.5
                        std_holding = (sum((x - mean_holding) ** 2 for x in holding_returns) / len(holding_returns)) ** 0.5
                        
                        if std_new > 0 and std_holding > 0:
                            correlation = numerator / (len(new_returns) * std_new * std_holding)
                            correlations[holding] = round(correlation, 3)
                            
                            if abs(correlation) > 0.7:
                                high_correlation_count += 1
            
            # Assess overall correlation risk
            if high_correlation_count >= 2:
                correlation_risk = "high"
                recommendation = "Consider avoiding - highly correlated with existing positions"
            elif high_correlation_count == 1:
                correlation_risk = "medium"
                recommendation = "Proceed with caution - some correlation with portfolio"
            else:
                correlation_risk = "low"
                recommendation = "Good diversification - low correlation with existing holdings"
            
            return {
                "symbol": symbol,
                "correlation_risk": correlation_risk,
                "correlations": correlations,
                "high_correlation_count": high_correlation_count,
                "recommendation": recommendation,
                "holdings_checked": list(correlations.keys()),
            }
        except Exception as e:
            logger.error(
                "get_correlation_check_error",
                symbol=symbol,
                error=str(e)
            )
            return {"error": str(e)}
    
    async def detect_chart_patterns(self, symbol: str) -> Dict[str, Any]:
        """Detect classic chart patterns for a symbol."""
        try:
            from services.pattern_detector import get_pattern_detector
            
            detector = get_pattern_detector()
            result = await detector.detect_all_patterns(symbol)
            
            logger.info(
                "chart_patterns_detected",
                symbol=symbol,
                patterns_found=result.get("patterns_detected", 0),
                bias=result.get("overall_bias", "neutral"),
            )
            
            return result
        except Exception as e:
            logger.error(
                "detect_chart_patterns_error",
                symbol=symbol,
                error=str(e)
            )
            return {"error": str(e), "patterns": []}
    
    async def get_conviction_score(self, symbol: str) -> Dict[str, Any]:
        """
        Calculate comprehensive conviction score combining all available signals.
        
        Combines:
        - Technical indicators (RSI, MACD, ADX)
        - Sentiment (Fear & Greed)
        - Chart patterns
        - Multi-timeframe alignment
        - Volume analysis
        
        Returns score 0-100 with interpretation.
        """
        try:
            scores = {}
            
            # 1. Get advanced indicators
            from services.advanced_indicators import get_advanced_indicators
            indicators = get_advanced_indicators()
            advanced = await indicators.get_all_advanced_indicators(symbol, include_multi_timeframe=True)
            
            # Extract signal from advanced indicators
            if "signals" in advanced and isinstance(advanced["signals"], dict):
                signal = advanced["signals"]
                # Map signal to score
                signal_map = {"strong_buy": 90, "buy": 70, "neutral": 50, "sell": 30, "strong_sell": 10}
                scores["technical"] = signal_map.get(signal.get("signal", "neutral"), 50)
            else:
                scores["technical"] = 50
            
            # 2. Get sentiment
            from services.sentiment_analyzer import get_sentiment_analyzer
            sentiment_analyzer = get_sentiment_analyzer()
            sentiment = await sentiment_analyzer.get_comprehensive_sentiment(symbol)
            
            if "overall_sentiment" in sentiment:
                overall = sentiment["overall_sentiment"]
                # Map bullish/bearish to score
                if overall.get("bias") == "bullish":
                    scores["sentiment"] = 60 + min(40, overall.get("score", 0) / 2.5)
                elif overall.get("bias") == "bearish":
                    scores["sentiment"] = max(10, 40 - overall.get("score", 0) / 2.5)
                else:
                    scores["sentiment"] = 50
            else:
                scores["sentiment"] = 50
            
            # 3. Get chart patterns
            patterns_result = await self.detect_chart_patterns(symbol)
            if patterns_result.get("patterns_detected", 0) > 0:
                bias = patterns_result.get("overall_bias", "neutral")
                if bias == "bullish":
                    scores["patterns"] = 70 + (patterns_result.get("bullish_patterns", 0) * 5)
                elif bias == "bearish":
                    scores["patterns"] = 30 - (patterns_result.get("bearish_patterns", 0) * 5)
                else:
                    scores["patterns"] = 50
            else:
                scores["patterns"] = 50  # Neutral if no patterns
            
            # 4. Multi-timeframe alignment
            if "multi_timeframe" in advanced and isinstance(advanced["multi_timeframe"], dict):
                mtf = advanced["multi_timeframe"]
                alignment_strength = mtf.get("alignment_strength", 0)
                if mtf.get("alignment") == "bullish":
                    scores["multi_timeframe"] = 50 + alignment_strength / 2
                elif mtf.get("alignment") == "bearish":
                    scores["multi_timeframe"] = 50 - alignment_strength / 2
                else:
                    scores["multi_timeframe"] = 50
            else:
                scores["multi_timeframe"] = 50
            
            # 5. Trend strength (ADX)
            if "adx" in advanced and isinstance(advanced["adx"], dict):
                adx_value = advanced["adx"].get("adx", 0)
                trend_direction = advanced["adx"].get("trend_direction", "neutral")
                
                if adx_value > 25:  # Strong trend
                    if trend_direction == "bullish":
                        scores["trend"] = 60 + min(40, adx_value)
                    else:
                        scores["trend"] = 40 - min(30, adx_value / 2)
                else:
                    scores["trend"] = 50  # Weak trend
            else:
                scores["trend"] = 50
            
            # Calculate weighted overall score
            weights = {
                "technical": 0.25,
                "sentiment": 0.15,
                "patterns": 0.20,
                "multi_timeframe": 0.20,
                "trend": 0.20,
            }
            
            overall_score = sum(scores[k] * weights[k] for k in weights)
            overall_score = max(0, min(100, overall_score))
            
            # Determine action and interpretation
            if overall_score >= 75:
                action = "STRONG_BUY"
                interpretation = "Very high conviction - multiple strong bullish signals aligned"
            elif overall_score >= 60:
                action = "BUY"
                interpretation = "Good conviction - majority of signals favor buying"
            elif overall_score >= 45:
                action = "HOLD"
                interpretation = "Mixed signals - wait for clearer direction"
            elif overall_score >= 30:
                action = "SELL"
                interpretation = "Weak conviction - signals favor reducing exposure"
            else:
                action = "STRONG_SELL"
                interpretation = "Very low conviction - multiple bearish signals aligned"
            
            logger.info(
                "conviction_score_calculated",
                symbol=symbol,
                overall_score=overall_score,
                action=action,
            )
            
            return {
                "symbol": symbol,
                "conviction_score": round(overall_score, 1),
                "action_suggested": action,
                "component_scores": scores,
                "weights_used": weights,
                "interpretation": interpretation,
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(
                "get_conviction_score_error",
                symbol=symbol,
                error=str(e)
            )
            return {"error": str(e), "conviction_score": 50, "action_suggested": "HOLD"}
    
    # ========== NEW PHASE 1: ADVANCED LOCAL ANALYSIS TOOLS ==========
    
    async def get_support_resistance_levels(self, symbol: str, lookback_days: int = 60) -> Dict[str, Any]:
        """Get automatically detected support and resistance levels."""
        from services.advanced_indicators import get_advanced_indicators
        
        symbol = symbol.upper()
        indicators = get_advanced_indicators()
        
        try:
            result = await indicators.get_support_resistance_levels(symbol, lookback_days)
            
            logger.info(
                "support_resistance_analyzed",
                agent=self.agent_name,
                symbol=symbol,
                resistances_found=len(result.get("resistances", [])),
                supports_found=len(result.get("supports", [])),
            )
            
            return result
        except Exception as e:
            logger.error(
                "get_support_resistance_error",
                agent=self.agent_name,
                symbol=symbol,
                error=str(e)
            )
            return {"error": str(e)}
    
    async def analyze_volatility_regime(self, symbol: str) -> Dict[str, Any]:
        """Analyze and classify the current volatility regime."""
        from services.advanced_indicators import get_advanced_indicators
        
        symbol = symbol.upper()
        indicators = get_advanced_indicators()
        
        try:
            result = await indicators.analyze_volatility_regime(symbol)
            
            logger.info(
                "volatility_regime_analyzed",
                agent=self.agent_name,
                symbol=symbol,
                regime=result.get("regime"),
                position_multiplier=result.get("position_multiplier"),
            )
            
            return result
        except Exception as e:
            logger.error(
                "analyze_volatility_regime_error",
                agent=self.agent_name,
                symbol=symbol,
                error=str(e)
            )
            return {"error": str(e)}
    
    async def get_momentum_divergence(self, symbol: str) -> Dict[str, Any]:
        """Detect momentum divergences between price and RSI."""
        from services.advanced_indicators import get_advanced_indicators
        
        symbol = symbol.upper()
        indicators = get_advanced_indicators()
        
        try:
            result = await indicators.get_momentum_divergence(symbol)
            
            logger.info(
                "momentum_divergence_analyzed",
                agent=self.agent_name,
                symbol=symbol,
                divergence_count=result.get("divergence_count", 0),
                overall_signal=result.get("overall_signal"),
            )
            
            return result
        except Exception as e:
            logger.error(
                "get_momentum_divergence_error",
                agent=self.agent_name,
                symbol=symbol,
                error=str(e)
            )
            return {"error": str(e)}
    
    async def analyze_price_structure(self, symbol: str) -> Dict[str, Any]:
        """Analyze price structure for trend health and reversals."""
        from services.advanced_indicators import get_advanced_indicators
        
        symbol = symbol.upper()
        indicators = get_advanced_indicators()
        
        try:
            result = await indicators.analyze_price_structure(symbol)
            
            logger.info(
                "price_structure_analyzed",
                agent=self.agent_name,
                symbol=symbol,
                structure=result.get("structure"),
                bias=result.get("bias"),
            )
            
            return result
        except Exception as e:
            logger.error(
                "analyze_price_structure_error",
                agent=self.agent_name,
                symbol=symbol,
                error=str(e)
            )
            return {"error": str(e)}
    
    # ========== NEW PHASE 2: MEMORY AND LEARNING TOOLS ==========
    
    async def recall_similar_trades(
        self, 
        symbol: str = None, 
        action: str = None,
        lookback_days: int = 90,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Recall similar trades from history."""
        from services.memory_tools import get_memory_tools
        
        memory = get_memory_tools(self.agent_name)
        
        try:
            result = await memory.recall_similar_trades(
                symbol=symbol,
                action=action,
                lookback_days=lookback_days,
                limit=limit
            )
            
            logger.info(
                "similar_trades_recalled",
                agent=self.agent_name,
                trades_found=result.get("trades_found", 0),
            )
            
            return result
        except Exception as e:
            logger.error(
                "recall_similar_trades_error",
                agent=self.agent_name,
                error=str(e)
            )
            return {"error": str(e)}
    
    async def get_agent_performance_history(self, lookback_days: int = 30) -> Dict[str, Any]:
        """Get agent's performance history."""
        from services.memory_tools import get_memory_tools
        
        memory = get_memory_tools(self.agent_name)
        
        try:
            result = await memory.get_agent_performance_history(
                agent_name=self.agent_name,
                lookback_days=lookback_days
            )
            
            logger.info(
                "performance_history_retrieved",
                agent=self.agent_name,
            )
            
            return result
        except Exception as e:
            logger.error(
                "get_agent_performance_history_error",
                agent=self.agent_name,
                error=str(e)
            )
            return {"error": str(e)}
    
    async def get_market_regime_history(self, lookback_days: int = 60) -> Dict[str, Any]:
        """Get historical market regime analysis."""
        from services.memory_tools import get_memory_tools
        
        memory = get_memory_tools(self.agent_name)
        
        try:
            result = await memory.get_market_regime_history(lookback_days=lookback_days)
            
            logger.info(
                "market_regime_history_retrieved",
                agent=self.agent_name,
                current_regime=result.get("current_regime"),
            )
            
            return result
        except Exception as e:
            logger.error(
                "get_market_regime_history_error",
                agent=self.agent_name,
                error=str(e)
            )
            return {"error": str(e)}
    
    async def record_trade_insight(
        self, 
        symbol: str,
        insight_type: str,
        content: str,
        importance: str = "medium"
    ) -> Dict[str, Any]:
        """Record a trading insight for future reference."""
        from services.memory_tools import get_memory_tools
        
        memory = get_memory_tools(self.agent_name)
        
        try:
            result = await memory.record_trade_insight(
                symbol=symbol,
                insight_type=insight_type,
                content=content,
                importance=importance
            )
            
            logger.info(
                "trade_insight_recorded",
                agent=self.agent_name,
                symbol=symbol,
                insight_type=insight_type,
            )
            
            return result
        except Exception as e:
            logger.error(
                "record_trade_insight_error",
                agent=self.agent_name,
                symbol=symbol,
                error=str(e)
            )
            return {"error": str(e)}
    
    # ========== NEW PHASE 3: PORTFOLIO INTELLIGENCE TOOLS ==========
    
    async def analyze_portfolio_risk(self) -> Dict[str, Any]:
        """Analyze portfolio risk comprehensively."""
        from services.portfolio_intelligence import get_portfolio_intelligence
        
        portfolio = get_portfolio_intelligence(self.agent_name)
        
        try:
            result = await portfolio.analyze_portfolio_risk(self.agent_name)
            
            logger.info(
                "portfolio_risk_analyzed",
                agent=self.agent_name,
                risk_score=result.get("risk_score"),
            )
            
            return result
        except Exception as e:
            logger.error("analyze_portfolio_risk_error", agent=self.agent_name, error=str(e))
            return {"error": str(e)}
    
    async def get_sector_exposure(self) -> Dict[str, Any]:
        """Get portfolio sector exposure breakdown."""
        from services.portfolio_intelligence import get_portfolio_intelligence
        
        portfolio = get_portfolio_intelligence(self.agent_name)
        
        try:
            result = await portfolio.get_sector_exposure(self.agent_name)
            
            logger.info("sector_exposure_retrieved", agent=self.agent_name)
            
            return result
        except Exception as e:
            logger.error("get_sector_exposure_error", agent=self.agent_name, error=str(e))
            return {"error": str(e)}
    
    async def calculate_portfolio_beta(self) -> Dict[str, Any]:
        """Calculate portfolio beta vs market."""
        from services.portfolio_intelligence import get_portfolio_intelligence
        
        portfolio = get_portfolio_intelligence(self.agent_name)
        
        try:
            result = await portfolio.calculate_portfolio_beta(self.agent_name)
            
            logger.info(
                "portfolio_beta_calculated",
                agent=self.agent_name,
                beta=result.get("portfolio_beta"),
            )
            
            return result
        except Exception as e:
            logger.error("calculate_portfolio_beta_error", agent=self.agent_name, error=str(e))
            return {"error": str(e)}
    
    async def optimize_portfolio_allocation(self) -> Dict[str, Any]:
        """Get portfolio optimization suggestions."""
        from services.portfolio_intelligence import get_portfolio_intelligence
        
        portfolio = get_portfolio_intelligence(self.agent_name)
        
        try:
            result = await portfolio.optimize_portfolio_allocation(self.agent_name)
            
            logger.info(
                "portfolio_optimization_calculated",
                agent=self.agent_name,
                optimization_score=result.get("optimization_score"),
            )
            
            return result
        except Exception as e:
            logger.error("optimize_portfolio_allocation_error", agent=self.agent_name, error=str(e))
            return {"error": str(e)}
    
    # ========== NEW PHASE 4: ADVANCED REASONING TOOLS ==========
    
    async def evaluate_trade_thesis(
        self, 
        symbol: str, 
        thesis: str, 
        action: str = "buy"
    ) -> Dict[str, Any]:
        """Evaluate a trading thesis with structured analysis."""
        from services.reasoning_tools import get_reasoning_tools
        
        symbol = symbol.upper()
        reasoning = get_reasoning_tools(self.agent_name)
        
        try:
            result = await reasoning.evaluate_trade_thesis(symbol, thesis, action)
            
            logger.info(
                "trade_thesis_evaluated",
                agent=self.agent_name,
                symbol=symbol,
                conviction=result.get("conviction_score"),
            )
            
            return result
        except Exception as e:
            logger.error("evaluate_trade_thesis_error", agent=self.agent_name, symbol=symbol, error=str(e))
            return {"error": str(e)}
    
    async def compare_scenarios(self, symbol: str) -> Dict[str, Any]:
        """Compare bull/bear/neutral scenarios."""
        from services.reasoning_tools import get_reasoning_tools
        
        symbol = symbol.upper()
        reasoning = get_reasoning_tools(self.agent_name)
        
        try:
            result = await reasoning.compare_scenarios(symbol)
            
            logger.info(
                "scenarios_compared",
                agent=self.agent_name,
                symbol=symbol,
                most_likely=result.get("most_likely_scenario"),
            )
            
            return result
        except Exception as e:
            logger.error("compare_scenarios_error", agent=self.agent_name, symbol=symbol, error=str(e))
            return {"error": str(e)}
    
    async def get_risk_reward_analysis(self, symbol: str, entry_price: float = None) -> Dict[str, Any]:
        """Calculate risk/reward analysis with stop loss and take profit levels."""
        from services.reasoning_tools import get_reasoning_tools
        
        symbol = symbol.upper()
        reasoning = get_reasoning_tools(self.agent_name)
        
        try:
            result = await reasoning.get_risk_reward_analysis(symbol, entry_price)
            
            logger.info(
                "risk_reward_analyzed",
                agent=self.agent_name,
                symbol=symbol,
                rr_ratio=result.get("risk_reward_ratio"),
            )
            
            return result
        except Exception as e:
            logger.error("get_risk_reward_analysis_error", agent=self.agent_name, symbol=symbol, error=str(e))
            return {"error": str(e)}
    
    async def detect_market_anomaly(self, symbol: str) -> Dict[str, Any]:
        """Detect unusual market activity and anomalies."""
        from services.reasoning_tools import get_reasoning_tools
        
        symbol = symbol.upper()
        reasoning = get_reasoning_tools(self.agent_name)
        
        try:
            result = await reasoning.detect_market_anomaly(symbol)
            
            logger.info(
                "market_anomaly_checked",
                agent=self.agent_name,
                symbol=symbol,
                anomaly_count=result.get("anomaly_count"),
            )
            
            return result
        except Exception as e:
            logger.error("detect_market_anomaly_error", agent=self.agent_name, symbol=symbol, error=str(e))
            return {"error": str(e)}
    
    # ========== NEW PHASE 1: ADVANCED DECISION ENGINE METHODS ==========
    
    async def get_decision_score(self, symbol: str) -> Dict[str, Any]:
        """Get comprehensive multi-factor decision score for a symbol."""
        from services.decision_engine import MultiFactorScorer
        from services.data_collector import get_data_collector
        from services.advanced_indicators import get_advanced_indicators
        
        symbol = symbol.upper()
        
        try:
            # Collect all necessary data
            collector = get_data_collector()
            indicators_service = get_advanced_indicators()
            
            # Get price data
            price_data = await collector.get_current_price(symbol)
            
            # Get technical indicators
            indicators = await indicators_service.calculate_all_indicators(symbol)
            
            # Get market context
            market_context = await self._get_market_context_for_scoring(symbol)
            
            # Prepare technical data for scoring
            technical_data = {
                "current_price": price_data.get("price"),
                "change_1d": price_data.get("change_percent", 0),
                "change_7d": indicators.get("change_7d", 0),
                "volume_ratio": indicators.get("volume_ratio", 1.0),
                "rsi": indicators.get("rsi"),
                "macd": indicators.get("macd", {}),
                "bollinger": indicators.get("bollinger", {}),
                "sma_50": indicators.get("sma_50"),
                "sma_200": indicators.get("sma_200"),
                "adx": indicators.get("adx"),
                "atr_percent": indicators.get("atr_percent"),
                "nearest_support": indicators.get("support_levels", [None])[0] if indicators.get("support_levels") else None,
                "nearest_resistance": indicators.get("resistance_levels", [None])[0] if indicators.get("resistance_levels") else None,
            }
            
            # Calculate decision score
            scorer = MultiFactorScorer()
            result = scorer.calculate_score(symbol, technical_data, market_context)
            
            logger.info(
                "decision_score_calculated",
                agent=self.agent_name,
                symbol=symbol,
                score=result.get("total_score"),
                recommendation=result.get("recommendation"),
            )
            
            return result
            
        except Exception as e:
            logger.error("get_decision_score_error", agent=self.agent_name, symbol=symbol, error=str(e))
            return {"error": str(e), "total_score": 50, "recommendation": "NEUTRAL"}
    
    async def get_signal_confluence(self, symbol: str) -> Dict[str, Any]:
        """Analyze confluence of trading signals."""
        from services.decision_engine import SignalConfluenceDetector
        from services.data_collector import get_data_collector
        from services.advanced_indicators import get_advanced_indicators
        
        symbol = symbol.upper()
        
        try:
            # Collect data
            collector = get_data_collector()
            indicators_service = get_advanced_indicators()
            
            price_data = await collector.get_current_price(symbol)
            indicators = await indicators_service.calculate_all_indicators(symbol)
            market_context = await self._get_market_context_for_scoring(symbol)
            
            # Prepare technical data
            technical_data = {
                "current_price": price_data.get("price"),
                "change_1d": price_data.get("change_percent", 0),
                "volume_ratio": indicators.get("volume_ratio", 1.0),
                "rsi": indicators.get("rsi"),
                "macd": indicators.get("macd", {}),
                "bollinger": indicators.get("bollinger", {}),
                "sma_50": indicators.get("sma_50"),
                "sma_200": indicators.get("sma_200"),
            }
            
            # Analyze confluence
            detector = SignalConfluenceDetector()
            result = detector.analyze_confluence(technical_data, market_context)
            
            logger.info(
                "signal_confluence_analyzed",
                agent=self.agent_name,
                symbol=symbol,
                confluence_score=result.get("confluence_score"),
                direction=result.get("direction"),
                reliability=result.get("reliability"),
            )
            
            return result
            
        except Exception as e:
            logger.error("get_signal_confluence_error", agent=self.agent_name, symbol=symbol, error=str(e))
            return {"error": str(e), "confluence_score": 0, "direction": "NEUTRAL", "reliability": "LOW"}
    
    async def get_success_probability(self, symbol: str, action: str) -> Dict[str, Any]:
        """Calculate Bayesian probability of trade success."""
        from services.decision_engine import BayesianDecisionTree
        
        symbol = symbol.upper()
        action = action.lower()
        
        try:
            # Get current market conditions
            market_conditions = await self._get_market_conditions_for_bayesian(symbol)
            
            # Calculate success probability
            bayesian_tree = BayesianDecisionTree()
            result = bayesian_tree.calculate_success_probability(
                self.agent_name,
                symbol,
                action,
                market_conditions
            )
            
            logger.info(
                "success_probability_calculated",
                agent=self.agent_name,
                symbol=symbol,
                action=action,
                probability=result.get("success_probability"),
                confidence=result.get("confidence_level"),
            )
            
            return result
            
        except Exception as e:
            logger.error("get_success_probability_error", agent=self.agent_name, symbol=symbol, error=str(e))
            return {
                "error": str(e),
                "success_probability": 0.5,
                "confidence_level": "LOW",
                "recommendation": "Insufficient data"
            }
    
    async def _get_market_context_for_scoring(self, symbol: str) -> Dict[str, Any]:
        """Helper to get market context for decision scoring."""
        try:
            # Try to get fear & greed index
            fear_greed = None
            try:
                fg_result = await self.get_fear_greed_index()
                fear_greed = fg_result.get("index")
            except:
                pass
            
            # Try to get market regime
            market_regime = None
            try:
                regime_result = await self.get_market_regime(symbol="SPY")
                market_regime = regime_result.get("regime")
            except:
                pass
            
            # Try to get news sentiment
            news_sentiment = 0.0
            try:
                news_result = await self.search_news(symbol=symbol, days=3)
                # Simple sentiment based on news count
                news_count = len(news_result.get("results", {}).get(symbol, []))
                if news_count > 5:
                    news_sentiment = 0.2  # Positive if lots of news
            except:
                pass
            
            # Try to get economic impact
            eco_impact = "LOW"
            try:
                eco_result = await self.get_economic_events(days_ahead=3, min_impact="HIGH")
                events = eco_result.get("events", [])
                if len(events) > 0:
                    eco_impact = "HIGH"
            except:
                pass
            
            return {
                "fear_greed_index": fear_greed,
                "market_regime": market_regime,
                "news_sentiment": news_sentiment,
                "economic_impact": eco_impact,
            }
        except Exception as e:
            logger.warning("market_context_collection_error", error=str(e))
            return {}
    
    async def _get_market_conditions_for_bayesian(self, symbol: str) -> Dict[str, Any]:
        """Helper to get market conditions for Bayesian analysis."""
        try:
            from services.data_collector import get_data_collector
            from services.advanced_indicators import get_advanced_indicators
            
            collector = get_data_collector()
            indicators_service = get_advanced_indicators()
            
            price_data = await collector.get_current_price(symbol)
            indicators = await indicators_service.calculate_all_indicators(symbol)
            
            return {
                "price": price_data.get("price"),
                "rsi": indicators.get("rsi"),
                "atr_percent": indicators.get("atr_percent"),
                "volume_ratio": indicators.get("volume_ratio", 1.0),
            }
        except Exception as e:
            logger.warning("market_conditions_collection_error", error=str(e))
            return {}
    
    # ========== NEW PHASE 3: ADVANCED RISK MANAGEMENT METHODS ==========
    
    async def calculate_kelly_position_size(self, symbol: str = None) -> Dict[str, Any]:
        """Calculate optimal position size using Kelly Criterion."""
        from services.advanced_risk import calculate_kelly_position_size as kelly_calc
        
        try:
            result = kelly_calc(self.agent_name, symbol)
            
            logger.info(
                "kelly_position_calculated",
                agent=self.agent_name,
                symbol=symbol,
                kelly_fraction=result.get("kelly_fraction"),
                adjusted_fraction=result.get("adjusted_fraction"),
            )
            
            return result
            
        except Exception as e:
            logger.error("calculate_kelly_position_size_error", agent=self.agent_name, error=str(e))
            return {
                "error": str(e),
                "kelly_fraction": 0.02,
                "adjusted_fraction": 0.02,
                "recommendation": "Error calculating Kelly - using conservative 2% default"
            }
    
    async def calculate_sharpe_ratio(self, lookback_days: int = 30) -> Dict[str, Any]:
        """Calculate Sharpe ratio for risk-adjusted returns."""
        from services.advanced_risk import calculate_sharpe_ratio as sharpe_calc
        
        try:
            result = sharpe_calc(self.agent_name, lookback_days)
            
            logger.info(
                "sharpe_ratio_calculated",
                agent=self.agent_name,
                sharpe_ratio=result.get("sharpe_ratio"),
                recommendation=result.get("position_adjustment"),
            )
            
            return result
            
        except Exception as e:
            logger.error("calculate_sharpe_ratio_error", agent=self.agent_name, error=str(e))
            return {
                "error": str(e),
                "sharpe_ratio": 0,
                "recommendation": "Error calculating Sharpe - maintain current approach",
                "position_adjustment": "maintain"
            }
    
    async def get_adaptive_position_size(
        self,
        symbol: str,
        current_price: float,
        portfolio_value: float,
        atr_percent: float = None,
        market_volatility: str = "NORMAL"
    ) -> Dict[str, Any]:
        """Get optimal position size combining Kelly, Sharpe, and volatility."""
        from services.advanced_risk import get_adaptive_position_size as adaptive_calc
        
        symbol = symbol.upper()
        
        try:
            result = adaptive_calc(
                self.agent_name,
                symbol,
                current_price,
                portfolio_value,
                atr_percent,
                market_volatility
            )
            
            logger.info(
                "adaptive_position_calculated",
                agent=self.agent_name,
                symbol=symbol,
                suggested_quantity=result.get("suggested_quantity"),
                percent_of_portfolio=result.get("percent_of_portfolio"),
            )
            
            return result
            
        except Exception as e:
            logger.error("get_adaptive_position_size_error", agent=self.agent_name, symbol=symbol, error=str(e))
            # Fallback to conservative sizing
            conservative_fraction = 0.02
            conservative_investment = portfolio_value * conservative_fraction
            conservative_quantity = int(conservative_investment / current_price) if current_price > 0 else 0
            
            return {
                "error": str(e),
                "suggested_quantity": conservative_quantity,
                "suggested_investment": conservative_investment,
                "percent_of_portfolio": 2.0,
                "reasoning": "Error in adaptive calculation - using conservative 2% default"
            }
    
    async def calculate_dynamic_stop_loss(
        self,
        entry_price: float,
        atr: float,
        direction: str = "long",
        atr_multiplier: float = 2.0
    ) -> Dict[str, Any]:
        """Calculate volatility-based stop-loss."""
        from services.advanced_risk import calculate_dynamic_stop_loss as stop_calc
        
        try:
            result = stop_calc(entry_price, atr, direction, atr_multiplier)
            
            logger.info(
                "dynamic_stop_loss_calculated",
                agent=self.agent_name,
                entry_price=entry_price,
                stop_loss_price=result.get("stop_loss_price"),
                stop_distance_percent=result.get("stop_distance_percent"),
            )
            
            return result
            
        except Exception as e:
            logger.error("calculate_dynamic_stop_loss_error", agent=self.agent_name, error=str(e))
            # Fallback to simple 5% stop
            fallback_stop = entry_price * 0.95 if direction == "long" else entry_price * 1.05
            
            return {
                "error": str(e),
                "stop_loss_price": round(fallback_stop, 2),
                "stop_distance_percent": 5.0,
                "recommendation": "Error in calculation - using simple 5% stop-loss"
            }



    # ========== NEW PHASE 2: PATTERN LEARNING & MEMORY METHODS ==========
    
    async def analyze_trade_patterns(self, lookback_days: int = 90) -> Dict[str, Any]:
        """Analyze trade patterns to identify winning and losing setups."""
        from services.pattern_learning import analyze_trade_patterns as analyze_patterns
        
        try:
            result = analyze_patterns(self.agent_name, lookback_days)
            logger.info("trade_patterns_analyzed", agent=self.agent_name, total_trades=result.get("total_trades"))
            return result
        except Exception as e:
            logger.error("analyze_trade_patterns_error", agent=self.agent_name, error=str(e))
            return {"error": str(e), "winning_clusters": [], "losing_clusters": [], "insights": ["Error analyzing patterns"]}
    
    async def extract_winning_patterns(self) -> Dict[str, Any]:
        """Extract golden rules from winning trades."""
        from services.pattern_learning import extract_winning_patterns as extract_patterns
        
        try:
            result = extract_patterns(self.agent_name)
            logger.info("winning_patterns_extracted", agent=self.agent_name, golden_rules_count=len(result.get("golden_rules", [])))
            return result
        except Exception as e:
            logger.error("extract_winning_patterns_error", agent=self.agent_name, error=str(e))
            return {"error": str(e), "golden_rules": [], "recommendations": ["Error extracting patterns"]}
    
    async def detect_recurring_errors(self, lookback_days: int = 60) -> Dict[str, Any]:
        """Detect recurring error patterns in losing trades."""
        from services.error_learning import detect_recurring_errors as detect_errors
        
        try:
            result = detect_errors(self.agent_name, lookback_days)
            logger.info("recurring_errors_detected", agent=self.agent_name, error_patterns_found=len(result.get("error_patterns", [])))
            return result
        except Exception as e:
            logger.error("detect_recurring_errors_error", agent=self.agent_name, error=str(e))
            return {"error": str(e), "error_patterns": [], "message": "Error detecting patterns"}
    
    async def get_avoidance_rules(self) -> Dict[str, Any]:
        """Get avoidance rules generated from historical errors."""
        from services.error_learning import get_avoidance_rules as get_rules
        
        try:
            result = get_rules(self.agent_name)
            logger.info("avoidance_rules_retrieved", agent=self.agent_name, rules_count=len(result.get("avoidance_rules", [])))
            return result
        except Exception as e:
            logger.error("get_avoidance_rules_error", agent=self.agent_name, error=str(e))
            return {"error": str(e), "avoidance_rules": [], "formatted_for_prompt": ""}
    
    async def get_strategy_adjustments(self, lookback_days: int = 30) -> Dict[str, Any]:
        """Get suggested strategy parameter adjustments."""
        from services.pattern_learning import get_strategy_adjustments as get_adjustments
        
        try:
            result = get_adjustments(self.agent_name, lookback_days)
            logger.info("strategy_adjustments_generated", agent=self.agent_name, adjustments_count=len(result.get("adjustments", [])))
            return result
        except Exception as e:
            logger.error("get_strategy_adjustments_error", agent=self.agent_name, error=str(e))
            return {"error": str(e), "adjustments": [], "recommendations": ["Error generating adjustments"]}
    
    # ========== NEW PHASE 7: PSYCHOLOGICAL EDGE METHODS ==========
    
    async def detect_emotional_trade(self, symbol: str, action: str, reasoning: str = "") -> Dict[str, Any]:
        """Detect if a proposed trade is emotionally motivated."""
        from services.psychological_monitor import detect_emotional_trade as detect_emotion
        
        try:
            result = detect_emotion(self.agent_name, symbol, action, reasoning)
            logger.info("emotional_trade_check", agent=self.agent_name, symbol=symbol, is_emotional=result.get("is_emotional"), emotion_type=result.get("emotion_type"))
            return result
        except Exception as e:
            logger.error("detect_emotional_trade_error", agent=self.agent_name, error=str(e))
            return {"error": str(e), "is_emotional": False, "should_block": False, "warning_message": "Error checking emotions"}
    
    async def check_trading_cooldown(self) -> Dict[str, Any]:
        """Check if trading cooldown is active after losses."""
        from services.psychological_monitor import check_trading_cooldown as check_cooldown
        
        try:
            result = check_cooldown(self.agent_name)
            logger.info("cooldown_check", agent=self.agent_name, cooldown_active=result.get("cooldown_active"))
            return result
        except Exception as e:
            logger.error("check_trading_cooldown_error", agent=self.agent_name, error=str(e))
            return {"error": str(e), "cooldown_active": False, "minutes_remaining": 0}
    
    async def check_drawdown_controls(self) -> Dict[str, Any]:
        """Get position size controls based on current drawdown."""
        from services.psychological_monitor import check_drawdown_controls as check_dd
        
        try:
            result = check_dd(self.agent_name)
            logger.info("drawdown_check", agent=self.agent_name, control_level=result.get("control_level"), drawdown=result.get("current_drawdown_percent"))
            return result
        except Exception as e:
            logger.error("check_drawdown_controls_error", agent=self.agent_name, error=str(e))
            return {"error": str(e), "position_size_multiplier": 1.0, "should_pause_trading": False}
    
    async def check_circuit_breaker(self) -> Dict[str, Any]:
        """Check if circuit breaker is active due to loss streak."""
        from services.psychological_monitor import check_circuit_breaker as check_breaker
        
        try:
            result = check_breaker(self.agent_name)
            logger.info("circuit_breaker_check", agent=self.agent_name, breaker_active=result.get("breaker_active"), consecutive_losses=result.get("consecutive_losses"))
            return result
        except Exception as e:
            logger.error("check_circuit_breaker_error", agent=self.agent_name, error=str(e))
            return {"error": str(e), "breaker_active": False, "consecutive_losses": 0}
    
    # ========== NEW PHASE 6: CONTEXT AWARENESS METHODS ==========
    
    async def get_market_context(self) -> Dict[str, Any]:
        """Get comprehensive market and portfolio context."""
        from services.context_awareness import get_market_context as get_context
        
        try:
            result = get_context(self.agent_name)
            logger.info("market_context_retrieved", agent=self.agent_name, activity_level=result.get("market_summary", {}).get("activity_level"))
            return result
        except Exception as e:
            logger.error("get_market_context_error", agent=self.agent_name, error=str(e))
            return {"error": str(e), "market_summary": {}, "recommendations": ["Error retrieving context"]}
    
    async def check_portfolio_correlation(self, new_symbol: str = None) -> Dict[str, Any]:
        """Check portfolio correlation and diversification."""
        from services.context_awareness import check_portfolio_correlation as check_corr
        
        try:
            result = check_corr(self.agent_name, new_symbol)
            logger.info("portfolio_correlation_checked", agent=self.agent_name, correlation_risk=result.get("correlation_risk"), diversification_score=result.get("diversification_score"))
            return result
        except Exception as e:
            logger.error("check_portfolio_correlation_error", agent=self.agent_name, error=str(e))
            return {"error": str(e), "correlation_risk": "UNKNOWN", "diversification_score": 50}
    
    # ========== NEW PHASE 4: MARKET INTELLIGENCE METHODS ==========
    
    async def analyze_ict_concepts(self, symbol: str, price_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze ICT concepts (Order Blocks, FVG, Liquidity)."""
        from services.market_intelligence import analyze_ict_concepts as analyze_ict
        
        try:
            result = analyze_ict(symbol, price_data)
            logger.info("ict_analysis", agent=self.agent_name, symbol=symbol, structure=result.get("market_structure"))
            return result
        except Exception as e:
            logger.error("analyze_ict_concepts_error", agent=self.agent_name, error=str(e))
            return {"error": str(e), "market_structure": "UNKNOWN", "recommendation": "Error analyzing ICT"}
    
    async def analyze_wyckoff_phase(self, symbol: str, price_history: List[float]) -> Dict[str, Any]:
        """Analyze Wyckoff accumulation/distribution phase."""
        from services.market_intelligence import analyze_wyckoff_phase as analyze_wyckoff
        
        try:
            result = analyze_wyckoff(symbol, price_history)
            logger.info("wyckoff_analysis", agent=self.agent_name, symbol=symbol, phase=result.get("current_phase"), bias=result.get("bias"))
            return result
        except Exception as e:
            logger.error("analyze_wyckoff_phase_error", agent=self.agent_name, error=str(e))
            return {"error": str(e), "current_phase": "UNKNOWN", "bias": "NEUTRAL"}
    
    async def detect_elliott_wave_pattern(self, symbol: str, price_history: List[float]) -> Dict[str, Any]:
        """Detect Elliott Wave patterns."""
        from services.market_intelligence import detect_elliott_wave_pattern as detect_wave
        
        try:
            result = detect_wave(symbol, price_history)
            logger.info("elliott_wave_detected", agent=self.agent_name, symbol=symbol, pattern=result.get("pattern_detected"))
            return result
        except Exception as e:
            logger.error("detect_elliott_wave_pattern_error", agent=self.agent_name, error=str(e))
            return {"error": str(e), "pattern_detected": "NONE", "recommendation": "Error detecting wave"}
    
    # ========== NEW PHASE 5: AGENT COORDINATION METHODS ==========
    
    async def get_agent_consensus(self, symbol: str, agent_decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get consensus from multiple agent decisions."""
        from services.agent_coordination import get_agent_consensus as get_consensus
        
        try:
            result = get_consensus(symbol, agent_decisions)
            logger.info("agent_consensus", symbol=symbol, consensus_action=result.get("consensus_action"), strength=result.get("consensus_strength"))
            return result
        except Exception as e:
            logger.error("get_agent_consensus_error", error=str(e))
            return {"error": str(e), "consensus_action": "HOLD", "consensus_strength": 0}
    
    async def resolve_agent_conflict(self, symbol: str, conflicting_decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Resolve conflicts between agents."""
        from services.agent_coordination import resolve_agent_conflict as resolve_conflict
        
        try:
            result = resolve_conflict(symbol, conflicting_decisions)
            logger.info("conflict_resolved", symbol=symbol, resolution=result.get("resolution"), method=result.get("resolution_method"))
            return result
        except Exception as e:
            logger.error("resolve_agent_conflict_error", error=str(e))
            return {"error": str(e), "resolution": "HOLD", "resolution_method": "error_default"}
    
    async def filter_collaborative_signals(self, symbol: str, agent_signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Filter and combine signals from multiple agents."""
        from services.agent_coordination import filter_collaborative_signals as filter_signals
        
        try:
            result = filter_signals(symbol, agent_signals)
            logger.info("signals_filtered", symbol=symbol, filtered_signal=result.get("filtered_signal"), quality=result.get("signal_quality"))
            return result
        except Exception as e:
            logger.error("filter_collaborative_signals_error", error=str(e))
            return {"error": str(e), "filtered_signal": "NEUTRAL", "signal_quality": "LOW"}
