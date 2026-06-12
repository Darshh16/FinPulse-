"""
Quick end-to-end test: fetch from Google News RSS, run through pipeline, check DB.
"""
import asyncio
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

print("=== Step 1: Test Google News RSS for Indian stocks ===")
from src.data_sources.rss_scraper import (
    _fetch_google_news_for_company, _fetch_cnbc, _fetch_yahoo_for_ticker,
    COMPANY_SEARCH_QUERIES
)

total = 0
for ticker, query in list(COMPANY_SEARCH_QUERIES.items())[:4]:
    arts = _fetch_google_news_for_company(ticker, query)
    print(f"  {ticker}: {len(arts)} articles from Google News")
    if arts:
        h = arts[0]["headline"]
        print(f"    Sample: {h[:80]}")
    total += len(arts)
print(f"  Subtotal: {total} articles\n")

print("=== Step 2: Test NewsAPI with company query ===")
import asyncio
from src.data_sources.news_api import fetch_financial_news
newsapi_arts = asyncio.run(fetch_financial_news())
print(f"  NewsAPI: {len(newsapi_arts)} articles")
if newsapi_arts:
    h = newsapi_arts[0]["headline"]
    print(f"  Sample: {h[:80]}")

print("\n=== Step 3: Run one pipeline cycle ===")
from src.streaming.pipeline import StreamingPipeline
pipeline = StreamingPipeline()
asyncio.run(pipeline.pipeline_cycle())

print("\n=== Step 4: Check DB for articles ===")
from src.database import get_db_session, NewsHeadline, AggregatedSentiment
from sqlalchemy import func
db = get_db_session()

rows = db.query(
    NewsHeadline.ticker,
    func.count(NewsHeadline.id)
).filter(
    NewsHeadline.ticker.isnot(None)
).group_by(NewsHeadline.ticker).all()

print(f"  Articles in DB by ticker:")
for ticker, count in rows:
    print(f"    {ticker}: {count} articles")

agg_rows = db.query(
    AggregatedSentiment.ticker,
    func.count(AggregatedSentiment.id)
).group_by(AggregatedSentiment.ticker).all()
print(f"\n  Aggregated sentiment rows:")
for ticker, count in agg_rows:
    print(f"    {ticker}: {count} aggregate windows")

db.close()
print("\n=== DONE ===")
