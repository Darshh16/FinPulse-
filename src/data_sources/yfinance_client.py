import yfinance as yf
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Problematic tickers to skip
BLACKLISTED_TICKERS = {'SQ', 'AFPS', 'DEFUNCT'}  # Add tickers that consistently fail


class StockPriceClient:
    """Client for fetching stock prices from yfinance with retry logic"""
    
    def __init__(self, max_workers: int = 5, max_retries: int = 3):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.max_retries = max_retries
    
    def _fetch_with_retry(self, ticker: str, period: str = "1d", interval: str = "1h", retries: int = 0) -> Optional[Dict]:
        """
        Fetch stock price with retry logic for handling transient errors
        
        Args:
            ticker: Stock ticker symbol
            period: Time period
            interval: Time interval
            retries: Current retry count
            
        Returns:
            Dictionary with price data or None if error
        """
        try:
            # Skip blacklisted tickers
            if ticker in BLACKLISTED_TICKERS:
                logger.debug(f"Skipping blacklisted ticker: {ticker}")
                return None
            
            # Add exponential backoff for retries
            if retries > 0:
                wait_time = 2 ** retries  # 2, 4, 8 seconds
                logger.debug(f"Retry {retries} for {ticker}, waiting {wait_time}s")
                time.sleep(wait_time)
            
            data = yf.download(
                ticker, 
                period=period, 
                interval=interval, 
                progress=False,
                timeout=10  # Add timeout
            )
            
            if data.empty:
                logger.warning(f"No data found for ticker: {ticker}")
                return None
            
            # Get latest price info
            latest = data.iloc[-1]
            
            return {
                "ticker": ticker,
                "timestamp": data.index[-1].to_pydatetime(),
                "open": float(latest["Open"].iloc[0]) if "Open" in latest.index else 0.0,
                "high": float(latest["High"].iloc[0]) if "High" in latest.index else 0.0,
                "low": float(latest["Low"].iloc[0]) if "Low" in latest.index else 0.0,
                "close": float(latest["Close"].iloc[0]) if "Close" in latest.index else 0.0,
                "volume": int(latest["Volume"].iloc[0]) if "Volume" in latest.index else 0
            }
        except Exception as e:
            error_str = str(e).lower()
            
            # Handle specific error types
            if "crumb" in error_str or "unauthorized" in error_str or "401" in error_str:
                # Crumb error - retry with backoff
                if retries < self.max_retries:
                    logger.info(f"Crumb error for {ticker}, retrying ({retries + 1}/{self.max_retries})")
                    return self._fetch_with_retry(ticker, period, interval, retries + 1)
                else:
                    logger.error(f"Max retries exceeded for {ticker} - crumb error")
                    return None
            
            elif "delisted" in error_str or "no data found" in error_str or "symbol may be delisted" in error_str:
                # Delisted or defunct ticker - add to blacklist
                logger.warning(f"Ticker {ticker} appears to be delisted or invalid, adding to blacklist")
                BLACKLISTED_TICKERS.add(ticker)
                return None
            
            elif "timeout" in error_str:
                # Timeout error - retry with backoff
                if retries < self.max_retries:
                    logger.info(f"Timeout for {ticker}, retrying ({retries + 1}/{self.max_retries})")
                    return self._fetch_with_retry(ticker, period, interval, retries + 1)
                else:
                    logger.error(f"Max retries exceeded for {ticker} - timeout")
                    return None
            
            else:
                # Other errors
                logger.error(f"Error fetching price for {ticker}: {str(e)}")
                return None
    
    def fetch_price(self, ticker: str, period: str = "1d", interval: str = "1h") -> Optional[Dict]:
        """
        Fetch stock price data for a single ticker
        
        Args:
            ticker: Stock ticker symbol
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, etc.)
            interval: Time interval (1m, 5m, 15m, 30m, 60m, 1d, etc.)
            
        Returns:
            Dictionary with price data or None if error
        """
        return self._fetch_with_retry(ticker, period, interval)
    
    def fetch_current_price(self, ticker: str) -> Optional[float]:
        """
        Fetch current price for a ticker
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Current price or None
        """
        price_data = self._fetch_with_retry(ticker, "1d", "1m")
        if price_data:
            return price_data.get("close")
        return None
    
    async def fetch_prices_async(self, tickers: List[str], period: str = "1d") -> List[Dict]:
        """
        Fetch prices for multiple tickers asynchronously
        
        Args:
            tickers: List of stock ticker symbols
            period: Time period
            
        Returns:
            List of price data dictionaries
        """
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(self.executor, self.fetch_price, ticker, period, "1h")
            for ticker in tickers
        ]
        
        results = await asyncio.gather(*tasks)
        return [r for r in results if r is not None]
    
    def fetch_price_history(
        self,
        ticker: str,
        period: str = "1mo",
        interval: str = "1d"
    ) -> List[Dict]:
        """
        Fetch historical price data with retry logic
        
        Args:
            ticker: Stock ticker symbol
            period: Time period
            interval: Time interval
            
        Returns:
            List of historical price data points
        """
        try:
            # Skip blacklisted tickers
            if ticker in BLACKLISTED_TICKERS:
                logger.debug(f"Skipping blacklisted ticker: {ticker}")
                return []
            
            data = yf.download(ticker, period=period, interval=interval, progress=False, timeout=10)
            
            if data.empty:
                logger.warning(f"No historical data found for {ticker}")
                return []
            
            results = []
            for timestamp, row in data.iterrows():
                results.append({
                    "ticker": ticker,
                    "timestamp": timestamp.to_pydatetime(),
                    "open": float(row["Open"].iloc[0]) if "Open" in row.index else 0.0,
                    "high": float(row["High"].iloc[0]) if "High" in row.index else 0.0,
                    "low": float(row["Low"].iloc[0]) if "Low" in row.index else 0.0,
                    "close": float(row["Close"].iloc[0]) if "Close" in row.index else 0.0,
                    "volume": int(row["Volume"].iloc[0]) if "Volume" in row.index else 0
                })
            
            return results
        except Exception as e:
            error_str = str(e).lower()
            
            # Handle delisted/invalid tickers
            if "delisted" in error_str or "no data found" in error_str:
                logger.warning(f"Ticker {ticker} appears invalid, adding to blacklist")
                BLACKLISTED_TICKERS.add(ticker)
            else:
                logger.error(f"Error fetching price history for {ticker}: {str(e)}")
            
            return []


async def fetch_stock_prices(tickers: List[str], period: str = "1d") -> List[Dict]:
    """
    Fetch current stock prices for multiple tickers
    
    Args:
        tickers: List of stock ticker symbols
        period: Time period to fetch
        
    Returns:
        List of price data
    """
    client = StockPriceClient()
    prices = await client.fetch_prices_async(tickers, period=period)
    logger.info(f"Fetched prices for {len(prices)} tickers")
    return prices


def get_stock_info(ticker: str) -> Optional[Dict]:
    """
    Get basic stock information
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Dictionary with stock info or None
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        return {
            "ticker": ticker,
            "name": info.get("longName", ""),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "market_cap": info.get("marketCap", 0),
            "pe_ratio": info.get("trailingPE", 0),
            "dividend_yield": info.get("dividendYield", 0)
        }
    except Exception as e:
        logger.error(f"Error fetching info for {ticker}: {str(e)}")
        return None


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def test():
        # Fetch prices for popular stocks
        tickers = ["AAPL", "MSFT", "TSLA", "GOOGL"]
        prices = await fetch_stock_prices(tickers)
        
        for price in prices:
            print(f"{price['ticker']}: ${price['close']}")
    
    asyncio.run(test())
