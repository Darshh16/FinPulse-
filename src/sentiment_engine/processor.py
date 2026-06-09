import logging
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from src.database.models import NewsHeadline
from src.sentiment_engine.finbert_analyzer import analyze_headline

logger = logging.getLogger(__name__)


def process_news_sentiment(
    db_session: Session,
    headline_id: int,
    headline_text: str
) -> Optional[Dict]:
    """
    Process sentiment for a single headline and store in database
    
    Args:
        db_session: Database session
        headline_id: ID of the headline
        headline_text: Text of the headline
        
    Returns:
        Sentiment analysis result or None
    """
    try:
        # Analyze sentiment
        sentiment_result = analyze_headline(headline_text)
        
        # Update database record
        headline = db_session.query(NewsHeadline).filter(
            NewsHeadline.id == headline_id
        ).first()
        
        if headline:
            headline.sentiment_label = sentiment_result["label"]
            headline.sentiment_score = sentiment_result["normalized_score"]
            db_session.commit()
            
            logger.info(f"Updated sentiment for headline {headline_id}: {sentiment_result['label']}")
            return sentiment_result
        else:
            logger.warning(f"Headline {headline_id} not found")
            return None
    except Exception as e:
        logger.error(f"Error processing sentiment for headline {headline_id}: {str(e)}")
        db_session.rollback()
        return None


def batch_process_news_sentiment(
    db_session: Session,
    headlines: List[Dict]
) -> List[Dict]:
    """
    Process sentiment for multiple headlines
    
    Args:
        db_session: Database session
        headlines: List of headline dictionaries with id and text
        
    Returns:
        List of processed sentiment results
    """
    results = []
    
    for headline in headlines:
        result = process_news_sentiment(
            db_session,
            headline["id"],
            headline["text"]
        )
        if result:
            results.append(result)
    
    return results


def get_sentiment_summary(
    db_session: Session,
    ticker: Optional[str] = None
) -> Dict:
    """
    Get sentiment summary for headlines
    
    Args:
        db_session: Database session
        ticker: Optional ticker filter
        
    Returns:
        Sentiment summary dictionary
    """
    try:
        query = db_session.query(NewsHeadline)
        
        if ticker:
            query = query.filter(NewsHeadline.ticker == ticker)
        
        headlines = query.all()
        
        if not headlines:
            return {
                "total": 0,
                "positive": 0,
                "negative": 0,
                "neutral": 0,
                "avg_score": 0.0
            }
        
        positive = sum(1 for h in headlines if h.sentiment_label == "positive")
        negative = sum(1 for h in headlines if h.sentiment_label == "negative")
        neutral = sum(1 for h in headlines if h.sentiment_label == "neutral")
        avg_score = sum(h.sentiment_score or 0 for h in headlines) / len(headlines)
        
        return {
            "total": len(headlines),
            "positive": positive,
            "negative": negative,
            "neutral": neutral,
            "avg_score": avg_score,
            "positive_pct": (positive / len(headlines) * 100) if headlines else 0,
            "negative_pct": (negative / len(headlines) * 100) if headlines else 0,
            "neutral_pct": (neutral / len(headlines) * 100) if headlines else 0
        }
    except Exception as e:
        logger.error(f"Error getting sentiment summary: {str(e)}")
        return {}
