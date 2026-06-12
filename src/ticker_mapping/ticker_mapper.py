"""
Fixed 10-stock ticker universe for FinPulse.

Stocks are organized by sector. Each entry has:
  - Yahoo Finance ticker symbol
  - Sector label
  - All keyword aliases used for news relevance matching

Only articles mentioning these companies will be processed.
"""
import logging
import re
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Fixed Universe Definition
# ─────────────────────────────────────────────────────────────────────────────

UNIVERSE: Dict[str, Dict] = {
    # ── Banking (India) ──────────────────────────────────────────────────────
    "HDFCBANK.NS": {
        "name":     "HDFC Bank",
        "sector":   "Banking (India)",
        "exchange": "NSE",
        "keywords": {
            "hdfc bank", "hdfcbank", "hdfc", "hdfc banking",
            "housing development finance", "hdfc bank ltd",
        },
    },
    "SBIN.NS": {
        "name":     "State Bank of India",
        "sector":   "Banking (India)",
        "exchange": "NSE",
        "keywords": {
            "state bank of india", "sbi", "sbin", "state bank",
            "sbi bank", "sbi india",
        },
    },

    # ── Retail (India) ───────────────────────────────────────────────────────
    "TRENT.NS": {
        "name":     "Trent",
        "sector":   "Retail (India)",
        "exchange": "NSE",
        "keywords": {
            "trent", "trent limited", "trent ltd", "westside",
            "zudio", "tata trent",
        },
    },
    "DMART.NS": {
        "name":     "Avenue Supermarts (DMart)",
        "sector":   "Retail (India)",
        "exchange": "NSE",
        "keywords": {
            "avenue supermarts", "dmart", "d-mart", "d mart",
            "avenue supermart", "radhakishan damani",
        },
    },

    # ── Manufacturing (India) ────────────────────────────────────────────────
    "SIEMENS.NS": {
        "name":     "Siemens India",
        "sector":   "Manufacturing (India)",
        "exchange": "NSE",
        "keywords": {
            "siemens india", "siemens", "siemens limited",
            "siemens ltd", "siemens ns",
        },
    },
    "ABB.NS": {
        "name":     "ABB India",
        "sector":   "Manufacturing (India)",
        "exchange": "NSE",
        "keywords": {
            "abb india", "abb limited india", "abb ltd india",
            "abb ns", "asea brown boveri india",
        },
    },

    # ── Automobile (India) ───────────────────────────────────────────────────
    "MARUTI.NS": {
        "name":     "Maruti Suzuki India",
        "sector":   "Automobile (India)",
        "exchange": "NSE",
        "keywords": {
            "maruti suzuki", "maruti", "msil", "maruti suzuki india",
            "maruti limited", "suzuki india",
        },
    },
    "M&M.NS": {
        "name":     "Mahindra & Mahindra",
        "sector":   "Automobile (India)",
        "exchange": "NSE",
        "keywords": {
            "mahindra", "mahindra & mahindra", "mahindra and mahindra",
            "m&m", "m and m", "mm india", "mahindra auto",
        },
    },

    # ── Global Tech ──────────────────────────────────────────────────────────
    "MSFT": {
        "name":     "Microsoft",
        "sector":   "Global Tech",
        "exchange": "NASDAQ",
        "keywords": {
            "microsoft", "msft", "microsoft corp", "microsoft corporation",
            "azure", "windows", "copilot microsoft", "satya nadella",
        },
    },
    "NVDA": {
        "name":     "NVIDIA",
        "sector":   "Global Tech",
        "exchange": "NASDAQ",
        "keywords": {
            "nvidia", "nvda", "nvidia corp", "nvidia corporation",
            "nvidia ai", "jensen huang", "geforce", "cuda nvidia",
        },
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Derived lookups (built once at import time)
# ─────────────────────────────────────────────────────────────────────────────

# All tickers as a set
ALL_TICKERS: Set[str] = set(UNIVERSE.keys())

# Flat keyword → ticker map  (lowercase keyword → ticker symbol)
_KEYWORD_TO_TICKER: Dict[str, str] = {}
for _ticker, _meta in UNIVERSE.items():
    for _kw in _meta["keywords"]:
        _KEYWORD_TO_TICKER[_kw.lower()] = _ticker

# All keywords as a flat set (used for relevance filtering)
ALL_KEYWORDS: Set[str] = set(_KEYWORD_TO_TICKER.keys())

# Sector → list of tickers
SECTOR_MAP: Dict[str, List[str]] = {}
for _ticker, _meta in UNIVERSE.items():
    SECTOR_MAP.setdefault(_meta["sector"], []).append(_ticker)


# ─────────────────────────────────────────────────────────────────────────────
# TickerMapper class
# ─────────────────────────────────────────────────────────────────────────────

class TickerMapper:
    """
    Maps company names / keywords in news text to stock tickers
    from the fixed 10-stock universe.
    """

    def __init__(self):
        logger.info(f"TickerMapper initialized with {len(ALL_TICKERS)} fixed tickers")

    # ── Public API ────────────────────────────────────────────────────────────

    def map_headline_to_tickers(self, text: str) -> Set[str]:
        """
        Scan text (headline + description) and return all matching tickers.

        Strategy:
          1. Explicit ticker patterns: $MSFT, (NVDA), HDFCBANK.NS
          2. Keyword/alias matching from UNIVERSE keywords
        """
        tickers: Set[str] = set()
        text_lower = text.lower()

        # 1. Explicit ticker patterns
        for pattern in [
            r'\$([A-Z&]{1,10}(?:\.[A-Z]{1,3})?)',      # $MSFT, $HDFCBANK.NS
            r'\(([A-Z&]{1,10}(?:\.[A-Z]{1,3})?)\)',    # (MSFT), (HDFCBANK.NS)
        ]:
            for match in re.findall(pattern, text, re.IGNORECASE):
                candidate = match.upper()
                if candidate in ALL_TICKERS:
                    tickers.add(candidate)

        # 2. Keyword matching (sorted by length desc to prefer longer matches first)
        sorted_kws = sorted(_KEYWORD_TO_TICKER.keys(), key=len, reverse=True)
        for kw in sorted_kws:
            if kw in text_lower:
                tickers.add(_KEYWORD_TO_TICKER[kw])

        return tickers

    def map_company_to_ticker(self, company_name: str) -> Optional[str]:
        """Direct company-name to ticker lookup."""
        return _KEYWORD_TO_TICKER.get(company_name.lower().strip())

    def get_all_tickers(self) -> Set[str]:
        return ALL_TICKERS.copy()

    def get_ticker_name(self, ticker: str) -> str:
        """Return human-readable company name for a ticker."""
        return UNIVERSE.get(ticker, {}).get("name", ticker)

    def get_ticker_sector(self, ticker: str) -> str:
        """Return sector label for a ticker."""
        return UNIVERSE.get(ticker, {}).get("sector", "Unknown")

    def get_tickers_by_sector(self) -> Dict[str, List[str]]:
        """Return tickers grouped by sector."""
        return SECTOR_MAP.copy()

    def get_all_keywords(self) -> Set[str]:
        """Return all company keywords for relevance filtering."""
        return ALL_KEYWORDS.copy()

    def get_ticker_info(self, ticker: str) -> Optional[Dict]:
        """Return full metadata for a ticker."""
        return UNIVERSE.get(ticker)


# ─────────────────────────────────────────────────────────────────────────────
# Module-level singleton + convenience functions
# ─────────────────────────────────────────────────────────────────────────────

_mapper: Optional[TickerMapper] = None


def get_mapper() -> TickerMapper:
    global _mapper
    if _mapper is None:
        _mapper = TickerMapper()
    return _mapper


def map_headline_to_tickers(text: str) -> Set[str]:
    return get_mapper().map_headline_to_tickers(text)


def get_company_ticker(company_name: str) -> Optional[str]:
    return get_mapper().map_company_to_ticker(company_name)


def get_all_tickers() -> Set[str]:
    return ALL_TICKERS.copy()


def get_all_keywords() -> Set[str]:
    return ALL_KEYWORDS.copy()


def get_ticker_sector(ticker: str) -> str:
    return get_mapper().get_ticker_sector(ticker)


def get_ticker_name(ticker: str) -> str:
    return get_mapper().get_ticker_name(ticker)


# ─────────────────────────────────────────────────────────────────────────────
# Quick self-test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mapper = get_mapper()
    tests = [
        "HDFC Bank posts record Q4 profits amid rising NPA concerns",
        "State Bank of India (SBIN) cuts home loan rates",
        "Mahindra & Mahindra launches new EV SUV at Auto Expo",
        "Microsoft Azure revenue jumps 31% in Q3 earnings",
        "NVIDIA (NVDA) stock hits all-time high on AI demand",
        "Maruti Suzuki reports 12% dip in monthly sales",
        "Unrelated: Government announces new highway project",
    ]
    print("=== TickerMapper Self-Test ===")
    for t in tests:
        tickers = mapper.map_headline_to_tickers(t)
        print(f"  [{', '.join(tickers) or 'NONE'}] {t[:70]}")
