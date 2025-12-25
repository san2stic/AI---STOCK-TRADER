"""
Binance connector for cryptocurrency spot trading.
Supports both testnet (paper trading) and production.
"""
from typing import Dict, Any, Optional, List
import asyncio
from config import get_settings
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()
settings = get_settings()


class BinanceConnectionError(Exception):
    """Raised when connection to Binance fails."""
    pass


class BinanceOrderError(Exception):
    """Raised when an order fails to execute."""
    pass


class BinanceConnector:
    """Binance Spot API connector with retry logic."""
    
    MAX_RETRIES = 3
    RETRY_MIN_WAIT = 1
    RETRY_MAX_WAIT = 10
    
    def __init__(self):
        self.api_key = settings.binance_api_key
        self.api_secret = settings.binance_api_secret
        self.testnet = settings.binance_testnet
        self.connected = False
        self.client = None
        self.data_client = None  # Always Production for reliable data
        self._connection_attempts = 0
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True
    )
    async def connect(self) -> bool:
        """Establish connection to Binance API with retry logic."""
        if self.testnet:
            logger.info("binance_testnet_mode", message="Connecting to Binance Testnet (Execution) + Production (Data)")
        else:
            logger.info("binance_production_mode", message="Connecting to Binance Production")
        
        try:
            from binance.client import Client
            from binance.exceptions import BinanceAPIException
            
            # 1. Create EXECUTION client (Testnet or Prod based on config)
            if self.testnet:
                self.client = Client(
                    self.api_key,
                    self.api_secret,
                    testnet=True
                )
            else:
                self.client = Client(
                    self.api_key,
                    self.api_secret
                )
            
            # 2. Create DATA client (Always Production for reliable market data)
            # Anonymous client is sufficient for public data
            self.data_client = Client(None, None)
            
            # Test connection by getting account info (Execution client)
            account = self.client.get_account()
            
            # Test data connection
            self.data_client.ping()
            
            self.connected = True
            
            # Calculate total balance in USDT
            total_usdt = 0.0
            for balance in account['balances']:
                free = float(balance['free'])
                locked = float(balance['locked'])
                total = free + locked
                if total > 0:
                    # For simplicity, only count USDT and stablecoins directly
                    if balance['asset'] in ['USDT', 'BUSD', 'USDC']:
                        total_usdt += total
            
            logger.info(
                "binance_connected",
                testnet=self.testnet,
                can_trade=account['canTrade'],
                usdt_balance=total_usdt,
            )
            self._connection_attempts = 0
            return True
            
        except Exception as e:
            self._connection_attempts += 1
            logger.error(
                "binance_connection_failed", 
                error=str(e),
                attempt=self._connection_attempts
            )
            self.connected = False
            raise BinanceConnectionError(f"Failed to connect to Binance: {str(e)}")
    
    async def disconnect(self):
        """Disconnect from Binance API."""
        self.client = None
        self.connected = False
        logger.info("binance_disconnected")
    
    async def place_order(
        self,
        symbol: str,
        action: str,
        quantity: float,
    ) -> Dict[str, Any]:
        """
        Place a market order for cryptocurrency.
        
        Args:
            symbol: Crypto pair (e.g., "BTCUSDT")
            action: "BUY" or "SELL"
            quantity: Amount of base currency (e.g., BTC amount for BTCUSDT)
            
        Returns:
            Execution result
        """
        try:
            if not self.connected:
                await self.connect()
            
            from binance.exceptions import BinanceAPIException
            
            # Convert action to Binance format (BUY/SELL uppercase)
            side = action.upper()
            
            # Place market order
            logger.info(
                "binance_placing_order",
                symbol=symbol,
                side=side,
                quantity=quantity,
            )
            
            order = self.client.order_market(
                symbol=symbol,
                side=side,
                quantity=quantity
            )
            
            logger.info(
                "binance_order_placed",
                symbol=symbol,
                action=action,
                order_id=order['orderId'],
                status=order['status'],
            )
            
            # Check if order was filled
            if order['status'] == 'FILLED':
                # Calculate average fill price
                fills = order.get('fills', [])
                total_cost = 0.0
                total_qty = 0.0
                
                for fill in fills:
                    price = float(fill['price'])
                    qty = float(fill['qty'])
                    total_cost += price * qty
                    total_qty += qty
                
                avg_price = total_cost / total_qty if total_qty > 0 else 0.0
                
                logger.info(
                    "binance_order_filled",
                    symbol=symbol,
                    action=action,
                    quantity=total_qty,
                    avg_price=avg_price,
                    order_id=order['orderId'],
                )
                
                return {
                    "status": "filled",
                    "symbol": symbol,
                    "action": action,
                    "quantity": total_qty,
                    "price": avg_price,
                    "order_id": order['orderId'],
                    "is_testnet": self.testnet,
                }
            else:
                # Order not immediately filled (unusual for market orders)
                return {
                    "status": "pending",
                    "error": f"Order status: {order['status']}",
                    "order_id": order['orderId'],
                }
            
        except Exception as e:
            logger.error(
                "binance_order_error",
                symbol=symbol,
                action=action,
                error=str(e),
            )
            return {
                "status": "error",
                "error": str(e),
            }
    
    async def get_crypto_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get real-time cryptocurrency price from Binance."""
        try:
            if not self.connected:
                await self.connect()
            
            # Get current ticker
            ticker = self.data_client.get_ticker(symbol=symbol)
            
            # Get 24h price change
            current_price = float(ticker['lastPrice'])
            price_change = float(ticker['priceChange'])
            price_change_percent = float(ticker['priceChangePercent'])
            
            return {
                "symbol": symbol,
                "price": current_price,
                "change": price_change,
                "change_percent": price_change_percent,
                "bid": float(ticker['bidPrice']),
                "ask": float(ticker['askPrice']),
                "volume": float(ticker['volume']),
                "high_24h": float(ticker['highPrice']),
                "low_24h": float(ticker['lowPrice']),
            }
            
        except Exception as e:
            logger.error("binance_price_fetch_error", symbol=symbol, error=str(e))
            return None
    
    async def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Get account information and balances."""
        try:
            if not self.connected:
                await self.connect()
            
            account = self.client.get_account()
            
            # Parse balances
            balances = {}
            total_usdt_value = 0.0
            
            for balance in account['balances']:
                free = float(balance['free'])
                locked = float(balance['locked'])
                total = free + locked
                
                if total > 0:
                    balances[balance['asset']] = {
                        'free': free,
                        'locked': locked,
                        'total': total,
                    }
                    
                    # Simple approximation: count stablecoins as USDT value
                    if balance['asset'] in ['USDT', 'BUSD', 'USDC', 'DAI']:
                        total_usdt_value += total
            
            return {
                "can_trade": account['canTrade'],
                "can_withdraw": account['canWithdraw'],
                "can_deposit": account['canDeposit'],
                "balances": balances,
                "total_usdt_value": total_usdt_value,
                "account_type": account['accountType'],
            }
            
        except Exception as e:
            logger.error("binance_account_fetch_error", error=str(e))
            return None
    
    async def get_positions(self) -> list:
        """Get all non-zero crypto holdings."""
        try:
            if not self.connected:
                await self.connect()
            
            account = self.client.get_account()
            positions = []
            
            for balance in account['balances']:
                free = float(balance['free'])
                locked = float(balance['locked'])
                total = free + locked
                
                if total > 0 and balance['asset'] != 'USDT':
                    # Get current price against USDT
                    symbol = f"{balance['asset']}USDT"
                    
                    try:
                        ticker = self.data_client.get_ticker(symbol=symbol)
                        current_price = float(ticker['lastPrice'])
                        market_value = total * current_price
                        
                        positions.append({
                            "asset": balance['asset'],
                            "symbol": symbol,
                            "quantity": total,
                            "free": free,
                            "locked": locked,
                            "current_price": current_price,
                            "market_value": market_value,
                        })
                    except Exception as e:
                        logger.warning(
                            "binance_position_price_fetch_warning",
                            asset=balance['asset'],
                            error=str(e)
                        )
                        # Pair doesn't exist or error fetching price
                        # Include position without price
                        positions.append({
                            "asset": balance['asset'],
                            "symbol": None,
                            "quantity": total,
                            "free": free,
                            "locked": locked,
                            "current_price": None,
                            "market_value": None,
                        })
            
            return positions
            
        except Exception as e:
            logger.error("binance_positions_fetch_error", error=str(e))
            return []
    
    async def healthcheck(self) -> bool:
        """Check Binance API connection health."""
        if not self.connected:
            return await self.connect()
        
        try:
            # Simple check - ping server
            self.client.ping()
            return True
        except Exception:
            return False
    
    async def get_exchange_info(self, symbol: Optional[str] = None) -> Optional[Dict]:
        """Get exchange trading rules and symbol information."""
        try:
            if not self.connected:
                await self.connect()
            
            if symbol:
                info = self.data_client.get_symbol_info(symbol)
                return info
            else:
                info = self.data_client.get_exchange_info()
                return info
            
        except Exception as e:
            logger.error("binance_exchange_info_error", error=str(e))
            return None
    
    async def get_all_tradable_pairs(self) -> list:
        """Get all tradable USDT pairs from Binance."""
        try:
            if not self.connected:
                await self.connect()
            
            exchange_info = self.data_client.get_exchange_info()
            
            tradable_pairs = []
            for symbol_info in exchange_info['symbols']:
                # Only include USDT pairs that are actively trading
                if (symbol_info['quoteAsset'] == 'USDT' and 
                    symbol_info['status'] == 'TRADING' and
                    symbol_info['isSpotTradingAllowed']):
                    
                    tradable_pairs.append({
                        'symbol': symbol_info['symbol'],
                        'baseAsset': symbol_info['baseAsset'],
                        'quoteAsset': symbol_info['quoteAsset'],
                    })
            
            logger.info(
                "binance_tradable_pairs_fetched",
                count=len(tradable_pairs),
            )
            
            return tradable_pairs
            
        except Exception as e:
            logger.error("binance_tradable_pairs_error", error=str(e))
            return []
    
    # ========== NEW CRYPTO INTELLIGENCE METHODS ==========
    
    async def get_funding_rate(self, symbol: str) -> Dict[str, Any]:
        """
        Get funding rate for perpetual futures.
        Note: This uses the Futures API endpoint.
        Positive = longs pay shorts (bullish overextended)
        Negative = shorts pay longs (bearish overextended)
        """
        try:
            import httpx
            
            # Use Binance Futures API for funding rates
            # This is a public endpoint, no API key required
            # ALWAYS use Production for data analysis to ensure accurate sentiment
            base_url = "https://fapi.binance.com"
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Get current funding rate
                response = await client.get(
                    f"{base_url}/fapi/v1/premiumIndex",
                    params={"symbol": symbol}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    funding_rate = float(data.get("lastFundingRate", 0))
                    mark_price = float(data.get("markPrice", 0))
                    index_price = float(data.get("indexPrice", 0))
                    next_funding_time = data.get("nextFundingTime", 0)
                    
                    # Convert funding rate to annualized (funding every 8 hours = 3x daily)
                    daily_rate = funding_rate * 3
                    annualized_rate = daily_rate * 365 * 100  # As percentage
                    
                    # Interpret funding rate
                    if funding_rate > 0.001:  # > 0.1%
                        sentiment = "extreme_bullish"
                        signal = "caution_longs"
                        interpretation = "High positive funding - longs may be overextended"
                    elif funding_rate > 0.0005:
                        sentiment = "bullish"
                        signal = "neutral"
                        interpretation = "Moderate positive funding - slight bullish bias"
                    elif funding_rate < -0.001:
                        sentiment = "extreme_bearish"
                        signal = "caution_shorts"
                        interpretation = "High negative funding - shorts may be overextended"
                    elif funding_rate < -0.0005:
                        sentiment = "bearish"
                        signal = "neutral"
                        interpretation = "Moderate negative funding - slight bearish bias"
                    else:
                        sentiment = "neutral"
                        signal = "neutral"
                        interpretation = "Neutral funding - balanced market"
                    
                    return {
                        "symbol": symbol,
                        "funding_rate": funding_rate,
                        "funding_rate_percent": round(funding_rate * 100, 4),
                        "annualized_rate_percent": round(annualized_rate, 2),
                        "mark_price": mark_price,
                        "index_price": index_price,
                        "next_funding_time": next_funding_time,
                        "sentiment": sentiment,
                        "signal": signal,
                        "interpretation": interpretation,
                    }
                else:
                    return {"error": f"Failed to fetch funding rate: {response.status_code}"}
                    
        except Exception as e:
            logger.error("binance_funding_rate_error", symbol=symbol, error=str(e))
            return {"error": str(e)}
    
    async def get_order_book_analysis(self, symbol: str, depth: int = 20) -> Dict[str, Any]:
        """
        Analyze order book depth for support/resistance levels.
        Returns bid/ask imbalance and significant order walls.
        """
        try:
            if not self.connected:
                await self.connect()
            
            # Get order book
            order_book = self.data_client.get_order_book(symbol=symbol, limit=depth)
            
            bids = order_book.get("bids", [])
            asks = order_book.get("asks", [])
            
            # Calculate total bid and ask volume
            total_bid_volume = sum(float(bid[1]) for bid in bids)
            total_ask_volume = sum(float(ask[1]) for ask in asks)
            
            # Calculate imbalance
            total_volume = total_bid_volume + total_ask_volume
            imbalance = 0
            if total_volume > 0:
                imbalance = (total_bid_volume - total_ask_volume) / total_volume
            
            # Find significant walls (orders with > 5% of total volume)
            threshold = total_volume * 0.05
            
            bid_walls = []
            for bid in bids:
                price = float(bid[0])
                volume = float(bid[1])
                if volume > threshold:
                    bid_walls.append({
                        "price": price,
                        "volume": volume,
                        "percent_of_total": round((volume / total_volume) * 100, 2),
                        "type": "support"
                    })
            
            ask_walls = []
            for ask in asks:
                price = float(ask[0])
                volume = float(ask[1])
                if volume > threshold:
                    ask_walls.append({
                        "price": price,
                        "volume": volume,
                        "percent_of_total": round((volume / total_volume) * 100, 2),
                        "type": "resistance"
                    })
            
            # Get best bid/ask
            best_bid = float(bids[0][0]) if bids else 0
            best_ask = float(asks[0][0]) if asks else 0
            spread = best_ask - best_bid
            spread_percent = (spread / best_bid * 100) if best_bid > 0 else 0
            
            # Interpret imbalance
            if imbalance > 0.3:
                imbalance_signal = "strong_buy_pressure"
                interpretation = "Strong buy-side pressure - potential upward move"
            elif imbalance > 0.1:
                imbalance_signal = "buy_pressure"
                interpretation = "Moderate buy-side pressure"
            elif imbalance < -0.3:
                imbalance_signal = "strong_sell_pressure"
                interpretation = "Strong sell-side pressure - potential downward move"
            elif imbalance < -0.1:
                imbalance_signal = "sell_pressure"
                interpretation = "Moderate sell-side pressure"
            else:
                imbalance_signal = "balanced"
                interpretation = "Balanced order book"
            
            return {
                "symbol": symbol,
                "best_bid": best_bid,
                "best_ask": best_ask,
                "spread": round(spread, 8),
                "spread_percent": round(spread_percent, 4),
                "total_bid_volume": round(total_bid_volume, 4),
                "total_ask_volume": round(total_ask_volume, 4),
                "imbalance": round(imbalance, 4),
                "imbalance_signal": imbalance_signal,
                "bid_walls": bid_walls[:3],  # Top 3 support walls
                "ask_walls": ask_walls[:3],  # Top 3 resistance walls
                "interpretation": interpretation,
                "depth_analyzed": depth,
            }
            
        except Exception as e:
            logger.error("binance_order_book_error", symbol=symbol, error=str(e))
            return {"error": str(e)}


# Singleton
_binance_connector: Optional[BinanceConnector] = None


def get_binance_connector() -> BinanceConnector:
    """Get Binance connector instance."""
    global _binance_connector
    if _binance_connector is None:
        _binance_connector = BinanceConnector()
    return _binance_connector
