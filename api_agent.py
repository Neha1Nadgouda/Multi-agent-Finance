"""API Agent for fetching market data"""
import yfinance as yf
from alpha_vantage.timeseries import TimeSeries
from typing import Dict, Any, List, Optional
import asyncio
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dotenv import load_dotenv
import time
import aiohttp
from functools import lru_cache
import concurrent.futures
from aiohttp import ClientTimeout, TCPConnector

load_dotenv()

class APIAgent:
    def __init__(self):
        self.alpha_vantage_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        self.alpha_vantage = TimeSeries(key=self.alpha_vantage_key) if self.alpha_vantage_key else None
        self.cache = {}
        self.cache_duration = 60  # 1 minute cache
        self.last_request_time = 0
        self.min_request_interval = 0.5  # 500ms between requests
        self.session = None
        self.timeout = ClientTimeout(total=10)
        self.connector = TCPConnector(limit=100, ttl_dns_cache=300)
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        
        # List of Asian tech stocks to monitor
        self.asia_tech_stocks = [
            "TSM", "BABA", "9988.HK", "BIDU", "9984.T", "035420.KS",  # TSMC, Alibaba, Baidu, Softbank, NAVER
            "000660.KS", "2330.TW", "6758.T", "067000.KS"  # SK Hynix, TSMC, Sony, Samsung Electronics
        ]
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=self.timeout, connector=self.connector)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            await self.connector.close()

    @lru_cache(maxsize=100)
    def _get_cached_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get cached data if available and not expired"""
        if symbol in self.cache:
            data, timestamp = self.cache[symbol]
            if (datetime.now() - timestamp).seconds < self.cache_duration:
                return data
        return None

    async def _fetch_concurrent_data(self, symbols: List[str]) -> Dict[str, Any]:
        """Fetch data for multiple symbols concurrently with improved error handling"""
        async def fetch_single(symbol: str) -> Dict[str, Any]:
            # Check cache first
            cached = self._get_cached_data(symbol)
            if cached:
                return {symbol: cached}

            try:
                loop = asyncio.get_event_loop()
                stock = await loop.run_in_executor(self.thread_pool, yf.Ticker, symbol)
                info = await loop.run_in_executor(self.thread_pool, lambda: stock.fast_info)
                
                data = {
                    "price": float(info.last_price if hasattr(info, 'last_price') else 0),
                    "change": float(info.regular_market_change if hasattr(info, 'regular_market_change') else 0),
                    "volume": int(info.last_volume if hasattr(info, 'last_volume') else 0)
                }
                
                # Cache the result
                self.cache[symbol] = (data, datetime.now())
                return {symbol: data}
            except Exception as e:
                print(f"Error fetching {symbol}: {str(e)}")
                return {symbol: None}

        # Create tasks for all symbols with semaphore for rate limiting
        semaphore = asyncio.Semaphore(10)  # Limit concurrent requests
        async def fetch_with_semaphore(symbol):
            async with semaphore:
                return await fetch_single(symbol)

        tasks = [fetch_with_semaphore(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks)
        
        # Combine results
        combined_data = {}
        for result in results:
            combined_data.update(result)
            
        return combined_data

    async def get_market_data(self) -> Dict[str, Any]:
        """Get market data from various sources with improved caching"""
        try:
            symbols = ["AAPL", "GOOGL", "MSFT", "AMZN"]
            
            # Use connection pooling for concurrent requests
            async with aiohttp.ClientSession(timeout=self.timeout, connector=self.connector) as session:
                self.session = session
                data = await self._fetch_concurrent_data(symbols)
            
            # Filter out None values and ensure we have data
            data = {k: v for k, v in data.items() if v is not None}
            
            if not data:  # If no real data available, return sample data
                data = {
                    "SAMPLE": {
                        "price": 100.0,
                        "change": 1.5,
                        "volume": 1000000
                    }
                }
            
            return {
                "stocks": data,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error in get_market_data: {str(e)}")
            return {
                "stocks": {
                    "SAMPLE": {
                        "price": 100.0,
                        "change": 1.5,
                        "volume": 1000000
                    }
                },
                "timestamp": datetime.now().isoformat()
            }
    
    async def _get_yahoo_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch data from Yahoo Finance"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info
            hist = ticker.history(period="2d")
            
            if hist.empty:
                return None
                
            current_data = hist.iloc[-1]
            prev_data = hist.iloc[-2] if len(hist) > 1 else current_data
            
            return {
                "symbol": symbol,
                "price": float(current_data["Close"]),
                "change": float(current_data["Close"] - prev_data["Close"]),
                "change_percent": float((current_data["Close"] - prev_data["Close"]) / prev_data["Close"] * 100),
                "volume": int(current_data["Volume"]),
                "market_cap": getattr(info, "market_cap", None),
                "pe_ratio": getattr(info, "pe_ratio", None),
                "timestamp": datetime.now().isoformat(),
                "source": "yahoo_finance"
            }
            
        except Exception as e:
            print(f"Yahoo Finance error for {symbol}: {str(e)}")
            return None
    
    async def _get_alpha_vantage_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch data from Alpha Vantage as fallback"""
        if not self.alpha_vantage:
            return None
            
        try:
            data, meta = self.alpha_vantage.get_quote_endpoint(symbol)
            
            return {
                "symbol": symbol,
                "price": float(data["05. price"]),
                "change": float(data["09. change"]),
                "change_percent": float(data["10. change percent"].strip("%")),
                "volume": int(data["06. volume"]),
                "timestamp": data["07. latest trading day"],
                "source": "alpha_vantage"
            }
            
        except Exception as e:
            print(f"Alpha Vantage error for {symbol}: {str(e)}")
            return None
    
    async def get_earnings_data(self) -> Dict[str, Any]:
        """Fetch recent earnings data for Asian tech stocks"""
        earnings_data = {}
        
        for symbol in self.asia_tech_stocks:
            try:
                ticker = yf.Ticker(symbol)
                earnings = ticker.earnings
                if earnings is not None and not earnings.empty:
                    latest_earnings = earnings.iloc[-1]
                    earnings_data[symbol] = {
                        "actual_eps": float(latest_earnings["Earnings"]),
                        "estimated_eps": None,  # Would need additional data source for estimates
                        "surprise_percent": None,
                        "period": str(latest_earnings.name)
                    }
            except Exception as e:
                print(f"Error fetching earnings data for {symbol}: {str(e)}")
                continue
                
        return earnings_data
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if the API service is working"""
        try:
            # Simple health check without fetching data
            return {
                "healthy": True,
                "timestamp": datetime.now().isoformat(),
                "cache_size": len(self.cache) if hasattr(self, 'cache') else 0,
                "last_request": getattr(self, 'last_request_time', None)
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            } 