from datetime import datetime, timedelta
from sqlalchemy import func, desc, and_
from sqlalchemy.orm import Session
from src.database.models import NewsHeadline, AggregatedSentiment, StockPrice
from src.ticker_mapping.ticker_mapper import ALL_TICKERS, get_ticker_name

def get_recent_headlines(db: Session, ticker: str = None, limit: int = 5, days_lookback: int = 7):
    """Retrieve recent headlines for a specific stock or overall."""
    start_time = datetime.utcnow() - timedelta(days=days_lookback)
    query = db.query(NewsHeadline).filter(NewsHeadline.timestamp >= start_time)
    
    if ticker:
        t_upper = ticker.upper()
        query = query.filter(NewsHeadline.ticker.in_([t_upper, f"{t_upper}.NS"]))
        
    headlines = query.order_by(desc(NewsHeadline.timestamp)).limit(limit).all()
    
    return [
        {
            "headline": h.headline,
            "source": h.source,
            "sentiment": h.sentiment_label,
            "score": h.sentiment_score,
            "timestamp": h.timestamp.isoformat() if h.timestamp else None
        }
        for h in headlines
    ]

def _get_ticker_sentiment_stats(db: Session, days_lookback: int = 7):
    """Helper to get aggregate stats per ticker over the lookback period."""
    start_time = datetime.utcnow() - timedelta(days=days_lookback)
    stats = db.query(
        NewsHeadline.ticker,
        func.count(NewsHeadline.id).label("count"),
        func.avg(NewsHeadline.sentiment_score).label("avg_score")
    ).filter(
        and_(NewsHeadline.timestamp >= start_time, NewsHeadline.ticker.isnot(None))
    ).group_by(NewsHeadline.ticker).all()
    
    # Filter only configured tickers
    return [s for s in stats if s.ticker in ALL_TICKERS]

def get_highest_sentiment_stock(db: Session, days_lookback: int = 7):
    """Get the stock with the highest average sentiment score."""
    stats = _get_ticker_sentiment_stats(db, days_lookback)
    if not stats: return None
    highest = max(stats, key=lambda x: x.avg_score if x.avg_score is not None else -999)
    return {"ticker": highest.ticker, "name": get_ticker_name(highest.ticker), "average_sentiment_score": round(highest.avg_score, 3), "article_count": highest.count}

def get_lowest_sentiment_stock(db: Session, days_lookback: int = 7):
    """Get the stock with the lowest average sentiment score."""
    stats = _get_ticker_sentiment_stats(db, days_lookback)
    if not stats: return None
    lowest = min(stats, key=lambda x: x.avg_score if x.avg_score is not None else 999)
    return {"ticker": lowest.ticker, "name": get_ticker_name(lowest.ticker), "average_sentiment_score": round(lowest.avg_score, 3), "article_count": lowest.count}

def get_top_positive_stocks(db: Session, limit: int = 3, days_lookback: int = 7):
    """Get the top N stocks with the highest average sentiment score."""
    stats = _get_ticker_sentiment_stats(db, days_lookback)
    stats_sorted = sorted(stats, key=lambda x: x.avg_score if x.avg_score is not None else -999, reverse=True)
    return [{"ticker": s.ticker, "name": get_ticker_name(s.ticker), "average_sentiment_score": round(s.avg_score, 3), "article_count": s.count} for s in stats_sorted[:limit]]

def get_top_negative_stocks(db: Session, limit: int = 3, days_lookback: int = 7):
    """Get the top N stocks with the lowest average sentiment score."""
    stats = _get_ticker_sentiment_stats(db, days_lookback)
    stats_sorted = sorted(stats, key=lambda x: x.avg_score if x.avg_score is not None else 999)
    return [{"ticker": s.ticker, "name": get_ticker_name(s.ticker), "average_sentiment_score": round(s.avg_score, 3), "article_count": s.count} for s in stats_sorted[:limit]]

def get_stock_sentiment(db: Session, ticker: str, days_lookback: int = 7):
    """Get sentiment summary for a specific stock."""
    ticker = ticker.upper()
    start_time = datetime.utcnow() - timedelta(days=days_lookback)
    
    real_stats = db.query(NewsHeadline.sentiment_label, func.count(NewsHeadline.id)).filter(
        NewsHeadline.ticker.in_([ticker, f"{ticker}.NS"]), NewsHeadline.timestamp >= start_time
    ).group_by(NewsHeadline.sentiment_label).all()
    
    pos_cnt = sum(cnt for lbl, cnt in real_stats if lbl == 'positive')
    neg_cnt = sum(cnt for lbl, cnt in real_stats if lbl == 'negative')
    neu_cnt = sum(cnt for lbl, cnt in real_stats if lbl == 'neutral')
    total_cnt = pos_cnt + neg_cnt + neu_cnt
    
    avg_score = db.query(func.avg(NewsHeadline.sentiment_score)).filter(
        NewsHeadline.ticker.in_([ticker, f"{ticker}.NS"]), NewsHeadline.timestamp >= start_time
    ).scalar()
    
    return {
        "ticker": ticker,
        "name": get_ticker_name(ticker),
        "total_articles": total_cnt,
        "positive": pos_cnt,
        "negative": neg_cnt,
        "neutral": neu_cnt,
        "average_sentiment_score": round(avg_score, 3) if avg_score is not None else 0.0
    }

def get_article_count(db: Session, ticker: str = None, days_lookback: int = 7):
    """Get total article count analyzed for a stock or overall."""
    start_time = datetime.utcnow() - timedelta(days=days_lookback)
    query = db.query(func.count(NewsHeadline.id)).filter(NewsHeadline.timestamp >= start_time)
    if ticker:
        t_upper = ticker.upper()
        query = query.filter(NewsHeadline.ticker.in_([t_upper, f"{t_upper}.NS"]))
    count = query.scalar()
    return {"ticker": ticker or "ALL", "total_articles": count}

def get_anomalies(db: Session, limit: int = 5):
    """Find recent highly positive or highly negative news anomalies (score > 0.8 or < -0.8)."""
    start_time = datetime.utcnow() - timedelta(days=2) # anomalies are usually recent
    anomalies = db.query(NewsHeadline).filter(
        NewsHeadline.timestamp >= start_time,
        (NewsHeadline.sentiment_score >= 0.8) | (NewsHeadline.sentiment_score <= -0.8)
    ).order_by(desc(func.abs(NewsHeadline.sentiment_score))).limit(limit).all()
    
    return [
        {
            "ticker": h.ticker,
            "headline": h.headline,
            "sentiment": h.sentiment_label,
            "score": h.sentiment_score,
            "timestamp": h.timestamp.isoformat() if h.timestamp else None
        }
        for h in anomalies
    ]
