"""
News normalizer and deduplicator for FinPulse.

Responsibilities:
  1. Normalize article text (strip HTML, decode entities, truncate for FinBERT)
  2. Deduplicate: URL-exact match + fuzzy headline similarity
  3. Relevance filter: only keep articles mentioning tracked tickers/companies
"""
import hashlib
import logging
import re
from difflib import SequenceMatcher
from typing import List, Dict, Set, Optional

from bs4 import BeautifulSoup

from config.settings import settings

logger = logging.getLogger(__name__)

# Max chars for FinBERT (tokenizer limit is 512 tokens ≈ ~400–450 chars to be safe)
_MAX_TEXT_LEN = 450


def _strip_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    if not text:
        return ""
    try:
        return BeautifulSoup(text, "lxml").get_text(separator=" ").strip()
    except Exception:
        return re.sub(r"<[^>]+>", " ", text).strip()


def _normalize_headline(headline: str) -> str:
    """Lowercase + collapse whitespace for comparison."""
    return re.sub(r"\s+", " ", headline.lower().strip())


def _url_fingerprint(url: str) -> str:
    """Create a short hash from a URL for fast de-dup lookup."""
    return hashlib.md5(url.strip().lower().encode()).hexdigest()


def _headline_fingerprint(headline: str) -> str:
    """Create a short hash from normalized headline for exact de-dup."""
    return hashlib.md5(_normalize_headline(headline).encode()).hexdigest()


def _similarity(a: str, b: str) -> float:
    """Return Ratcliff/Obershelp similarity ratio between two strings."""
    return SequenceMatcher(None, _normalize_headline(a), _normalize_headline(b)).ratio()


class NewsNormalizer:
    """
    Normalizes, deduplicates, and filters a mixed list of articles
    from NewsAPI and RSS scrapers before sentiment analysis.
    """

    def __init__(self, similarity_threshold: float = None):
        self.threshold = similarity_threshold or settings.dedup_similarity_threshold

    # ──────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────

    def normalize(self, article: Dict) -> Dict:
        """
        Clean a single article dict in-place.

        Strips HTML from headline/description, truncates to FinBERT limit,
        and ensures all required fields exist.
        """
        article["headline"]    = _strip_html(article.get("headline", ""))[:_MAX_TEXT_LEN]
        article["description"] = _strip_html(article.get("description", ""))[:_MAX_TEXT_LEN]
        article["url"]         = (article.get("url") or "").strip()
        article["source"]      = (article.get("source") or "unknown").strip()
        article["source_weight"] = float(article.get("source_weight", settings.weight_newsapi))
        return article

    def deduplicate(self, articles: List[Dict]) -> List[Dict]:
        """
        Remove duplicate articles from the list.

        Deduplication strategy (in order):
          1. Exact URL match  → keep first occurrence
          2. Exact headline hash match → keep higher-weight source
          3. Fuzzy headline similarity > threshold → keep higher-weight source

        Returns deduplicated list sorted by source_weight DESC.
        """
        # Normalize all first
        articles = [self.normalize(a) for a in articles if a.get("headline")]

        seen_urls: Set[str]      = set()
        seen_headline_hashes: Dict[str, int] = {}  # hash → index in kept
        kept: List[Dict] = []

        for article in sorted(articles, key=lambda x: x.get("source_weight", 0), reverse=True):
            url_fp = _url_fingerprint(article["url"]) if article["url"] else None
            head_fp = _headline_fingerprint(article["headline"])

            # 1. URL de-dup
            if url_fp and url_fp in seen_urls:
                logger.debug(f"Dedup (URL): {article['headline'][:60]}")
                continue

            # 2. Exact headline de-dup
            if head_fp in seen_headline_hashes:
                logger.debug(f"Dedup (exact headline): {article['headline'][:60]}")
                continue

            # 3. Fuzzy de-dup against already-kept headlines
            is_dupe = False
            for kept_art in kept[-50:]:  # only compare against last 50 for performance
                if _similarity(article["headline"], kept_art["headline"]) >= self.threshold:
                    is_dupe = True
                    # Keep the higher-weight one — swap if needed
                    if article.get("source_weight", 0) > kept_art.get("source_weight", 0):
                        kept_art.update(article)
                    logger.debug(f"Dedup (fuzzy): {article['headline'][:60]}")
                    break

            if is_dupe:
                continue

            # Article is unique — keep it
            if url_fp:
                seen_urls.add(url_fp)
            seen_headline_hashes[head_fp] = len(kept)
            kept.append(article)

        logger.info(f"Dedup: {len(articles)} → {len(kept)} unique articles")
        return kept

    def filter_by_relevance(
        self,
        articles: List[Dict],
        company_keywords: Set[str],
    ) -> List[Dict]:
        """
        Keep only articles that mention at least one tracked company keyword
        in the headline or description.

        Args:
            articles: normalized articles
            company_keywords: set of lowercase keyword strings to match
                              (company names, ticker symbols, aliases)

        Returns:
            Filtered list
        """
        relevant = []
        for art in articles:
            text = (art["headline"] + " " + art["description"]).lower()
            if any(kw in text for kw in company_keywords):
                relevant.append(art)

        logger.info(f"Relevance filter: {len(articles)} → {len(relevant)} articles (matched keywords)")
        return relevant

    def process(
        self,
        articles: List[Dict],
        company_keywords: Optional[Set[str]] = None,
    ) -> List[Dict]:
        """
        Full pipeline: normalize → deduplicate → relevance filter.

        Args:
            articles: raw mixed list from NewsAPI + RSS
            company_keywords: optional set of keywords for relevance filter
                              (skip filter if None)

        Returns:
            Clean, unique, relevant articles ready for FinBERT
        """
        deduped = self.deduplicate(articles)
        if company_keywords:
            return self.filter_by_relevance(deduped, company_keywords)
        return deduped
