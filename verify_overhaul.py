from src.database.models import init_db
init_db()
print("DB migration OK")

from src.ticker_mapping.ticker_mapper import ALL_TICKERS, get_ticker_name, get_ticker_sector
print(f"Fixed universe ({len(ALL_TICKERS)} tickers): {sorted(ALL_TICKERS)}")
print(f"MSFT -> {get_ticker_name('MSFT')} | {get_ticker_sector('MSFT')}")
print(f"HDFCBANK.NS -> {get_ticker_name('HDFCBANK.NS')} | {get_ticker_sector('HDFCBANK.NS')}")
print(f"SBIN.NS -> {get_ticker_name('SBIN.NS')} | {get_ticker_sector('SBIN.NS')}")

# Test ticker mapping
from src.ticker_mapping.ticker_mapper import map_headline_to_tickers
tests = [
    "HDFC Bank posts record Q4 profits amid rising NPA concerns",
    "State Bank of India cuts home loan rates",
    "Mahindra & Mahindra launches new EV SUV",
    "Microsoft Azure revenue jumps 31 percent in Q3",
    "NVIDIA stock hits all-time high on AI demand",
    "Unrelated: Government announces new highway project",
]
print("\nTicker mapping tests:")
for t in tests:
    tickers = map_headline_to_tickers(t)
    print(f"  [{', '.join(tickers) if tickers else 'NONE'}] {t[:65]}")

# Test deduplication
from src.data_sources.news_normalizer import NewsNormalizer
n = NewsNormalizer()
test_articles = [
    {"headline":"HDFC Bank reports record profits for Q4","description":"Banking giant HDFC Bank saw strong growth","url":"http://test1.com","source":"reuters","source_weight":1.0,"published_at":None},
    {"headline":"HDFC Bank reports record profits for Q4","description":"HDFC Bank saw strong growth","url":"http://test2.com","source":"cnbc","source_weight":0.95,"published_at":None},
    {"headline":"Microsoft Azure revenue surges in Q3","description":"Azure cloud business grew 31 percent","url":"http://test3.com","source":"yahoo","source_weight":0.90,"published_at":None},
]
result = n.deduplicate(test_articles)
print(f"\nDedup test: {len(test_articles)} articles -> {len(result)} unique (should be 2)")

from src.data_sources.rss_scraper import RSSScraperClient, SOURCE_WEIGHTS
print(f"\nSource weights: {SOURCE_WEIGHTS}")

from src.aggregation.aggregator import SentimentAggregator
print("\nAll imports OK")
