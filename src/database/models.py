from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, Index, create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from config.settings import settings

Base = declarative_base()

class NewsHeadline(Base):
    """News Headlines Table"""
    __tablename__ = "news_headlines"
    
    id = Column(Integer, primary_key=True)
    headline = Column(Text, nullable=False)
    description = Column(Text)
    source = Column(String(255), nullable=False)
    url = Column(Text, unique=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    ticker = Column(String(20))           # filled by ticker mapping
    sentiment_label = Column(String(20))  # positive, negative, neutral
    sentiment_score = Column(Float)       # raw FinBERT score -1 to 1
    source_weight = Column(Float, default=1.0)   # credibility weight (Reuters=1.0 ... NewsAPI=0.85)
    
    __table_args__ = (
        Index('idx_news_timestamp', 'timestamp'),
        Index('idx_news_ticker', 'ticker'),
        Index('idx_news_source', 'source'),
    )


class StockPrice(Base):
    """Stock Price Table"""
    __tablename__ = "stock_prices"
    
    id = Column(Integer, primary_key=True)
    ticker = Column(String(20), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float, nullable=False)
    volume = Column(Integer)
    
    __table_args__ = (
        Index('idx_stock_ticker_timestamp', 'ticker', 'timestamp'),
        Index('idx_stock_ticker', 'ticker'),    
    )


class AggregatedSentiment(Base):
    """Aggregated Sentiment Scores Table"""
    __tablename__ = "aggregated_sentiment"
    
    id = Column(Integer, primary_key=True)
    ticker = Column(String(20), nullable=False)
    window_start = Column(DateTime, nullable=False)
    window_end = Column(DateTime, nullable=False)
    avg_sentiment = Column(Float)           # simple average (backward compat)
    weighted_sentiment = Column(Float)      # source-weight-adjusted average
    positive_count = Column(Integer, default=0)
    negative_count = Column(Integer, default=0)
    neutral_count = Column(Integer, default=0)
    news_count = Column(Integer, default=0)
    contributing_articles = Column(JSON, nullable=True)  # for hover feature
    # Trend-Based Recommendation Layer
    confidence_level = Column(String(10), nullable=True)       # High / Medium / Low
    trend_score = Column(Float, nullable=True)                 # -1.0 to +1.0 from price history
    price_momentum = Column(String(20), nullable=True)         # improving / deteriorating / stable
    recommendation_score = Column(Float, nullable=True)        # blended sentiment + trend
    recommendation_label = Column(String(10), nullable=True)   # BUY / SELL / HOLD
    
    __table_args__ = (
        Index('idx_sentiment_ticker_window', 'ticker', 'window_start', 'window_end'),
    )


class PriceSentimentAlignment(Base):
    """Price and Sentiment Alignment Table"""
    __tablename__ = "price_sentiment_alignment"
    
    id = Column(Integer, primary_key=True)
    ticker = Column(String(20), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    avg_sentiment = Column(Float)
    price_close = Column(Float)
    price_change_percent = Column(Float)
    news_count = Column(Integer)
    
    __table_args__ = (
        Index('idx_alignment_ticker_timestamp', 'ticker', 'timestamp'),
    )


# Database Engine and Session
def get_engine():
    """Create database engine"""
    return create_engine(settings.database_url, pool_pre_ping=True)

def get_session_maker():
    """Get session maker"""
    engine = get_engine()
    return sessionmaker(bind=engine)

def init_db():
    """Initialize database tables and run lightweight migrations."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    
    # Idempotent column migrations
    migrations = [
        "ALTER TABLE news_headlines ADD COLUMN IF NOT EXISTS source_weight FLOAT DEFAULT 1.0",
        "ALTER TABLE aggregated_sentiment ADD COLUMN IF NOT EXISTS weighted_sentiment FLOAT",
        "ALTER TABLE aggregated_sentiment ADD COLUMN IF NOT EXISTS contributing_articles JSON",
        # Trend-Based Recommendation Layer columns
        "ALTER TABLE aggregated_sentiment ADD COLUMN IF NOT EXISTS confidence_level VARCHAR(10)",
        "ALTER TABLE aggregated_sentiment ADD COLUMN IF NOT EXISTS trend_score FLOAT",
        "ALTER TABLE aggregated_sentiment ADD COLUMN IF NOT EXISTS price_momentum VARCHAR(20)",
        "ALTER TABLE aggregated_sentiment ADD COLUMN IF NOT EXISTS recommendation_score FLOAT",
        "ALTER TABLE aggregated_sentiment ADD COLUMN IF NOT EXISTS recommendation_label VARCHAR(10)",
    ]
    with engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                pass  # Column already exists
    
    print("Database initialized successfully!")

def get_db_session():
    """Get database session"""
    SessionLocal = get_session_maker()
    return SessionLocal()
