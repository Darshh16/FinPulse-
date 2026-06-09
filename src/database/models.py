from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Index, create_engine
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
    ticker = Column(String(20))  # Initially NULL, filled by ticker mapping
    sentiment_label = Column(String(20))  # positive, negative, neutral
    sentiment_score = Column(Float)  # Score between -1 and 1
    
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
    avg_sentiment = Column(Float)  # Average sentiment score
    positive_count = Column(Integer, default=0)
    negative_count = Column(Integer, default=0)
    neutral_count = Column(Integer, default=0)
    news_count = Column(Integer, default=0)
    
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
    """Initialize database tables"""
    engine = get_engine()
    Base.metadata.create_all(engine)
    print("Database initialized successfully!")

def get_db_session():
    """Get database session"""
    SessionLocal = get_session_maker()
    return SessionLocal()
