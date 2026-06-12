import aiohttp
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
from config.settings import settings

logger = logging.getLogger(__name__)


class NewsAPIClient:
    """Client for fetching news from NewsAPI"""
    
    BASE_URL = "https://newsapi.org/v2"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def fetch_news(
        self,
        query: str = "finance stock market",
        country: str = "us",
        sort_by: str = "publishedAt",
        language: str = "en",
        page_size: int = 100
    ) -> List[Dict]:
        """
        Fetch news headlines from NewsAPI
        
        Args:
            query: Search query
            country: Country code (e.g., 'us')
            sort_by: Sort order (publishedAt, relevancy, popularity)
            language: Language code
            page_size: Number of results per page
            
        Returns:
            List of news articles
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use 'async with' context manager.")
        
        endpoint = f"{self.BASE_URL}/everything"
        
        params = {
            "q": query,
            "language": language,
            "sortBy": sort_by,
            "pageSize": page_size,
            "apiKey": self.api_key
        }
        
        try:
            async with self.session.get(endpoint, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    data = await response.json()
                    articles = data.get("articles", [])
                    logger.info(f"Fetched {len(articles)} news articles")
                    return articles
                elif response.status == 401:
                    logger.error("Invalid API key")
                    return []
                elif response.status == 429:
                    logger.error("Rate limit exceeded")
                    return []
                else:
                    logger.error(f"NewsAPI error: {response.status}")
                    return []
        except asyncio.TimeoutError:
            logger.error("Request timeout")
            return []
        except Exception as e:
            logger.error(f"Error fetching news: {str(e)}")
            return []
    
    async def fetch_top_headlines(
        self,
        country: str = "us",
        category: str = "business",
        page_size: int = 100
    ) -> List[Dict]:
        """
        Fetch top headlines
        
        Args:
            country: Country code
            category: News category
            page_size: Number of results
            
        Returns:
            List of top headlines
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use 'async with' context manager.")
        
        endpoint = f"{self.BASE_URL}/top-headlines"
        
        params = {
            "country": country,
            "category": category,
            "pageSize": page_size,
            "apiKey": self.api_key
        }
        
        try:
            async with self.session.get(endpoint, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    data = await response.json()
                    articles = data.get("articles", [])
                    logger.info(f"Fetched {len(articles)} top headlines")
                    return articles
                else:
                    logger.error(f"Error: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Error fetching headlines: {str(e)}")
            return []


def normalize_article(article: Dict) -> Dict:
    """
    Normalize article data from NewsAPI
    
    Args:
        article: Raw article data from NewsAPI
        
    Returns:
        Normalized article dictionary
    """
    return {
        "headline": article.get("title", ""),
        "description": article.get("description", ""),
        "source": article.get("source", {}).get("name", "Unknown"),
        "url": article.get("url", ""),
        "published_at": article.get("publishedAt", ""),
        "image_url": article.get("urlToImage", ""),
        "content": article.get("content", "")
    }


# Target company search terms for NewsAPI
_COMPANY_QUERY = (
    "HDFC Bank OR SBI OR \"State Bank of India\" OR Trent OR DMart OR "
    "\"Avenue Supermarts\" OR Siemens India OR \"ABB India\" OR "
    "\"Maruti Suzuki\" OR Mahindra OR Microsoft OR Nvidia"
)


async def fetch_financial_news(
    query: str = None,
    days_back: int = 1
) -> List[Dict]:
    """
    Fetch financial news articles from NewsAPI.
    Uses a company-specific query targeting our fixed 10-stock universe.
    """
    if query is None:
        query = _COMPANY_QUERY

    async with NewsAPIClient(settings.news_api_key) as client:
        articles = await client.fetch_news(
            query=query,
            sort_by=settings.news_sort_by,
            page_size=100
        )

        normalized = [normalize_article(article) for article in articles]
        logger.info(f"NewsAPI normalized {len(normalized)} articles (company-specific query)")
        return normalized


# Example of how to use this module
if __name__ == "__main__":
    import asyncio
    
    async def test():
        articles = await fetch_financial_news()
        for article in articles[:5]:
            print(f"Title: {article['headline']}")
            print(f"Source: {article['source']}")
            print("---")
    
    asyncio.run(test())
