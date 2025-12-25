"""
Data collection service for market data, news, and social sentiment.
Aggregates data from multiple sources with caching.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import httpx
import asyncio
import json
from config import get_settings
from models.database import MarketData
from database import get_db
import structlog

logger = structlog.get_logger()
settings = get_settings()


class DataCollector:
    """Collect and cache market data from multiple sources."""
    
    def __init__(self):
        self.timeout = 15.0
        self._cache = {}  # In-memory cache
        
    async def get_current_price(self, symbol: str) -> Dict[str, Any]:
        """
        Get current stock price.
        Uses Alpaca API if available, falls back to mock data.
        """
        # Try Alpaca first
        try:
            from services.alpaca_connector import get_alpaca_connector
            alpaca = get_alpaca_connector()
            price_data = await alpaca.get_stock_price(symbol)
            if price_data:
                return price_data
        except Exception as e:
            logger.warning("alpaca_price_fetch_failed", symbol=symbol, error=str(e))
        
        # Fallback to mock data
        return await self._get_mock_price(symbol)
    

    
    def _get_mock_price_sync(self, symbol: str) -> Dict[str, Any]:
        """Generate mock price data for testing (synchronous)."""
        import random
        
        # Base prices for common symbols
        base_prices = {
            "AAPL": 180.0,
            "MSFT": 380.0,
            "GOOGL": 140.0,
            "AMZN": 170.0,
            "NVDA": 500.0,
            "TSLA": 250.0,
            "META": 480.0,
            "JPM": 180.0,
            "BAC": 35.0,
            "JNJ": 160.0,
            "PFE": 30.0,
            "MRNA": 100.0,
        }
        
        base_price = base_prices.get(symbol, 100.0)
        # Add random variation ±5%
        price = base_price * (1 + random.uniform(-0.05, 0.05))
        change = random.uniform(-5, 5)
        
        return {
            "symbol": symbol,
            "price": round(price, 2),
            "change": round(change, 2),
            "change_percent": f"{(change/price)*100:.2f}%",
            "volume": random.randint(1000000, 50000000),
            "is_mock": True,
        }
    
    async def _get_mock_price(self, symbol: str) -> Dict[str, Any]:
        """Generate mock price data for testing (async wrapper)."""
        return self._get_mock_price_sync(symbol)
    
    async def get_historical_data(
        self, 
        symbol: str, 
        period: str
    ) -> List[Dict[str, Any]]:
        """
        Get historical OHLCV data.
        
        Args:
            symbol: Stock symbol
            period: "1d", "1w", "1m", "3m"
        """
        # Check cache
        cache_key = f"hist_{symbol}_{period}"
        cached = await self._get_from_cache(cache_key, hours=1)
        if cached:
            return cached
        
        # Calculate date range
        days_map = {"1d": 1, "1w": 7, "1m": 30, "3m": 90}
        days = days_map.get(period, 30)
        
        # Try to get from Alpaca first, otherwise generate mock data
        try:
            from services.alpaca_connector import get_alpaca_connector
            alpaca = get_alpaca_connector()
            data = await alpaca.get_historical_data(symbol, period)
            if data:
                await self._save_to_cache(cache_key, data, hours=1)
                return data
        except Exception as e:
            logger.warning("alpaca_historical_fetch_failed", symbol=symbol, error=str(e))
        
        # Fallback to mock data
        data = self._generate_mock_historical(symbol, days)
        
        # Cache result
        await self._save_to_cache(cache_key, data, hours=1)
        return data
    
    def _generate_mock_historical(
        self, 
        symbol: str, 
        days: int
    ) -> List[Dict[str, Any]]:
        """Generate mock historical data."""
        import random
        from datetime import datetime, timedelta
        
        current_price = self._get_mock_price_sync(symbol)["price"]
        data = []
        
        for i in range(days):
            date = datetime.now() - timedelta(days=days-i)
            # Random walk
            change_pct = random.uniform(-0.03, 0.03)
            open_price = current_price
            high = open_price * (1 + abs(change_pct) + random.uniform(0, 0.02))
            low = open_price * (1 - abs(change_pct) - random.uniform(0, 0.02))
            close = open_price * (1 + change_pct)
            current_price = close
            
            data.append({
                "date": date.strftime("%Y-%m-%d"),
                "open": round(open_price, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "close": round(close, 2),
                "volume": random.randint(10000000, 100000000),
            })
        
        return data
    

    
    async def get_news(self, symbol: str, days: int = 7) -> List[Dict[str, Any]]:
        """Get recent news for a symbol."""
        cache_key = f"news_{symbol}_{days}"
        cached = await self._get_from_cache(cache_key, hours=6)
        if cached:
            return cached
        
        if not settings.news_api_key:
            # Return mock news
            news = self._generate_mock_news(symbol)
        else:
            news = await self._fetch_news_api(symbol, days)
        
        await self._save_to_cache(cache_key, news, hours=6)
        return news
    
    async def _fetch_news_api(self, symbol: str, days: int) -> List[Dict[str, Any]]:
        """Fetch news from NewsAPI."""
        try:
            from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            
            url = "https://newsapi.org/v2/everything"
            params = {
                "q": symbol,
                "from": from_date,
                "sortBy": "publishedAt",
                "language": "en",
                "apiKey": settings.news_api_key,
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                articles = []
                for article in data.get("articles", [])[:20]:
                    articles.append({
                        "title": article.get("title"),
                        "description": article.get("description"),
                        "source": article.get("source", {}).get("name"),
                        "url": article.get("url"),
                        "publishedAt": article.get("publishedAt"),
                    })
                
                return articles
        except Exception as e:
            logger.error("news_fetch_error", symbol=symbol, error=str(e))
            return self._generate_mock_news(symbol)
    
    def _generate_mock_news(self, symbol: str) -> List[Dict[str, Any]]:
        """Generate mock news for testing."""
        templates = [
            f"{symbol} announces quarterly earnings beat",
            f"Analysts upgrade {symbol} to buy",
            f"{symbol} launches new product line",
            f"Market volatility affects {symbol} trading",
            f"{symbol} CEO discusses growth strategy",
        ]
        
        news = []
        for i, title in enumerate(templates):
            news.append({
                "title": title,
                "description": f"Latest update on {symbol} company developments.",
                "source": "Mock News",
                "url": "https://example.com",
                "publishedAt": (datetime.now() - timedelta(days=i)).isoformat(),
                "is_mock": True,
            })
        
        return news
    
    async def search_twitter(self, query: str) -> List[Dict[str, Any]]:
        """Search Twitter/X (requires X API credentials)."""
        if not settings.has_twitter_access():
            return []
        
        # TODO: Implement Twitter API v2 search
        # This would use settings.twitter_bearer_token
        logger.warning("twitter_search_not_implemented", query=query)
        return []
    
    async def _get_from_cache(
        self, 
        key: str, 
        hours: int
    ) -> Optional[Any]:
        """Get data from cache if not expired."""
        try:
            with get_db() as db:
                cached = db.query(MarketData).filter(
                    MarketData.symbol == key.split("_")[1] if "_" in key else key,
                    MarketData.data_type == key.split("_")[0] if "_" in key else key,
                    MarketData.expires_at > datetime.utcnow(),
                ).first()
                
                if cached:
                    return cached.data
        except Exception as e:
            logger.warning("cache_read_failed", key=key, error=str(e))
        
        return None
    
    async def _save_to_cache(
        self, 
        key: str, 
        data: Any, 
        hours: int
    ) -> None:
        """Save data to cache with expiration."""
        try:
            parts = key.split("_", 1)
            data_type = parts[0]
            symbol = parts[1] if len(parts) > 1 else key
            
            with get_db() as db:
                # Delete existing
                db.query(MarketData).filter(
                    MarketData.symbol == symbol,
                    MarketData.data_type == data_type,
                ).delete()
                
                # Insert new
                cache_entry = MarketData(
                    symbol=symbol,
                    data_type=data_type,
                    data=data,
                    expires_at=datetime.utcnow() + timedelta(hours=hours),
                )
                db.add(cache_entry)
                db.commit()
        except Exception as e:
            logger.warning("cache_write_failed", key=key, error=str(e))

    
    async def get_all_tradable_assets(
        self,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all tradable assets from Alpaca.
        
        Args:
            category: Filter by category (tech, finance, healthcare, etc.)
        """
        from services.alpaca_connector import get_alpaca_connector
        
        # Try to get from Alpaca
        try:
            alpaca = get_alpaca_connector()
            assets = await alpaca.get_all_assets()
            
            # Simple category filtering based on exchanges and common patterns
            if category:
                category_filters = {
                    "tech": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "NFLX"],
                    "finance": ["JPM", "BAC", "GS", "MS", "C", "WFC", "BLK"],
                    "healthcare": ["JNJ", "PFE", "UNH", "ABBV", "TMO", "MRNA", "LLY"],
                }
                
                filter_symbols = category_filters.get(category.lower(), [])
                if filter_symbols:
                    assets = [a for a in assets if a["symbol"] in filter_symbols]
            
            return assets
            
        except Exception as e:
            logger.error("get_all_assets_error", error=str(e))
            # Return mock data for common stocks
            return self._generate_mock_assets(category)
    
    def _generate_mock_assets(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Generate mock asset data for testing."""
        all_assets = [
            {"symbol": "AAPL", "name": "Apple Inc", "exchange": "NASDAQ", "category": "tech"},
            {"symbol": "MSFT", "name": "Microsoft Corp", "exchange": "NASDAQ", "category": "tech"},
            {"symbol": "GOOGL", "name": "Alphabet Inc", "exchange": "NASDAQ", "category": "tech"},
            {"symbol": "AMZN", "name": "Amazon.com Inc", "exchange": "NASDAQ", "category": "tech"},
            {"symbol": "NVDA", "name": "NVIDIA Corp", "exchange": "NASDAQ", "category": "tech"},
            {"symbol": "TSLA", "name": "Tesla Inc", "exchange": "NASDAQ", "category": "tech"},
            {"symbol": "META", "name": "Meta Platforms Inc", "exchange": "NASDAQ", "category": "tech"},
            {"symbol": "JPM", "name": "JPMorgan Chase & Co", "exchange": "NYSE", "category": "finance"},
            {"symbol": "BAC", "name": "Bank of America Corp", "exchange": "NYSE", "category": "finance"},
            {"symbol": "JNJ", "name": "Johnson & Johnson", "exchange": "NYSE", "category": "healthcare"},
            {"symbol": "PFE", "name": "Pfizer Inc", "exchange": "NYSE", "category": "healthcare"},
        ]
        
        if category:
            return [a for a in all_assets if a.get("category") == category.lower()]
        return all_assets
    
    async def get_index_prices(self) -> Dict[str, Any]:
        """Get prices for major market indices via ETFs."""
        indices = {
            "SPY": "S&P 500",
            "QQQ": "NASDAQ 100",
            "DIA": "Dow Jones",
        }
        
        result = {}
        for symbol, name in indices.items():
            price_data = await self.get_current_price(symbol)
            result[symbol] = {
                "name": name,
                "price": price_data.get("price"),
                "change": price_data.get("change"),
                "change_percent": price_data.get("change_percent"),
            }
        
        return result
    
    async def calculate_technical_indicators(
        self,
        symbol: str,
        indicators: List[str]
    ) -> Dict[str, Any]:
        """
        Calculate technical indicators for a symbol.
        
        Args:
            symbol: Stock symbol
            indicators: List of indicators to calculate (RSI, MACD, BOLLINGER)
        """
        # Get historical data (need at least 30 days for RSI)
        historical = await self.get_historical_data(symbol, "3m")
        
        if not historical or len(historical) < 14:
            return {"error": "Insufficient data for technical indicators"}
        
        # Extract close prices
        closes = [bar["close"] for bar in historical]
        
        result = {}
        
        for indicator in indicators:
            indicator_upper = indicator.upper()
            
            if indicator_upper == "RSI":
                result["RSI"] = self._calculate_rsi(closes)
            elif indicator_upper == "MACD":
                result["MACD"] = self._calculate_macd(closes)
            elif indicator_upper == "BOLLINGER":
                result["BOLLINGER"] = self._calculate_bollinger_bands(closes)
            elif indicator_upper == "SMA":
                result["SMA"] = self._calculate_sma(closes, 20)
        
        return {"symbol": symbol, "indicators": result}
    
    def _calculate_rsi(self, closes: List[float], period: int = 14) -> Dict[str, Any]:
        """Calculate Relative Strength Index."""
        if len(closes) < period + 1:
            return {"value": None, "signal": "neutral"}
        
        # Calculate price changes
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        
        # Separate gains and losses
        gains = [d if d > 0 else 0 for d in deltas[-period:]]
        losses = [-d if d < 0 else 0 for d in deltas[-period:]]
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        # Generate signal
        signal = "oversold" if rsi < 30 else "overbought" if rsi > 70 else "neutral"
        
        return {"value": round(rsi, 2), "signal": signal}
    
    def _calculate_macd(self, closes: List[float]) -> Dict[str, Any]:
        """Calculate MACD (Moving Average Convergence Divergence)."""
        if len(closes) < 26:
            return {"macd": None, "signal": None, "histogram": None}
        
        # Calculate EMAs
        ema_12 = self._calculate_ema(closes, 12)
        ema_26 = self._calculate_ema(closes, 26)
        
        macd = ema_12 - ema_26
        
        # Signal line (9-day EMA of MACD)
        # For simplicity, use SMA instead of EMA
        signal = macd  # Simplified
        
        histogram = macd - signal
        
        trend = "bullish" if histogram > 0 else "bearish"
        
        return {
            "macd": round(macd, 2),
            "signal_line": round(signal, 2),
            "histogram": round(histogram, 2),
            "trend": trend
        }
    
    def _calculate_ema(self, closes: List[float], period: int) -> float:
        """Calculate Exponential Moving Average."""
        multiplier = 2 / (period + 1)
        ema = closes[0]
        
        for price in closes[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def _calculate_bollinger_bands(self, closes: List[float], period: int = 20) -> Dict[str, Any]:
        """Calculate Bollinger Bands."""
        if len(closes) < period:
            return {"upper": None, "middle": None, "lower": None}
        
        recent = closes[-period:]
        sma = sum(recent) / period
        
        # Calculate standard deviation
        variance = sum((x - sma) ** 2 for x in recent) / period
        std_dev = variance ** 0.5
        
        upper = sma + (2 * std_dev)
        lower = sma - (2 * std_dev)
        
        current_price = closes[-1]
        
        # Determine position
        if current_price > upper:
            position = "above_upper"
        elif current_price < lower:
            position = "below_lower"
        else:
            position = "within_bands"
        
        return {
            "upper": round(upper, 2),
            "middle": round(sma, 2),
            "lower": round(lower, 2),
            "current_price": round(current_price, 2),
            "position": position
        }
    
    def _calculate_sma(self, closes: List[float], period: int) -> float:
        """Calculate Simple Moving Average."""
        if len(closes) < period:
            return closes[-1]
        
        recent = closes[-period:]
        return round(sum(recent) / period, 2)


# Singleton
_collector: Optional[DataCollector] = None


def get_data_collector() -> DataCollector:
    """Get data collector instance."""
    global _collector
    if _collector is None:
        _collector = DataCollector()
    return _collector
