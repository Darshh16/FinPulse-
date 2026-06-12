"""
One-shot aggregation script.
Aggregates sentiment (7-day window) and aligns prices for the fixed 10-stock universe.
Run this after the pipeline has fetched news.
"""
import logging
from src.database import get_db_session
from src.database.models import NewsHeadline
from src.ticker_mapping.ticker_mapper import ALL_TICKERS, get_ticker_name
from sqlalchemy import func
from src.aggregation.aggregator import SentimentAggregator
from src.price_alignment.aligner import PriceAligner

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

db = get_db_session()

# Only process our fixed 10-stock universe
TICKERS_TO_AGG = list(ALL_TICKERS)

# Show what's in DB for each fixed ticker
print(f"\n{'='*55}")
print(f"  FinPulse Aggregation — Fixed Universe ({len(TICKERS_TO_AGG)} tickers)")
print(f"{'='*55}")
rows = db.query(
    NewsHeadline.ticker,
    func.count(NewsHeadline.id)
).filter(
    NewsHeadline.ticker.in_(TICKERS_TO_AGG)
).group_by(NewsHeadline.ticker).all()

article_counts = {t: c for t, c in rows}
for ticker in sorted(TICKERS_TO_AGG):
    count = article_counts.get(ticker, 0)
    name  = get_ticker_name(ticker)
    print(f"  {ticker:15s}  {name:30s}  {count:4d} articles")

print(f"\n--- Running aggregation (30-day window) ---")
agg     = SentimentAggregator(db)
aligner = PriceAligner(db)

agg_count   = 0
align_count = 0

for ticker in sorted(TICKERS_TO_AGG):
    result = agg.aggregate_by_window(ticker, window_minutes=43200)  # 30 days
    name   = get_ticker_name(ticker)
    if result:
        agg_count += 1
        ws  = result.get("weighted_sentiment", result["avg_sentiment"])
        avg = result["avg_sentiment"]
        logger.info(
            f"AGG {ticker:15s} ({name:28s}): "
            f"weighted={ws:+.4f}  avg={avg:+.4f}  "
            f"articles={result['news_count']}  "
            f"pos={result['positive_count']} neg={result['negative_count']} neu={result['neutral_count']}"
        )
        aligned = aligner.align_sentiment_with_price(ticker)
        if aligned:
            align_count += 1
            logger.info(f"  ALIGN {ticker}: {len(aligned)} sentiment-price pairs")
    else:
        logger.warning(f"NO ARTICLES in 7-day window for: {ticker} ({name})")

db.close()
print(f"\n{'='*55}")
print(f"  DONE: Aggregated {agg_count}/{len(TICKERS_TO_AGG)} tickers, aligned {align_count}")
print(f"{'='*55}\n")
