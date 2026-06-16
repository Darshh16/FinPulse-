# FinPulse - Real-Time Financial News Sentiment Pipeline

## Project Overview

FinPulse is a comprehensive real-time financial news sentiment analysis platform that:

1. **Continuously ingests** financial news from NewsAPI
2. **Analyzes sentiment** using FinBERT (financial domain-specific model)
3. **Maps news** to relevant stock tickers
4. **Aggregates sentiment** over time windows
5. **Aligns sentiment** with stock price movements
6. **Exposes data** through REST APIs
7. **Visualizes insights** on an interactive dashboard

---

## 📋 Features & Expected Outcomes

### ✅ Core Features

#### 1. **News Ingestion Pipeline**
- Fetches real-time financial news from NewsAPI
- Continuous data streaming (configurable intervals)
- Source tracking and deduplication

**Output:** News headlines stored in database with metadata

#### 2. **Sentiment Analysis (FinBERT)**
- Financial domain-specific sentiment classification
- Accuracy: 85-90% on financial texts
- Labels: Positive, Negative, Neutral
- Normalized scores: -1.0 (very negative) to +1.0 (very positive)

**Output:** Sentiment labels and scores for each article

#### 3. **Ticker Mapping**
- Intelligent company name recognition
- Maps 100+ companies to stock tickers
- Handles variations and abbreviations
- Supports custom mappings

**Output:** Relevant stock tickers linked to news articles

#### 4. **Sentiment Aggregation**
- Configurable time windows (15 min, hourly, daily)
- Sentiment statistics per ticker
- Positive/Negative/Neutral distribution
- Volume metrics

**Output:** Aggregated sentiment data per ticker per time window

#### 5. **Price-Sentiment Alignment**
- Correlates sentiment trends with stock price movements
- Calculates Pearson correlation coefficient
- Identifies sentiment-price divergences
- Tracks price changes alongside sentiment

**Output:** Correlation analysis and alignment data

#### 6. **REST API Endpoints**
- `GET /api/v1/news` - Fetch news articles
- `GET /api/v1/ticker/{symbol}` - Get ticker summary
- `GET /api/v1/sentiment/{symbol}` - Get sentiment trends
- `GET /api/v1/correlation/{symbol}` - Get price-sentiment correlation
- `GET /api/v1/signals` - Get trading signals (educational)
- `GET /api/v1/dashboard-summary` - Dashboard metrics

#### 7. **Interactive Dashboard (Streamlit)**
- Real-time metrics and KPIs
- Top tickers by news volume
- Sentiment trend visualization
- Price-sentiment correlation charts
- Trading signals display
- Live news feed with filtering
- **Dynamic Theme System** (Dark, Bloomberg Terminal, Light modes)
- **Live Currency Conversion** (Global stocks dynamically converted to INR via `yfinance` `INR=X`)

---

## 🏗️ Architecture

```
NewsAPI + Scraping
    ↓
[News Processor] → Sentiment Analysis (FinBERT) → Ticker Mapping
    ↓
PostgreSQL Database
    ├─ news_headlines
    ├─ stock_prices
    ├─ aggregated_sentiment
    └─ price_sentiment_alignment
    ↓
[Aggregation Engine] → [Price Aligner]
    ↓
FastAPI Backend
    ├─ /news
    ├─ /ticker/{symbol}
    ├─ /sentiment/{symbol}
    ├─ /correlation/{symbol}
    ├─ /signals
    └─ /dashboard-summary
    ↓
Streamlit Dashboard + Plotly Visualizations
```

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| News Source | NewsAPI |
| Sentiment Model | FinBERT (ProsusAI) |
| Stock Prices | yfinance |
| Database | PostgreSQL |
| Backend API | FastAPI |
| Dashboard | Streamlit + Plotly |
| Language | Python 3.9+ |
| Async | asyncio, aiohttp |

---

## 📦 Installation & Setup

### Prerequisites
- Python 3.9+
- PostgreSQL 12+
- pip or conda

### Step 1: Clone and Setup

```bash
cd c:\coding\FinPulse
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### Step 2: Manual Configuration Required ⚙️

#### **A. Get NewsAPI Key**
1. Go to https://newsapi.org/
2. Sign up (free tier available)
3. Copy your API key

#### **B. Setup PostgreSQL Database**
1. Install PostgreSQL from https://www.postgresql.org/download/
2. Create database:
```sql
CREATE DATABASE finpulse;
CREATE USER finpulse_user WITH PASSWORD 'your_secure_password';
ALTER ROLE finpulse_user SET client_encoding TO 'utf8';
ALTER ROLE finpulse_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE finpulse_user SET default_transaction_deferrable TO on;
ALTER ROLE finpulse_user SET default_transaction_read_committed TO 'read committed';
GRANT ALL PRIVILEGES ON DATABASE finpulse TO finpulse_user;
```

#### **C. Environment Configuration**
1. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

2. Update `.env` with your credentials:
```env
NEWS_API_KEY=your_newsapi_key_here
DB_HOST=localhost
DB_PORT=5432
DB_NAME=finpulse
DB_USER=finpulse_user
DB_PASSWORD=your_secure_password
```

---

## 🚀 Running the System

### Option 1: Run Everything Together (Recommended for Testing)

```bash
# Terminal 1: Start FastAPI Backend
cd c:\coding\FinPulse
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Start Streamlit Dashboard
streamlit run src/dashboard/app.py --logger.level=debug

# Terminal 3: Start Streaming Pipeline (Optional - for continuous data ingestion)
# This will continuously fetch news and process them
python src/streaming/pipeline.py
```

### Option 2: Quick Test (Without Pipeline)

```bash
# Just start the API and Dashboard
# Terminal 1:
python -m uvicorn src.api.main:app --reload

# Terminal 2:
streamlit run src/dashboard/app.py
```

---

## Dashboard Access

Once running:
- **Dashboard:** http://localhost:8502
- **API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

---

## 🔄 Data Flow Example

1. **NewsAPI** provides financial news headlines
2. **FinBERT** analyzes sentiment → "positive" (0.95)
3. **Ticker Mapper** identifies "Apple" → "AAPL"
4. **Database** stores: headline, sentiment, ticker
5. **Aggregator** calculates hourly sentiment for AAPL
6. **Price Aligner** fetches AAPL price and calculates correlation
7. **API** serves data to dashboard
8. **Dashboard** visualizes trends and signals

---

## Example Output

### News Processing
```
Input: "Apple announces record profits and expansion plans"
Output:
  - Headline: "HDFC announces record profits and expansion plans"
  - Sentiment: positive (0.89)
  - Ticker: HDFC  
  - Source: Financial Times
```

### Sentiment Aggregation (Hourly)
```
Ticker: HDFC
Window: 2024-01-15 10:00 - 2024-01-15 11:00
Average Sentiment: 0.62
News Count: 5
Distribution:
  - Positive: 3 (60%)
  - Negative: 1 (20%)
  - Neutral: 1 (20%)
```

### Trading Signals (Educational)
```
Ticker: HDFC
Signal: BUY
Strength: 0.78
Confidence: 78%
Sentiment: 0.62
News Volume: 5
[Disclaimer: Educational purposes only]
```

---

## What You Can Do With FinPulse

✅ **Monitor:** Real-time sentiment for any stock ticker
✅ **Analyze:** Correlations between news sentiment and price movements
✅ **Discover:** Trading signal candidates based on sentiment spikes
✅ **Research:** Historical sentiment trends and patterns
✅ **Learn:** Understand NLP and sentiment analysis in finance

---

## Configuration Options

Edit `.env` to customize:

```env
# News Fetching Interval (seconds)
NEWS_FETCH_INTERVAL=300

# Sentiment Aggregation Window (seconds)
SENTIMENT_WINDOW=900

# Database Connection
DB_HOST=localhost
DB_PORT=5432

# API Server
API_HOST=0.0.0.0
API_PORT=8000

# Model
MODEL_NAME=ProsusAI/finbert
```

---

## Key Code Modules

| Module | Purpose |
|--------|---------|
| `src/data_sources/news_api.py` | NewsAPI integration |
| `src/data_sources/yfinance_client.py` | Stock price fetching & Currency Conversion |
| `src/sentiment_engine/finbert_analyzer.py` | FinBERT sentiment analysis |
| `src/ticker_mapping/ticker_mapper.py` | Company name to ticker mapping |
| `src/streaming/pipeline.py` | Main streaming pipeline |
| `src/aggregation/aggregator.py` | Sentiment aggregation |
| `src/price_alignment/aligner.py` | Price-sentiment alignment |
| `src/api/main.py` | FastAPI application |
| `src/api/routes.py` | API endpoints |
| `src/dashboard/app.py` | Streamlit dashboard |
| `src/dashboard/themes/` | Modular CSS for Dynamic Themes |
| `src/database/models.py` | Database schemas |

---

## Important Disclaimers

### Educational Use Only
FinPulse is an **educational analytics tool**. The generated insights are for **educational and analytical purposes only** and should **NOT** be considered financial advice.

### Not Investment Advice
Trading signals generated by FinPulse are for educational demonstration only. Always:
- Conduct your own research
- Consult with a licensed financial advisor
- Never trade based solely on automated signals
- Understand the risks involved in trading

---

## Troubleshooting

### Database Connection Error
```
Error: Could not connect to database
Solution: 
1. Check PostgreSQL is running
2. Verify credentials in .env
3. Ensure database 'finpulse' exists
```

### NewsAPI Key Error
```
Error: Invalid API key
Solution:
1. Get key from https://newsapi.org/
2. Update NEWS_API_KEY in .env
```

### FinBERT Model Download
First run will download ~450MB model:
```
Solution: Ensure internet connection and disk space
```

### Streamlit Connection Error
```
Error: Could not connect to API
Solution:
1. Ensure FastAPI is running on port 8000
2. Check API_URL in dashboard/app.py
```

---

## Database Schema

### news_headlines
- `id`: Primary key
- `headline`: Article title
- `description`: Article description
- `source`: News source
- `url`: Article URL
- `timestamp`: Published time
- `ticker`: Stock ticker (mapped)
- `sentiment_label`: positive/negative/neutral
- `sentiment_score`: -1.0 to 1.0

### stock_prices
- `id`: Primary key
- `ticker`: Stock symbol
- `timestamp`: Price time
- `open`, `high`, `low`, `close`: OHLC values
- `volume`: Trading volume

### aggregated_sentiment
- `id`: Primary key
- `ticker`: Stock ticker
- `window_start`, `window_end`: Time window
- `avg_sentiment`: Average sentiment score
- `positive_count`, `negative_count`, `neutral_count`: Distribution
- `news_count`: Number of articles

### price_sentiment_alignment
- `id`: Primary key
- `ticker`: Stock ticker
- `timestamp`: Time point
- `avg_sentiment`: Sentiment score
- `price_close`: Stock price
- `price_change_percent`: Price change %
- `news_count`: Article count

---

## Next Steps

1. ✅ Setup PostgreSQL database
2. ✅ Get NewsAPI key
3. ✅ Configure `.env` file
4. ✅ Install dependencies
5. ✅ Run FastAPI backend
6. ✅ Start Streamlit dashboard
7. ✅ View insights on http://localhost:8502
8. ⏸️ Deployment (future phase)

---

## Support

For issues or questions:
1. Check `.env` configuration
2. Review error logs
3. Verify all services are running
4. Check internet connectivity

---

## License

Educational Project - Use for learning purposes

---

**Happy Analyzing! **
