"""
Alpaca Markets connector for live and paper trading.
100% Free API - No subscription fees required.
"""
from typing import Dict, Any, Optional
import asyncio
from config import get_settings
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = structlog.get_logger()
settings = get_settings()


class AlpacaConnectionError(Exception):
    """Raised when connection to Alpaca fails."""
    pass


class AlpacaOrderError(Exception):
    """Raised when an order fails to execute."""
    pass


class AlpacaConnector:
    """Alpaca Markets API connector with retry logic."""
    
    MAX_RETRIES = 3
    RETRY_MIN_WAIT = 1
    RETRY_MAX_WAIT = 10
    
    def __init__(self):
        self.api_key = settings.alpaca_api_key
        self.api_secret = settings.alpaca_api_secret
        self.base_url = settings.alpaca_base_url
        self.connected = False
        self.api = None
        self._connection_attempts = 0
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True
    )
    async def connect(self) -> bool:
        """Establish connection to Alpaca API with retry logic."""
        if settings.is_paper_trading():
            logger.info("alpaca_paper_trading_mode", message="Connecting to Alpaca Paper API")
        
        try:
            from alpaca_trade_api import REST
            
            self.api = REST(
                key_id=self.api_key,
                secret_key=self.api_secret,
                base_url=self.base_url,
            )
            
            # Test connection by getting account info
            account = self.api.get_account()
            
            self.connected = True
            self._connection_attempts = 0
            
            logger.info(
                "alpaca_connected",
                base_url=self.base_url,
                account_id=account.id,
                status=account.status,
                cash=float(account.cash),
                portfolio_value=float(account.portfolio_value),
            )
            return True
            
        except Exception as e:
            self._connection_attempts += 1
            logger.error(
                "alpaca_connection_failed", 
                error=str(e),
                attempt=self._connection_attempts
            )
            self.connected = False
            raise AlpacaConnectionError(f"Failed to connect to Alpaca: {str(e)}")
    
    async def disconnect(self):
        """Disconnect from Alpaca API."""
        self.api = None
        self.connected = False
        logger.info("alpaca_disconnected")
    
    async def place_order(
        self,
        symbol: str,
        action: str,
        quantity: int,
    ) -> Dict[str, Any]:
        """
        Place a market order.
        
        Args:
            symbol: Stock symbol
            action: "BUY" or "SELL"
            quantity: Number of shares
            
        Returns:
            Execution result
        """
        try:
            if not self.connected:
                await self.connect()
            
            # Convert action to Alpaca format (buy/sell lowercase)
            side = action.lower()
            
            # Submit market order
            order = self.api.submit_order(
                symbol=symbol,
                qty=quantity,
                side=side,
                type='market',
                time_in_force='day'
            )
            
            logger.info(
                "alpaca_order_submitted",
                symbol=symbol,
                action=action,
                quantity=quantity,
                order_id=order.id,
                status=order.status,
            )
            
            # Wait for order to fill (timeout after 30s)
            for _ in range(30):
                await asyncio.sleep(1)
                order = self.api.get_order(order.id)
                
                if order.status == 'filled':
                    fill_price = float(order.filled_avg_price)
                    
                    logger.info(
                        "alpaca_order_filled",
                        symbol=symbol,
                        action=action,
                        quantity=quantity,
                        price=fill_price,
                        order_id=order.id,
                    )
                    
                    return {
                        "status": "filled",
                        "symbol": symbol,
                        "action": action,
                        "quantity": int(order.filled_qty),
                        "price": fill_price,
                        "order_id": order.id,
                        "is_paper": settings.is_paper_trading(),
                    }
                
                elif order.status in ['canceled', 'rejected', 'expired']:
                    return {
                        "status": "error",
                        "error": f"Order {order.status}",
                        "order_id": order.id,
                    }
            
            # Timeout
            return {
                "status": "timeout",
                "error": "Order did not fill within 30 seconds",
                "order_id": order.id,
            }
            
        except Exception as e:
            logger.error(
                "alpaca_order_error",
                symbol=symbol,
                action=action,
                error=str(e),
            )
            return {
                "status": "error",
                "error": str(e),
            }
    
    async def get_stock_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get real-time stock price from Alpaca."""
        try:
            if not self.connected:
                await self.connect()
            
            # Get latest trade
            trade = self.api.get_latest_trade(symbol)
            
            # Get latest quote for additional info
            quote = self.api.get_latest_quote(symbol)
            
            # Get previous close for change calculation
            bars = self.api.get_bars(
                symbol,
                '1Day',
                limit=2
            ).df
            
            prev_close = float(bars['close'].iloc[-2]) if len(bars) >= 2 else float(trade.price)
            current_price = float(trade.price)
            
            return {
                "symbol": symbol,
                "price": current_price,
                "change": current_price - prev_close,
                "change_percent": ((current_price - prev_close) / prev_close) * 100,
                "bid": float(quote.bid_price),
                "ask": float(quote.ask_price),
                "volume": int(trade.size),
            }
            
        except Exception as e:
            logger.error("alpaca_price_fetch_error", symbol=symbol, error=str(e))
            return None
    
    async def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Get account information."""
        try:
            if not self.connected:
                await self.connect()
            
            account = self.api.get_account()
            
            return {
                "account_id": account.id,
                "status": account.status,
                "cash": float(account.cash),
                "portfolio_value": float(account.portfolio_value),
                "buying_power": float(account.buying_power),
                "equity": float(account.equity),
                "last_equity": float(account.last_equity),
                "pattern_day_trader": account.pattern_day_trader,
            }
            
        except Exception as e:
            logger.error("alpaca_account_fetch_error", error=str(e))
            return None
    
    async def get_positions(self) -> list:
        """Get all open positions."""
        try:
            if not self.connected:
                await self.connect()
            
            positions = self.api.list_positions()
            
            return [
                {
                    "symbol": pos.symbol,
                    "qty": int(pos.qty),
                    "side": pos.side,
                    "market_value": float(pos.market_value),
                    "cost_basis": float(pos.cost_basis),
                    "unrealized_pl": float(pos.unrealized_pl),
                    "unrealized_plpc": float(pos.unrealized_plpc),
                    "current_price": float(pos.current_price),
                    "avg_entry_price": float(pos.avg_entry_price),
                }
                for pos in positions
            ]
            
        except Exception as e:
            logger.error("alpaca_positions_fetch_error", error=str(e))
            return []
    
    async def healthcheck(self) -> bool:
        """Check Alpaca API connection health."""
        if not self.connected:
            return await self.connect()
        
        try:
            # Simple check - request account info
            account = self.api.get_account()
            return account.status == 'ACTIVE'
        except Exception:
            return False
    
    async def get_all_assets(
        self,
        asset_class: str = "us_equity",
        status: str = "active"
    ) -> list:
        """
        Get all tradable assets from Alpaca.
        
        Args:
            asset_class: Type of asset (us_equity, crypto)
            status: Asset status (active, inactive)
            
        Returns:
            List of assets with symbol, name, exchange, tradable status
        """
        try:
            if not self.connected:
                await self.connect()
            
            assets = self.api.list_assets(
                status=status,
                asset_class=asset_class
            )
            
            result = []
            for asset in assets:
                if asset.tradable and asset.fractionable:
                    result.append({
                        "symbol": asset.symbol,
                        "name": asset.name,
                        "exchange": asset.exchange,
                        "asset_class": getattr(asset, 'asset_class', asset_class),
                        "tradable": asset.tradable,
                        "marginable": asset.marginable,
                        "shortable": asset.shortable,
                        "easy_to_borrow": asset.easy_to_borrow,
                    })
            
            logger.info(
                "alpaca_assets_fetched",
                count=len(result),
                asset_class=asset_class,
            )
            
            return result
            
        except Exception as e:
            logger.error("alpaca_assets_fetch_error", error=str(e))
            return []
    
    async def get_historical_data(
        self,
        symbol: str,
        period: str
    ) -> list:
        """
        Get historical OHLCV data from Alpaca.
        
        Args:
            symbol: Stock symbol
            period: Time period ("1d", "1w", "1m", "3m")
            
        Returns:
            List of OHLCV bars with date, open, high, low, close, volume
        """
        try:
            if not self.connected:
                await self.connect()
            
            # Map period to Alpaca timeframe and limit
            period_map = {
                "1d": ("1Day", 1),
                "1w": ("1Day", 7),
                "1m": ("1Day", 30),
                "3m": ("1Day", 90),
            }
            
            timeframe, limit = period_map.get(period, ("1Day", 30))
            
            # Get bars from Alpaca
            bars = self.api.get_bars(
                symbol,
                timeframe,
                limit=limit
            ).df
            
            if bars.empty:
                logger.warning("alpaca_no_historical_data", symbol=symbol, period=period)
                return []
            
            # Convert DataFrame to list of dicts
            result = []
            for index, row in bars.iterrows():
                result.append({
                    "date": index.strftime("%Y-%m-%d"),
                    "open": float(row['open']),
                    "high": float(row['high']),
                    "low": float(row['low']),
                    "close": float(row['close']),
                    "volume": int(row['volume']),
                })
            
            logger.info(
                "alpaca_historical_fetched",
                symbol=symbol,
                period=period,
                bars=len(result)
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "alpaca_historical_fetch_error",
                symbol=symbol,
                period=period,
                error=str(e)
            )
            return []


# Singleton
_alpaca_connector: Optional[AlpacaConnector] = None


def get_alpaca_connector() -> AlpacaConnector:
    """Get Alpaca connector instance."""
    global _alpaca_connector
    if _alpaca_connector is None:
        _alpaca_connector = AlpacaConnector()
    return _alpaca_connector
