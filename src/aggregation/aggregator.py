import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.database import NewsHeadline, AggregatedSentiment, get_db_session

logger = logging.getLogger(__name__)


class SentimentAggregator:
    """Aggregate sentiment scores over time windows"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    def aggregate_by_window(
        self,
        ticker: str,
        window_minutes: int = 60
    ) -> Optional[Dict]:
        """
        Aggregate sentiment for a ticker over a time window
        
        Args:
            ticker: Stock ticker
            window_minutes: Window duration in minutes (how far back to look for news)
            
        Returns:
            Aggregated sentiment dictionary or None
        """
        try:
            # Get news from the specified look-back window
            look_back_start = datetime.utcnow() - timedelta(minutes=window_minutes)
            
            headlines = self.db_session.query(NewsHeadline).filter(
                NewsHeadline.ticker == ticker,
                NewsHeadline.timestamp >= look_back_start,
                NewsHeadline.sentiment_label.isnot(None)
            ).all()
            
            if not headlines:
                return None
            
            # Calculate statistics
            sentiment_scores = [h.sentiment_score for h in headlines if h.sentiment_score is not None]
            labels = [h.sentiment_label for h in headlines]
            
            positive = labels.count("positive")
            negative = labels.count("negative")
            neutral = labels.count("neutral")
            
            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0
            
            # Use earliest article time as window_start, now as window_end
            window_start = min(h.timestamp for h in headlines)
            window_end = datetime.utcnow()
            
            aggregated = AggregatedSentiment(
                ticker=ticker,
                window_start=window_start,
                window_end=window_end,
                avg_sentiment=avg_sentiment,
                positive_count=positive,
                negative_count=negative,
                neutral_count=neutral,
                news_count=len(headlines)
            )
            
            self.db_session.add(aggregated)
            self.db_session.commit()
            
            return {
                "ticker": ticker,
                "window_start": window_start,
                "window_end": window_end,
                "avg_sentiment": avg_sentiment,
                "positive_count": positive,
                "negative_count": negative,
                "neutral_count": neutral,
                "news_count": len(headlines)
            }
        
        except Exception as e:
            logger.error(f"Error aggregating sentiment: {str(e)}")
            self.db_session.rollback()
            return None
    
    def get_historical_aggregates(
        self,
        ticker: str,
        days: int = 7,
        window_minutes: int = 60
    ) -> List[Dict]:
        """
        Get historical aggregated sentiment
        
        Args:
            ticker: Stock ticker
            days: Number of days to look back
            window_minutes: Window duration
            
        Returns:
            List of aggregated sentiment records
        """
        try:
            start_time = datetime.utcnow() - timedelta(days=days)
            
            aggregates = self.db_session.query(AggregatedSentiment).filter(
                AggregatedSentiment.ticker == ticker,
                AggregatedSentiment.window_start >= start_time
            ).order_by(AggregatedSentiment.window_start).all()
            
            return [
                {
                    "ticker": agg.ticker,
                    "window_start": agg.window_start,
                    "window_end": agg.window_end,
                    "avg_sentiment": agg.avg_sentiment,
                    "positive_count": agg.positive_count,
                    "negative_count": agg.negative_count,
                    "neutral_count": agg.neutral_count,
                    "news_count": agg.news_count
                }
                for agg in aggregates
            ]
        except Exception as e:
            logger.error(f"Error fetching historical aggregates: {str(e)}")
            return []
    
    def aggregate_all_tickers(self, window_minutes: int = 60):
        """Aggregate sentiment for all tickers"""
        try:
            # Get unique tickers with recent news
            window_start = datetime.utcnow() - timedelta(minutes=window_minutes)
            
            tickers = self.db_session.query(func.distinct(NewsHeadline.ticker)).filter(
                NewsHeadline.ticker.isnot(None),
                NewsHeadline.timestamp >= window_start
            ).all()
            
            results = []
            for (ticker,) in tickers:
                result = self.aggregate_by_window(ticker, window_minutes)
                if result:
                    results.append(result)
            
            logger.info(f"Aggregated sentiment for {len(results)} tickers")
            return results
        
        except Exception as e:
            logger.error(f"Error aggregating all tickers: {str(e)}")
            return []


def aggregate_sentiment(ticker: str, window_minutes: int = 60) -> Optional[Dict]:
    """
    Aggregate sentiment for a ticker
    
    Args:
        ticker: Stock ticker
        window_minutes: Window duration in minutes
        
    Returns:
        Aggregated sentiment data
    """
    db_session = get_db_session()
    try:
        aggregator = SentimentAggregator(db_session)
        return aggregator.aggregate_by_window(ticker, window_minutes)
    finally:
        db_session.close()


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    db_session = get_db_session()
    aggregator = SentimentAggregator(db_session)
    
    # Test aggregation
    result = aggregator.aggregate_all_tickers(window_minutes=60)
    print(f"Aggregated {len(result)} tickers")
    for agg in result[:5]:
        print(f"{agg['ticker']}: {agg['avg_sentiment']:.4f} ({agg['news_count']} news)")
