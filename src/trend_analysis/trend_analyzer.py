"""
Trend Analyzer — computes price-based trend metrics.

Uses 6-month historical stock price data to derive:
  - trend_score:    normalized [-1, +1] via linear regression slope + tanh
  - price_momentum: "improving" / "deteriorating" / "stable"
                    based on 20-day vs 50-day SMA crossover

IMPORTANT: This module has ZERO dependency on sentiment data.
           Trend and sentiment are independent signals.
"""
import logging
import math
from typing import Dict, Optional

import numpy as np

logger = logging.getLogger(__name__)


class TrendAnalyzer:
    """Computes price-based trend metrics from historical stock data."""

    def __init__(self, lookback_months: int = 6):
        self.lookback_months = lookback_months

    def compute_trend(self, ticker: str) -> Optional[Dict]:
        """
        Fetch historical price data and compute trend metrics.

        Args:
            ticker: Yahoo Finance ticker symbol (e.g. "HDFCBANK.NS", "MSFT")

        Returns:
            {
                "trend_score":    float in [-1, +1],
                "price_momentum": "improving" | "deteriorating" | "stable",
                "current_price":  float,
                "sma_20":         float,
                "sma_50":         float,
            }
            or None if insufficient data
        """
        try:
            import yfinance as yf

            period = f"{self.lookback_months}mo"
            hist = yf.Ticker(ticker).history(period=period, interval="1d")

            if hist.empty or len(hist) < 50:
                logger.warning(f"Insufficient price history for {ticker} ({len(hist) if not hist.empty else 0} days)")
                return None

            closes = hist["Close"].dropna().values.astype(float)

            if len(closes) < 50:
                logger.warning(f"Not enough close prices for {ticker}")
                return None

            # ── Trend Score via Linear Regression ────────────────────────────
            trend_score = self._compute_trend_score(closes)

            # ── Price Momentum via SMA Crossover ─────────────────────────────
            sma_20 = float(np.mean(closes[-20:]))
            sma_50 = float(np.mean(closes[-50:]))
            momentum = self._compute_momentum(sma_20, sma_50)

            current_price = float(closes[-1])

            return {
                "trend_score":    round(trend_score, 4),
                "price_momentum": momentum,
                "current_price":  round(current_price, 2),
                "sma_20":         round(sma_20, 2),
                "sma_50":         round(sma_50, 2),
            }

        except Exception as e:
            logger.error(f"Error computing trend for {ticker}: {e}")
            return None

    def _compute_trend_score(self, closes: np.ndarray) -> float:
        """
        Fit a linear regression to the closing prices and normalize
        the slope into [-1, +1] using tanh-based scaling.

        A positive slope → positive trend_score (bullish).
        A negative slope → negative trend_score (bearish).
        """
        n = len(closes)
        x = np.arange(n, dtype=float)

        # Normalize prices to percentage change from first close
        # This makes the slope scale-independent across stocks
        if closes[0] == 0:
            return 0.0
        normalized = (closes - closes[0]) / closes[0] * 100.0

        # Linear regression: slope = cov(x, y) / var(x)
        x_mean = np.mean(x)
        y_mean = np.mean(normalized)
        numerator = np.sum((x - x_mean) * (normalized - y_mean))
        denominator = np.sum((x - x_mean) ** 2)

        if denominator == 0:
            return 0.0

        slope = numerator / denominator

        # Scale the slope using tanh so the output is bounded [-1, +1]
        # The multiplier (0.5) controls sensitivity — a 2% daily change
        # maps to roughly ±0.76
        trend_score = math.tanh(slope * 0.5)

        return trend_score

    def _compute_momentum(self, sma_20: float, sma_50: float) -> str:
        """
        Determine momentum from SMA crossover.

        - If 20d SMA is 1%+ above 50d SMA → improving
        - If 20d SMA is 1%+ below 50d SMA → deteriorating
        - Otherwise → stable
        """
        if sma_50 == 0:
            return "stable"

        pct_diff = (sma_20 - sma_50) / sma_50 * 100

        if pct_diff > 1.0:
            return "improving"
        elif pct_diff < -1.0:
            return "deteriorating"
        else:
            return "stable"
