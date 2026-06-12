from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from src.database import NewsHeadline, StockPrice, AggregatedSentiment, PriceSentimentAlignment, get_db_session
from src.ticker_mapping.ticker_mapper import UNIVERSE, get_ticker_name, get_ticker_sector, ALL_TICKERS
from typing import List, Optional

router = APIRouter(prefix="/api/v1", tags=["data"])


@router.get("/tickers")
def get_tickers():
    """Return the fixed 10-stock universe grouped by sector."""
    sectors = {}
    for ticker, meta in UNIVERSE.items():
        sector = meta["sector"]
        sectors.setdefault(sector, []).append({
            "ticker": ticker,
            "name":   meta["name"],
            "sector": sector,
            "exchange": meta.get("exchange", ""),
        })
    return {"universe": sectors, "total": len(UNIVERSE)}


@router.get("/news")
def get_news(
    ticker: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    days: int = Query(7, ge=1, le=30)
):
    """Get financial news headlines with source weight and URL."""
    db_session = get_db_session()
    try:
        query = db_session.query(NewsHeadline)
        if ticker:
            query = query.filter(NewsHeadline.ticker == ticker.upper())
        start_time = datetime.utcnow() - timedelta(days=days)
        query = query.filter(NewsHeadline.timestamp >= start_time)
        total = query.count()
        articles = query.order_by(NewsHeadline.timestamp.desc()).offset(offset).limit(limit).all()
        return {
            "total": total,
            "count": len(articles),
            "data": [
                {
                    "id":              a.id,
                    "headline":        a.headline,
                    "description":     a.description,
                    "source":          a.source,
                    "source_weight":   getattr(a, "source_weight", 1.0),
                    "ticker":          a.ticker,
                    "ticker_name":     get_ticker_name(a.ticker) if a.ticker else None,
                    "sector":          get_ticker_sector(a.ticker) if a.ticker else None,
                    "sentiment_label": a.sentiment_label,
                    "sentiment_score": a.sentiment_score,
                    "timestamp":       a.timestamp,
                    "url":             a.url,
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
    """Get aggregated data for a ticker (includes sector and company name)."""
    db_session = get_db_session()
    try:
        symbol = symbol.upper()
        start_time = datetime.utcnow() - timedelta(days=days)

        latest_news = db_session.query(NewsHeadline).filter(
            and_(NewsHeadline.ticker == symbol, NewsHeadline.timestamp >= start_time)
        ).order_by(NewsHeadline.timestamp.desc()).limit(10).all()

        latest_price = db_session.query(StockPrice).filter(
            and_(StockPrice.ticker == symbol, StockPrice.timestamp >= start_time)
        ).order_by(StockPrice.timestamp.desc()).first()

        aggregates = db_session.query(AggregatedSentiment).filter(
            and_(AggregatedSentiment.ticker == symbol, AggregatedSentiment.window_start >= start_time)
        ).order_by(AggregatedSentiment.window_start.desc()).limit(10).all()

        if not latest_news and not latest_price:
            raise HTTPException(status_code=404, detail=f"No data found for ticker {symbol}")

        return {
            "ticker":       symbol,
            "name":         get_ticker_name(symbol),
            "sector":       get_ticker_sector(symbol),
            "latest_news":  [
                {
                    "headline":      n.headline,
                    "source":        n.source,
                    "source_weight": getattr(n, "source_weight", 1.0),
                    "sentiment":     n.sentiment_label,
                    "score":         n.sentiment_score,
                    "url":           n.url,
                    "timestamp":     n.timestamp,
                }
                for n in latest_news
            ],
            "latest_price": {
                "close":     latest_price.close,
                "timestamp": latest_price.timestamp
            } if latest_price else None,
            "sentiment_aggregates": [
                {
                    "window_start":          a.window_start,
                    "avg_sentiment":         a.avg_sentiment,
                    "weighted_sentiment":    getattr(a, "weighted_sentiment", a.avg_sentiment),
                    "news_count":            a.news_count,
                    "positive":              a.positive_count,
                    "negative":              a.negative_count,
                    "neutral":               a.neutral_count,
                    "contributing_articles": getattr(a, "contributing_articles", []) or [],
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
    """Get sentiment analysis for a ticker, including weighted_sentiment and contributing_articles."""
    db_session = get_db_session()
    try:
        symbol = symbol.upper()
        start_time = datetime.utcnow() - timedelta(days=days)

        aggregates = db_session.query(AggregatedSentiment).filter(
            and_(AggregatedSentiment.ticker == symbol, AggregatedSentiment.window_start >= start_time)
        ).order_by(AggregatedSentiment.window_start).all()

        if not aggregates:
            raise HTTPException(status_code=404, detail=f"No sentiment data for {symbol}")

        return {
            "ticker": symbol,
            "name":   get_ticker_name(symbol),
            "sector": get_ticker_sector(symbol),
            "window": window,
            "data": [
                {
                    "timestamp":             a.window_start,
                    "avg_sentiment":         a.avg_sentiment,
                    "weighted_sentiment":    getattr(a, "weighted_sentiment", a.avg_sentiment),
                    "positive_count":        a.positive_count,
                    "negative_count":        a.negative_count,
                    "neutral_count":         a.neutral_count,
                    "news_count":            a.news_count,
                    "contributing_articles": getattr(a, "contributing_articles", []) or [],
                    "confidence_level":      getattr(a, "confidence_level", None),
                    "trend_score":           getattr(a, "trend_score", None),
                    "price_momentum":        getattr(a, "price_momentum", None),
                    "recommendation_score":  getattr(a, "recommendation_score", None),
                    "recommendation_label":  getattr(a, "recommendation_label", None),
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
    """Get sentiment-price correlation for a ticker."""
    db_session = get_db_session()
    try:
        symbol = symbol.upper()
        start_time = datetime.utcnow() - timedelta(days=days)

        alignments = db_session.query(PriceSentimentAlignment).filter(
            and_(PriceSentimentAlignment.ticker == symbol, PriceSentimentAlignment.timestamp >= start_time)
        ).order_by(PriceSentimentAlignment.timestamp).all()

        if len(alignments) < 2:
            raise HTTPException(status_code=400, detail="Not enough data for correlation")

        sentiments = [a.avg_sentiment for a in alignments]
        prices = [a.price_change_percent for a in alignments]

        from numpy import corrcoef
        correlation = float(corrcoef(sentiments, prices)[0, 1])

        return {
            "ticker":         symbol,
            "name":           get_ticker_name(symbol),
            "sector":         get_ticker_sector(symbol),
            "correlation":    correlation,
            "data_points":    len(alignments),
            "interpretation": (
                "Strong positive correlation"   if correlation > 0.5  else
                "Moderate positive correlation" if correlation > 0.3  else
                "Weak correlation"              if correlation > -0.3 else
                "Moderate negative correlation" if correlation > -0.5 else
                "Strong negative correlation"
            )
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@router.get("/signals")
def get_trading_signals(days: int = Query(7, ge=1, le=30)):
    """
    Sentiment-based trading signals for the fixed universe.
    Educational purposes only — not investment advice.
    """
    db_session = get_db_session()
    try:
        start_time = datetime.utcnow() - timedelta(days=days)

        recent_data = db_session.query(AggregatedSentiment).filter(
            AggregatedSentiment.window_start >= start_time
        ).order_by(AggregatedSentiment.avg_sentiment.desc()).limit(100).all()

        signals = []
        seen_tickers = set()

        for data in recent_data:
            if data.ticker in seen_tickers:
                continue
            seen_tickers.add(data.ticker)

            # Use recommendation_label if available, fall back to sentiment-based
            rec_label = getattr(data, "recommendation_label", None)
            rec_score = getattr(data, "recommendation_score", None)
            confidence = getattr(data, "confidence_level", None)
            t_score = getattr(data, "trend_score", None)
            p_momentum = getattr(data, "price_momentum", None)

            # Use weighted_sentiment if available, fall back to avg_sentiment
            score = getattr(data, "weighted_sentiment", None) or data.avg_sentiment or 0.0

            # Signal from recommendation if available, else from raw sentiment
            if rec_label:
                signal_type = rec_label
            elif score > 0.30:
                signal_type = "BUY"
            elif score < -0.15:
                signal_type = "SELL"
            else:
                signal_type = "HOLD"

            signals.append({
                "ticker":               data.ticker,
                "name":                 get_ticker_name(data.ticker),
                "sector":               get_ticker_sector(data.ticker),
                "signal":               signal_type,
                "strength":             round(abs(rec_score if rec_score is not None else score), 4),
                "confidence":           round(abs(rec_score if rec_score is not None else score) * 100, 2),
                "sentiment":            round(score, 4),
                "news_count":           data.news_count,
                "confidence_level":     confidence,
                "trend_score":          t_score,
                "price_momentum":       p_momentum,
                "recommendation_score": round(rec_score, 4) if rec_score is not None else None,
                "recommendation_label": rec_label,
                "timestamp":            data.window_start,
                "disclaimer":           "Educational only. Not financial advice.",
            })

        return {
            "signals":    signals,
            "count":      len(signals),
            "disclaimer": "Signals are generated for educational analysis only. Not financial advice.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@router.get("/dashboard-summary")
def get_dashboard_summary():
    """Dashboard overview — uses 7-day window to ensure data shows after pipeline runs."""
    db_session = get_db_session()
    try:
        start_time = datetime.utcnow() - timedelta(days=7)

        total_news = db_session.query(func.count(NewsHeadline.id)).filter(
            NewsHeadline.timestamp >= start_time
        ).scalar()

        total_tickers = db_session.query(func.count(func.distinct(NewsHeadline.ticker))).filter(
            and_(NewsHeadline.timestamp >= start_time, NewsHeadline.ticker.isnot(None))
        ).scalar()

        avg_sent = db_session.query(func.avg(NewsHeadline.sentiment_score)).filter(
            NewsHeadline.timestamp >= start_time
        ).scalar() or 0.0

        top_tickers_raw = db_session.query(
            NewsHeadline.ticker,
            func.count(NewsHeadline.id).label("count"),
            func.avg(NewsHeadline.sentiment_score).label("avg_sentiment")
        ).filter(
            and_(NewsHeadline.timestamp >= start_time, NewsHeadline.ticker.isnot(None))
        ).group_by(NewsHeadline.ticker).order_by(func.count(NewsHeadline.id).desc()).limit(20).all()

        return {
            "summary": {
                "total_news_24h":      total_news,
                "total_tickers_24h":   total_tickers,
                "avg_sentiment_24h":   float(avg_sent),
            },
            "top_tickers": [
                {
                    "ticker":        t[0],
                    "name":          get_ticker_name(t[0]),
                    "sector":        get_ticker_sector(t[0]),
                    "news_count":    t[1],
                    "avg_sentiment": float(t[2]) if t[2] else 0.0,
                }
                for t in top_tickers_raw
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()
