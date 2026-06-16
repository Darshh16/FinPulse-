import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.database.models import get_engine
from sqlalchemy import text

engine = get_engine()
with engine.connect() as conn:
    rows = conn.execute(text("SELECT timestamp, avg_sentiment, price_change_percent FROM price_sentiment_alignment WHERE ticker = 'MARUTI.NS' ORDER BY timestamp")).fetchall()
    print("ROWS:", rows)
