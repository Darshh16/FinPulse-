"""
One-shot script: aggregates sentiment and aligns prices for all tickers already in DB.
Run this after the pipeline has fetched news (news is already stored).
"""
import logging
from src.database import get_db_session
from src.database.models import NewsHeadline
from sqlalchemy import func
from src.aggregation.aggregator import SentimentAggregator
from src.price_alignment.aligner import PriceAligner

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
logger = logging.getLogger(__name__)

db = get_db_session()

# List tickers in DB
rows = db.query(NewsHeadline.ticker, func.count(NewsHeadline.id)).filter(
    NewsHeadline.ticker.isnot(None)
).group_by(NewsHeadline.ticker).all()

print(f"\nFound {len(rows)} tickers in DB:")
for t, c in rows:
    print(f"  {t}: {c} articles")

print("\n--- Running aggregation (24h window) ---")
agg = SentimentAggregator(db)
aligner = PriceAligner(db)

agg_count = 0
align_count = 0
for ticker, count in rows:
    result = agg.aggregate_by_window(ticker, window_minutes=1440)
    if result:
        agg_count += 1
        logger.info(f"AGG {ticker}: avg={result['avg_sentiment']:.4f}, articles={result['news_count']}, pos={result['positive_count']}, neg={result['negative_count']}")
        aligned = aligner.align_sentiment_with_price(ticker)
        if aligned:
            align_count += 1
            logger.info(f"ALIGN {ticker}: {len(aligned)} sentiment-price pairs")
    else:
        logger.warning(f"NO ARTICLES IN WINDOW: {ticker}")

db.close()
print(f"\n=== DONE: Aggregated {agg_count} tickers, aligned {align_count} tickers ===")
