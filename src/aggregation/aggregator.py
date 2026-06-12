"""
Sentiment aggregator with source-weighted scoring and contributing article tracking.

Weighted sentiment = sum(score * weight) / sum(weight)
Contributing articles are stored as JSON for hover-to-see-news in the dashboard.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List

from src.database.models import NewsHeadline, AggregatedSentiment
from config.settings import settings

logger = logging.getLogger(__name__)


class SentimentAggregator:
    """Aggregates FinBERT sentiment scores into time-windowed summaries."""

    def __init__(self, db_session):
        self.db_session = db_session

    def aggregate_by_window(
        self,
        ticker: str,
        window_minutes: int = 60,
    ) -> Optional[Dict]:
        """
        Aggregate sentiment for a ticker over a look-back window.

        Uses source-weighted average: sum(score * weight) / sum(weight).
        Stores top contributing articles as JSON for the hover feature.

        Args:
            ticker: Stock ticker symbol
            window_minutes: How far back to look for articles

        Returns:
            Aggregated sentiment dict
        """
        try:
            look_back_start = datetime.utcnow() - timedelta(minutes=window_minutes)

            headlines: List[NewsHeadline] = (
                self.db_session.query(NewsHeadline)
                .filter(
                    NewsHeadline.ticker == ticker,
                    NewsHeadline.timestamp >= look_back_start,
                    NewsHeadline.sentiment_label.isnot(None),
                )
                .all()
            )

            # ── Sentiment statistics ─────────────────────────────────────────
            scores   = [h.sentiment_score  for h in headlines if h.sentiment_score  is not None]
            weights  = [h.source_weight    for h in headlines if h.sentiment_score  is not None]
            labels   = [h.sentiment_label  for h in headlines]

            positive = labels.count("positive")
            negative = labels.count("negative")
            neutral  = labels.count("neutral")

            # Simple average (backward compat)
            avg_sentiment = sum(scores) / len(scores) if scores else 0.0

            # Weighted average
            if scores and weights:
                weighted_sum    = sum(s * w for s, w in zip(scores, weights))
                total_weight    = sum(weights)
                weighted_sentiment = weighted_sum / total_weight if total_weight > 0 else avg_sentiment
            else:
                weighted_sentiment = avg_sentiment

            # ── Window timestamps ────────────────────────────────────────────
            window_start = min((h.timestamp for h in headlines), default=look_back_start)
            window_end   = datetime.utcnow()

            # ── Contributing articles (for hover tooltip) ────────────────────
            # Sort by abs(score) desc → most impactful first; keep top 10
            sorted_heads = sorted(
                headlines,
                key=lambda h: abs(h.sentiment_score or 0),
                reverse=True,
            )
            contributing_articles = [
                {
                    "headline": h.headline[:120] if h.headline else "",
                    "url":      h.url or "",
                    "source":   h.source or "unknown",
                    "score":    round(h.sentiment_score or 0, 4),
                    "weight":   round(h.source_weight or 1.0, 2),
                    "label":    h.sentiment_label or "neutral",
                    "timestamp": h.timestamp.isoformat() if h.timestamp else "",
                }
                for h in sorted_heads[:10]
            ]

            # ── Trend-Based Recommendation Layer ─────────────────────────────
            confidence_level = None
            trend_score = None
            price_momentum = None
            recommendation_score = None
            recommendation_label = None

            try:
                from src.trend_analysis.trend_analyzer import TrendAnalyzer
                from src.trend_analysis.recommender import Recommender

                trend_data = TrendAnalyzer(
                    lookback_months=settings.trend_lookback_months
                ).compute_trend(ticker)

                if trend_data:
                    trend_score = trend_data["trend_score"]
                    price_momentum = trend_data["price_momentum"]

                    rec = Recommender().compute(
                        sentiment_score=weighted_sentiment,
                        news_count=len(headlines),
                        trend_score=trend_score,
                    )
                    confidence_level = rec["confidence_level"]
                    recommendation_score = rec["recommendation_score"]
                    recommendation_label = rec["recommendation_label"]
                else:
                    # No price data — fall back to sentiment-only recommendation
                    from src.trend_analysis.recommender import Recommender as Rec
                    rec = Rec().compute(
                        sentiment_score=weighted_sentiment,
                        news_count=len(headlines),
                        trend_score=0.0,
                    )
                    confidence_level = rec["confidence_level"]
                    recommendation_score = rec["recommendation_score"]
                    recommendation_label = rec["recommendation_label"]
            except Exception as trend_err:
                logger.warning(f"Trend/recommendation computation failed for {ticker}: {trend_err}")

            # ── Persist ──────────────────────────────────────────────────────
            aggregated = AggregatedSentiment(
                ticker               = ticker,
                window_start         = window_start,
                window_end           = window_end,
                avg_sentiment        = avg_sentiment,
                weighted_sentiment   = weighted_sentiment,
                positive_count       = positive,
                negative_count       = negative,
                neutral_count        = neutral,
                news_count           = len(headlines),
                contributing_articles= contributing_articles,
                confidence_level     = confidence_level,
                trend_score          = trend_score,
                price_momentum       = price_momentum,
                recommendation_score = recommendation_score,
                recommendation_label = recommendation_label,
            )

            self.db_session.add(aggregated)
            self.db_session.commit()

            return {
                "ticker":                ticker,
                "window_start":          window_start,
                "window_end":            window_end,
                "avg_sentiment":         avg_sentiment,
                "weighted_sentiment":    weighted_sentiment,
                "positive_count":        positive,
                "negative_count":        negative,
                "neutral_count":         neutral,
                "news_count":            len(headlines),
                "contributing_articles": contributing_articles,
                "confidence_level":      confidence_level,
                "trend_score":           trend_score,
                "price_momentum":        price_momentum,
                "recommendation_score":  recommendation_score,
                "recommendation_label":  recommendation_label,
            }

        except Exception as e:
            logger.error(f"Error aggregating sentiment for {ticker}: {e}")
            self.db_session.rollback()
            return None

    def get_latest_aggregation(self, ticker: str) -> Optional[Dict]:
        """Return the most recent aggregated sentiment row for a ticker."""
        try:
            row = (
                self.db_session.query(AggregatedSentiment)
                .filter(AggregatedSentiment.ticker == ticker)
                .order_by(AggregatedSentiment.window_end.desc())
                .first()
            )
            if not row:
                return None
            return {
                "ticker":                row.ticker,
                "window_start":          row.window_start,
                "window_end":            row.window_end,
                "avg_sentiment":         row.avg_sentiment,
                "weighted_sentiment":    getattr(row, "weighted_sentiment", row.avg_sentiment),
                "positive_count":        row.positive_count,
                "negative_count":        row.negative_count,
                "neutral_count":         row.neutral_count,
                "news_count":            row.news_count,
                "contributing_articles": getattr(row, "contributing_articles", []) or [],
                "confidence_level":      getattr(row, "confidence_level", None),
                "trend_score":           getattr(row, "trend_score", None),
                "price_momentum":        getattr(row, "price_momentum", None),
                "recommendation_score":  getattr(row, "recommendation_score", None),
                "recommendation_label":  getattr(row, "recommendation_label", None),
            }
        except Exception as e:
            logger.error(f"Error fetching latest aggregation for {ticker}: {e}")
            return None
