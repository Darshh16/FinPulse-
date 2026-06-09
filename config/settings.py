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
    news_fetch_interval: int = 300  # 5 minutes
    sentiment_window: int = 900  # 15 minutes
    price_fetch_interval: int = 300  # 5 minutes
    
    # News Configuration
    news_search_query: str = "finance OR stock OR market"
    news_country: str = "us"
    news_sort_by: str = "publishedAt"
    
    @property
    def database_url(self) -> str:
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
