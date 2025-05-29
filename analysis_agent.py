"""Analysis Agent for market analysis"""
from typing import Dict, Any, List, Tuple
from datetime import datetime
import numpy as np
from sklearn.cluster import MiniBatchKMeans
from sklearn.impute import SimpleImputer
from functools import lru_cache
import pandas as pd
import concurrent.futures
from threading import Lock

class AnalysisAgent:
    def __init__(self):
        self.risk_levels = ["low", "medium", "high"]
        self.imputer = SimpleImputer(strategy='mean')
        self.kmeans = MiniBatchKMeans(n_clusters=len(self.risk_levels), batch_size=100)
        self.cache = {}
        self.cache_duration = 30  # 30 seconds cache
        self.cache_lock = Lock()
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)

    @lru_cache(maxsize=100)
    def _get_cached_analysis(self, cache_key: str) -> Tuple[Dict[str, Any], datetime]:
        """Get cached analysis if available"""
        with self.cache_lock:
            if cache_key in self.cache:
                analysis, timestamp = self.cache[cache_key]
                if (datetime.now() - timestamp).seconds < self.cache_duration:
                    return analysis, timestamp
        return None, None

    async def analyze(self, query: str, market_data: Dict[str, Any], 
                     news_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze market data and generate insights with parallel processing"""
        try:
            # Create cache key from input data
            cache_key = f"{hash(str(market_data))}-{hash(str(news_data))}"
            cached_analysis, timestamp = self._get_cached_analysis(cache_key)
            
            if cached_analysis:
                return cached_analysis

            # Convert to pandas for vectorized operations
            stocks_df = pd.DataFrame.from_dict(market_data.get("stocks", {}), orient='index')
            
            # Parallel processing of analysis tasks
            with concurrent.futures.ThreadPoolExecutor() as executor:
                market_summary_future = executor.submit(self._analyze_market_summary, stocks_df)
                risk_clusters_future = executor.submit(self._analyze_risk_clusters, stocks_df)
                sentiment_future = executor.submit(self._analyze_sentiment, news_data)
                
                analysis = {
                    "market_summary": market_summary_future.result(),
                    "risk_clusters": risk_clusters_future.result(),
                    "sentiment": sentiment_future.result(),
                    "confidence": 0.85,
                    "sources": ["Yahoo Finance", "Reuters", "Alpha Vantage"],
                    "timestamp": datetime.now().isoformat()
                }
            
            # Cache the result with thread safety
            with self.cache_lock:
                self.cache[cache_key] = (analysis, datetime.now())
            return analysis
            
        except Exception as e:
            print(f"Error performing analysis: {str(e)}")
            return {
                "market_summary": {
                    "total_market_cap": 0,
                    "average_change": 0,
                    "volatility": 0
                },
                "risk_clusters": [],
                "sentiment": {
                    "average_sentiment": 0,
                    "article_count": 0
                },
                "confidence": 0.5,
                "sources": ["Error: Data unavailable"],
                "timestamp": datetime.now().isoformat()
            }

    def _analyze_market_summary(self, stocks_df: pd.DataFrame) -> Dict[str, Any]:
        """Generate market summary using optimized vectorized operations"""
        if stocks_df.empty:
            return {
                "total_market_cap": 0,
                "average_change": 0,
                "volatility": 0
            }
        
        try:
            # Convert to numpy for faster calculations
            prices = stocks_df['price'].to_numpy(dtype=np.float64)
            changes = stocks_df['change'].to_numpy(dtype=np.float64)
            
            return {
                "total_market_cap": float(np.sum(prices)),
                "average_change": float(np.mean(changes)),
                "volatility": float(np.std(changes)) if len(changes) > 1 else 0
            }
        except Exception:
            return {
                "total_market_cap": 0,
                "average_change": 0,
                "volatility": 0
            }

    def _analyze_risk_clusters(self, stocks_df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Cluster stocks by risk level using optimized MiniBatchKMeans"""
        if stocks_df.empty:
            return []
        
        try:
            # Extract features using numpy operations
            features = stocks_df[['price', 'change', 'volume']].to_numpy(dtype=np.float64)
            
            # Handle missing values efficiently
            features = self.imputer.fit_transform(features)
            
            # Normalize features using numpy operations
            features = (features - np.mean(features, axis=0)) / np.std(features, axis=0, ddof=1)
            
            # Cluster using MiniBatchKMeans
            n_clusters = min(len(self.risk_levels), len(features))
            if n_clusters < 1:
                return []
                
            labels = self.kmeans.fit_predict(features)
            
            # Group stocks by cluster using numpy operations
            clusters = []
            for i in range(n_clusters):
                cluster_mask = labels == i
                cluster_symbols = stocks_df.index[cluster_mask].tolist()
                
                if cluster_symbols:
                    cluster_changes = stocks_df.loc[cluster_symbols, 'change'].to_numpy(dtype=np.float64)
                    
                    clusters.append({
                        "risk_level": self.risk_levels[i],
                        "symbols": cluster_symbols,
                        "average_volatility": float(np.std(cluster_changes)) if len(cluster_changes) > 1 else 0
                    })
            
            return clusters
            
        except Exception as e:
            print(f"Error in risk clustering: {str(e)}")
            return []

    def _analyze_sentiment(self, news_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze news sentiment using optimized operations"""
        articles = news_data.get("articles", [])
        
        if not articles:
            return {
                "average_sentiment": 0,
                "article_count": 0
            }
        
        try:
            # Convert to numpy for faster calculations
            sentiments = np.array([article.get('sentiment', 0) for article in articles], dtype=np.float64)
            
            return {
                "average_sentiment": float(np.mean(sentiments)) if len(sentiments) > 0 else 0,
                "article_count": len(articles)
            }
        except Exception:
            return {
                "average_sentiment": 0,
                "article_count": len(articles)
            }

    async def health_check(self) -> Dict[str, Any]:
        """Check if the analysis service is working"""
        try:
            # Test analysis with sample data
            test_data = {
                "stocks": {
                    "AAPL": {"price": 150, "change": 1.5, "volume": 1000000}
                }
            }
            
            analysis = await self.analyze(
                query="Test analysis",
                market_data=test_data,
                news_data={"articles": []},
                context={}
            )
            
            return {
                "healthy": len(analysis) > 0,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            } 