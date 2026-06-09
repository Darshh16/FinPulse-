import streamlit as st
import sys
from pathlib import Path

# Add project root to Python path BEFORE any imports from config
ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import requests
import logging
from config.settings import settings

logger = logging.getLogger(__name__)

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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Global reset ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    color: #e2e8f0;
}

.main .block-container {
    padding: 2rem 2.5rem 3rem;
    max-width: 1400px;
}

/* ── Background ── */
.stApp {
    background: #070c18;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #0b1120;
    border-right: 1px solid rgba(99,179,237,0.12);
}
[data-testid="stSidebar"] .block-container {
    padding: 1.5rem 1rem;
}

/* ── Headings ── */
h1 { font-size: 1.9rem !important; font-weight: 700 !important; letter-spacing: -0.5px; color: #f0f6ff !important; }
h2 { font-size: 1.3rem !important; font-weight: 600 !important; color: #cbd5e1 !important; }
h3 { font-size: 1.05rem !important; font-weight: 600 !important; color: #94a3b8 !important; letter-spacing: 0.3px; }

/* ── Metric cards ── */
[data-testid="stMetric"] {
    background: linear-gradient(145deg, #0f1829 0%, #111d35 100%);
    border: 1px solid rgba(99,179,237,0.12);
    border-radius: 14px;
    padding: 1.1rem 1.3rem;
    box-shadow: 0 4px 24px rgba(0,0,0,0.35);
    transition: border-color 0.2s;
}
[data-testid="stMetric"]:hover {
    border-color: rgba(99,179,237,0.3);
}
[data-testid="stMetricLabel"] {
    font-size: 0.72rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #64748b !important;
}
[data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 1.6rem !important;
    font-weight: 600 !important;
    color: #e2e8f0 !important;
}
[data-testid="stMetricDelta"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.8rem !important;
}

/* ── Tabs ── */
[data-testid="stTabs"] [role="tablist"] {
    background: #0b1120;
    border-radius: 10px;
    padding: 4px;
    border: 1px solid rgba(99,179,237,0.1);
    gap: 2px;
}
[data-testid="stTabs"] [role="tab"] {
    font-size: 0.82rem;
    font-weight: 500;
    letter-spacing: 0.04em;
    color: #64748b;
    border-radius: 7px;
    padding: 0.5rem 1.1rem;
    border: none;
    background: transparent;
    transition: all 0.2s;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    background: linear-gradient(135deg, #1e3a5f 0%, #1a3252 100%);
    color: #93c5fd;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}
[data-testid="stTabs"] [role="tab"]:hover:not([aria-selected="true"]) {
    color: #94a3b8;
    background: rgba(255,255,255,0.04);
}

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%);
    color: #e2e8f0;
    border: none;
    border-radius: 8px;
    padding: 0.45rem 1.2rem;
    font-size: 0.82rem;
    font-weight: 500;
    letter-spacing: 0.04em;
    transition: all 0.2s;
    box-shadow: 0 2px 8px rgba(29,78,216,0.35);
}
.stButton > button:hover {
    background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
    transform: translateY(-1px);
    box-shadow: 0 4px 16px rgba(29,78,216,0.45);
}

/* ── Inputs ── */
.stTextInput input, .stSelectbox select {
    background: #0f1829 !important;
    border: 1px solid rgba(99,179,237,0.2) !important;
    border-radius: 8px !important;
    color: #e2e8f0 !important;
    font-family: 'Inter', sans-serif !important;
}
.stTextInput input:focus {
    border-color: rgba(99,179,237,0.5) !important;
    box-shadow: 0 0 0 3px rgba(99,179,237,0.1) !important;
}

/* ── Slider ── */
.stSlider [data-baseweb="slider"] { padding-top: 0.3rem; }

/* ── Divider ── */
hr {
    border: none;
    border-top: 1px solid rgba(99,179,237,0.08);
    margin: 1.5rem 0;
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
    border: 1px solid rgba(99,179,237,0.1);
    border-radius: 10px;
    overflow: hidden;
}
[data-testid="stDataFrame"] table { font-size: 0.82rem; }
[data-testid="stDataFrame"] thead th {
    background: #0f1829 !important;
    color: #64748b !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-weight: 600 !important;
}
[data-testid="stDataFrame"] tbody tr:hover { background: rgba(99,179,237,0.05) !important; }

/* ── Info / warning boxes ── */
[data-testid="stAlert"] {
    border-radius: 10px;
    border: none;
    font-size: 0.85rem;
}

/* ── Sidebar metrics ── */
.sidebar-stat {
    background: #0f1829;
    border: 1px solid rgba(99,179,237,0.1);
    border-radius: 10px;
    padding: 0.8rem 1rem;
    margin-bottom: 0.6rem;
}
.sidebar-stat-label {
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #475569;
    font-weight: 500;
    margin-bottom: 0.2rem;
}
.sidebar-stat-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.25rem;
    font-weight: 600;
    color: #e2e8f0;
}

/* ── Signal badges ── */
.signal-buy   { color: #34d399; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
.signal-sell  { color: #f87171; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
.signal-hold  { color: #fbbf24; font-weight: 700; font-family: 'JetBrains Mono', monospace; }

/* ── News cards ── */
.news-card {
    background: #0f1829;
    border: 1px solid rgba(99,179,237,0.1);
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.7rem;
    transition: border-color 0.2s;
}
.news-card:hover { border-color: rgba(99,179,237,0.28); }
.news-headline { font-size: 0.9rem; font-weight: 500; color: #e2e8f0; line-height: 1.45; }
.news-meta { font-size: 0.74rem; color: #475569; margin-top: 0.3rem; }
.news-score-pos { color: #34d399; font-family: 'JetBrains Mono', monospace; font-size: 0.82rem; font-weight: 600; }
.news-score-neg { color: #f87171; font-family: 'JetBrains Mono', monospace; font-size: 0.82rem; font-weight: 600; }
.news-score-neu { color: #94a3b8; font-family: 'JetBrains Mono', monospace; font-size: 0.82rem; font-weight: 600; }

/* ── Section labels ── */
.section-label {
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #3b82f6;
    margin-bottom: 0.8rem;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid rgba(59,130,246,0.2);
}

/* ── Status bar ── */
.status-bar {
    background: #0b1120;
    border: 1px solid rgba(99,179,237,0.08);
    border-radius: 8px;
    padding: 0.5rem 1rem;
    font-size: 0.75rem;
    color: #475569;
    display: flex;
    align-items: center;
    gap: 1rem;
}
.status-dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    background: #34d399;
    display: inline-block;
    margin-right: 5px;
    box-shadow: 0 0 6px #34d399;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────
API_URL = f"http://localhost:{settings.api_port}/api/v1"

CHART_THEME = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(11,17,32,0)",
    plot_bgcolor="rgba(15,24,41,0.6)",
    font=dict(family="Inter, sans-serif", color="#94a3b8", size=12),
    margin=dict(l=10, r=10, t=40, b=10),
    xaxis=dict(gridcolor="rgba(99,179,237,0.06)", linecolor="rgba(99,179,237,0.1)"),
    yaxis=dict(gridcolor="rgba(99,179,237,0.06)", linecolor="rgba(99,179,237,0.1)"),
    hoverlabel=dict(bgcolor="#0f1829", bordercolor="rgba(99,179,237,0.3)", font_size=12),
)

SENTIMENT_SCALE = [
    [0.0,  "#ef4444"],
    [0.5,  "#fbbf24"],
    [1.0,  "#22c55e"],
]

# ─────────────────────────────────────────────
# Data fetchers (cached)
# ─────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_dashboard_summary():
    try:
        r = requests.get(f"{API_URL}/dashboard-summary", timeout=5)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        logger.error(f"Error fetching dashboard summary: {e}")
    return None


@st.cache_data(ttl=300)
def fetch_news(ticker=None, limit=50, days=7):
    try:
        params = {"limit": limit, "days": days}
        if ticker:
            params["ticker"] = ticker
        r = requests.get(f"{API_URL}/news", params=params, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        logger.error(f"Error fetching news: {e}")
    return None


@st.cache_data(ttl=300)
def fetch_sentiment(ticker, days=7):
    try:
        r = requests.get(f"{API_URL}/sentiment/{ticker}", params={"days": days}, timeout=5)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        logger.error(f"Error fetching sentiment: {e}")
    return None


@st.cache_data(ttl=300)
def fetch_correlation(ticker, days=7):
    try:
        r = requests.get(f"{API_URL}/correlation/{ticker}", params={"days": days}, timeout=5)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        logger.error(f"Error fetching correlation: {e}")
    return None


@st.cache_data(ttl=300)
def fetch_signals():
    try:
        r = requests.get(f"{API_URL}/signals", timeout=5)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        logger.error(f"Error fetching signals: {e}")
    return None


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def sentiment_color(score):
    if score > 0.2:   return "#22c55e"
    if score < -0.2:  return "#ef4444"
    return "#fbbf24"

def signal_color(sig):
    return {"BUY": "#22c55e", "SELL": "#ef4444", "HOLD": "#fbbf24"}.get(sig, "#94a3b8")

def apply_chart_theme(fig, title="", height=380):
    fig.update_layout(
        **CHART_THEME,
        title=dict(text=title, font=dict(size=13, color="#94a3b8"), x=0),
        height=height,
    )
    return fig


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
            data = summary.get("summary", {})
            total_news    = data.get("total_news_24h", 0)
            total_tickers = data.get("total_tickers_24h", 0)
            avg_sent      = data.get("avg_sentiment_24h", 0.0)

            st.markdown(f"""
            <div class="sidebar-stat">
                <div class="sidebar-stat-label">Articles (24h)</div>
                <div class="sidebar-stat-value">{total_news:,}</div>
            </div>
            <div class="sidebar-stat">
                <div class="sidebar-stat-label">Active Tickers</div>
                <div class="sidebar-stat-value">{total_tickers}</div>
            </div>
            <div class="sidebar-stat">
                <div class="sidebar-stat-label">Market Sentiment</div>
                <div class="sidebar-stat-value" style="color:{sentiment_color(avg_sent)}">{avg_sent:+.3f}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.caption("API unavailable")

        st.divider()
        st.markdown('<div class="section-label">Controls</div>', unsafe_allow_html=True)
        if st.button("Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.divider()
        st.markdown('<div class="section-label">Data Sources</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style='font-size:0.78rem;color:#475569;line-height:2'>
        News &nbsp;&nbsp;&mdash;&nbsp; NewsAPI<br>
        Model &nbsp;&mdash;&nbsp; FinBERT (ProsusAI)<br>
        Prices &nbsp;&mdash;&nbsp; Yahoo Finance<br>
        Store &nbsp;&nbsp;&mdash;&nbsp; PostgreSQL
        </div>
        """, unsafe_allow_html=True)

        st.divider()
        st.markdown(
            f'<div style="font-size:0.7rem;color:#334155">'
            f'<span class="status-dot"></span>API Online &nbsp;|&nbsp; '
            f'{datetime.now().strftime("%H:%M:%S")}</div>',
            unsafe_allow_html=True
        )


# ─────────────────────────────────────────────
# Tab 1 — Overview
# ─────────────────────────────────────────────
def render_overview():
    st.markdown('<div class="section-label">Market Overview — Last 24 Hours</div>', unsafe_allow_html=True)

    summary = fetch_dashboard_summary()
    if summary and "summary" in summary:
        d = summary["summary"]
        avg_sent = d.get("avg_sentiment_24h", 0.0)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Articles", f"{d.get('total_news_24h', 0):,}")
        c2.metric("Tickers Tracked", d.get("total_tickers_24h", 0))
        c3.metric("Market Sentiment", f"{avg_sent:+.3f}")
        c4.metric("Last Refresh", datetime.now().strftime("%H:%M:%S"))
    else:
        st.info("No data available. Start the pipeline to populate the dashboard.")
        return

    st.divider()

    if summary and "top_tickers" in summary and summary["top_tickers"]:
        df = pd.DataFrame(summary["top_tickers"])
        st.markdown('<div class="section-label">Top Tickers by News Volume</div>', unsafe_allow_html=True)

        col_chart, col_table = st.columns([3, 2])

        with col_chart:
            fig = go.Figure(go.Bar(
                x=df.head(12)["ticker"],
                y=df.head(12)["news_count"],
                marker=dict(
                    color=df.head(12)["avg_sentiment"],
                    colorscale=SENTIMENT_SCALE,
                    cmin=-1, cmax=1,
                    colorbar=dict(
                        title=dict(text="Sentiment", font=dict(size=11)),
                        thickness=12,
                        len=0.7,
                        tickfont=dict(family="JetBrains Mono", size=10),
                    ),
                    line=dict(color="rgba(0,0,0,0)", width=0),
                ),
                text=df.head(12)["news_count"],
                textposition="outside",
                textfont=dict(size=10, color="#94a3b8", family="JetBrains Mono"),
            ))
            apply_chart_theme(fig, "Article Volume by Ticker", height=360)
            fig.update_layout(
                xaxis=dict(tickfont=dict(family="JetBrains Mono", size=11)),
                bargap=0.35,
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        with col_table:
            display = df[["ticker", "news_count", "avg_sentiment"]].copy()
            display.columns = ["Ticker", "Articles", "Sentiment"]
            display["Sentiment"] = display["Sentiment"].apply(lambda x: f"{x:+.4f}")
            st.dataframe(display, use_container_width=True, hide_index=True, height=360)
    else:
        st.info("Run the pipeline to populate ticker data.")


# ─────────────────────────────────────────────
# Tab 2 — Ticker Analysis
# ─────────────────────────────────────────────
def render_ticker_analysis():
    st.markdown('<div class="section-label">Ticker Deep Dive</div>', unsafe_allow_html=True)

    c1, c2 = st.columns([2, 1])
    with c1:
        ticker = st.text_input("Stock Ticker", "AAPL", placeholder="e.g. AAPL, MSFT, TSLA").upper().strip()
    with c2:
        days = st.slider("Lookback (days)", 1, 30, 7)

    if not ticker:
        return

    sentiment_data = fetch_sentiment(ticker, days)

    if not sentiment_data or not sentiment_data.get("data"):
        st.warning(f"No sentiment data found for **{ticker}**. Make sure the pipeline has processed articles mentioning this company.")
        return

    df = pd.DataFrame(sentiment_data["data"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], format='ISO8601')
    df = df.sort_values("timestamp")

    # KPI row
    pos  = int(df["positive_count"].sum())
    neg  = int(df["negative_count"].sum())
    neu  = int(df["neutral_count"].sum())
    avg  = float(df["avg_sentiment"].mean())
    total = int(df["news_count"].sum())

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Articles", f"{total:,}")
    k2.metric("Avg Sentiment", f"{avg:+.3f}")
    k3.metric("Positive", pos)
    k4.metric("Negative", neg)
    k5.metric("Neutral", neu)

    st.divider()

    left, right = st.columns(2)

    with left:
        # Sentiment trend area chart
        sc = [sentiment_color(v) for v in df["avg_sentiment"]]
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["timestamp"],
            y=df["avg_sentiment"],
            mode="lines+markers",
            line=dict(color="#3b82f6", width=2.5),
            marker=dict(color=sc, size=7, line=dict(color="#070c18", width=1.5)),
            fill="tozeroy",
            fillcolor="rgba(59,130,246,0.08)",
            hovertemplate="<b>%{x|%b %d %H:%M}</b><br>Sentiment: <b>%{y:+.4f}</b><extra></extra>",
        ))
        fig.add_hline(y=0, line=dict(color="rgba(255,255,255,0.08)", width=1, dash="dot"))
        apply_chart_theme(fig, f"{ticker} — Sentiment Trend")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with right:
        # Distribution donut
        fig2 = go.Figure(go.Pie(
            labels=["Positive", "Negative", "Neutral"],
            values=[pos, neg, neu],
            hole=0.62,
            marker=dict(
                colors=["#22c55e", "#ef4444", "#475569"],
                line=dict(color="#070c18", width=3),
            ),
            textinfo="label+percent",
            textfont=dict(size=11, family="Inter"),
            hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Share: %{percent}<extra></extra>",
        ))
        fig2.update_layout(
            **CHART_THEME,
            title=dict(text=f"{ticker} — Sentiment Distribution", font=dict(size=13, color="#94a3b8"), x=0),
            height=380,
            showlegend=False,
            annotations=[dict(
                text=f"<b>{avg:+.2f}</b>",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=22, color=sentiment_color(avg), family="JetBrains Mono"),
            )],
        )
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    # Price correlation section
    st.divider()
    st.markdown('<div class="section-label">Price — Sentiment Correlation</div>', unsafe_allow_html=True)
    corr_data = fetch_correlation(ticker, days)
    if corr_data:
        cv = corr_data.get("correlation", 0.0)
        dp = corr_data.get("data_points", 0)
        interp = corr_data.get("interpretation", "—")

        cc1, cc2, cc3 = st.columns(3)
        cc1.metric("Pearson Correlation", f"{cv:+.4f}")
        cc2.metric("Data Points", dp)
        with cc3:
            if cv > 0.3:
                st.success(interp)
            elif cv < -0.3:
                st.error(interp)
            else:
                st.warning(interp)
    else:
        st.caption("Not enough alignment data to compute correlation. Run more pipeline cycles.")


# ─────────────────────────────────────────────
# Tab 3 — Signals
# ─────────────────────────────────────────────
def render_signals():
    st.markdown('<div class="section-label">Trading Signals — Sentiment-Driven (Educational Only)</div>', unsafe_allow_html=True)

    data = fetch_signals()

    if not data or not data.get("signals"):
        st.info("No signals available yet. Run the data pipeline to generate sentiment-based signals.")
        return

    signals = data["signals"]
    df = pd.DataFrame(signals)

    buy  = len(df[df["signal"] == "BUY"])
    sell = len(df[df["signal"] == "SELL"])
    hold = len(df[df["signal"] == "HOLD"])

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Buy Signals",  buy)
    k2.metric("Sell Signals", sell)
    k3.metric("Hold Signals", hold)
    k4.metric("Total Signals", len(signals))

    st.divider()

    col_a, col_b = st.columns(2)

    with col_a:
        fig = go.Figure(go.Bar(
            x=["BUY", "SELL", "HOLD"],
            y=[buy, sell, hold],
            marker=dict(
                color=["#22c55e", "#ef4444", "#fbbf24"],
                line=dict(color="#070c18", width=0),
            ),
            text=[buy, sell, hold],
            textposition="outside",
            textfont=dict(family="JetBrains Mono", size=12, color="#94a3b8"),
        ))
        apply_chart_theme(fig, "Signal Distribution", height=340)
        fig.update_layout(bargap=0.5, showlegend=False)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col_b:
        confidences = [s.get("confidence", 0) for s in signals]
        fig2 = go.Figure(go.Histogram(
            x=confidences,
            nbinsx=12,
            marker=dict(
                color="#3b82f6",
                line=dict(color="#070c18", width=1.5),
            ),
            opacity=0.85,
        ))
        apply_chart_theme(fig2, "Confidence Score Distribution", height=340)
        fig2.update_layout(
            xaxis_title="Confidence (%)",
            yaxis_title="Count",
            bargap=0.1,
        )
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    st.divider()
    st.markdown('<div class="section-label">Active Signals Table</div>', unsafe_allow_html=True)

    display_df = df[["ticker", "signal", "strength", "confidence", "sentiment", "news_count"]].copy()
    display_df = display_df.sort_values("confidence", ascending=False)
    display_df.columns = ["Ticker", "Signal", "Strength", "Confidence (%)", "Sentiment", "Articles"]
    display_df["Strength"]       = display_df["Strength"].apply(lambda x: f"{x:.4f}")
    display_df["Confidence (%)"] = display_df["Confidence (%)"].apply(lambda x: f"{x:.1f}%")
    display_df["Sentiment"]      = display_df["Sentiment"].apply(lambda x: f"{x:+.4f}")
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.divider()
    st.caption("Disclaimer: These signals are generated for educational analysis only and do not constitute financial advice.")




# ─────────────────────────────────────────────
# Tab 5 — Market Insights
# ─────────────────────────────────────────────
def render_insights():
    st.markdown('<div class="section-label">Market Analytics</div>', unsafe_allow_html=True)

    summary = fetch_dashboard_summary()
    if not summary:
        st.info("No market data available yet. Run the pipeline to fetch data.")
        return

    data         = summary.get("summary", {})
    top_tickers  = summary.get("top_tickers", [])

    c1, c2, c3, c4 = st.columns(4)
    avg_sent = data.get("avg_sentiment_24h", 0.0)
    c1.metric("Articles (24h)",   f"{data.get('total_news_24h', 0):,}")
    c2.metric("Unique Tickers",   data.get("total_tickers_24h", 0))
    c3.metric("Market Sentiment", f"{avg_sent:+.3f}")
    c4.metric("Refreshed",        datetime.now().strftime("%H:%M"))

    st.divider()

    if not top_tickers:
        st.info("No ticker data available yet.")
        return

    df = pd.DataFrame(top_tickers)
    col_left, col_right = st.columns(2)

    with col_left:
        sentiments = df["avg_sentiment"].tolist()
        fig = go.Figure(go.Box(
            y=sentiments,
            name="Sentiment Score",
            marker=dict(color="#3b82f6", size=6),
            line=dict(color="#3b82f6", width=2),
            fillcolor="rgba(59,130,246,0.12)",
            boxmean="sd",
            hovertemplate="Value: %{y:+.4f}<extra></extra>",
        ))
        apply_chart_theme(fig, "Sentiment Score Distribution (All Tickers)", height=360)
        fig.update_layout(showlegend=False, xaxis=dict(showticklabels=False))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col_right:
        fig2 = go.Figure(go.Bar(
            x=df.head(12)["ticker"],
            y=df.head(12)["news_count"],
            marker=dict(
                color=df.head(12)["avg_sentiment"],
                colorscale=SENTIMENT_SCALE,
                cmin=-1, cmax=1,
                line=dict(color="#070c18", width=0),
            ),
            text=df.head(12)["news_count"],
            textposition="outside",
            textfont=dict(family="JetBrains Mono", size=10, color="#94a3b8"),
        ))
        apply_chart_theme(fig2, "Article Count by Ticker (Color = Sentiment)", height=360)
        fig2.update_layout(bargap=0.35, showlegend=False)
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    st.divider()

    # Scatter: sentiment vs volume
    fig3 = go.Figure(go.Scatter(
        x=df["avg_sentiment"],
        y=df["news_count"],
        mode="markers+text",
        text=df["ticker"],
        textposition="top center",
        textfont=dict(family="JetBrains Mono", size=10, color="#64748b"),
        marker=dict(
            size=df["news_count"].apply(lambda n: max(8, min(30, n * 1.5))),
            color=df["avg_sentiment"],
            colorscale=SENTIMENT_SCALE,
            cmin=-1, cmax=1,
            line=dict(color="#070c18", width=1.5),
            opacity=0.85,
        ),
        hovertemplate="<b>%{text}</b><br>Sentiment: %{x:+.4f}<br>Articles: %{y}<extra></extra>",
    ))
    fig3.add_vline(x=0, line=dict(color="rgba(255,255,255,0.07)", width=1, dash="dot"))
    apply_chart_theme(fig3, "Sentiment vs. News Volume — Bubble Chart", height=420)
    fig3.update_layout(
        xaxis_title="Avg Sentiment Score",
        yaxis_title="Article Count",
    )
    st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})


# ─────────────────────────────────────────────
# Tab 6 — News Feed
# ─────────────────────────────────────────────
def render_news_feed():
    st.markdown('<div class="section-label">Latest Financial News</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        ticker_input = st.text_input("Filter by Ticker", "", placeholder="Leave blank for all tickers").upper().strip()
    with c2:
        news_limit = st.slider("Articles to show", 10, 100, 30, step=10)
    with c3:
        days_filter = st.slider("Days back", 1, 30, 7)

    ticker_filter = ticker_input if ticker_input else None
    news_data = fetch_news(ticker=ticker_filter, limit=news_limit, days=days_filter)

    if not news_data or not news_data.get("data"):
        st.info("No news articles found. Run the pipeline to fetch news.")
        return

    articles = news_data["data"]
    st.caption(f"Showing {len(articles)} of {news_data.get('total', 0)} articles")
    st.divider()

    for art in articles:
        label  = art.get("sentiment_label", "neutral")
        score  = art.get("sentiment_score", 0.0)
        ticker = art.get("ticker") or "—"
        source = art.get("source", "Unknown")
        ts     = art.get("timestamp", "")

        if label == "positive":
            score_class, score_prefix = "news-score-pos", "+"
        elif label == "negative":
            score_class, score_prefix = "news-score-neg", ""
        else:
            score_class, score_prefix = "news-score-neu", ""

        st.markdown(f"""
        <div class="news-card">
            <div class="news-headline">{art.get('headline', '')}</div>
            <div class="news-meta">
                <span style="color:#334155">{source}</span>
                &nbsp;&middot;&nbsp;
                <span style="color:#1d4ed8;font-weight:500">{ticker}</span>
                &nbsp;&middot;&nbsp;
                <span class="{score_class}">{label.upper()} &nbsp; {score_prefix}{score:.4f}</span>
                &nbsp;&middot;&nbsp;
                <span style="color:#334155">{str(ts)[:16].replace('T',' ')}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
def main():
    render_sidebar()

    # Header
    st.markdown("""
    <div style="margin-bottom:1.5rem">
        <h1 style="margin-bottom:0.1rem">FinPulse</h1>
        <div style="font-size:0.82rem;color:#475569;letter-spacing:0.04em">
            Real-Time Financial News Sentiment Intelligence &nbsp;&middot;&nbsp; Powered by FinBERT
        </div>
    </div>
    """, unsafe_allow_html=True)

    tabs = st.tabs([
        "Overview",
        "Ticker Analysis",
        "Signals",
        "Market Insights",
        "News Feed",
    ])

    with tabs[0]: render_overview()
    with tabs[1]: render_ticker_analysis()
    with tabs[2]: render_signals()
    with tabs[3]: render_insights()
    with tabs[4]: render_news_feed()

    # Footer
    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        <div style="font-size:0.78rem;color:#334155;line-height:2">
        <b style="color:#475569">Platform</b><br>
        Real-time sentiment analysis<br>
        Trading signal generation<br>
        Price-sentiment correlation
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div style="font-size:0.78rem;color:#334155;line-height:2">
        <b style="color:#475569">Pipeline</b><br>
        News aggregation (100+ sources)<br>
        FinBERT sentiment scoring<br>
        Ticker extraction and mapping
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div style="font-size:0.78rem;color:#334155;line-height:2">
        <b style="color:#475569">Disclaimer</b><br>
        Educational analytics tool only.<br>
        Not investment advice.<br>
        Always consult a financial advisor.
        </div>""", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
