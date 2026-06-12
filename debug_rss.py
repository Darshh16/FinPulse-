import asyncio
import logging
logging.basicConfig(level=logging.INFO)

from src.data_sources.rss_scraper import _fetch_reuters, _fetch_cnbc, _fetch_yahoo_for_ticker

print("=== Testing RSS Feeds ===")

reuters = _fetch_reuters()
print(f"Reuters: {len(reuters)} articles")
if reuters:
    h = reuters[0]["headline"]
    print(f"  Sample: {h[:80]}")

cnbc = _fetch_cnbc()
print(f"CNBC: {len(cnbc)} articles")
if cnbc:
    h = cnbc[0]["headline"]
    print(f"  Sample: {h[:80]}")

print("\nYahoo Finance per-ticker:")
for ticker in ["HDFCBANK.NS", "MSFT", "NVDA", "SBIN.NS", "MARUTI.NS"]:
    arts = _fetch_yahoo_for_ticker(ticker)
    print(f"  {ticker}: {len(arts)} articles")
    if arts:
        h = arts[0]["headline"]
        print(f"    Sample: {h[:70]}")

# Also test normalizer with relevance filter
print("\n=== Relevance Filter Test ===")
from src.data_sources.news_normalizer import NewsNormalizer
from src.ticker_mapping.ticker_mapper import ALL_KEYWORDS
normalizer = NewsNormalizer()

# Simulate what pipeline does: combine RSS + newsapi articles
all_articles = reuters + cnbc
for ticker in ["HDFCBANK.NS", "MSFT", "NVDA", "SBIN.NS"]:
    all_articles += _fetch_yahoo_for_ticker(ticker)

print(f"Total raw articles: {len(all_articles)}")
filtered = normalizer.process(all_articles, company_keywords=ALL_KEYWORDS)
print(f"After dedup + relevance filter: {len(filtered)}")
if filtered:
    for a in filtered[:5]:
        h = a["headline"]
        print(f"  [{a['source'].upper()}] {h[:70]}")
