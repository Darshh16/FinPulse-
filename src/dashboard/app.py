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
    page_icon="⚡",
    layout="wide"
)

# ─────────────────────────────────────────────
from themes.theme_manager import THEMES, get_theme_css, get_chart_theme, get_sentiment_scale

# ─────────────────────────────────────────────
# Theme Setup
# ─────────────────────────────────────────────
if "selected_theme" not in st.session_state:
    st.session_state.selected_theme = "FinPulse Dark"

css = get_theme_css(st.session_state.selected_theme)
st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

CHART_THEME = get_chart_theme(st.session_state.selected_theme)
SENTIMENT_SCALE = get_sentiment_scale(st.session_state.selected_theme)

# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────
import os
# Read API_URL from environment variables for production (Streamlit Cloud), fallback to localhost for local dev
API_URL = os.environ.get("API_URL", "http://localhost:8001/api/v1")

BUY_THRESHOLD  =  0.30
SELL_THRESHOLD = -0.15

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
    return {"universe": {
        "Banking (India)":       [{"ticker":"HDFCBANK.NS","name":"HDFC Bank"},{"ticker":"SBIN.NS","name":"State Bank of India"}],
        "Retail (India)":        [{"ticker":"TRENT.NS","name":"Trent"},{"ticker":"DMART.NS","name":"Avenue Supermarts (DMart)"}],
        "Manufacturing (India)": [{"ticker":"SIEMENS.NS","name":"Siemens India"},{"ticker":"ABB.NS","name":"ABB India"}],
        "Automobile (India)":    [{"ticker":"MARUTI.NS","name":"Maruti Suzuki"},{"ticker":"M&M.NS","name":"Mahindra & Mahindra"}],
        "Global Tech":           [{"ticker":"MSFT","name":"Microsoft"},{"ticker":"NVDA","name":"NVIDIA"}],
    }}

SECTOR_COLORS = {
    "Banking (India)": "🟢",
    "Retail (India)": "🔵",
    "Manufacturing (India)": "🟠",
    "Automobile (India)": "🟣",
    "Global Tech": "⚪"
}

def get_ticker_options():
    return get_universe().get("universe", {})

# ─────────────────────────────────────────────
# Data fetchers (unchanged)
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

@st.cache_data(ttl=600)
def fetch_top_indian_gainers():
    try:
        import yfinance as yf
        import pandas as pd
        nifty_tickers = [
            "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "BHARTIARTL.NS",
            "INFY.NS", "ITC.NS", "SBIN.NS", "L&T.NS", "BAJFINANCE.NS",
            "HINDUNILVR.NS", "AXISBANK.NS", "KOTAKBANK.NS", "TATAMOTORS.NS", "M&M.NS",
            "SUNPHARMA.NS", "MARUTI.NS", "NTPC.NS", "ASIANPAINT.NS", "ULTRACEMCO.NS",
            "POWERGRID.NS", "ONGC.NS", "TATASTEEL.NS", "COALINDIA.NS", "ADANIPORTS.NS"
        ]
        data = yf.download(nifty_tickers, period="2d", progress=False)["Close"]
        if len(data) >= 2:
            changes = ((data.iloc[-1] - data.iloc[-2]) / data.iloc[-2]) * 100
            top2 = changes.nlargest(2)
            return [{"ticker": t.replace(".NS", ""), "change": round(c, 2)} for t, c in top2.items() if pd.notna(c)]
    except Exception as e:
        logger.error(f"yfinance gainers error: {e}")
    return []

@st.cache_data(ttl=300)
def fetch_signals():
    try:
        r = requests.get(f"{API_URL}/signals", timeout=5)
        if r.status_code == 200: return r.json()
    except Exception as e: logger.error(e)
    return None

@st.cache_data(ttl=3600)
def get_usdinr_rate():
    try:
        import yfinance as yf
        return float(yf.Ticker("INR=X").fast_info.last_price) or 83.5
    except Exception:
        return 83.5

@st.cache_data(ttl=60)
def fetch_live_price(ticker: str):
    try:
        import yfinance as yf
        fi = yf.Ticker(ticker).fast_info
        price = float(fi.last_price) if fi.last_price is not None else None
        prev  = float(fi.previous_close) if fi.previous_close is not None else None
        if price is None: return None
        
        # Convert USD to INR if global ticker
        if not ticker.endswith((".NS", ".BO")):
            rate = get_usdinr_rate()
            price *= rate
            if prev is not None: prev *= rate

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
        
        if not ticker.endswith((".NS", ".BO")):
            rate = get_usdinr_rate()
            for col in ["Open", "High", "Low", "Close"]:
                if col in hist.columns: hist[col] *= rate

        hist.index = hist.index.tz_localize(None) if hist.index.tzinfo else hist.index
        return hist
    except Exception as e: logger.error(e)
    return None

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def sentiment_color(score):
    if score > BUY_THRESHOLD:  return "#2ECC71"
    if score < SELL_THRESHOLD: return "#E74C3C"
    return "#F39C12"

def signal_from_score(score: float) -> str:
    if score > BUY_THRESHOLD:  return "BUY"
    if score < SELL_THRESHOLD: return "SELL"
    return "HOLD"

def apply_chart_theme(fig, title="", height=380):
    fig.update_layout(**CHART_THEME,
        title=dict(text=title, font=dict(size=12, color="#5C6370"), x=0),
        height=height)
    return fig

def render_legend(ticker=None, show_headlines=False):
    legend_html = """
    <div class="fp-legend">
        <div class="fp-legend-title">Signal Reference — Sentiment Score Thresholds</div>
        <div class="fp-legend-row">
            <span class="fp-badge fp-badge-buy">BUY</span>
            <span>Score &gt; +0.30 &nbsp;·&nbsp; Strong positive news sentiment — review for upside potential</span>
        </div>
        <div class="fp-legend-row">
            <span class="fp-badge fp-badge-hold">HOLD</span>
            <span>Score −0.15 to +0.30 &nbsp;·&nbsp; Mixed or neutral — wait for clearer signals</span>
        </div>
        <div class="fp-legend-row">
            <span class="fp-badge fp-badge-sell">SELL</span>
            <span>Score &lt; −0.15 &nbsp;·&nbsp; Predominantly negative news — exercise caution</span>
        </div>
        <div style="font-size:0.7rem;color:#7A8499;margin-top:0.7rem;font-family:'DM Mono',monospace">
            SOURCE WEIGHTS &nbsp;·&nbsp; Reuters 1.00 &nbsp;·&nbsp; CNBC 0.95 &nbsp;·&nbsp; Yahoo Finance 0.90 &nbsp;·&nbsp; NewsAPI 0.85
        </div>
    </div>
    """

    if show_headlines:
        col1, col2 = st.columns([2.5, 1], gap="large")
        with col1:
            st.markdown(legend_html, unsafe_allow_html=True)
            
        with col2:
            news_resp = fetch_news(ticker=ticker, limit=3)
            news = news_resp.get("data", []) if news_resp else []
            if news:
                st.markdown('<div style="font-size: 0.65rem; color: #5B578A; letter-spacing: 0.05em; font-weight: 600; font-family: \'Inter\', sans-serif; margin-bottom: 0.5rem; text-transform: uppercase;">Today\'s Top Recent Headlines</div>', unsafe_allow_html=True)
                for h in news:
                    label_color = "#2ECC71" if h.get("sentiment_label") == "positive" else ("#E74C3C" if h.get("sentiment_label") == "negative" else "#5B578A")
                    timestamp = fmt_ist(h.get('timestamp')) if 'timestamp' in h else ''
                    st.markdown(f"""
                    <div style="background: rgba(255,255,255,0.03); padding: 0.6rem 0.8rem; border-radius: 4px; margin-bottom: 0.4rem; border-left: 2px solid {label_color};">
                        <div style="font-size: 0.85rem; color: #F1F0FF; margin-bottom: 0.2rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                            <a href="{h.get('url', '#')}" target="_blank" style="color: inherit; text-decoration: none;">{h.get('headline')}</a>
                        </div>
                        <div style="font-size: 0.65rem; color: #5B578A; font-family: 'DM Mono', monospace;">
                            {h.get('source', '').upper()} &nbsp;•&nbsp; {timestamp}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
    else:
        st.markdown(legend_html, unsafe_allow_html=True)

def render_insight_card(ticker: str, name: str, score: float, pos: int, neg: int, neu: int,
                        total: int, days: int, trend: str = "stable",
                        confidence_level: str = None, trend_score: float = None,
                        price_momentum: str = None, rec_score: float = None, rec_label: str = None):
    if rec_label:
        signal = rec_label
    else:
        signal = signal_from_score(score)
    col = sentiment_color(score)

    conf = confidence_level or "Unknown"
    is_low_confidence = conf == "Low"

    if signal == "BUY":
        if is_low_confidence:
            rec_text = (
                f"Only <b>{total}</b> relevant articles found for <b>{name}</b> over the last <b>{days} days</b>. "
                f"Confidence is <b style='color:#E74C3C'>low</b>. "
                f"Despite limited coverage, sentiment is <b style='color:#2ECC71'>positive</b> "
                f"(score: <b>{score:+.3f}</b>). Consider waiting for broader coverage before acting."
            )
        else:
            rec_text = (
                f"Analysis of <b>{total}</b> articles over <b>{days} days</b> shows a "
                f"<b style='color:#2ECC71'>strongly positive</b> outlook for <b>{name}</b> "
                f"(score: <b style='color:#2ECC71'>{score:+.3f}</b>). "
                f"Positive articles dominate ({pos} positive vs {neg} negative). "
                f"Review recent earnings and sector trends before acting."
            )
        rec_label_html = "<span style='color:#2ECC71'>Recommendation: BUY (with due diligence)</span>"
    elif signal == "SELL":
        if is_low_confidence:
            rec_text = (
                f"Only <b>{total}</b> relevant articles found for <b>{name}</b> over the last <b>{days} days</b>. "
                f"Confidence is <b style='color:#E74C3C'>low</b>. "
                f"Despite limited coverage, sentiment is <b style='color:#E74C3C'>negative</b> "
                f"(score: <b>{score:+.3f}</b>). Limited data reduces signal reliability."
            )
        else:
            rec_text = (
                f"Analysis of <b>{total}</b> articles over <b>{days} days</b> shows a "
                f"<b style='color:#E74C3C'>predominantly negative</b> outlook for <b>{name}</b> "
                f"(score: <b style='color:#E74C3C'>{score:+.3f}</b>). "
                f"Negative articles dominate ({neg} negative vs {pos} positive). "
                f"Review recent news and fundamentals before making any decisions."
            )
        rec_label_html = "<span style='color:#E74C3C'>Recommendation: SELL / CAUTION</span>"
    else:
        if is_low_confidence:
            rec_text = (
                f"Only <b>{total}</b> relevant articles found for <b>{name}</b> over the last <b>{days} days</b>. "
                f"Confidence is <b style='color:#E74C3C'>low</b>. "
                f"Sentiment is <b style='color:#F39C12'>mixed or neutral</b> "
                f"(score: <b>{score:+.3f}</b>). Wait for more data before acting."
            )
        else:
            rec_text = (
                f"Analysis of <b>{total}</b> articles over <b>{days} days</b> shows a "
                f"<b style='color:#F39C12'>mixed or neutral</b> outlook for <b>{name}</b> "
                f"(score: <b style='color:#F39C12'>{score:+.3f}</b>). "
                f"Coverage is balanced ({pos} positive, {neg} negative, {neu} neutral). "
                f"Wait for a stronger directional signal before acting."
            )
        rec_label_html = "<span style='color:#F39C12'>Recommendation: HOLD / MONITOR</span>"

    trend_arrow = {"improving": "trending up ↗", "declining": "trending down ↘", "stable": "stable →"}.get(trend, "stable →")
    conf_color = {"High": "#2ECC71", "Medium": "#F39C12", "Low": "#E74C3C"}.get(str(confidence_level), "#5C6370")
    conf_display = confidence_level or '—'

    st.markdown(f"""
    <div class="fp-insight">
        <div class="fp-insight-body">
            {rec_text}
            <div style='margin-top:0.6rem;font-size:0.75rem;color:#3C4558;font-family:"DM Mono",monospace'>
                TREND: <span style='color:#5C6370'>{trend_arrow}</span> &nbsp;·&nbsp;
                ARTICLES: <span style='color:#5C6370'>{total}</span> &nbsp;·&nbsp;
                CONFIDENCE: <span style='color:{conf_color}'>{conf_display}</span> &nbsp;·&nbsp;
                LOOKBACK: <span style='color:#5C6370'>{days}d</span>
            </div>
        </div>
        <div class="fp-insight-rec">{rec_label_html}</div>
        <div class="fp-insight-disclaimer">
            Automated signal based on news sentiment for educational purposes only.
            Not financial advice. Always consult a registered financial advisor before investing.
        </div>
    </div>
    """, unsafe_allow_html=True)



# ─────────────────────────────────────────────
# Tab 1 — Overview
# ─────────────────────────────────────────────
def render_overview():
    st.markdown('<div class="fp-eyebrow">Market Overview — Last 7 Days</div>', unsafe_allow_html=True)

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
        st.markdown('<div class="fp-eyebrow">Top Tickers by News Volume</div>', unsafe_allow_html=True)
        col_chart, col_table = st.columns([3, 2])
        with col_chart:
            top_10 = df.head(10).copy()
            if "name" not in top_10.columns:
                top_10["name"] = top_10["ticker"]
            if "sector" not in top_10.columns:
                top_10["sector"] = "Unknown"

            fig = go.Figure(go.Bar(
                x=top_10["ticker"], y=top_10["news_count"],
                marker=dict(
                    color=top_10["avg_sentiment"], colorscale=SENTIMENT_SCALE, cmin=-1, cmax=1,
                    colorbar=dict(title=dict(text="Sentiment", font=dict(size=10)), thickness=10, len=0.65,
                        tickfont=dict(family="DM Mono", size=9)),
                    line=dict(color="rgba(0,0,0,0)", width=0)
                ),
                text=top_10["news_count"], textposition="outside",
                textfont=dict(size=10, color="#5C6370", family="DM Mono"),
                customdata=top_10[["name", "sector", "avg_sentiment"]],
                hovertemplate=(
                    "<b>%{customdata[0]}</b> (%{x})<br>"
                    "Sector: %{customdata[1]}<br>"
                    "Articles: <b>%{y}</b><br>"
                    "Avg Sentiment: <b>%{customdata[2]:+.3f}</b><extra></extra>"
                ),
            ))
            apply_chart_theme(fig, "Article Volume by Ticker", height=360)
            fig.update_layout(xaxis=dict(tickfont=dict(family="DM Mono", size=11)), bargap=0.4)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        with col_table:
            display = df[["ticker","name","sector","news_count","avg_sentiment"]].copy() if "name" in df.columns else df[["ticker","news_count","avg_sentiment"]].copy()
            display.columns = [c.title() for c in display.columns]
            if "Avg_Sentiment" in display.columns:
                display["Avg_Sentiment"] = display["Avg_Sentiment"].apply(lambda x: f"{x:+.4f}")
            elif "Avg Sentiment" in display.columns:
                display["Avg Sentiment"] = display["Avg Sentiment"].apply(lambda x: f"{x:+.4f}")
            st.dataframe(display, use_container_width=True, hide_index=True, height=360)

    st.divider()
    render_legend(show_headlines=True)


# ─────────────────────────────────────────────
# Tab 2 — Ticker Analysis
# ─────────────────────────────────────────────
def render_ticker_analysis():
    st.markdown('<div class="fp-eyebrow">Ticker Deep Dive</div>', unsafe_allow_html=True)

    sectors_dict = get_ticker_options()
    sectors = list(sectors_dict.keys())

    c1, c2, c3 = st.columns([1.5, 1.5, 1])
    with c1:
        selected_sector = st.selectbox("Select Sector", sectors, format_func=lambda x: f"{SECTOR_COLORS.get(x, '⚪')} {x}", key="ta_sector")
    with c2:
        stocks = sectors_dict[selected_sector]
        labels = [f"{s['name']} [{s['ticker']}]" for s in stocks]
        selected_label = st.selectbox("Select Stock", labels, key="ta_stock")
    with c3:
        days = st.slider("Lookback (days)", 1, 90, 7)

    ticker = stocks[labels.index(selected_label)]["ticker"]
    name   = selected_label.split("[")[0].strip()

    sentiment_data = fetch_sentiment(ticker, days)

    if not sentiment_data or not sentiment_data.get("data"):
        st.warning(f"No sentiment data for **{name}** yet. Run the pipeline and `run_aggregation.py` to populate.")
        return

    df = pd.DataFrame(sentiment_data["data"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="ISO8601")
    df["timestamp_ist"] = df["timestamp"].apply(lambda x: to_ist(x.to_pydatetime()))
    df = df.sort_values("timestamp")

    overall = sentiment_data.get("overall", {})
    pos   = overall.get("positive", int(df["positive_count"].sum()) if "positive_count" in df.columns else 0)
    neg   = overall.get("negative", int(df["negative_count"].sum()) if "negative_count" in df.columns else 0)
    neu   = overall.get("neutral", int(df["neutral_count"].sum()) if "neutral_count" in df.columns else 0)
    total = overall.get("total", int(df["news_count"].sum()) if "news_count" in df.columns else 0)
    if "weighted_sentiment" in df.columns and df["weighted_sentiment"].notna().any():
        avg = float(df["weighted_sentiment"].mean())
    else:
        avg = float(df["avg_sentiment"].mean())

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Articles", f"{total:,}")
    k2.metric("Weighted Sentiment", f"{avg:+.3f}")
    k3.metric("Positive", pos)
    k4.metric("Negative", neg)
    k5.metric("Neutral", neu)

    latest_row = df.iloc[-1] if len(df) > 0 else None
    conf_level = latest_row.get("confidence_level") if latest_row is not None and "confidence_level" in df.columns else None
    t_score = latest_row.get("trend_score") if latest_row is not None and "trend_score" in df.columns else None
    p_momentum = latest_row.get("price_momentum") if latest_row is not None and "price_momentum" in df.columns else None
    rec_score = latest_row.get("recommendation_score") if latest_row is not None and "recommendation_score" in df.columns else None
    rec_label = latest_row.get("recommendation_label") if latest_row is not None and "recommendation_label" in df.columns else None

    if t_score is not None and pd.isna(t_score): t_score = None
    if rec_score is not None and pd.isna(rec_score): rec_score = None
    if conf_level is not None and (isinstance(conf_level, float) and pd.isna(conf_level)): conf_level = None
    if p_momentum is not None and (isinstance(p_momentum, float) and pd.isna(p_momentum)): p_momentum = None
    if rec_label is not None and (isinstance(rec_label, float) and pd.isna(rec_label)): rec_label = None

    # ── Live Price
    st.divider()
    st.markdown('<div class="fp-eyebrow">Current Price</div>', unsafe_allow_html=True)
    price_data = fetch_live_price(ticker)
    if price_data:
        p, ch, cp, pc = price_data["price"], price_data["change"], price_data["change_pct"], price_data["prev_close"]
        mc, vol = price_data["market_cap"], price_data["volume"]
        p1, p2, p3, p4 = st.columns(4)
        p1.metric("Current Price", f"₹{p:,.2f}",
                  delta=f"{ch:+.2f} ({cp:+.2f}%)", delta_color="normal" if ch >= 0 else "inverse")
        p2.metric("Previous Close", f"₹{pc:,.2f}" if pc else "—")
        p3.metric("Market Cap",
                  f"₹{mc/1e12:.2f}T" if mc and mc >= 1e12
                  else f"₹{mc/1e9:.1f}B" if mc and mc >= 1e9
                  else "—")
        p4.metric("Avg Volume (3M)", f"{vol/1e6:.1f}M" if vol and vol >= 1e6 else f"{vol:,.0f}" if vol else "—")

        hist = fetch_price_history(ticker, period="5d", interval="1h")
        if hist is not None and not hist.empty:
            fig_p = go.Figure(go.Candlestick(
                x=hist.index, open=hist["Open"], high=hist["High"], low=hist["Low"], close=hist["Close"],
                increasing=dict(line=dict(color="#2ECC71", width=1.5), fillcolor="rgba(46,204,113,0.2)"),
                decreasing=dict(line=dict(color="#E74C3C", width=1.5), fillcolor="rgba(231,76,60,0.2)"),
                name="Price",
            ))
            apply_chart_theme(fig_p, f"{name} — 5-Day Price (1h candles)", height=300)
            fig_p.update_layout(
                xaxis_rangeslider_visible=False,
                xaxis=dict(
                    tickfont=dict(family="DM Mono", size=10),
                    rangebreaks=[
                        dict(bounds=["sat", "mon"]),
                        dict(bounds=[16.5, 9.25], pattern="hour")
                    ]
                ),
                yaxis=dict(tickprefix="₹" if ".NS" in ticker else "$", tickfont=dict(family="DM Mono", size=10))
            )
            st.plotly_chart(fig_p, use_container_width=True, config={"displayModeBar": False})
    else:
        st.caption(f"Live price unavailable for {ticker}.")

    # ── Sentiment charts
    st.divider()
    st.markdown('<div class="fp-eyebrow">Sentiment Analysis</div>', unsafe_allow_html=True)

    left, right = st.columns(2)

    hover_texts = []
    contributing_list = df["contributing_articles"].tolist() if "contributing_articles" in df.columns else []
    
    import json
    for i in range(len(contributing_list)):
        if isinstance(contributing_list[i], str):
            try:
                contributing_list[i] = json.loads(contributing_list[i])
            except Exception:
                contributing_list[i] = []
        elif contributing_list[i] is None:
            contributing_list[i] = []

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
                short_head = headline[:55] + "..." if len(headline) > 55 else headline
                if url:
                    lines.append(f"{label_icon} [{art.get('source','?').upper()}] <a href='{url}' target='_blank' style='color:#F5A623'>{short_head}</a>")
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
            line=dict(color="#F5A623", width=2),
            marker=dict(color=sc, size=7, line=dict(color="#080A0F", width=1.5)),
            fill="tozeroy", fillcolor="rgba(245,166,35,0.06)",
            text=hover_texts,
            hovertemplate="%{text}<extra></extra>",
        ))
        fig.add_hline(y=BUY_THRESHOLD, line=dict(color="rgba(46,204,113,0.25)", width=1, dash="dot"))
        fig.add_hline(y=SELL_THRESHOLD, line=dict(color="rgba(231,76,60,0.25)", width=1, dash="dot"))
        fig.add_hline(y=0, line=dict(color="rgba(255,255,255,0.05)", width=1, dash="dot"))
        apply_chart_theme(fig, f"{name} — Sentiment Trend (IST)")
        fig.update_layout(xaxis=dict(tickformat="%d %b %H:%M"))
        
        selection = st.plotly_chart(
            fig, 
            use_container_width=True, 
            config={"displayModeBar": False},
            on_select="rerun",
            selection_mode="points",
            key="ta_sentiment_chart"
        )

    with right:
        fig2 = go.Figure(go.Pie(
            labels=["Positive", "Negative", "Neutral"], values=[pos, neg, neu], hole=0.65,
            marker=dict(colors=["#2ECC71", "#E74C3C", "#2C3440"], line=dict(color="#080A0F", width=3)),
            textinfo="label+percent", textfont=dict(size=11, family="Inter"),
            hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Share: %{percent}<extra></extra>",
        ))
        fig2.update_layout(**CHART_THEME,
            title=dict(text=f"{name} — Sentiment Distribution", font=dict(size=12, color="#5C6370"), x=0),
            height=380, showlegend=False,
            annotations=[dict(text=f"<b>{avg:+.2f}</b>", x=0.5, y=0.5, showarrow=False,
                font=dict(size=20, color=sentiment_color(avg), family="DM Mono"))])
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False}, key="ta_sentiment_dist")
        
        with st.expander("Detailed Signal Reference"):
            render_legend(show_headlines=False)

    # Show clicked news
    selected_points = selection.get("selection", {}).get("points", []) if selection else []
    if selected_points:
        point_idx = selected_points[0].get("point_index")
        if point_idx is not None and 0 <= point_idx < len(contributing_list):
            articles = contributing_list[point_idx]
            if articles:
                st.markdown(f'<div class="fp-eyebrow" style="margin-top: 1rem;">News for {fmt_ist(df.iloc[point_idx]["timestamp"])}</div>', unsafe_allow_html=True)
                for art in articles:
                    label_color = "#2ECC71" if art.get("label") == "positive" else ("#E74C3C" if art.get("label") == "negative" else "#F5A623")
                    st.markdown(f"""
                    <div style="padding: 0.8rem; background: rgba(255,255,255,0.03); border-left: 3px solid {label_color}; margin-bottom: 0.5rem; border-radius: 4px;">
                        <div style="font-size: 0.75rem; color: #9B96C9; margin-bottom: 0.2rem; font-family: 'DM Mono', monospace;">
                            [{art.get('source', '?').upper()}] &nbsp;•&nbsp; Score: {art.get('score', 0):+.4f}
                        </div>
                        <a href="{art.get('url', '#')}" target="_blank" style="color: #F1F0FF; text-decoration: none; font-size: 0.95rem;">{art.get('headline', '')}</a>
                    </div>
                    """, unsafe_allow_html=True)



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

    # ── 6-Month Trend
    st.markdown('<div class="fp-eyebrow" style="margin-top:2rem">6-Month Price Trend</div>', unsafe_allow_html=True)
    hist_6m = fetch_price_history(ticker, period="6mo", interval="1d")
    if hist_6m is not None and not hist_6m.empty:
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(
            x=hist_6m.index, y=hist_6m["Close"],
            mode="lines",
            line=dict(color="#F5A623", width=2),
            fill="tozeroy", fillcolor="rgba(245,166,35,0.06)",
            name="Daily Close",
            hovertemplate="<b>%{x|%d %b %Y}</b><br>Close: %{y:.2f}<extra></extra>"
        ))
        if len(hist_6m) >= 50:
            sma_50 = hist_6m["Close"].rolling(window=50).mean()
            fig_trend.add_trace(go.Scatter(
                x=hist_6m.index, y=sma_50,
                mode="lines",
                line=dict(color="#3498DB", width=1.5, dash="dot"),
                name="50d SMA",
                hovertemplate="<b>%{x|%d %b %Y}</b><br>50d SMA: %{y:.2f}<extra></extra>"
            ))
        apply_chart_theme(fig_trend, f"{name} — 6-Month Price Trend", height=350)
        fig_trend.update_layout(
            xaxis=dict(tickformat="%b %Y"),
            yaxis=dict(tickprefix="₹", tickfont=dict(family="DM Mono", size=10))
        )
        st.plotly_chart(fig_trend, use_container_width=True, config={"displayModeBar": False})

        if t_score is not None:
            trend_sugg = "BUY" if t_score > 0.2 else "SELL" if t_score < -0.2 else "HOLD / MONITOR"
            trend_color = "#2ECC71" if trend_sugg == "BUY" else "#E74C3C" if trend_sugg == "SELL" else "#F39C12"
            st.markdown(f"""
            <div class="fp-trend-box">
                <div class="fp-trend-box-label">Trend Analysis Suggestion</div>
                <div style='color:{trend_color}; font-weight:700; font-size:1rem; font-family:"DM Mono",monospace'>{trend_sugg}</div>
                <div class="fp-trend-box-note">Based on historical 6-month price action and momentum only.</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.caption(f"Historical price trend unavailable for {ticker}.")

    # ── Correlation Score (Standalone)
    st.divider()
    corr_data = fetch_correlation(ticker, days)
    if corr_data:
        cv = corr_data.get("correlation", 0.0)
        st.metric("Pearson Correlation (Price vs Sentiment)", f"{cv:+.4f}")
    else:
        st.caption("Not enough alignment data yet for correlation.")



# ─────────────────────────────────────────────
# Tab 3 — Signals
# ─────────────────────────────────────────────
def render_signals():
    st.markdown('<div class="fp-eyebrow">Trading Signals — Sentiment-Driven</div>', unsafe_allow_html=True)
    render_legend()

    data = fetch_signals()
    if not data or not data.get("signals"):
        st.info("No signals yet. Run the pipeline to generate sentiment-based signals.")
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
    k4.metric("Total",        len(signals))

    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        fig = go.Figure(go.Bar(
            x=["BUY", "SELL", "HOLD"], y=[buy, sell, hold],
            marker=dict(color=["#2ECC71", "#E74C3C", "#F39C12"], line=dict(color="#080A0F", width=0)),
            text=[buy, sell, hold], textposition="outside",
            textfont=dict(family="DM Mono", size=12, color="#5C6370"),
        ))
        apply_chart_theme(fig, "Signal Distribution", height=320)
        fig.update_layout(bargap=0.5, showlegend=False)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col_b:
        display_names = [s.get("name") for s in signals]
        sentiments = [s.get("sentiment", 0) for s in signals]
        fig2 = go.Figure(go.Bar(
            y=display_names,
            x=sentiments,
            orientation="h",
            marker=dict(
                color=["#2ECC71" if v > 0 else "#E74C3C" if v < 0 else "#F39C12" for v in sentiments],
                line=dict(color="#080A0F", width=1)
            ),
            opacity=0.85,
        ))
        apply_chart_theme(fig2, "Sentiment by Ticker", height=320)
        fig2.update_layout(xaxis_title="Sentiment Score", yaxis_title="", yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    st.divider()
    st.markdown('<div class="fp-eyebrow">Active Signals Table</div>', unsafe_allow_html=True)
    display_cols = [c for c in ["ticker","name","sector","signal","confidence","sentiment","news_count"] if c in df.columns]
    display_df = df[display_cols].copy().sort_values("confidence", ascending=False)
    if "confidence" in display_df.columns:
        display_df["confidence"] = display_df["confidence"].apply(lambda x: f"{x:.1f}%")
    if "sentiment" in display_df.columns:
        display_df["sentiment"] = display_df["sentiment"].apply(lambda x: f"{x:+.4f}")
    display_df.columns = [c.replace("_", " ").title() for c in display_df.columns]
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    st.caption("Signals are generated for educational analysis only. Not financial advice.")

# ─────────────────────────────────────────────
# Tab 4 — Radar & Correlation (inside Overview tab)
# ─────────────────────────────────────────────
def render_pe_chart():
    st.markdown('<div class="fp-eyebrow">Dynamic PE Chart</div>', unsafe_allow_html=True)
    st.caption("Historical Trailing P/E based on 1-Month Prices.")
    
    import yfinance as yf
    
    sectors_dict = get_ticker_options()
    sectors = list(sectors_dict.keys())
    
    col1, col2 = st.columns(2)
    with col1:
        selected_sector = st.selectbox("Select Sector", sectors, format_func=lambda x: f"{SECTOR_COLORS.get(x, '⚪')} {x}", key="pe_sector")
    with col2:
        stocks = sectors_dict[selected_sector]
        labels = [f"{s['name']} [{s['ticker']}]" for s in stocks]
        selected_label = st.selectbox("Select Stock", labels, key="pe_stock")
        
    selected_ticker = stocks[labels.index(selected_label)]["ticker"]
        
    with st.spinner(f"Calculating P/E for {selected_ticker}..."):
        try:
            t = yf.Ticker(selected_ticker)
            info = t.info
            eps = info.get("trailingEps")
            
            if not eps or eps <= 0:
                st.warning(f"No positive EPS data available for {selected_ticker}.")
                return
                
            hist = t.history(period="1mo")
            if hist.empty:
                st.warning(f"No price history available for {selected_ticker}.")
                return
                
            hist["PE"] = hist["Close"] / eps
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=hist.index,
                y=hist["PE"],
                fill='tozeroy',
                mode='lines',
                line=dict(color='#22D3EE', width=2),
                fillcolor='rgba(34, 211, 238, 0.15)',
                name="P/E Ratio"
            ))
            
            fig.update_layout(**CHART_THEME)
            fig.update_layout(
                margin=dict(l=0, r=0, t=10, b=0),
                height=250,
                xaxis=dict(
                    showgrid=False,
                    tickfont=dict(family="DM Mono", size=10)
                ),
                yaxis=dict(
                    showgrid=True,
                    tickfont=dict(family="DM Mono", size=10)
                )
            )
            
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            
        except Exception as e:
            st.error(f"Error fetching P/E data: {e}")

# ─────────────────────────────────────────────
# Tab 4 — Radar & Correlation (inside Overview tab)
# ─────────────────────────────────────────────
def render_radar():
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        st.markdown('<div class="fp-eyebrow">Sentiment Anomaly Radar</div>', unsafe_allow_html=True)
        st.caption("Detects sudden spikes in news volume or extreme 24h sentiment shifts.")

        sectors_dict = get_ticker_options()
        all_tickers = []
        for stocks in sectors_dict.values():
            all_tickers.extend([s['ticker'] for s in stocks])

        anomalies = []
        correlations = []

        with st.spinner("Scanning market for anomalies..."):
            for ticker in all_tickers:
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

                        if avg_vol > 0 and today["news_count"] > avg_vol * 2.0 and today["news_count"] >= 5:
                            anomalies.append({
                                "ticker": ticker, "type": "Volume Spike",
                                "details": f"News volume jumped to {int(today['news_count'])} articles today (7d avg: {avg_vol:.1f})",
                                "severity": "high"
                            })

                        if abs(today["avg_sentiment"] - avg_sent) > 0.4:
                            swing_dir = "Drop" if today["avg_sentiment"] < avg_sent else "Surge"
                            anomalies.append({
                                "ticker": ticker, "type": f"Sentiment {swing_dir}",
                                "details": f"Sentiment shifted from {avg_sent:+.2f} (7d avg) to {today['avg_sentiment']:+.2f} today",
                                "severity": "critical" if swing_dir == "Drop" else "medium"
                            })



        if not anomalies:
            st.success("✅ Market stable — no major sentiment swings or volume spikes detected today.")
        else:
            for anom in anomalies:
                color = "#E74C3C" if anom["severity"] == "critical" else ("#F39C12" if anom["severity"] == "high" else "#2ECC71")
                st.markdown(f"""
                <div class="fp-anomaly" style="border-left:3px solid {color}">
                    <div class="fp-anomaly-title" style="color:{color}">{anom['ticker']} — {anom['type']}</div>
                    <div class="fp-anomaly-detail">{anom['details']}</div>
                </div>
                """, unsafe_allow_html=True)
                
    with col2:
        render_pe_chart()

    st.divider()
    st.markdown('<div class="fp-eyebrow">Top 2 Gainers — Indian Market</div>', unsafe_allow_html=True)
    st.caption("Top performing major Indian stocks over the last trading session.")

    gainers = fetch_top_indian_gainers()
    if gainers and len(gainers) >= 2:
        g1, g2 = gainers[0], gainers[1]
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"""
            <div class="fp-gainer">
                <div class="fp-gainer-ticker">{g1['ticker']}</div>
                <div class="fp-gainer-change">+{g1['change']}%</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="fp-gainer">
                <div class="fp-gainer-ticker">{g2['ticker']}</div>
                <div class="fp-gainer-change">+{g2['change']}%</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Market data currently unavailable for top gainers.")

# ─────────────────────────────────────────────
# Tab 5 — News Feed
# ─────────────────────────────────────────────
def render_news_feed():
    st.markdown('<div class="fp-eyebrow">Latest Financial News</div>', unsafe_allow_html=True)

    sectors_dict = get_ticker_options()
    sectors = ["All Sectors"] + list(sectors_dict.keys())

    c1, c2, c3, c4 = st.columns([1.2, 1.2, 1, 1])
    with c1:
        selected_sector = st.selectbox("Filter by Sector", sectors, format_func=lambda x: f"{SECTOR_COLORS.get(x, '⚪')} {x}" if x != "All Sectors" else x)
    with c2:
        if selected_sector == "All Sectors":
            selected_stock = st.selectbox("Filter by Stock", ["All Tickers"])
            ticker_filter = None
        else:
            stocks = sectors_dict[selected_sector]
            labels = [f"{s['name']} [{s['ticker']}]" for s in stocks]
            selected_stock = st.selectbox("Filter by Stock", labels)
            ticker_filter = stocks[labels.index(selected_stock)]["ticker"]
            
    with c3:
        news_limit = st.slider("Articles", 10, 100, 30, step=10)
    with c4:
        days_filter = st.slider("Days back", 1, 90, 7)
        
    news_data = fetch_news(ticker=ticker_filter, limit=news_limit, days=days_filter)

    if not news_data or not news_data.get("data"):
        st.info("No news articles found. Run the pipeline to fetch news.")
        return

    articles = news_data["data"]
    st.caption(f"Showing {len(articles)} of {news_data.get('total', 0)} articles")
    st.divider()

    for art in articles:
        label  = art.get("sentiment_label", "neutral")
        score  = art.get("sentiment_score", 0.0) or 0.0
        source = art.get("source", "Unknown")
        weight = art.get("source_weight", 0.85)
        ticker = art.get("ticker") or "—"
        ts     = fmt_ist(art.get("timestamp", ""))
        url    = art.get("url", "")

        if label == "positive":
            score_class, score_prefix = "fp-score-pos", "+"
        elif label == "negative":
            score_class, score_prefix = "fp-score-neg", ""
        else:
            score_class, score_prefix = "fp-score-neu", ""

        headline_html = (
            f'<a href="{url}" target="_blank">{art.get("headline","")}</a>'
            if url else art.get("headline", "")
        )

        st.markdown(f"""
        <div class="fp-news">
            <div class="fp-news-headline">{headline_html}</div>
            <div class="fp-news-meta">
                <span class="fp-tag">{source.upper()} {weight:.2f}</span>
                <span style="color:#3C4558">·</span>
                <span style="color:#3498DB;font-weight:600;font-family:'DM Mono',monospace">{ticker}</span>
                <span style="color:#3C4558">·</span>
                <span class="{score_class}">{label.upper()} {score_prefix}{score:.4f}</span>
                <span style="color:#3C4558">·</span>
                <span style="color:#3C4558">{ts}</span>
                {"<span style='color:#3C4558'>·</span><a href='" + url + "' target='_blank' style='color:#F5A623;font-size:0.7rem'>View →</a>" if url else ""}
            </div>
        </div>
        """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
def main():
    st.markdown("""
    <div class="fp-hero">
        <div class="fp-hero-tag">⚡ Real-Time Intelligence Platform</div>
        <div class="fp-hero-title">Fin<span>Pulse</span></div>
        <div class="fp-hero-desc">
            Financial news sentiment analysis powered by FinBERT.
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown('<div class="fp-sidebar-section">Settings</div>', unsafe_allow_html=True)
        theme_names = list(THEMES.keys())
        default_index = theme_names.index(st.session_state.selected_theme) if st.session_state.selected_theme in theme_names else 0
        selected = st.selectbox("Dashboard Theme", theme_names, index=default_index, key="theme_selector")
        if selected != st.session_state.selected_theme:
            st.session_state.selected_theme = selected
            st.rerun()


    tabs = st.tabs(["Overview", "Ticker Analysis", "Signals", "News Feed"])
    with tabs[0]:
        render_overview()
        st.write("---")
        render_radar()
    with tabs[1]: render_ticker_analysis()
    with tabs[2]: render_signals()
    with tabs[3]: render_news_feed()



if __name__ == "__main__":
    main()