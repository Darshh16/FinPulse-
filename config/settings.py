from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application Settings"""
    
    # API Keys
    news_api_key: str
    
    # Database
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "finpulse"
    db_user: str = "postgres"
    db_password: str
    
    # App Config
    debug: bool = False
    log_level: str = "INFO"
    
    # API Config
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Model Config
    model_name: str = "ProsusAI/finbert"
    
    # Pipeline Timing
    news_fetch_interval: int = 300   # 5 minutes
    sentiment_window: int = 900      # 15 minutes
    price_fetch_interval: int = 300  # 5 minutes
    
    # NewsAPI Configuration (kept for hybrid approach)
    news_search_query: str = "finance OR stock OR market"
    news_country: str = "us"
    news_sort_by: str = "publishedAt"
    
    # Scraping / RSS Configuration
    scraping_enabled: bool = True
    scraping_delay_min: float = 1.0   # min seconds between feed fetches
    scraping_delay_max: float = 3.0   # max seconds between feed fetches
    scraping_timeout: int = 15        # seconds per feed request
    
    # RSS Feed URLs
    rss_reuters_url: str = "https://feeds.reuters.com/reuters/businessNews"
    rss_cnbc_url: str = "https://www.cnbc.com/id/100003114/device/rss/rss.html"
    rss_yahoo_base_url: str = "https://finance.yahoo.com/rss/headline?s={ticker}"
    
    # Source Weights (for weighted sentiment)
    weight_reuters: float = 1.0
    weight_cnbc: float = 0.95
    weight_yahoo: float = 0.90
    weight_newsapi: float = 0.85
    
    # Timezone
    display_timezone: str = "Asia/Kolkata"   # IST
    
    # Deduplication
    dedup_similarity_threshold: float = 0.82  # headline fuzzy match threshold

    # Recommendation Engine
    recommendation_buy_threshold: float = 0.40
    recommendation_sell_threshold: float = -0.40
    trend_lookback_months: int = 6

    # Confidence Levels (based on news_count)
    confidence_high_min: int = 20
    confidence_medium_min: int = 5

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
