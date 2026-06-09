import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
import pandas as pd
from numpy import corrcoef
from src.database import StockPrice, AggregatedSentiment, PriceSentimentAlignment, get_db_session

logger = logging.getLogger(__name__)


class PriceAligner:
    """Align sentiment scores with stock prices"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    def align_sentiment_with_price(
        self,
        ticker: str,
        days: int = 7
    ) -> List[Dict]:
        """
        Align sentiment windows with stock prices
        
        Args:
            ticker: Stock ticker
            days: Number of days to align
            
        Returns:
            List of aligned sentiment-price records
        """
        try:
            start_time = datetime.utcnow() - timedelta(days=days)
            
            # Get aggregated sentiment
            sentiments = self.db_session.query(AggregatedSentiment).filter(
                and_(
                    AggregatedSentiment.ticker == ticker,
                    AggregatedSentiment.window_start >= start_time
                )
            ).order_by(AggregatedSentiment.window_start).all()
            
            # Get stock prices
            prices = self.db_session.query(StockPrice).filter(
                and_(
                    StockPrice.ticker == ticker,
                    StockPrice.timestamp >= start_time
                )
            ).order_by(StockPrice.timestamp).all()
            
            if not sentiments or not prices:
                logger.warning(f"No data found for alignment: {ticker}")
                return []
            
            aligned_records = []
            
            for sentiment in sentiments:
                # Find closest price point(s)
                window_mid = sentiment.window_start + (sentiment.window_end - sentiment.window_start) / 2
                
                # Get price closest to window
                closest_price = self._find_closest_price(prices, window_mid)
                
                if closest_price:
                    # Calculate price change
                    price_change = 0.0
                    if len(prices) > 1:
                        prev_prices = [p for p in prices if p.timestamp < window_mid]
                        if prev_prices:
                            prev_price = prev_prices[-1].close
                            price_change = ((closest_price.close - prev_price) / prev_price * 100) if prev_price > 0 else 0
                    
                    alignment = PriceSentimentAlignment(
                        ticker=ticker,
                        timestamp=window_mid,
                        avg_sentiment=sentiment.avg_sentiment,
                        price_close=closest_price.close,
                        price_change_percent=price_change,
                        news_count=sentiment.news_count
                    )
                    
                    self.db_session.add(alignment)
                    
                    aligned_records.append({
                        "ticker": ticker,
                        "timestamp": window_mid,
                        "avg_sentiment": sentiment.avg_sentiment,
                        "price_close": closest_price.close,
                        "price_change_percent": price_change,
                        "news_count": sentiment.news_count
                    })
            
            self.db_session.commit()
            logger.info(f"Aligned {len(aligned_records)} sentiment-price pairs for {ticker}")
            
            return aligned_records
        
        except Exception as e:
            logger.error(f"Error aligning sentiment with price: {str(e)}")
            self.db_session.rollback()
            return []
    
    def _find_closest_price(self, prices: List, target_time: datetime) -> Optional[StockPrice]:
        """Find price record closest to target time"""
        if not prices:
            return None
        
        closest = prices[0]
        min_diff = abs((prices[0].timestamp - target_time).total_seconds())
        
        for price in prices[1:]:
            diff = abs((price.timestamp - target_time).total_seconds())
            if diff < min_diff:
                min_diff = diff
                closest = price
        
        return closest
    
    def calculate_correlation(
        self,
        ticker: str,
        days: int = 7
    ) -> Optional[Dict]:
        """
        Calculate correlation between sentiment and price changes
        
        Args:
            ticker: Stock ticker
            days: Number of days to analyze
            
        Returns:
            Correlation analysis dictionary
        """
        try:
            start_time = datetime.utcnow() - timedelta(days=days)
            
            alignments = self.db_session.query(PriceSentimentAlignment).filter(
                and_(
                    PriceSentimentAlignment.ticker == ticker,
                    PriceSentimentAlignment.timestamp >= start_time
                )
            ).order_by(PriceSentimentAlignment.timestamp).all()
            
            if len(alignments) < 2:
                logger.warning(f"Not enough data to calculate correlation for {ticker}")
                return None
            
            sentiments = [a.avg_sentiment for a in alignments]
            prices = [a.price_change_percent for a in alignments]
            
            # Calculate correlation
            correlation_matrix = corrcoef(sentiments, prices)
            correlation = correlation_matrix[0, 1]
            
            # Create DataFrame for analysis
            df = pd.DataFrame({
                'sentiment': sentiments,
                'price_change': prices
            })
            
            return {
                "ticker": ticker,
                "correlation": float(correlation) if not pd.isna(correlation) else 0.0,
                "data_points": len(alignments),
                "avg_sentiment": float(df['sentiment'].mean()),
                "avg_price_change": float(df['price_change'].mean()),
                "sentiment_std": float(df['sentiment'].std()),
                "price_change_std": float(df['price_change'].std())
            }
        
        except Exception as e:
            logger.error(f"Error calculating correlation: {str(e)}")
            return None
    
    def get_alignment_history(
        self,
        ticker: str,
        days: int = 7
    ) -> List[Dict]:
        """Get historical alignment data"""
        try:
            start_time = datetime.utcnow() - timedelta(days=days)
            
            alignments = self.db_session.query(PriceSentimentAlignment).filter(
                and_(
                    PriceSentimentAlignment.ticker == ticker,
                    PriceSentimentAlignment.timestamp >= start_time
                )
            ).order_by(PriceSentimentAlignment.timestamp).all()
            
            return [
                {
                    "ticker": a.ticker,
                    "timestamp": a.timestamp,
                    "avg_sentiment": a.avg_sentiment,
                    "price_close": a.price_close,
                    "price_change_percent": a.price_change_percent,
                    "news_count": a.news_count
                }
                for a in alignments
            ]
        except Exception as e:
            logger.error(f"Error getting alignment history: {str(e)}")
            return []


def align_prices_with_sentiment(ticker: str, days: int = 7) -> List[Dict]:
    """
    Align stock prices with sentiment
    
    Args:
        ticker: Stock ticker
        days: Number of days to align
        
    Returns:
        List of aligned records
    """
    db_session = get_db_session()
    try:
        aligner = PriceAligner(db_session)
        return aligner.align_sentiment_with_price(ticker, days)
    finally:
        db_session.close()


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    db_session = get_db_session()
    aligner = PriceAligner(db_session)
    
    # Test alignment
    aligned = aligner.align_sentiment_with_price("AAPL", days=7)
    print(f"Aligned {len(aligned)} records")
    
    # Calculate correlation
    correlation = aligner.calculate_correlation("AAPL", days=7)
    if correlation:
        print(f"Correlation: {correlation['correlation']:.4f}")
