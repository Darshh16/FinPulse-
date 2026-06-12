"""
Recommendation Engine — blends sentiment + trend based on article confidence.

Formula:
  If news_count >= 5:
    recommendation_score = 0.70 * sentiment_score + 0.30 * trend_score
  If news_count < 5:
    recommendation_score = 1.00 * trend_score

Labels:
  BUY  → recommendation_score > buy_threshold
  SELL → recommendation_score < sell_threshold
  HOLD → otherwise

Confidence levels:
  High   → news_count >= confidence_high_min
  Medium → news_count >= confidence_medium_min
  Low    → otherwise
"""
import logging
from typing import Dict, Tuple

from config.settings import settings

logger = logging.getLogger(__name__)


class Recommender:
    """Blends news sentiment with price trend into a recommendation."""

    def __init__(self):
        self.buy_threshold = settings.recommendation_buy_threshold
        self.sell_threshold = settings.recommendation_sell_threshold
        self.high_min = settings.confidence_high_min
        self.medium_min = settings.confidence_medium_min

    def get_confidence_level(self, news_count: int) -> str:
        """Determine confidence level from article count."""
        if news_count >= self.high_min:
            return "High"
        elif news_count >= self.medium_min:
            return "Medium"
        else:
            return "Low"

    def compute(
        self,
        sentiment_score: float,
        news_count: int,
        trend_score: float,
    ) -> Dict:
        """
        Compute the blended recommendation.

        Args:
            sentiment_score: Weighted sentiment from FinBERT [-1, +1]
            news_count: Number of contributing news articles
            trend_score: Price-based trend score [-1, +1]

        Returns:
            {
                "confidence_level":      "High" | "Medium" | "Low",
                "recommendation_score":  float,
                "recommendation_label":  "BUY" | "SELL" | "HOLD",
                "sentiment_weight":      float,
                "trend_weight":          float,
            }
        """
        confidence = self.get_confidence_level(news_count)

        if confidence in ("High", "Medium"):
            # Sentiment is reliable enough to heavily weight
            sent_w, trend_w = 0.70, 0.30
            recommendation_score = 0.70 * sentiment_score + 0.30 * trend_score
        else:
            # Low confidence: Sentiment is unreliable (very few articles).
            # Fall back to 100% trend score to guide the recommendation.
            sent_w, trend_w = 0.0, 1.0
            recommendation_score = 1.00 * trend_score

        # Label
        if recommendation_score > self.buy_threshold:
            label = "BUY"
        elif recommendation_score < self.sell_threshold:
            label = "SELL"
        else:
            label = "HOLD"

        return {
            "confidence_level":     confidence,
            "recommendation_score": round(recommendation_score, 4),
            "recommendation_label": label,
            "sentiment_weight":     sent_w,
            "trend_weight":         trend_w,
        }
