from typing import Dict, Any, List, Optional
import aiohttp
import asyncio
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import json
import os
from dotenv import load_dotenv
import requests

load_dotenv()

class ScrapingAgent:
    def __init__(self):
        self.cache = {}
        self.cache_duration = timedelta(minutes=15)
        self.news_sources = [
            "https://finance.yahoo.com",
            "https://www.reuters.com/markets"
        ]
        
        # Initialize session
        self.session = None
    
    async def _ensure_session(self):
        """Ensure aiohttp session is created"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
    
    async def get_latest_news(self) -> Dict[str, Any]:
        """Get latest news from various sources"""
        try:
            # Simulated news data for now
            news_data = {
                "articles": [
                    {
                        "title": "Market Update: Tech Stocks Rally",
                        "source": "Sample News",
                        "timestamp": datetime.now().isoformat(),
                        "sentiment": 0.8
                    }
                ],
                "timestamp": datetime.now().isoformat()
            }
            return news_data
            
        except Exception as e:
            print(f"Error fetching news: {str(e)}")
            return {}
    
    async def _fetch_source(self, source: Dict[str, str]) -> List[Dict[str, Any]]:
        """Fetch news from a specific source"""
        try:
            if source["type"] == "rss":
                return await self._fetch_rss(source["url"])
            elif source["type"] == "html":
                return await self._fetch_html(source["url"])
            return []
            
        except Exception as e:
            print(f"Error fetching from {source['name']}: {str(e)}")
            return []
    
    async def _fetch_rss(self, url: str) -> List[Dict[str, Any]]:
        """Fetch and parse RSS feed"""
        try:
            async with self.session.get(url) as response:
                text = await response.text()
                soup = BeautifulSoup(text, "xml")
                items = soup.find_all("item")
                
                articles = []
                for item in items:
                    article = {
                        "title": item.title.text if item.title else "",
                        "link": item.link.text if item.link else "",
                        "description": item.description.text if item.description else "",
                        "published": item.pubDate.text if item.pubDate else datetime.now().isoformat(),
                        "source": url
                    }
                    articles.append(article)
                
                return articles
                
        except Exception as e:
            print(f"Error parsing RSS feed {url}: {str(e)}")
            return []
    
    async def _fetch_html(self, url: str) -> List[Dict[str, Any]]:
        """Fetch and parse HTML page"""
        try:
            async with self.session.get(url) as response:
                text = await response.text()
                soup = BeautifulSoup(text, "html.parser")
                
                articles = []
                # Example selectors - adjust based on actual site structure
                for article in soup.select("article"):
                    title = article.select_one("h2")
                    link = article.select_one("a")
                    desc = article.select_one("p")
                    date = article.select_one("time")
                    
                    if title and link:
                        articles.append({
                            "title": title.text.strip(),
                            "link": link["href"] if "href" in link.attrs else "",
                            "description": desc.text.strip() if desc else "",
                            "published": date["datetime"] if date and "datetime" in date.attrs else datetime.now().isoformat(),
                            "source": url
                        })
                
                return articles
                
        except Exception as e:
            print(f"Error parsing HTML page {url}: {str(e)}")
            return []
    
    async def get_filings(self, symbols: List[str]) -> Dict[str, Any]:
        """Fetch recent SEC filings for given symbols"""
        await self._ensure_session()
        
        filings_data = {
            "filings": [],
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            for symbol in symbols:
                # Use SEC EDGAR API
                url = f"https://data.sec.gov/submissions/CIK{symbol}.json"
                headers = {
                    "User-Agent": "CompanyName admin@company.com"  # Required by SEC
                }
                
                async with self.session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        recent_filings = data.get("filings", {}).get("recent", {})
                        
                        if recent_filings:
                            for i in range(len(recent_filings.get("accessionNumber", []))):
                                filing = {
                                    "symbol": symbol,
                                    "type": recent_filings["form"][i],
                                    "date": recent_filings["filingDate"][i],
                                    "accession_number": recent_filings["accessionNumber"][i],
                                    "description": recent_filings.get("primaryDocument", [""])[i]
                                }
                                filings_data["filings"].append(filing)
            
            return filings_data
            
        except Exception as e:
            print(f"Error fetching filings: {str(e)}")
            return filings_data
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if the scraping service is working"""
        try:
            news = await self.get_latest_news()
            return {
                "healthy": len(news) > 0,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def close(self):
        """Close the aiohttp session"""
        if self.session:
            await self.session.close()
            self.session = None 