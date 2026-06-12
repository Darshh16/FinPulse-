"""
RSS feed scraper for FinPulse hybrid news sourcing.

Sources:
  1. Google News RSS (per-company query) - works for ALL companies including Indian ones
  2. Yahoo Finance RSS (per-ticker) - works for global tickers (MSFT, NVDA)
  3. CNBC RSS (general business)
  4. MoneyControl RSS (India-specific financial news)

Anti-ban: random delays, User-Agent rotation, timeout limits.
"""
import asyncio
import logging
import random
import time
import urllib.parse
from datetime import datetime, timezone
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor

import feedparser
from bs4 import BeautifulSoup

from config.settings import settings

logger = logging.getLogger(__name__)

# Realistic browser User-Agents to rotate
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    "Feedfetcher-Google; (+http://www.google.com/feedfetcher.html)",
]

# Source weight constants
SOURCE_WEIGHTS = {
    "reuters":      settings.weight_reuters,   # 1.0
    "cnbc":         settings.weight_cnbc,      # 0.95
    "yahoo":        settings.weight_yahoo,     # 0.90
    "moneycontrol": settings.weight_yahoo,     # 0.90
    "google_news":  settings.weight_newsapi,   # 0.85
    "newsapi":      settings.weight_newsapi,   # 0.85
}

# Company name → search query mapping for Google News RSS
# Use the most distinctive search terms to get relevant articles
COMPANY_SEARCH_QUERIES = {
    "HDFCBANK.NS": "HDFC Bank stock NSE",
    "SBIN.NS":     "State Bank India SBI stock NSE",
    "TRENT.NS":    "Trent Limited Zudio stock NSE",
    "DMART.NS":    "Avenue Supermarts DMart stock NSE",
    "SIEMENS.NS":  "Siemens India stock NSE",
    "ABB.NS":      "ABB India stock NSE",
    "MARUTI.NS":   "Maruti Suzuki stock NSE",
    "M&M.NS":      "Mahindra Mahindra stock NSE",
    "MSFT":        "Microsoft stock MSFT earnings",
    "NVDA":        "Nvidia stock NVDA earnings GPU",
}

# Additional India-specific RSS feeds
INDIA_RSS_FEEDS = [
    ("https://www.moneycontrol.com/rss/marketstats.xml", "moneycontrol", SOURCE_WEIGHTS["moneycontrol"]),
    ("https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms", "economic_times", SOURCE_WEIGHTS["reuters"]),
]


def _get_ua() -> str:
    return random.choice(_USER_AGENTS)


def _polite_delay(min_s: float = None, max_s: float = None):
    lo = min_s or settings.scraping_delay_min
    hi = max_s or settings.scraping_delay_max
    time.sleep(random.uniform(lo, hi))


def _parse_feed_entry(entry: feedparser.FeedParserDict, source_name: str, weight: float) -> Optional[Dict]:
    """Convert a feedparser entry to a normalized article dict."""
    try:
        headline = entry.get("title", "").strip()
        if not headline:
            return None

        raw_desc = entry.get("summary", "") or entry.get("description", "") or ""
        soup = BeautifulSoup(raw_desc, "lxml")
        description = soup.get_text(separator=" ").strip()[:512]

        url = entry.get("link", "") or entry.get("url", "")

        published_at = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                published_at = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            except Exception:
                published_at = datetime.now(timezone.utc)
        else:
            published_at = datetime.now(timezone.utc)

        return {
            "headline":      headline,
            "description":   description,
            "url":           url,
            "source":        source_name,
            "source_weight": weight,
            "published_at":  published_at,
        }
    except Exception as e:
        logger.debug(f"Error parsing feed entry: {e}")
        return None


def _fetch_rss_feed(feed_url: str, source_name: str, weight: float) -> List[Dict]:
    """Fetch and parse a single RSS feed synchronously."""
    articles = []
    try:
        logger.info(f"Fetching RSS: {source_name} -> {feed_url[:70]}")
        parsed = feedparser.parse(
            feed_url,
            request_headers={
                "User-Agent": _get_ua(),
                "Accept": "application/rss+xml, application/xml, text/xml, */*",
            },
        )

        if parsed.bozo:
            exc = getattr(parsed, "bozo_exception", None)
            logger.debug(f"RSS {source_name} bozo={parsed.bozo}: {exc}")

        for entry in parsed.entries:
            article = _parse_feed_entry(entry, source_name, weight)
            if article:
                articles.append(article)

        logger.info(f"RSS {source_name}: {len(articles)} articles")
        _polite_delay(0.5, 1.5)

    except Exception as e:
        logger.error(f"Error fetching RSS {source_name}: {e}")

    return articles


def _fetch_google_news_for_company(ticker: str, query: str) -> List[Dict]:
    """
    Use Google News RSS to search for a company by name.
    Works for ALL companies including Indian ones.
    URL: https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en
    """
    encoded_query = urllib.parse.quote(query)
    # Try India-localized first, fallback to global
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
    articles = _fetch_rss_feed(url, "google_news", SOURCE_WEIGHTS["google_news"])

    # Tag each article with the ticker it was fetched for
    for art in articles:
        art["_ticker_hint"] = ticker  # used by normalizer/mapper

    if len(articles) == 0:
        # Fallback: global search
        url_global = f"https://news.google.com/rss/search?q={encoded_query}&hl=en&gl=US&ceid=US:en"
        articles = _fetch_rss_feed(url_global, "google_news", SOURCE_WEIGHTS["google_news"])
        for art in articles:
            art["_ticker_hint"] = ticker

    return articles


def _fetch_yahoo_for_ticker(ticker: str) -> List[Dict]:
    """Yahoo Finance per-ticker RSS (works for global tickers; Indian .NS may return empty)."""
    url = settings.rss_yahoo_base_url.format(ticker=ticker)
    articles = _fetch_rss_feed(url, "yahoo", SOURCE_WEIGHTS["yahoo"])
    for art in articles:
        art["_ticker_hint"] = ticker
    return articles


def _fetch_cnbc() -> List[Dict]:
    return _fetch_rss_feed(
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "cnbc",
        SOURCE_WEIGHTS["cnbc"],
    )


def _fetch_india_feed(url: str, source: str, weight: float) -> List[Dict]:
    return _fetch_rss_feed(url, source, weight)


class RSSScraperClient:
    """
    Hybrid RSS feed scraper using Google News, Yahoo Finance, CNBC, and India-specific feeds.
    """

    def __init__(self, max_workers: int = 6):
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="rss")

    async def fetch_all(self, tickers: Optional[List[str]] = None) -> List[Dict]:
        """
        Fetch from all RSS sources concurrently.

        Args:
            tickers: list of ticker symbols (used to pick Google News queries)

        Returns:
            Combined list of article dicts from all sources
        """
        loop = asyncio.get_event_loop()
        feed_tasks = []

        # 1. Google News per company (primary source for Indian stocks)
        for ticker, query in COMPANY_SEARCH_QUERIES.items():
            if tickers is None or ticker in tickers:
                t, q = ticker, query  # capture
                feed_tasks.append(
                    loop.run_in_executor(self._executor, _fetch_google_news_for_company, t, q)
                )

        # 2. Yahoo Finance per-ticker (good for MSFT, NVDA; may return empty for .NS)
        if tickers:
            for ticker in tickers:
                t = ticker
                feed_tasks.append(
                    loop.run_in_executor(self._executor, _fetch_yahoo_for_ticker, t)
                )

        # 3. CNBC general business feed
        feed_tasks.append(loop.run_in_executor(self._executor, _fetch_cnbc))

        # 4. India-specific feeds (MoneyControl, Economic Times)
        for url, source, weight in INDIA_RSS_FEEDS:
            u, s, w = url, source, weight
            feed_tasks.append(
                loop.run_in_executor(self._executor, _fetch_india_feed, u, s, w)
            )

        results = await asyncio.gather(*feed_tasks, return_exceptions=True)

        all_articles: List[Dict] = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"RSS fetch task failed: {result}")
            elif isinstance(result, list):
                all_articles.extend(result)

        logger.info(f"RSS total raw: {len(all_articles)} articles from all feeds")
        return all_articles

    def fetch_all_sync(self, tickers: Optional[List[str]] = None) -> List[Dict]:
        return asyncio.run(self.fetch_all(tickers=tickers))


def get_source_weight(source: str) -> float:
    source_lower = (source or "").lower()
    for key, weight in SOURCE_WEIGHTS.items():
        if key in source_lower:
            return weight
    return SOURCE_WEIGHTS["newsapi"]
