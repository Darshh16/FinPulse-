import streamlit as st
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests
import logging
from config.settings import settings

logger = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")

def to_ist(dt):
    """Convert a naive UTC datetime (or ISO string) to IST datetime."""
    if dt is None:
        return None
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except Exception:
            return dt
    if hasattr(dt, "tzinfo") and dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(IST)

def fmt_ist(dt) -> str:
    """Format a datetime as IST string."""
    ist_dt = to_ist(dt)
    if ist_dt is None:
        return ""
    return ist_dt.strftime("%d %b %Y, %H:%M IST")

# ─────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="FinPulse — Sentiment Intelligence",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────
# Premium CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Fira+Code:wght@400;500&display=swap');

/* Base Theme */
html, body, [class*="css"] { font-family: 'Outfit', sans-serif; color: #e4e4e7; }
.main .block-container { padding: 2.5rem 3rem 4rem; max-width: 1500px; }
.stApp { background: #09090b; } /* Deep zinc */

/* Sidebar */
[data-testid="stSidebar"] { background: rgba(9, 9, 11, 0.85); backdrop-filter: blur(12px); border-right: 1px solid rgba(255, 255, 255, 0.05); }
[data-testid="stSidebar"] .block-container { padding: 2rem 1.2rem; }

/* Typography */
h1 { font-size: 2.2rem !important; font-weight: 700 !important; letter-spacing: -0.02em; color: #fafafa !important; }
h2 { font-size: 1.5rem !important; font-weight: 600 !important; color: #f4f4f5 !important; letter-spacing: -0.01em; }
h3 { font-size: 1.1rem !important; font-weight: 500 !important; color: #a1a1aa !important; }

/* Entrance Animations */
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(15px); }
    to { opacity: 1; transform: translateY(0); }
}
.stMarkdown, [data-testid="stMetric"], .news-card, .insight-card {
    animation: fadeInUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

/* Metrics Cards */
[data-testid="stMetric"] {
    background: rgba(24, 24, 27, 0.6);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.08); 
    border-radius: 16px;
    padding: 1.2rem 1.5rem; 
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    transition: all 0.3s ease;
}
[data-testid="stMetric"]:hover { 
    border-color: rgba(6, 182, 212, 0.4); /* Cyan glow */
    transform: translateY(-3px);
    box-shadow: 0 10px 25px -5px rgba(6, 182, 212, 0.15);
}
[data-testid="stMetricLabel"] { font-size: 0.75rem!important; font-weight: 500!important; letter-spacing: 0.08em; text-transform: uppercase; color: #a1a1aa!important; }
[data-testid="stMetricValue"] { font-family: 'Fira Code', monospace!important; font-size: 1.8rem!important; font-weight: 600!important; color: #fafafa!important; }
[data-testid="stMetricDelta"] { font-family: 'Fira Code', monospace!important; font-size: 0.85rem!important; }

/* Tabs */
[data-testid="stTabs"] [role="tablist"] { background: rgba(24, 24, 27, 0.8); border-radius: 12px; padding: 6px; border: 1px solid rgba(255, 255, 255, 0.05); gap: 4px; }
[data-testid="stTabs"] [role="tab"] { font-size: 0.85rem; font-weight: 500; letter-spacing: 0.03em; color: #a1a1aa; border-radius: 8px; padding: 0.6rem 1.4rem; border: none; background: transparent; transition: all 0.3s ease; }
[data-testid="stTabs"] [role="tab"][aria-selected="true"] { 
    background: linear-gradient(135deg, rgba(6, 182, 212, 0.15) 0%, rgba(139, 92, 246, 0.15) 100%); 
    color: #22d3ee; 
    border: 1px solid rgba(34, 211, 238, 0.3);
    box-shadow: 0 0 15px rgba(6, 182, 212, 0.1); 
}
[data-testid="stTabs"] [role="tab"]:hover:not([aria-selected="true"]) { color: #f4f4f5; background: rgba(255, 255, 255, 0.05); }

/* Buttons & Inputs */
.stButton>button { 
    background: linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%); 
    color: #ffffff; border: none; border-radius: 10px; padding: 0.5rem 1.5rem; 
    font-size: 0.85rem; font-weight: 600; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); 
    box-shadow: 0 4px 14px 0 rgba(6, 182, 212, 0.39); 
}
.stButton>button:hover { 
    transform: translateY(-2px); 
    box-shadow: 0 6px 20px rgba(6, 182, 212, 0.5); 
    filter: brightness(1.1);
}
.stSelectbox>div>div { background: #18181b!important; border: 1px solid rgba(255, 255, 255, 0.1)!important; border-radius: 10px!important; color: #fafafa!important; transition: border-color 0.2s; }
.stSelectbox>div>div:hover { border-color: rgba(6, 182, 212, 0.4)!important; }

/* Layout Utilities */
hr { border: none; border-top: 1px solid rgba(255, 255, 255, 0.06); margin: 2rem 0; }
.section-label { font-size: 0.7rem; font-weight: 600; letter-spacing: 0.15em; text-transform: uppercase; color: #22d3ee; margin-bottom: 1rem; padding-bottom: 0.5rem; border-bottom: 1px solid rgba(34, 211, 238, 0.15); display: inline-block; }

/* Dataframes */
[data-testid="stDataFrame"] { border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; overflow: hidden; background: #18181b; }
[data-testid="stDataFrame"] thead th { background: #09090b!important; color: #a1a1aa!important; font-size: 0.75rem!important; letter-spacing: 0.05em; text-transform: uppercase; font-weight: 600!important; border-bottom: 1px solid rgba(255,255,255,0.05); }

/* Sidebar Stats */
.sidebar-stat { background: rgba(24, 24, 27, 0.5); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 12px; padding: 1rem 1.2rem; margin-bottom: 0.8rem; transition: transform 0.2s; }
.sidebar-stat:hover { transform: translateX(4px); border-color: rgba(139, 92, 246, 0.3); }
.sidebar-stat-label { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; color: #a1a1aa; font-weight: 500; margin-bottom: 0.3rem; }
.sidebar-stat-value { font-family: 'Fira Code', monospace; font-size: 1.4rem; font-weight: 600; color: #fafafa; }

/* Legend & Badges */
.legend-card { background: #18181b; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 1.2rem 1.5rem; margin: 1rem 0; }
.legend-title { font-size: 0.7rem; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: #a1a1aa; margin-bottom: 0.8rem; }
.legend-row { display: flex; align-items: center; gap: 1rem; margin-bottom: 0.6rem; font-size: 0.85rem; }
.badge { border-radius: 6px; padding: 0.2rem 0.7rem; font-family: 'Fira Code', monospace; font-size: 0.75rem; font-weight: 600; }
.badge-buy  { background: rgba(16, 185, 129, 0.15);  color: #34d399; border: 1px solid rgba(16, 185, 129, 0.2); }
.badge-sell { background: rgba(244, 63, 94, 0.15);  color: #fb7185; border: 1px solid rgba(244, 63, 94, 0.2); }
.badge-hold { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.2); }

/* Insight Card */
.insight-card { 
    background: linear-gradient(160deg, #18181b 0%, #09090b 100%); 
    border: 1px solid rgba(139, 92, 246, 0.2); 
    border-radius: 16px; 
    padding: 1.8rem 2rem; 
    margin: 1.5rem 0; 
    box-shadow: 0 10px 30px -10px rgba(139, 92, 246, 0.1);
    position: relative;
    overflow: hidden;
}
.insight-card::before {
    content: ''; position: absolute; top: 0; left: 0; width: 4px; height: 100%;
    background: linear-gradient(to bottom, #06b6d4, #8b5cf6);
}
.insight-header { font-size: 0.75rem; font-weight: 600; letter-spacing: 0.15em; text-transform: uppercase; color: #22d3ee; margin-bottom: 0.8rem; }
.insight-body { font-size: 0.95rem; color: #e4e4e7; line-height: 1.8; }
.insight-rec { font-size: 1.1rem; font-weight: 600; margin-top: 1.2rem; }
.insight-disclaimer { font-size: 0.75rem; color: #71717a; margin-top: 1rem; font-style: italic; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 0.8rem; }

/* News Feed Cards */
.news-card { 
    background: #18181b; 
    border: 1px solid rgba(255, 255, 255, 0.06); 
    border-radius: 14px; 
    padding: 1.2rem 1.5rem; 
    margin-bottom: 1rem; 
    transition: all 0.3s ease; 
}
.news-card:hover { 
    border-color: rgba(6, 182, 212, 0.3); 
    transform: translateY(-2px);
    box-shadow: 0 8px 20px -8px rgba(0,0,0,0.5);
}
.news-headline { font-size: 0.95rem; font-weight: 500; color: #fafafa; line-height: 1.5; margin-bottom: 0.5rem; }
.news-headline a:hover { color: #22d3ee !important; transition: color 0.2s; }
.news-meta { font-size: 0.75rem; color: #a1a1aa; display: flex; align-items: center; flex-wrap: wrap; gap: 0.5rem; }
.news-score-pos { color: #34d399; font-family: 'Fira Code', monospace; font-weight: 500; }
.news-score-neg { color: #fb7185; font-family: 'Fira Code', monospace; font-weight: 500; }
.news-score-neu { color: #94a3b8; font-family: 'Fira Code', monospace; font-weight: 500; }
.source-badge { background: rgba(34, 211, 238, 0.1); color: #22d3ee; border: 1px solid rgba(34, 211, 238, 0.2); border-radius: 6px; padding: 0.15rem 0.5rem; font-size: 0.7rem; font-weight: 600; font-family: 'Fira Code', monospace; }

/* Pulse Animation for Status */
@keyframes pulseGlow {
    0% { box-shadow: 0 0 0 0 rgba(6, 182, 212, 0.7); }
    70% { box-shadow: 0 0 0 6px rgba(6, 182, 212, 0); }
    100% { box-shadow: 0 0 0 0 rgba(6, 182, 212, 0); }
}
.status-dot { width: 8px; height: 8px; border-radius: 50%; background: #22d3ee; display: inline-block; margin-right: 8px; animation: pulseGlow 2s infinite; }

/* Hero Banner */
@keyframes gradientShift {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

@keyframes floatElement {
    0% { transform: translateY(0px); }
    50% { transform: translateY(-8px); }
    100% { transform: translateY(0px); }
}

.hero-container {
    background: linear-gradient(-45deg, #09090b, #1e1b4b, #083344, #09090b);
    background-size: 300% 300%;
    animation: gradientShift 15s ease infinite;
    border-radius: 24px;
    padding: 3.5rem 4rem;
    margin-bottom: 2.5rem;
    box-shadow: 0 20px 40px -10px rgba(0, 0, 0, 0.5), inset 0 1px 1px rgba(255, 255, 255, 0.1);
    position: relative;
    overflow: hidden;
    border: 1px solid rgba(255, 255, 255, 0.08);
}

.hero-container::before {
    content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
    background: radial-gradient(circle at 80% 20%, rgba(139, 92, 246, 0.15) 0%, transparent 40%),
                radial-gradient(circle at 20% 80%, rgba(6, 182, 212, 0.15) 0%, transparent 40%);
    pointer-events: none;
}

.hero-title {
    font-size: 3.2rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.03em;
    background: linear-gradient(to right, #ffffff 20%, #22d3ee 60%, #a855f7 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.8rem;
    position: relative;
    z-index: 1;
    animation: floatElement 6s ease-in-out infinite;
}

.hero-subtitle {
    font-size: 1.15rem;
    color: #a1a1aa;
    font-weight: 400;
    letter-spacing: 0.01em;
    position: relative;
    z-index: 1;
    max-width: 800px;
    line-height: 1.6;
}

.hero-badge {
    display: inline-flex;
    align-items: center;
    background: rgba(6, 182, 212, 0.1);
    border: 1px solid rgba(34, 211, 238, 0.2);
    color: #22d3ee;
    padding: 0.4rem 1rem;
    border-radius: 30px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    margin-bottom: 1.5rem;
    position: relative;
    z-index: 1;
    backdrop-filter: blur(4px);
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────
API_URL = f"http://localhost:{settings.api_port}/api/v1"

CHART_THEME = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Outfit, sans-serif", color="#a1a1aa", size=12),
    margin=dict(l=10, r=10, t=40, b=10),
    xaxis=dict(gridcolor="rgba(255,255,255,0.03)", linecolor="rgba(255,255,255,0.08)"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.03)", linecolor="rgba(255,255,255,0.08)"),
    hoverlabel=dict(bgcolor="#18181b", bordercolor="rgba(6,182,212,0.3)", font_size=12, font_family="Outfit"),
)

SENTIMENT_SCALE = [[0.0,"#ef4444"],[0.5,"#fbbf24"],[1.0,"#22c55e"]]

# Buy/Sell/Hold thresholds (match routes.py)
BUY_THRESHOLD  =  0.30
SELL_THRESHOLD = -0.15

# Fixed universe (from API)
_UNIVERSE_CACHE = None

def get_universe():
    global _UNIVERSE_CACHE
    if _UNIVERSE_CACHE:
        return _UNIVERSE_CACHE
    try:
        r = requests.get(f"{API_URL}/tickers", timeout=5)
        if r.status_code == 200:
            _UNIVERSE_CACHE = r.json()
            return _UNIVERSE_CACHE
    except Exception:
        pass
    # Fallback hardcoded
    return {"universe": {
        "Banking (India)":       [{"ticker":"HDFCBANK.NS","name":"HDFC Bank"},{"ticker":"SBIN.NS","name":"State Bank of India"}],
        "Retail (India)":        [{"ticker":"TRENT.NS","name":"Trent"},{"ticker":"DMART.NS","name":"Avenue Supermarts (DMart)"}],
        "Manufacturing (India)": [{"ticker":"SIEMENS.NS","name":"Siemens India"},{"ticker":"ABB.NS","name":"ABB India"}],
        "Automobile (India)":    [{"ticker":"MARUTI.NS","name":"Maruti Suzuki"},{"ticker":"M&M.NS","name":"Mahindra & Mahindra"}],
        "Global Tech":           [{"ticker":"MSFT","name":"Microsoft"},{"ticker":"NVDA","name":"NVIDIA"}],
    }}

def get_ticker_options():
    """Returns list of (display_label, ticker) tuples grouped by sector."""
    u = get_universe()
    options = []
    for sector, stocks in u.get("universe", {}).items():
        for s in stocks:
            options.append((f"{s['name']}  [{s['ticker']}]  —  {sector}", s["ticker"]))
    return options

# ─────────────────────────────────────────────
# Data fetchers
# ─────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_dashboard_summary():
    try:
        r = requests.get(f"{API_URL}/dashboard-summary", timeout=5)
        if r.status_code == 200: return r.json()
    except Exception as e: logger.error(e)
    return None

@st.cache_data(ttl=300)
def fetch_news(ticker=None, limit=50, days=7):
    try:
        params = {"limit": limit, "days": days}
        if ticker: params["ticker"] = ticker
        r = requests.get(f"{API_URL}/news", params=params, timeout=10)
        if r.status_code == 200: return r.json()
    except Exception as e: logger.error(e)
    return None

@st.cache_data(ttl=300)
def fetch_sentiment(ticker, days=7):
    try:
        r = requests.get(f"{API_URL}/sentiment/{ticker}", params={"days": days}, timeout=5)
        if r.status_code == 200: return r.json()
    except Exception as e: logger.error(e)
    return None

@st.cache_data(ttl=300)
def fetch_correlation(ticker, days=7):
    try:
        r = requests.get(f"{API_URL}/correlation/{ticker}", params={"days": days}, timeout=5)
        if r.status_code == 200: return r.json()
    except Exception as e: logger.error(e)
    return None

@st.cache_data(ttl=300)
def fetch_signals():
    try:
        r = requests.get(f"{API_URL}/signals", timeout=5)
        if r.status_code == 200: return r.json()
    except Exception as e: logger.error(e)
    return None

@st.cache_data(ttl=60)
def fetch_live_price(ticker: str):
    try:
        import yfinance as yf
        fi = yf.Ticker(ticker).fast_info
        price = float(fi.last_price) if fi.last_price is not None else None
        prev  = float(fi.previous_close) if fi.previous_close is not None else None
        if price is None: return None
        ch  = price - prev if prev else 0.0
        chp = (ch / prev * 100) if prev else 0.0
        return {"price":price,"prev_close":prev,"change":ch,"change_pct":chp,
                "market_cap":fi.market_cap,"volume":fi.three_month_average_volume}
    except Exception as e: logger.error(e)
    return None

@st.cache_data(ttl=300)
def fetch_price_history(ticker: str, period="5d", interval="1h"):
    try:
        import yfinance as yf
        hist = yf.Ticker(ticker).history(period=period, interval=interval)
        if hist.empty: return None
        hist.index = hist.index.tz_localize(None) if hist.index.tzinfo else hist.index
        return hist
    except Exception as e: logger.error(e)
    return None

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def sentiment_color(score):
    if score > BUY_THRESHOLD:  return "#22c55e"
    if score < SELL_THRESHOLD: return "#ef4444"
    return "#fbbf24"

def signal_from_score(score: float) -> str:
    if score > BUY_THRESHOLD:  return "BUY"
    if score < SELL_THRESHOLD: return "SELL"
    return "HOLD"

def apply_chart_theme(fig, title="", height=380):
    fig.update_layout(**CHART_THEME,
        title=dict(text=title, font=dict(size=13,color="#94a3b8"), x=0),
        height=height)
    return fig

def render_legend():
    """Render Buy/Sell/Hold legend as a styled HTML card."""
    st.markdown("""
    <div class="legend-card">
        <div class="legend-title">Signal Legend — How to Read Sentiment Scores</div>
        <div class="legend-row"><span class="badge badge-buy">BUY</span>
            <span style="color:#94a3b8">Score &gt; +0.30 &nbsp;|&nbsp; Strong positive news sentiment — consider reviewing for potential upside</span>
        </div>
        <div class="legend-row"><span class="badge badge-hold">HOLD</span>
            <span style="color:#94a3b8">Score &minus;0.15 to +0.30 &nbsp;|&nbsp; Mixed or neutral sentiment — wait for clearer signals</span>
        </div>
        <div class="legend-row"><span class="badge badge-sell">SELL</span>
            <span style="color:#94a3b8">Score &lt; &minus;0.15 &nbsp;|&nbsp; Predominantly negative news — exercise caution</span>
        </div>
        <div style="font-size:0.7rem;color:#334155;margin-top:0.6rem">
            Scores are weighted by source credibility: Reuters 1.0 &nbsp;&bull;&nbsp; CNBC 0.95 &nbsp;&bull;&nbsp; Yahoo Finance 0.90 &nbsp;&bull;&nbsp; NewsAPI 0.85
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_insight_card(ticker: str, name: str, score: float, pos: int, neg: int, neu: int,
                        total: int, days: int, trend: str = "stable",
                        confidence_level: str = None, trend_score: float = None,
                        price_momentum: str = None, rec_score: float = None, rec_label: str = None):
    """Render an AI-generated insight card with confidence-aware recommendation."""
    # Determine effective signal
    if rec_label:
        signal = rec_label
    else:
        signal = signal_from_score(score)
    col = sentiment_color(score)

    # Build confidence-aware narrative
    conf = confidence_level or "Unknown"
    is_low_confidence = conf == "Low"

    if signal == "BUY":
        if is_low_confidence:
            rec_text = (
                f"Only <b>{total}</b> relevant articles were found for <b>{name}</b> during the last <b>{days} days</b>. "
                f"Sentiment confidence is <b style='color:#ef4444'>low</b>. "
                f"The recommendation is primarily influenced by the stock's "
                f"<b style='color:#22c55e'>positive 6-month price trend</b> "
                f"(trend score: <b>{trend_score:+.3f}</b>)" if trend_score is not None else ""
                f" and recent price momentum ({price_momentum or 'stable'})."
                f"<br><br>Consider waiting for more news coverage before acting on this signal."
            )
        else:
            rec_text = (
                f"Sentiment analysis of <b>{total}</b> articles over the last <b>{days} days</b> shows "
                f"a <b style='color:#22c55e'>strongly positive</b> outlook for <b>{name}</b> "
                f"(sentiment: <b style='color:#22c55e'>{score:+.3f}</b>). "
                f"Positive articles dominate ({pos} positive vs {neg} negative). "
            )
            if trend_score is not None:
                rec_text += f"Price trend confirms the sentiment (trend: <b>{trend_score:+.3f}</b>). "
            rec_text += "<br><br>Consider reviewing recent earnings, sector trends, and price action before acting."
        rec_label_html = "<span style='color:#22c55e'>Recommendation: BUY (with due diligence)</span>"
    elif signal == "SELL":
        if is_low_confidence:
            rec_text = (
                f"Only <b>{total}</b> relevant articles were found for <b>{name}</b> during the last <b>{days} days</b>. "
                f"Sentiment confidence is <b style='color:#ef4444'>low</b>. "
                f"The recommendation is primarily influenced by the stock's "
                f"<b style='color:#ef4444'>negative price trend</b> "
                f"(trend score: <b>{trend_score:+.3f}</b>)" if trend_score is not None else ""
                f" and recent price momentum ({price_momentum or 'stable'})."
                f"<br><br>Exercise caution — limited news data reduces signal reliability."
            )
        else:
            rec_text = (
                f"Sentiment analysis of <b>{total}</b> articles over the last <b>{days} days</b> shows "
                f"a <b style='color:#ef4444'>predominantly negative</b> outlook for <b>{name}</b> "
                f"(sentiment: <b style='color:#ef4444'>{score:+.3f}</b>). "
                f"Negative articles dominate ({neg} negative vs {pos} positive). "
            )
            if trend_score is not None:
                rec_text += f"Price trend aligns with sentiment (trend: <b>{trend_score:+.3f}</b>). "
            rec_text += "<br><br>Exercise caution — review recent news and fundamentals before making any decisions."
        rec_label_html = "<span style='color:#ef4444'>Recommendation: SELL / CAUTION</span>"
    else:
        if is_low_confidence:
            rec_text = (
                f"Only <b>{total}</b> relevant articles were found for <b>{name}</b> during the last <b>{days} days</b>. "
                f"Sentiment confidence is <b style='color:#ef4444'>low</b>. "
                f"Neither sentiment nor price trend provides a strong directional signal. "
                f"<br><br>Consider waiting for more data before acting."
            )
        else:
            rec_text = (
                f"Sentiment analysis of <b>{total}</b> articles over the last <b>{days} days</b> shows "
                f"a <b style='color:#fbbf24'>mixed or neutral</b> outlook for <b>{name}</b> "
                f"(sentiment: <b style='color:#fbbf24'>{score:+.3f}</b>). "
                f"News volume is balanced ({pos} positive, {neg} negative, {neu} neutral). "
            )
            if trend_score is not None:
                rec_text += f"Price trend is {'supporting' if trend_score > 0 else 'weakening'} (trend: <b>{trend_score:+.3f}</b>). "
            rec_text += "<br><br>Consider waiting for a stronger directional signal before acting."
        rec_label_html = "<span style='color:#fbbf24'>Recommendation: HOLD / MONITOR</span>"

    trend_arrow = {"improving": "trending up", "declining": "trending down", "stable": "stable"}.get(trend, "stable")

    # Build the confidence/weighting footer
    weight_info = ""
    if confidence_level:
        sent_w = "70%" if confidence_level != "Low" else "30%"
        trend_w = "30%" if confidence_level != "Low" else "70%"
        weight_info = f"Signal weights: Sentiment <b>{sent_w}</b> + Trend <b>{trend_w}</b>"

    conf_color = {"High": "#22c55e", "Medium": "#fbbf24", "Low": "#ef4444"}.get(str(confidence_level), "#94a3b8")
    conf_display = confidence_level or '—'
    weight_line = f'<br>{weight_info}' if weight_info else ''

    card_html = f"""
    <div class="insight-card">
        <div class="insight-header">AI Insights — {name}</div>
        <div class="insight-body">
            {rec_text}
            <div style='margin-top:0.5rem;font-size:0.8rem;color:#475569'>
                Trend: <b style='color:#94a3b8'>{trend_arrow}</b> &nbsp;&bull;&nbsp;
                Article volume: <b style='color:#94a3b8'>{total}</b> &nbsp;&bull;&nbsp;
                Confidence: <b style='color:{conf_color}'>{conf_display}</b> &nbsp;&bull;&nbsp;
                Lookback: <b style='color:#94a3b8'>{days} days</b>
                {weight_line}
            </div>
        </div>
        <div class="insight-rec">{rec_label_html}</div>
        <div class="insight-disclaimer">
            This is an automated signal combining news sentiment and price trend for educational purposes only.
            It does not constitute financial advice. Past patterns do not guarantee future price movement.
            Always consult a registered financial advisor before investing.
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style='margin-bottom:1.5rem'>
            <div style='font-size:1.35rem;font-weight:700;color:#f0f6ff;letter-spacing:-0.5px'>FinPulse</div>
            <div style='font-size:0.72rem;color:#475569;letter-spacing:0.08em;text-transform:uppercase;margin-top:2px'>Sentiment Intelligence Platform</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="section-label">Live Statistics</div>', unsafe_allow_html=True)
        summary = fetch_dashboard_summary()
        if summary:
            d = summary.get("summary", {})
            avg_sent = d.get("avg_sentiment_24h", 0.0)
            st.markdown(f"""
            <div class="sidebar-stat">
                <div class="sidebar-stat-label">Articles (7d)</div>
                <div class="sidebar-stat-value">{d.get('total_news_24h', 0):,}</div>
            </div>
            <div class="sidebar-stat">
                <div class="sidebar-stat-label">Active Tickers</div>
                <div class="sidebar-stat-value">{d.get('total_tickers_24h', 0)}</div>
            </div>
            <div class="sidebar-stat">
                <div class="sidebar-stat-label">Market Sentiment</div>
                <div class="sidebar-stat-value" style="color:{sentiment_color(avg_sent)}">{avg_sent:+.3f}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.caption("API unavailable — start the backend server")

        st.divider()
        st.markdown('<div class="section-label">Controls</div>', unsafe_allow_html=True)
        if st.button("Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.divider()
        st.markdown('<div class="section-label">Data Sources</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style='font-size:0.78rem;color:#475569;line-height:2.2'>
        Reuters &nbsp;&mdash;&nbsp; weight 1.00<br>
        CNBC &nbsp;&nbsp;&nbsp;&mdash;&nbsp; weight 0.95<br>
        Yahoo Finance &mdash; weight 0.90<br>
        NewsAPI &nbsp;&mdash;&nbsp; weight 0.85
        </div>
        """, unsafe_allow_html=True)

        st.divider()
        st.markdown(f"""
        <div style="font-size:0.7rem;color:#334155">
            <span class="status-dot"></span>API Online &nbsp;|&nbsp;
            {datetime.now(IST).strftime("%H:%M IST")}
        </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Tab 1 — Overview
# ─────────────────────────────────────────────
def render_overview():
    st.markdown('<div class="section-label">Market Overview — Last 7 Days</div>', unsafe_allow_html=True)

    summary = fetch_dashboard_summary()
    if summary and "summary" in summary:
        d = summary["summary"]
        avg_sent = d.get("avg_sentiment_24h", 0.0)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Articles", f"{d.get('total_news_24h', 0):,}")
        c2.metric("Tickers Active", d.get("total_tickers_24h", 0))
        c3.metric("Market Sentiment", f"{avg_sent:+.3f}")
        c4.metric("Updated", datetime.now(IST).strftime("%H:%M IST"))
    else:
        st.info("No data yet — run the pipeline to populate the dashboard.")
        return

    st.divider()

    if summary.get("top_tickers"):
        df = pd.DataFrame(summary["top_tickers"])
        st.markdown('<div class="section-label">Top Tickers by News Volume</div>', unsafe_allow_html=True)
        col_chart, col_table = st.columns([3, 2])
        with col_chart:
            # Prepare data for custom hover
            top_10 = df.head(10).copy()
            # If name/sector isn't present, add it as a fallback
            if "name" not in top_10.columns:
                top_10["name"] = top_10["ticker"]
            if "sector" not in top_10.columns:
                top_10["sector"] = "Unknown"
            
            fig = go.Figure(go.Bar(
                x=top_10["ticker"], y=top_10["news_count"],
                marker=dict(color=top_10["avg_sentiment"],colorscale=SENTIMENT_SCALE,cmin=-1,cmax=1,
                    colorbar=dict(title=dict(text="Sentiment",font=dict(size=11)),thickness=12,len=0.7,
                        tickfont=dict(family="Fira Code",size=10)),line=dict(color="rgba(0,0,0,0)",width=0)),
                text=top_10["news_count"], textposition="outside",
                textfont=dict(size=10,color="#a1a1aa",family="Fira Code"),
                customdata=top_10[["name", "sector", "avg_sentiment"]],
                hovertemplate="<b>%{customdata[0]}</b> (%{x})<br>" +
                              "Sector: %{customdata[1]}<br>" +
                              "News Count: <b>%{y}</b> articles<br>" +
                              "Avg Sentiment: <b>%{customdata[2]:+.3f}</b><extra></extra>",
            ))
            apply_chart_theme(fig, "Article Volume by Ticker", height=360)
            fig.update_layout(xaxis=dict(tickfont=dict(family="Fira Code",size=11)),bargap=0.35)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

        with col_table:
            display = df[["ticker","name","sector","news_count","avg_sentiment"]].copy() if "name" in df.columns else df[["ticker","news_count","avg_sentiment"]].copy()
            display.columns = [c.title() for c in display.columns]
            if "Avg_Sentiment" in display.columns:
                display["Avg_Sentiment"] = display["Avg_Sentiment"].apply(lambda x: f"{x:+.4f}")
            elif "Avg Sentiment" in display.columns:
                display["Avg Sentiment"] = display["Avg Sentiment"].apply(lambda x: f"{x:+.4f}")
            st.dataframe(display, use_container_width=True, hide_index=True, height=360)

    # ── Homepage Legend
    st.divider()
    render_legend()


# ─────────────────────────────────────────────
# Tab 2 — Ticker Analysis
# ─────────────────────────────────────────────
def render_ticker_analysis():
    st.markdown('<div class="section-label">Ticker Deep Dive</div>', unsafe_allow_html=True)

    options = get_ticker_options()
    labels  = [o[0] for o in options]
    tickers = [o[1] for o in options]

    c1, c2 = st.columns([3, 1])
    with c1:
        selected_label = st.selectbox("Select Stock", labels, index=0)
    with c2:
        days = st.slider("Lookback (days)", 1, 30, 7)

    ticker = tickers[labels.index(selected_label)]
    name   = selected_label.split("[")[0].strip()

    sentiment_data = fetch_sentiment(ticker, days)

    if not sentiment_data or not sentiment_data.get("data"):
        st.warning(f"No sentiment data for **{name}** yet. Run the pipeline and `run_aggregation.py` to populate.")
        return

    df = pd.DataFrame(sentiment_data["data"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="ISO8601")
    df["timestamp_ist"] = df["timestamp"].apply(lambda x: to_ist(x.to_pydatetime()))
    df = df.sort_values("timestamp")

    pos   = int(df["positive_count"].sum())
    neg   = int(df["negative_count"].sum())
    neu   = int(df["neutral_count"].sum())
    total = int(df["news_count"].sum())
    # Use weighted_sentiment if available
    if "weighted_sentiment" in df.columns and df["weighted_sentiment"].notna().any():
        avg = float(df["weighted_sentiment"].mean())
    else:
        avg = float(df["avg_sentiment"].mean())

    # ── Sentiment KPIs
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Articles", f"{total:,}")
    k2.metric("Weighted Sentiment", f"{avg:+.3f}")
    k3.metric("Positive", pos)
    k4.metric("Negative", neg)
    k5.metric("Neutral", neu)

    # ── Recommendation KPIs (from latest aggregation window)
    latest_row = df.iloc[-1] if len(df) > 0 else None
    conf_level = latest_row.get("confidence_level") if latest_row is not None and "confidence_level" in df.columns else None
    t_score = latest_row.get("trend_score") if latest_row is not None and "trend_score" in df.columns else None
    p_momentum = latest_row.get("price_momentum") if latest_row is not None and "price_momentum" in df.columns else None
    rec_score = latest_row.get("recommendation_score") if latest_row is not None and "recommendation_score" in df.columns else None
    rec_label = latest_row.get("recommendation_label") if latest_row is not None and "recommendation_label" in df.columns else None

    # Sanitize NaN values → None
    if t_score is not None and pd.isna(t_score): t_score = None
    if rec_score is not None and pd.isna(rec_score): rec_score = None
    if conf_level is not None and (isinstance(conf_level, float) and pd.isna(conf_level)): conf_level = None
    if p_momentum is not None and (isinstance(p_momentum, float) and pd.isna(p_momentum)): p_momentum = None
    if rec_label is not None and (isinstance(rec_label, float) and pd.isna(rec_label)): rec_label = None

    if any(v is not None for v in [conf_level, t_score, rec_label]):
        r1, r2, r3, r4, r5 = st.columns(5)
        r1.metric("Confidence", conf_level or "—")
        r2.metric("Trend Score", f"{t_score:+.3f}" if t_score is not None else "—")
        mom_icon = {"improving": "📈", "deteriorating": "📉", "stable": "➡️"}.get(str(p_momentum), "")
        r3.metric("Momentum", f"{mom_icon} {(p_momentum or '—').title()}")
        r4.metric("Rec. Score", f"{rec_score:+.3f}" if rec_score is not None else "—")
        r5.metric("Recommendation", rec_label or "—")

    # ── Live Price Section
    st.divider()
    st.markdown('<div class="section-label">Current Price</div>', unsafe_allow_html=True)
    price_data = fetch_live_price(ticker)
    if price_data:
        p, ch, cp, pc = price_data["price"], price_data["change"], price_data["change_pct"], price_data["prev_close"]
        mc, vol = price_data["market_cap"], price_data["volume"]
        p1,p2,p3,p4 = st.columns(4)
        p1.metric("Current Price", f"{'₹' if '.NS' in ticker else '$'}{p:,.2f}",
                  delta=f"{ch:+.2f} ({cp:+.2f}%)", delta_color="normal" if ch>=0 else "inverse")
        p2.metric("Previous Close", f"{'₹' if '.NS' in ticker else '$'}{pc:,.2f}" if pc else "—")
        p3.metric("Market Cap",
                  f"{'₹' if '.NS' in ticker else '$'}{mc/1e12:.2f}T" if mc and mc>=1e12
                  else f"{'₹' if '.NS' in ticker else '$'}{mc/1e9:.1f}B" if mc and mc>=1e9
                  else "—")
        p4.metric("Avg Volume (3M)", f"{vol/1e6:.1f}M" if vol and vol>=1e6 else f"{vol:,.0f}" if vol else "—")

        hist = fetch_price_history(ticker, period="5d", interval="1h")
        if hist is not None and not hist.empty:
            fig_p = go.Figure(go.Candlestick(
                x=hist.index, open=hist["Open"], high=hist["High"], low=hist["Low"], close=hist["Close"],
                increasing=dict(line=dict(color="#22c55e",width=1.5), fillcolor="rgba(34,197,94,0.25)"),
                decreasing=dict(line=dict(color="#ef4444",width=1.5), fillcolor="rgba(239,68,68,0.25)"),
                name="Price",
            ))
            apply_chart_theme(fig_p, f"{name} — 5-Day Price (1h candles)", height=300)
            fig_p.update_layout(
                xaxis_rangeslider_visible=False,
                xaxis=dict(
                    tickfont=dict(family="Fira Code",size=10),
                    rangebreaks=[
                        dict(bounds=["sat", "mon"]), # Hide weekends
                        dict(bounds=[16.5, 9.25], pattern="hour") # Hide overnight gaps (approx for India/US)
                    ]
                ),
                yaxis=dict(tickprefix="₹" if ".NS" in ticker else "$", tickfont=dict(family="Fira Code",size=10))
            )
            st.plotly_chart(fig_p, use_container_width=True, config={"displayModeBar":False})
    else:
        st.caption(f"Live price unavailable for {ticker}.")

    # ── Sentiment charts
    st.divider()
    st.markdown('<div class="section-label">Sentiment Analysis</div>', unsafe_allow_html=True)

    left, right = st.columns(2)

    # Build hover text with contributing articles
    hover_texts = []
    contributing_list = df["contributing_articles"].tolist() if "contributing_articles" in df.columns else []
    for i, articles in enumerate(contributing_list):
        if articles and isinstance(articles, list):
            lines = [f"<b>{fmt_ist(df.iloc[i]['timestamp'])}</b>"]
            lines.append(f"Sentiment: <b>{df.iloc[i]['avg_sentiment']:+.4f}</b>")
            lines.append("─────────────────")
            lines.append("<b>Contributing News:</b>")
            for art in articles[:5]:
                label_icon = "+" if art.get("label") == "positive" else ("-" if art.get("label") == "negative" else "~")
                headline = art.get('headline', '')
                url = art.get('url', '')
                
                # Ensure the headline doesn't stretch the tooltip too wide
                short_head = headline[:55] + "..." if len(headline) > 55 else headline
                
                if url:
                    lines.append(f"{label_icon} [{art.get('source','?').upper()}] <a href='{url}' target='_blank' style='color:#6ee7b7'>{short_head}</a>")
                else:
                    lines.append(f"{label_icon} [{art.get('source','?').upper()}] {short_head}")
                
                lines.append(f"  Score: {art.get('score',0):+.4f} | Weight: {art.get('weight',1.0):.2f}")
            hover_texts.append("<br>".join(lines))
        else:
            hover_texts.append(f"<b>{fmt_ist(df.iloc[i]['timestamp'])}</b><br>Sentiment: {df.iloc[i]['avg_sentiment']:+.4f}")

    with left:
        sc = [sentiment_color(v) for v in df["avg_sentiment"]]
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["timestamp_ist"], y=df["avg_sentiment"],
            mode="lines+markers",
            line=dict(color="#06b6d4", width=2.5),
            marker=dict(color=sc, size=8, line=dict(color="#09090b",width=1.5)),
            fill="tozeroy", fillcolor="rgba(6,182,212,0.08)",
            text=hover_texts,
            hovertemplate="%{text}<extra></extra>",
        ))
        fig.add_hline(y=BUY_THRESHOLD, line=dict(color="rgba(16,185,129,0.3)",width=1,dash="dot"))
        fig.add_hline(y=SELL_THRESHOLD, line=dict(color="rgba(244,63,94,0.3)",width=1,dash="dot"))
        fig.add_hline(y=0, line=dict(color="rgba(255,255,255,0.06)",width=1,dash="dot"))
        apply_chart_theme(fig, f"{name} — Sentiment Trend (IST)")
        fig.update_layout(xaxis=dict(tickformat="%d %b %H:%M"))
        
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

    with right:
        fig2 = go.Figure(go.Pie(
            labels=["Positive","Negative","Neutral"], values=[pos,neg,neu], hole=0.62,
            marker=dict(colors=["#10b981","#ef4444","#475569"],line=dict(color="#09090b",width=3)),
            textinfo="label+percent", textfont=dict(size=11,family="Outfit"),
            hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Share: %{percent}<extra></extra>",
        ))
        fig2.update_layout(**CHART_THEME,
            title=dict(text=f"{name} — Sentiment Distribution",font=dict(size=13,color="#a1a1aa"),x=0),
            height=380, showlegend=False,
            annotations=[dict(text=f"<b>{avg:+.2f}</b>",x=0.5,y=0.5,showarrow=False,
                font=dict(size=22,color=sentiment_color(avg),family="Fira Code"))])
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar":False})

    # ── Legend
    render_legend()

    # ── Insight card
    # Detect trend
    if len(df) >= 2:
        recent = df["avg_sentiment"].iloc[-3:].mean()
        earlier = df["avg_sentiment"].iloc[:3].mean()
        trend = "improving" if recent > earlier + 0.05 else "declining" if recent < earlier - 0.05 else "stable"
    else:
        trend = "stable"
    render_insight_card(
        ticker, name, avg, pos, neg, neu, total, days, trend,
        confidence_level=conf_level, trend_score=float(t_score) if t_score is not None else None,
        price_momentum=str(p_momentum) if p_momentum else None,
        rec_score=float(rec_score) if rec_score is not None else None,
        rec_label=str(rec_label) if rec_label else None,
    )

    # ── 6-Month Trend Graph
    st.markdown('<div class="section-label" style="margin-top:2rem;">6-Month Price Trend</div>', unsafe_allow_html=True)
    hist_6m = fetch_price_history(ticker, period="6mo", interval="1d")
    if hist_6m is not None and not hist_6m.empty:
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(
            x=hist_6m.index, y=hist_6m["Close"],
            mode="lines",
            line=dict(color="#a855f7", width=2.5),
            fill="tozeroy", fillcolor="rgba(168,85,247,0.08)",
            name="Daily Close",
            hovertemplate="<b>%{x|%d %b %Y}</b><br>Close: %{y:.2f}<extra></extra>"
        ))
        
        # Add 50-day moving average
        if len(hist_6m) >= 50:
            sma_50 = hist_6m["Close"].rolling(window=50).mean()
            fig_trend.add_trace(go.Scatter(
                x=hist_6m.index, y=sma_50,
                mode="lines",
                line=dict(color="#f97316", width=1.5, dash="dot"),
                name="50d SMA",
                hovertemplate="<b>%{x|%d %b %Y}</b><br>50d SMA: %{y:.2f}<extra></extra>"
            ))
            
        apply_chart_theme(fig_trend, f"{name} — 6-Month Price Trend", height=350)
        fig_trend.update_layout(
            xaxis=dict(tickformat="%b %Y"),
            yaxis=dict(tickprefix="₹" if ".NS" in ticker else "$", tickfont=dict(family="Fira Code",size=10))
        )
        st.plotly_chart(fig_trend, use_container_width=True, config={"displayModeBar":False})
    else:
        st.caption(f"Historical price trend unavailable for {ticker}.")

    # ── Correlation
    st.divider()
    st.markdown('<div class="section-label">Price — Sentiment Correlation</div>', unsafe_allow_html=True)
    corr_data = fetch_correlation(ticker, days)
    if corr_data:
        cv   = corr_data.get("correlation", 0.0)
        dp   = corr_data.get("data_points", 0)
        interp = corr_data.get("interpretation", "—")
        cc1,cc2,cc3 = st.columns(3)
        cc1.metric("Pearson Correlation", f"{cv:+.4f}")
        cc2.metric("Data Points", dp)
        with cc3:
            if cv > 0.3:   st.success(interp)
            elif cv < -0.3: st.error(interp)
            else:            st.warning(interp)
    else:
        st.caption("Not enough alignment data yet. Run more pipeline cycles.")

# ─────────────────────────────────────────────
# Tab 3 — Signals
# ─────────────────────────────────────────────
def render_signals():
    st.markdown('<div class="section-label">Trading Signals — Sentiment-Driven</div>', unsafe_allow_html=True)
    render_legend()

    data = fetch_signals()
    if not data or not data.get("signals"):
        st.info("No signals yet. Run the pipeline to generate sentiment-based signals.")
        return

    signals = data["signals"]
    df = pd.DataFrame(signals)

    buy  = len(df[df["signal"]=="BUY"])
    sell = len(df[df["signal"]=="SELL"])
    hold = len(df[df["signal"]=="HOLD"])

    k1,k2,k3,k4 = st.columns(4)
    k1.metric("Buy Signals",  buy)
    k2.metric("Sell Signals", sell)
    k3.metric("Hold Signals", hold)
    k4.metric("Total",        len(signals))

    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        fig = go.Figure(go.Bar(
            x=["BUY","SELL","HOLD"], y=[buy,sell,hold],
            marker=dict(color=["#22c55e","#ef4444","#fbbf24"],line=dict(color="#070c18",width=0)),
            text=[buy,sell,hold], textposition="outside",
            textfont=dict(family="JetBrains Mono",size=12,color="#94a3b8"),
        ))
        apply_chart_theme(fig, "Signal Distribution", height=320)
        fig.update_layout(bargap=0.5,showlegend=False)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

    with col_b:
        fig2 = go.Figure(go.Histogram(
            x=[s.get("confidence",0) for s in signals], nbinsx=10,
            marker=dict(color="#3b82f6",line=dict(color="#070c18",width=1.5)),opacity=0.85,
        ))
        apply_chart_theme(fig2, "Confidence Score Distribution", height=320)
        fig2.update_layout(xaxis_title="Confidence (%)",yaxis_title="Count",bargap=0.1)
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar":False})

    st.divider()
    st.markdown('<div class="section-label">Active Signals Table</div>', unsafe_allow_html=True)
    display_cols = [c for c in ["ticker","name","sector","signal","confidence_level","confidence","sentiment","trend_score","recommendation_score","news_count"] if c in df.columns]
    display_df = df[display_cols].copy().sort_values("confidence", ascending=False)
    if "confidence" in display_df.columns:
        display_df["confidence"] = display_df["confidence"].apply(lambda x: f"{x:.1f}%")
    if "sentiment" in display_df.columns:
        display_df["sentiment"] = display_df["sentiment"].apply(lambda x: f"{x:+.4f}")
    if "trend_score" in display_df.columns:
        display_df["trend_score"] = display_df["trend_score"].apply(lambda x: f"{x:+.3f}" if x is not None else "—")
    if "recommendation_score" in display_df.columns:
        display_df["recommendation_score"] = display_df["recommendation_score"].apply(lambda x: f"{x:+.3f}" if x is not None else "—")
    display_df.columns = [c.replace("_", " ").title() for c in display_df.columns]
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    st.caption("Signals are generated for educational analysis only. Not financial advice.")

# ─────────────────────────────────────────────
# Tab 4 — Radar & Correlation
# ─────────────────────────────────────────────
def render_radar():
    st.markdown('<div class="section-label">Sentiment Anomaly Radar</div>', unsafe_allow_html=True)
    st.caption("Detects massive sudden spikes in news volume or extreme 24h sentiment shifts.")
    
    options = get_ticker_options()
    all_tickers = [o[1] for o in options]
    
    anomalies = []
    correlations = []
    
    with st.spinner("Scanning market for anomalies..."):
        for ticker in all_tickers:
            # 1. Anomaly Detection
            sentiment_data = fetch_sentiment(ticker, days=7)
            if sentiment_data and sentiment_data.get("data"):
                df = pd.DataFrame(sentiment_data["data"])
                df["date"] = pd.to_datetime(df["timestamp"], format="ISO8601").dt.date
                daily = df.groupby("date").agg({"news_count": "sum", "avg_sentiment": "mean"}).reset_index()
                
                if len(daily) >= 2:
                    today = daily.iloc[-1]
                    history = daily.iloc[:-1]
                    
                    avg_vol = history["news_count"].mean()
                    avg_sent = history["avg_sentiment"].mean()
                    
                    # Detect volume spike
                    if avg_vol > 0 and today["news_count"] > avg_vol * 2.0 and today["news_count"] >= 5:
                        anomalies.append({
                            "ticker": ticker, "type": "Volume Spike", 
                            "details": f"News volume jumped to {int(today['news_count'])} articles today (7d avg: {avg_vol:.1f})",
                            "severity": "high"
                        })
                    
                    # Detect sentiment swing
                    if abs(today["avg_sentiment"] - avg_sent) > 0.4:
                        swing_dir = "Drop" if today["avg_sentiment"] < avg_sent else "Surge"
                        anomalies.append({
                            "ticker": ticker, "type": f"Sentiment {swing_dir}", 
                            "details": f"Sentiment shifted drastically from {avg_sent:+.2f} (7d avg) to {today['avg_sentiment']:+.2f} today",
                            "severity": "critical" if swing_dir == "Drop" else "medium"
                        })
            
            # 2. Correlation
            corr_data = fetch_correlation(ticker, days=7)
            if corr_data and "correlation" in corr_data:
                correlations.append({
                    "ticker": ticker, 
                    "correlation": corr_data["correlation"]
                })
                
    if not anomalies:
        st.success("✅ Market is stable. No massive sentiment swings or unusual news volumes detected today.")
    else:
        for anom in anomalies:
            color = "#ef4444" if anom["severity"] == "critical" else ("#f59e0b" if anom["severity"] == "high" else "#10b981")
            st.markdown(f"""
            <div style='background:rgba(9,9,11,0.6);border-left:4px solid {color};padding:1rem;margin-bottom:1rem;border-radius:4px;'>
                <div style='font-weight:700;font-size:1.1rem;color:#f8fafc;margin-bottom:0.25rem;'>
                    {anom['ticker']} &mdash; {anom['type']}
                </div>
                <div style='color:#94a3b8;font-size:0.9rem;'>
                    {anom['details']}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
    st.divider()
    st.markdown('<div class="section-label">Price vs. Sentiment Correlation (7-Day)</div>', unsafe_allow_html=True)
    st.caption("Measures how closely a stock's price movements follow its news sentiment. (+1.0 = Perfect Follower, -1.0 = Inverse).")
    
    if correlations:
        corr_df = pd.DataFrame(correlations).sort_values("correlation", ascending=True)
        colors = ["#10b981" if c > 0 else "#ef4444" for c in corr_df["correlation"]]
        
        fig = go.Figure(go.Bar(
            y=corr_df["ticker"], x=corr_df["correlation"],
            orientation="h",
            marker=dict(color=colors, line=dict(color="rgba(0,0,0,0)",width=0)),
            text=[f"{c:+.2f}" for c in corr_df["correlation"]],
            textposition="auto",
            textfont=dict(family="Fira Code",size=11,color="#f8fafc")
        ))
        apply_chart_theme(fig, "", height=380)
        fig.add_vline(x=0, line=dict(color="rgba(255,255,255,0.1)",width=1,dash="dot"))
        fig.update_layout(xaxis_range=[-1.0, 1.0], xaxis_title="Correlation Coefficient (r)", margin=dict(t=10, b=10))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
    else:
        st.info("Not enough data to calculate correlations yet. The backend aggregation pipeline needs at least 2 data points.")

# ─────────────────────────────────────────────
# Tab 5 — News Feed
# ─────────────────────────────────────────────
def render_news_feed():
    st.markdown('<div class="section-label">Latest Financial News</div>', unsafe_allow_html=True)

    options = get_ticker_options()
    labels  = ["All Tickers"] + [o[0] for o in options]
    tickers = [None] + [o[1] for o in options]

    c1,c2,c3 = st.columns([3,1,1])
    with c1:
        selected = st.selectbox("Filter by Stock", labels, index=0)
    with c2:
        news_limit = st.slider("Articles", 10,100,30,step=10)
    with c3:
        days_filter = st.slider("Days back", 1,30,7)

    ticker_filter = tickers[labels.index(selected)]
    news_data = fetch_news(ticker=ticker_filter, limit=news_limit, days=days_filter)

    if not news_data or not news_data.get("data"):
        st.info("No news articles found. Run the pipeline to fetch news.")
        return

    articles = news_data["data"]
    st.caption(f"Showing {len(articles)} of {news_data.get('total',0)} articles")
    st.divider()

    for art in articles:
        label  = art.get("sentiment_label","neutral")
        score  = art.get("sentiment_score",0.0) or 0.0
        source = art.get("source","Unknown")
        weight = art.get("source_weight",0.85)
        ticker = art.get("ticker") or "—"
        ts     = fmt_ist(art.get("timestamp",""))
        url    = art.get("url","")

        if label == "positive":
            score_class, score_prefix = "news-score-pos","+"
        elif label == "negative":
            score_class, score_prefix = "news-score-neg",""
        else:
            score_class, score_prefix = "news-score-neu",""

        headline_html = f'<a href="{url}" target="_blank" style="color:#e2e8f0;text-decoration:none">{art.get("headline","")}</a>' if url else art.get("headline","")

        st.markdown(f"""
        <div class="news-card">
            <div class="news-headline">{headline_html}</div>
            <div class="news-meta">
                <span class="source-badge">{source.upper()} {weight:.2f}</span>
                &nbsp;&bull;&nbsp;
                <span style="color:#1d4ed8;font-weight:500">{ticker}</span>
                &nbsp;&bull;&nbsp;
                <span class="{score_class}">{label.upper()} &nbsp;{score_prefix}{score:.4f}</span>
                &nbsp;&bull;&nbsp;
                <span style="color:#334155">{ts}</span>
                {"&nbsp;&bull;&nbsp;<a href='" + url + "' target='_blank' style='color:#3b82f6;font-size:0.72rem'>View Article</a>" if url else ""}
            </div>
        </div>
        """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
def main():
    render_sidebar()

    st.markdown("""
    <div class="hero-container">
        <div class="hero-badge">Next-Gen Analytics</div>
        <div class="hero-title">FinPulse Intelligence</div>
        <div class="hero-subtitle">
            Real-Time Financial News Sentiment &nbsp;&middot;&nbsp; Powered by FinBERT AI &nbsp;&middot;&nbsp; Hybrid RSS + NewsAPI Streaming
        </div>
    </div>
    """, unsafe_allow_html=True)

    tabs = st.tabs(["Overview", "Ticker Analysis", "Signals", "News Feed"])
    with tabs[0]: 
        render_overview()
        st.write("---")
        render_radar()
    with tabs[1]: render_ticker_analysis()
    with tabs[2]: render_signals()
    with tabs[3]: render_news_feed()

    st.divider()
    c1,c2,c3 = st.columns(3)
    with c1:
        st.markdown("""<div style="font-size:0.78rem;color:#334155;line-height:2">
        <b style="color:#475569">Universe</b><br>
        10 stocks across 5 sectors<br>
        8 Indian (NSE) + 2 Global<br>
        Real-time via RSS + NewsAPI
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown("""<div style="font-size:0.78rem;color:#334155;line-height:2">
        <b style="color:#475569">Pipeline</b><br>
        Hybrid RSS + NewsAPI fetch<br>
        FinBERT sentiment scoring<br>
        Source-weighted aggregation
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown("""<div style="font-size:0.78rem;color:#334155;line-height:2">
        <b style="color:#475569">Disclaimer</b><br>
        Educational analytics tool only.<br>
        Not investment advice.<br>
        Always consult a financial advisor.
        </div>""", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
