import logging
from typing import List, Dict, Optional, Set
import re

logger = logging.getLogger(__name__)


class TickerMapper:
    """Maps company names and keywords to stock tickers"""
    
    # Extended company-to-ticker mapping
    COMPANY_TICKER_MAP = {
        # Technology
        "apple": "AAPL",
        "microsoft": "MSFT",
        "google": "GOOGL",
        "alphabet": "GOOGL",
        "amazon": "AMZN",
        "tesla": "TSLA",
        "meta": "META",
        "facebook": "META",
        "nvidia": "NVDA",
        "intel": "INTC",
        "amd": "AMD",
        "qualcomm": "QCOM",
        "broadcom": "AVGO",
        "oracle": "ORCL",
        "ibm": "IBM",
        "cisco": "CSCO",
        "apple inc": "AAPL",
        "microsoft corp": "MSFT",
        
        # Finance
        "jpmorgan": "JPM",
        "jp morgan": "JPM",
        "goldman sachs": "GS",
        "bank of america": "BAC",
        "bofa": "BAC",
        "wells fargo": "WFC",
        "citigroup": "C",
        "citi": "C",
        "morgan stanley": "MS",
        "charles schwab": "SCHW",
        "paypal": "PYPL",
        "square": "SQ",
        "block inc": "SQ",
        
        # E-commerce & Retail
        "walmart": "WMT",
        "target": "TGT",
        "costco": "COST",
        "best buy": "BBY",
        "etsy": "ETSY",
        "shopify": "SHOP",
        "ebay": "EBAY",
        
        # Automotive
        "ford": "F",
        "general motors": "GM",
        "gm": "GM",
        "toyota": "TM",
        "honda": "HMC",
        "volkswagen": "VWAGY",
        "bmw": "BMWYY",
        "ferrari": "RACE",
        "lucid": "LCID",
        
        # Energy
        "exxonmobil": "XOM",
        "chevron": "CVX",
        "shell": "SHEL",
        "bp": "BP",
        "saudi aramco": "2222.SR",
        "tesla energy": "TSLA",
        
        # Pharma & Healthcare
        "pfizer": "PFE",
        "moderna": "MRNA",
        "johnson & johnson": "JNJ",
        "johnson johnson": "JNJ",
        "merck": "MRK",
        "abbvie": "ABBV",
        "eli lilly": "LLY",
        "astrazeneca": "AZN",
        "bristol myers": "BMY",
        
        # Industrial
        "boeing": "BA",
        "lockheed martin": "LMT",
        "ge": "GE",
        "general electric": "GE",
        "caterpillar": "CAT",
        "deere": "DE",
        "john deere": "DE",
        
        # Airlines
        "american airlines": "AAL",
        "delta": "DAL",
        "southwest": "LUV",
        "united airlines": "UAL",
        
        # Others
        "netflix": "NFLX",
        "disney": "DIS",
        "comcast": "CMCSA",
        "verizon": "VZ",
        "at&t": "T",
        "t mobile": "TMUS",
        "starbucks": "SBUX",
        "mcdonald's": "MCD",
        "coca-cola": "KO",
        "pepsi": "PEP",
    }
    
    # Keywords that often indicate ticker mentions
    KEYWORD_INDICATORS = {
        "ticker": True,
        "symbol": True,
        "stock": False,  # Too generic
        "shares": False,
        "trading": False,
        "publicly traded": False,
    }
    
    def __init__(self):
        """Initialize ticker mapper"""
        logger.info("TickerMapper initialized")
    
    def extract_tickers_from_text(self, text: str) -> Set[str]:
        """
        Extract ticker symbols from text
        
        Args:
            text: Input text
            
        Returns:
            Set of found tickers
        """
        tickers = set()
        text_lower = text.lower()
        
        # Look for ticker pattern: $TICKER or (TICKER)
        ticker_patterns = [
            r'\$([A-Z]{1,5})',  # $AAPL format
            r'\(([A-Z]{1,5})\)',  # (AAPL) format
            r'(?:ticker|symbol|trading as):\s*([A-Z]{1,5})',  # ticker: AAPL
        ]
        
        for pattern in ticker_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            tickers.update(matches)
        
        return tickers
    
    def map_company_to_ticker(self, company_name: str) -> Optional[str]:
        """
        Map company name to ticker symbol
        
        Args:
            company_name: Name of the company
            
        Returns:
            Ticker symbol or None
        """
        company_lower = company_name.lower().strip()
        
        # Direct match
        if company_lower in self.COMPANY_TICKER_MAP:
            return self.COMPANY_TICKER_MAP[company_lower]
        
        # Partial match (check if company_lower is substring)
        for company, ticker in self.COMPANY_TICKER_MAP.items():
            if company in company_lower or company_lower in company:
                return ticker
        
        return None
    
    def extract_companies_from_headline(self, headline: str) -> List[str]:
        """
        Extract company names from headline (heuristic)
        
        Args:
            headline: News headline
            
        Returns:
            List of potential company names
        """
        companies = []
        headline_lower = headline.lower()
        
        # Find capitalized words (potential company names)
        words = headline.split()
        for i, word in enumerate(words):
            cleaned_word = re.sub(r'[^\w]', '', word)
            
            # Check if word is in company map
            if self.map_company_to_ticker(cleaned_word):
                companies.append(cleaned_word)
            
            # Check two-word combinations
            if i < len(words) - 1:
                two_word = cleaned_word + " " + re.sub(r'[^\w]', '', words[i + 1])
                if self.map_company_to_ticker(two_word):
                    companies.append(two_word)
        
        return companies
    
    def map_headline_to_tickers(self, headline: str) -> Set[str]:
        """
        Map a headline to relevant stock tickers
        
        Args:
            headline: News headline
            
        Returns:
            Set of relevant tickers
        """
        tickers = set()
        
        # Method 1: Look for explicit ticker mentions
        explicit_tickers = self.extract_tickers_from_text(headline)
        tickers.update(explicit_tickers)
        
        # Method 2: Extract companies and map them
        companies = self.extract_companies_from_headline(headline)
        for company in companies:
            ticker = self.map_company_to_ticker(company)
            if ticker:
                tickers.add(ticker)
        
        return tickers
    
    def get_all_companies(self) -> List[str]:
        """Get list of all tracked companies"""
        return list(self.COMPANY_TICKER_MAP.keys())
    
    def get_all_tickers(self) -> Set[str]:
        """Get set of all tracked tickers"""
        return set(self.COMPANY_TICKER_MAP.values())
    
    def add_custom_mapping(self, company: str, ticker: str):
        """Add custom company-to-ticker mapping"""
        self.COMPANY_TICKER_MAP[company.lower()] = ticker.upper()
        logger.info(f"Added custom mapping: {company} -> {ticker}")


# Global singleton instance
_mapper: Optional[TickerMapper] = None


def get_mapper() -> TickerMapper:
    """Get or create ticker mapper instance"""
    global _mapper
    if _mapper is None:
        _mapper = TickerMapper()
    return _mapper


def map_headline_to_tickers(headline: str) -> Set[str]:
    """
    Map a headline to relevant stock tickers
    
    Args:
        headline: News headline
        
    Returns:
        Set of relevant tickers
    """
    mapper = get_mapper()
    return mapper.map_headline_to_tickers(headline)


def get_company_ticker(company_name: str) -> Optional[str]:
    """
    Get ticker for a company name
    
    Args:
        company_name: Name of the company
        
    Returns:
        Ticker symbol or None
    """
    mapper = get_mapper()
    return mapper.map_company_to_ticker(company_name)


# Example usage
if __name__ == "__main__":
    mapper = get_mapper()
    
    test_headlines = [
        "Apple announces new iPhone features",
        "Tesla stock surges after earnings report",
        "Microsoft (MSFT) expands cloud services",
        "Amazon and Google compete in cloud market",
        "JPMorgan warns of economic slowdown"
    ]
    
    print("Testing Ticker Mapping:")
    for headline in test_headlines:
        tickers = mapper.map_headline_to_tickers(headline)
        print(f"Headline: {headline}")
        print(f"Tickers: {tickers}")
        print("---")
