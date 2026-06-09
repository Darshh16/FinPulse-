from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from src.database import NewsHeadline, StockPrice, AggregatedSentiment, PriceSentimentAlignment, get_db_session
from typing import List, Optional

router = APIRouter(prefix="/api/v1", tags=["data"])


@router.get("/news")
def get_news(
    ticker: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    days: int = Query(7, ge=1, le=30)
):
    """Get financial news headlines"""
    db_session = get_db_session()
    try:
        query = db_session.query(NewsHeadline)
        
        if ticker:
            query = query.filter(NewsHeadline.ticker == ticker)
        
        start_time = datetime.utcnow() - timedelta(days=days)
        query = query.filter(NewsHeadline.timestamp >= start_time)
        
        total = query.count()
        articles = query.order_by(NewsHeadline.timestamp.desc()).offset(offset).limit(limit).all()
        
        return {
            "total": total,
            "count": len(articles),
            "data": [
                {
                    "id": a.id,
                    "headline": a.headline,
                    "description": a.description,
                    "source": a.source,
                    "ticker": a.ticker,
                    "sentiment_label": a.sentiment_label,
                    "sentiment_score": a.sentiment_score,
                    "timestamp": a.timestamp,
                    "url": a.url
                }
                for a in articles
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@router.get("/ticker/{symbol}")
def get_ticker_data(symbol: str, days: int = Query(7, ge=1, le=30)):
    """Get aggregated data for a ticker"""
    db_session = get_db_session()
    try:
        symbol = symbol.upper()
        start_time = datetime.utcnow() - timedelta(days=days)
        
        # Get latest news
        latest_news = db_session.query(NewsHeadline).filter(
            and_(
                NewsHeadline.ticker == symbol,
                NewsHeadline.timestamp >= start_time
            )
        ).order_by(NewsHeadline.timestamp.desc()).limit(10).all()
        
        # Get latest price
        latest_price = db_session.query(StockPrice).filter(
            and_(
                StockPrice.ticker == symbol,
                StockPrice.timestamp >= start_time
            )
        ).order_by(StockPrice.timestamp.desc()).first()
        
        # Get aggregated sentiment
        aggregates = db_session.query(AggregatedSentiment).filter(
            and_(
                AggregatedSentiment.ticker == symbol,
                AggregatedSentiment.window_start >= start_time
            )
        ).order_by(AggregatedSentiment.window_start.desc()).limit(10).all()
        
        if not latest_news and not latest_price:
            raise HTTPException(status_code=404, detail=f"No data found for ticker {symbol}")
        
        return {
            "ticker": symbol,
            "latest_news": [
                {
                    "headline": n.headline,
                    "source": n.source,
                    "sentiment": n.sentiment_label,
                    "timestamp": n.timestamp
                }
                for n in latest_news
            ],
            "latest_price": {
                "close": latest_price.close,
                "timestamp": latest_price.timestamp
            } if latest_price else None,
            "sentiment_aggregates": [
                {
                    "window_start": a.window_start,
                    "avg_sentiment": a.avg_sentiment,
                    "news_count": a.news_count,
                    "positive": a.positive_count,
                    "negative": a.negative_count,
                    "neutral": a.neutral_count
                }
                for a in aggregates
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@router.get("/sentiment/{symbol}")
def get_sentiment(symbol: str, days: int = Query(7, ge=1, le=30), window: str = Query("1h")):
    """Get sentiment analysis for a ticker"""
    db_session = get_db_session()
    try:
        symbol = symbol.upper()
        start_time = datetime.utcnow() - timedelta(days=days)
        
        aggregates = db_session.query(AggregatedSentiment).filter(
            and_(
                AggregatedSentiment.ticker == symbol,
                AggregatedSentiment.window_start >= start_time
            )
        ).order_by(AggregatedSentiment.window_start).all()
        
        if not aggregates:
            raise HTTPException(status_code=404, detail=f"No sentiment data for {symbol}")
        
        return {
            "ticker": symbol,
            "window": window,
            "data": [
                {
                    "timestamp": a.window_start,
                    "avg_sentiment": a.avg_sentiment,
                    "positive_count": a.positive_count,
                    "negative_count": a.negative_count,
                    "neutral_count": a.neutral_count,
                    "news_count": a.news_count
                }
                for a in aggregates
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@router.get("/correlation/{symbol}")
def get_correlation(symbol: str, days: int = Query(7, ge=1, le=30)):
    """Get sentiment-price correlation for a ticker"""
    db_session = get_db_session()
    try:
        symbol = symbol.upper()
        start_time = datetime.utcnow() - timedelta(days=days)
        
        alignments = db_session.query(PriceSentimentAlignment).filter(
            and_(
                PriceSentimentAlignment.ticker == symbol,
                PriceSentimentAlignment.timestamp >= start_time
            )
        ).order_by(PriceSentimentAlignment.timestamp).all()
        
        if len(alignments) < 2:
            raise HTTPException(status_code=400, detail="Not enough data for correlation")
        
        sentiments = [a.avg_sentiment for a in alignments]
        prices = [a.price_change_percent for a in alignments]
        
        from numpy import corrcoef
        correlation_matrix = corrcoef(sentiments, prices)
        correlation = float(correlation_matrix[0, 1])
        
        return {
            "ticker": symbol,
            "correlation": correlation,
            "data_points": len(alignments),
            "interpretation": "Strong positive correlation" if correlation > 0.5 else
                            "Moderate positive correlation" if correlation > 0.3 else
                            "Weak correlation" if correlation > -0.3 else
                            "Moderate negative correlation" if correlation > -0.5 else
                            "Strong negative correlation"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@router.get("/signals")
def get_trading_signals(days: int = Query(7, ge=1, le=30)):
    """
    Get potential trading signals based on sentiment
    
    Educational purposes only - not investment advice
    """
    db_session = get_db_session()
    try:
        # Get recent aggregated sentiments (last N days)
        start_time = datetime.utcnow() - timedelta(days=days)
        
        recent_data = db_session.query(AggregatedSentiment).filter(
            AggregatedSentiment.window_start >= start_time
        ).order_by(AggregatedSentiment.avg_sentiment.desc()).limit(50).all()
        
        signals = []
        seen_tickers = set()  # Avoid duplicate signals for same ticker
        
        for data in recent_data:
            if data.ticker in seen_tickers:
                continue
            seen_tickers.add(data.ticker)
            
            signal_type = "BUY" if data.avg_sentiment > 0.3 else "SELL" if data.avg_sentiment < -0.3 else "HOLD"
            strength = abs(data.avg_sentiment)
            
            signals.append({
                "ticker": data.ticker,
                "signal": signal_type,
                "strength": round(strength, 4),
                "confidence": round(strength * 100, 2),
                "sentiment": round(data.avg_sentiment, 4),
                "news_count": data.news_count,
                "timestamp": data.window_start,
                "disclaimer": "For educational purposes only. Not financial advice."
            })
        
        return {
            "signals": signals,
            "count": len(signals),
            "disclaimer": "These signals are generated for educational analysis only and should not be considered financial advice."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@router.get("/dashboard-summary")
def get_dashboard_summary():
    """Get summary data for dashboard"""
    db_session = get_db_session()
    try:
        # Count recent data
        start_time = datetime.utcnow() - timedelta(days=1)
        
        total_news = db_session.query(func.count(NewsHeadline.id)).filter(
            NewsHeadline.timestamp >= start_time
        ).scalar()
        
        total_tickers = db_session.query(func.count(func.distinct(NewsHeadline.ticker))).filter(
            and_(
                NewsHeadline.timestamp >= start_time,
                NewsHeadline.ticker.isnot(None)
            )
        ).scalar()
        
        # Get top tickers by news volume
        top_tickers = db_session.query(
            NewsHeadline.ticker,
            func.count(NewsHeadline.id).label('count'),
            func.avg(NewsHeadline.sentiment_score).label('avg_sentiment')
        ).filter(
            and_(
                NewsHeadline.timestamp >= start_time,
                NewsHeadline.ticker.isnot(None)
            )
        ).group_by(NewsHeadline.ticker).order_by(func.count(NewsHeadline.id).desc()).limit(10).all()
        
        return {
            "summary": {
                "total_news_24h": total_news,
                "total_tickers_24h": total_tickers,
                "avg_sentiment_24h": db_session.query(func.avg(NewsHeadline.sentiment_score)).filter(
                    NewsHeadline.timestamp >= start_time
                ).scalar() or 0.0
            },
            "top_tickers": [
                {
                    "ticker": t[0],
                    "news_count": t[1],
                    "avg_sentiment": float(t[2]) if t[2] else 0.0
                }
                for t in top_tickers
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()
