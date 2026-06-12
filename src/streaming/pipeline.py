"""
FinPulse Hybrid Streaming Pipeline.

Fetches news from BOTH NewsAPI and RSS feeds (Reuters, CNBC, Yahoo Finance),
merges, normalizes, deduplicates, filters to the fixed 10-stock universe,
runs FinBERT sentiment, fetches prices, aggregates with source weighting,
and aligns sentiment with prices.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Set

from sqlalchemy.orm import Session

from src.data_sources.news_api import fetch_financial_news
from src.data_sources.rss_scraper import RSSScraperClient
from src.data_sources.news_normalizer import NewsNormalizer
from src.data_sources.yfinance_client import fetch_stock_prices
from src.sentiment_engine import analyze_headline
from src.ticker_mapping import map_headline_to_tickers
from src.ticker_mapping.ticker_mapper import (
    ALL_TICKERS, ALL_KEYWORDS, get_ticker_name,
    get_mapper,
)
from src.database import NewsHeadline, StockPrice, get_db_session
from src.aggregation.aggregator import SentimentAggregator
from src.price_alignment.aligner import PriceAligner
from config.settings import settings

logger = logging.getLogger(__name__)

# Fixed universe tickers (always fetch prices for all of them)
FIXED_TICKERS: List[str] = list(ALL_TICKERS)


# ─────────────────────────────────────────────────────────────────────────────
# NewsAPI adapter — normalise to common article schema
# ─────────────────────────────────────────────────────────────────────────────

def _normalise_newsapi_article(article: Dict) -> Dict:
    """Convert a NewsAPI article to the common article schema."""
    pub = article.get("published_at", "")
    try:
        if pub:
            ts = datetime.fromisoformat(pub.replace("Z", "+00:00"))
        else:
            ts = datetime.now(timezone.utc)
    except Exception:
        ts = datetime.now(timezone.utc)

    return {
        "headline":      article.get("headline", ""),
        "description":   article.get("description", ""),
        "url":           article.get("url", ""),
        "source":        article.get("source", "newsapi"),
        "source_weight": settings.weight_newsapi,
        "published_at":  ts,
    }


# ─────────────────────────────────────────────────────────────────────────────
# News Processor
# ─────────────────────────────────────────────────────────────────────────────

class NewsProcessor:
    """Process news articles through sentiment analysis and store to DB."""

    def __init__(self, db_session: Session):
        self.db_session = db_session

    async def process_news_batch(self, articles: List[Dict]) -> List[Dict]:
        """
        Run articles through FinBERT, map to tickers, store to DB.

        For articles with _ticker_hint (from company-specific RSS feeds),
        assigns that ticker directly without requiring keyword match.
        For others, uses keyword-based ticker mapping.
        """
        processed = []

        for article in articles:
            try:
                headline    = article.get("headline", "").strip()
                description = article.get("description", "").strip()
                url         = article.get("url", "").strip()
                source      = article.get("source", "unknown")
                weight      = float(article.get("source_weight", settings.weight_newsapi))
                ticker_hint = article.get("_ticker_hint")  # from company-specific RSS

                if not headline:
                    continue

                # DB de-dup (URL check)
                if url:
                    if self.db_session.query(NewsHeadline).filter(
                        NewsHeadline.url == url
                    ).first():
                        logger.debug(f"Skip (URL exists): {headline[:60]}")
                        continue

                # Map to tickers
                # 1. Use _ticker_hint if provided (company-specific RSS feed)
                if ticker_hint and ticker_hint in ALL_TICKERS:
                    tickers: Set[str] = {ticker_hint}
                else:
                    # 2. Keyword-based mapping
                    tickers = map_headline_to_tickers(f"{headline} {description}")
                    if not tickers:
                        continue  # Only store news relevant to our universe

                # Sentiment analysis
                text_to_analyze = f"{headline} {description}"[:450]
                sentiment_result = analyze_headline(text_to_analyze)

                # Parse timestamp
                pub_at = article.get("published_at")
                if isinstance(pub_at, datetime):
                    ts = pub_at.replace(tzinfo=None) if pub_at.tzinfo else pub_at
                elif pub_at:
                    try:
                        ts = datetime.fromisoformat(
                            str(pub_at).replace("Z", "+00:00")
                        ).replace(tzinfo=None)
                    except Exception:
                        ts = datetime.utcnow()
                else:
                    ts = datetime.utcnow()

                # Store one row per ticker
                url_used = False
                for ticker in tickers:
                    existing = self.db_session.query(NewsHeadline).filter(
                        NewsHeadline.headline == headline,
                        NewsHeadline.ticker == ticker,
                    ).first()
                    if existing:
                        continue

                    # Only store URL on first ticker row (unique constraint)
                    row_url = url if (url and not url_used) else None
                    news_record = NewsHeadline(
                        headline        = headline,
                        description     = description,
                        source          = source,
                        url             = row_url,
                        timestamp       = ts,
                        ticker          = ticker,
                        sentiment_label = sentiment_result["label"],
                        sentiment_score = sentiment_result["normalized_score"],
                        source_weight   = weight,
                    )
                    self.db_session.add(news_record)
                    if row_url:
                        url_used = True

                processed.append({
                    "headline":        headline,
                    "source":          source,
                    "source_weight":   weight,
                    "sentiment_label": sentiment_result["label"],
                    "sentiment_score": sentiment_result["normalized_score"],
                    "tickers":         list(tickers),
                    "timestamp":       ts,
                    "url":             url,
                })

                logger.info(f"[{source}] {headline[:55]}... -> {sentiment_result['label']} ({list(tickers)})")

            except Exception as e:
                logger.error(f"Error processing article: {e}")
                continue

        try:
            self.db_session.commit()
            logger.info(f"Stored {len(processed)} articles to DB")
        except Exception as e:
            logger.error(f"DB commit error: {e}")
            self.db_session.rollback()

        return processed


# ─────────────────────────────────────────────────────────────────────────────
# Price Processor
# ─────────────────────────────────────────────────────────────────────────────

class PriceProcessor:
    """Fetch and store stock prices for the fixed universe."""

    def __init__(self, db_session: Session):
        self.db_session = db_session

    async def process_price_batch(self, tickers: List[str], period: str = "1d") -> List[Dict]:
        try:
            prices = await fetch_stock_prices(tickers, period=period)

            for price_data in prices:
                price_record = StockPrice(
                    ticker    = price_data["ticker"],
                    timestamp = price_data["timestamp"],
                    open      = price_data.get("open", 0),
                    high      = price_data.get("high", 0),
                    low       = price_data.get("low", 0),
                    close     = price_data["close"],
                    volume    = price_data.get("volume", 0),
                )
                self.db_session.add(price_record)

            self.db_session.commit()
            logger.info(f"Stored prices for {len(prices)} tickers")
            return prices

        except Exception as e:
            logger.error(f"Error processing prices: {e}")
            self.db_session.rollback()
            return []


# ─────────────────────────────────────────────────────────────────────────────
# Streaming Pipeline
# ─────────────────────────────────────────────────────────────────────────────

class StreamingPipeline:
    """Hybrid pipeline orchestrator: NewsAPI + RSS → Normalize → Sentiment → Price → Aggregate."""

    def __init__(self):
        self.db_session    = get_db_session()
        self.news_proc     = NewsProcessor(self.db_session)
        self.price_proc    = PriceProcessor(self.db_session)
        self.aggregator    = SentimentAggregator(self.db_session)
        self.aligner       = PriceAligner(self.db_session)
        self.normalizer    = NewsNormalizer()
        self.rss_client    = RSSScraperClient()
        self.running       = False

    async def start(self):
        """Run the pipeline continuously."""
        self.running = True
        logger.info("Starting FinPulse hybrid streaming pipeline...")
        try:
            while self.running:
                await self.pipeline_cycle()
                await asyncio.sleep(settings.news_fetch_interval)
        except KeyboardInterrupt:
            logger.info("Pipeline interrupted")
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
        finally:
            await self.stop()

    async def pipeline_cycle(self):
        """Execute one complete hybrid pipeline cycle."""
        try:
            logger.info("=== Pipeline cycle starting ===")

            # ── Step 1: Fetch from NewsAPI ────────────────────────────────────
            logger.info("Step 1a: Fetching from NewsAPI...")
            newsapi_raw = await fetch_financial_news()
            newsapi_articles = [_normalise_newsapi_article(a) for a in (newsapi_raw or [])]
            logger.info(f"  NewsAPI: {len(newsapi_articles)} articles")

            # ── Step 1b: Fetch from RSS feeds ─────────────────────────────────
            rss_articles = []
            if settings.scraping_enabled:
                logger.info("Step 1b: Fetching from RSS feeds (Reuters, CNBC, Yahoo)...")
                try:
                    rss_articles = await self.rss_client.fetch_all(tickers=FIXED_TICKERS)
                    logger.info(f"  RSS: {len(rss_articles)} raw articles")
                except Exception as e:
                    logger.error(f"RSS fetch error (continuing with NewsAPI only): {e}")

            # ── Step 2: Merge + normalize + deduplicate ───────────────────────
            logger.info("Step 2: Normalizing and deduplicating...")
            all_raw = newsapi_articles + rss_articles

            # For articles with _ticker_hint, skip relevance filter
            # (they are already targeted to specific companies)
            hinted   = [a for a in all_raw if a.get("_ticker_hint")]
            unhinted = [a for a in all_raw if not a.get("_ticker_hint")]

            # Deduplicate unhinted articles + apply relevance filter
            clean_unhinted = self.normalizer.process(unhinted, company_keywords=ALL_KEYWORDS)
            # Deduplicate hinted articles (no relevance filter — already company-targeted)
            clean_hinted = self.normalizer.deduplicate(hinted)

            clean_articles = clean_hinted + clean_unhinted
            logger.info(f"  Hinted (RSS): {len(clean_hinted)} | Unhinted filtered: {len(clean_unhinted)} | Total: {len(clean_articles)}")

            if not clean_articles:
                logger.warning("No relevant articles after filtering. Skipping this cycle.")
                return

            # ── Step 3: Sentiment analysis + store ───────────────────────────
            logger.info("Step 3: Running FinBERT sentiment analysis...")
            processed_news = await self.news_proc.process_news_batch(clean_articles)
            logger.info(f"  Processed & stored: {len(processed_news)} articles")

            # ── Step 4: Prices for full fixed universe ────────────────────────
            logger.info(f"Step 4: Fetching prices for {len(FIXED_TICKERS)} tickers...")
            await self.price_proc.process_price_batch(FIXED_TICKERS)

            # ── Step 5: Aggregate sentiment (30-day window) ──────────────────
            logger.info("Step 5: Aggregating sentiment (30-day window)...")
            for ticker in FIXED_TICKERS:
                result = self.aggregator.aggregate_by_window(ticker, window_minutes=43200)  # 30 days
                if result:
                    ws = result.get("weighted_sentiment", result["avg_sentiment"])
                    logger.info(
                        f"  {ticker} ({get_ticker_name(ticker)}): "
                        f"weighted={ws:+.4f}, articles={result['news_count']}"
                    )
                else:
                    logger.warning(f"  No articles in window for: {ticker}")

            # ── Step 6: Align sentiment with prices ───────────────────────────
            logger.info("Step 6: Aligning sentiment with prices...")
            for ticker in FIXED_TICKERS:
                self.aligner.align_sentiment_with_price(ticker)

            logger.info("=== Pipeline cycle completed successfully ===")

        except Exception as e:
            logger.error(f"Pipeline cycle error: {e}", exc_info=True)

    async def stop(self):
        self.running = False
        logger.info("Pipeline stopped")
        if self.db_session:
            self.db_session.close()


async def run_pipeline():
    pipeline = StreamingPipeline()
    await pipeline.start()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_pipeline())
