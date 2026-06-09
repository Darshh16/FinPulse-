import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from src.data_sources.news_api import fetch_financial_news
from src.data_sources.yfinance_client import fetch_stock_prices
from src.sentiment_engine import analyze_headline, process_news_sentiment
from src.ticker_mapping import map_headline_to_tickers
from src.database import NewsHeadline, StockPrice, get_db_session
from src.aggregation.aggregator import SentimentAggregator
from src.price_alignment.aligner import PriceAligner
from config.settings import settings

logger = logging.getLogger(__name__)


class NewsProcessor:
    """Process news headlines through the pipeline"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    async def process_news_batch(self, articles: List[Dict]) -> List[Dict]:
        """
        Process a batch of news articles through the sentiment and ticker pipeline
        
        Args:
            articles: List of news articles
            
        Returns:
            List of processed articles with sentiment and tickers
        """
        processed = []
        
        for article in articles:
            try:
                # Extract headline and description
                headline = article.get("headline", "")
                description = article.get("description", "")
                text_to_analyze = f"{headline} {description}"
                url = article.get("url", "")
                
                # Check if URL already exists in database (avoid duplicates)
                existing = self.db_session.query(NewsHeadline).filter(
                    NewsHeadline.url == url
                ).first()
                
                if existing:
                    logger.debug(f"Article already exists (URL: {url}), skipping")
                    continue
                
                # Analyze sentiment
                sentiment_result = analyze_headline(text_to_analyze)
                
                # Map to tickers
                tickers = map_headline_to_tickers(headline)
                
                # Store in database
                news_record = NewsHeadline(
                    headline=headline,
                    description=description,
                    source=article.get("source", "Unknown"),
                    url=url,
                    timestamp=datetime.fromisoformat(
                        article.get("published_at", "").replace("Z", "+00:00")
                    ) if article.get("published_at") else datetime.utcnow(),
                    ticker=list(tickers)[0] if tickers else None,  # Primary ticker
                    sentiment_label=sentiment_result["label"],
                    sentiment_score=sentiment_result["normalized_score"]
                )
                
                self.db_session.add(news_record)
                
                processed.append({
                    "headline": headline,
                    "source": article.get("source", "Unknown"),
                    "sentiment_label": sentiment_result["label"],
                    "sentiment_score": sentiment_result["normalized_score"],
                    "tickers": list(tickers),
                    "timestamp": news_record.timestamp
                })
                
                logger.info(f"Processed: {headline[:60]}... -> {sentiment_result['label']}")
                
            except Exception as e:
                logger.error(f"Error processing article: {str(e)}")
                continue
        
        # Commit all changes
        try:
            self.db_session.commit()
            logger.info(f"Successfully processed {len(processed)} articles")
        except Exception as e:
            logger.error(f"Error committing to database: {str(e)}")
            self.db_session.rollback()
        
        return processed


class PriceProcessor:
    """Process stock prices through the pipeline"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    async def process_price_batch(self, tickers: List[str], period: str = "1d") -> List[Dict]:
        """
        Process stock prices for multiple tickers
        
        Args:
            tickers: List of stock tickers
            period: Time period to fetch
            
        Returns:
            List of price data
        """
        try:
            prices = await fetch_stock_prices(tickers, period=period)
            
            for price_data in prices:
                # Store in database
                price_record = StockPrice(
                    ticker=price_data["ticker"],
                    timestamp=price_data["timestamp"],
                    open=price_data.get("open", 0),
                    high=price_data.get("high", 0),
                    low=price_data.get("low", 0),
                    close=price_data["close"],
                    volume=price_data.get("volume", 0)
                )
                
                self.db_session.add(price_record)
            
            # Commit all changes
            self.db_session.commit()
            logger.info(f"Processed prices for {len(prices)} tickers")
            return prices
            
        except Exception as e:
            logger.error(f"Error processing prices: {str(e)}")
            self.db_session.rollback()
            return []


class StreamingPipeline:
    """Main streaming pipeline orchestrator"""
    
    def __init__(self):
        self.db_session = get_db_session()
        self.news_processor = NewsProcessor(self.db_session)
        self.price_processor = PriceProcessor(self.db_session)
        self.aggregator = SentimentAggregator(self.db_session)
        self.aligner = PriceAligner(self.db_session)
        self.running = False
    
    async def start(self):
        """Start the streaming pipeline"""
        self.running = True
        logger.info("Starting FinPulse streaming pipeline...")
        
        try:
            while self.running:
                await self.pipeline_cycle()
                await asyncio.sleep(settings.news_fetch_interval)
        except KeyboardInterrupt:
            logger.info("Pipeline interrupted by user")
        except Exception as e:
            logger.error(f"Pipeline error: {str(e)}")
        finally:
            await self.stop()
    
    async def pipeline_cycle(self):
        """Execute one complete pipeline cycle"""
        try:
            logger.info("Starting pipeline cycle...")
            
            # Step 1: Fetch news
            logger.info("Fetching financial news...")
            articles = await fetch_financial_news()
            
            if not articles:
                logger.warning("No news articles fetched")
                return
            
            # Step 2: Process news through sentiment and ticker mapping
            logger.info("Processing news sentiment and tickers...")
            processed_news = await self.news_processor.process_news_batch(articles)
            
            # Step 3: Collect unique tickers
            tickers = set()
            for item in processed_news:
                tickers.update(item["tickers"])
            
            if tickers:
                # Step 4: Fetch stock prices
                logger.info(f"Fetching prices for {len(tickers)} tickers...")
                await self.price_processor.process_price_batch(list(tickers))
                
                # Step 5: Aggregate sentiment by time window (24h to capture all fetched news)
                logger.info(f"Aggregating sentiment for {len(tickers)} tickers...")
                for ticker in tickers:
                    aggregate_result = self.aggregator.aggregate_by_window(ticker, window_minutes=1440)
                    if aggregate_result:
                        logger.info(f"Aggregated sentiment for {ticker}: {aggregate_result['avg_sentiment']:.4f}")
                    else:
                        logger.warning(f"No articles found to aggregate for {ticker}")
                
                # Step 6: Align sentiment with price changes for each ticker
                logger.info(f"Aligning sentiment with prices...")
                for ticker in tickers:
                    self.aligner.align_sentiment_with_price(ticker)
            
            logger.info("Pipeline cycle completed successfully")
            
        except Exception as e:
            logger.error(f"Error in pipeline cycle: {str(e)}")
    
    async def stop(self):
        """Stop the streaming pipeline"""
        self.running = False
        logger.info("Stopping streaming pipeline")
        if self.db_session:
            self.db_session.close()


async def run_pipeline():
    """Run the streaming pipeline"""
    pipeline = StreamingPipeline()
    await pipeline.start()


# Example usage
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_pipeline())
