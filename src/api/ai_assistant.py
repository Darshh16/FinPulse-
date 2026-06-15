from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import requests
import json
import logging
from src.database import get_db_session
from src.api import db_tools

router = APIRouter(prefix="/api/v1/assistant", tags=["ai_assistant"])
logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma3:4b"

class ChatRequest(BaseModel):
    question: str

INTENT_PROMPT = """You are an intent classification engine for FinPulse, a financial news sentiment analysis platform.
Classify the user's question into one of the following exact intents:
- HIGHEST_SENTIMENT (e.g., Which stock has the highest sentiment?)
- LOWEST_SENTIMENT (e.g., Which stock has the lowest sentiment?)
- STOCK_SENTIMENT (e.g., What is the sentiment for MSFT? Show sentiment for Apple)
- ARTICLE_COUNT (e.g., How many articles for Tesla? How many news items total?)
- TOP_POSITIVE (e.g., Show top positive stocks)
- TOP_NEGATIVE (e.g., Show top negative stocks)
- RECENT_ANOMALIES (e.g., Any recent anomalies? Show extreme news)
- RECENT_NEWS (e.g., Summarize recent news for AAPL)
- UNRELATED (e.g., How do I bake a cake? Should I buy TSLA? What is the weather?)

Also extract the stock ticker symbol if mentioned (e.g. AAPL, MSFT, TSLA, INFY.NS).

Return ONLY a valid JSON object in this format, with no extra text:
{"intent": "INTENT_NAME", "ticker": "TICKER_SYMBOL_OR_NULL"}

User Question: "{question}"
JSON:"""

def call_ollama(prompt: str, system: str = "", is_json: bool = False) -> str:
    """Call local Ollama API."""
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "temperature": 0.0 # Keep it deterministic
    }
    if is_json:
        payload["format"] = "json"
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=300)
        response.raise_for_status()
        data = response.json()
        ans = data.get("response", "").strip()
        if not ans and "thinking" in data:
            ans = data.get("thinking", "").strip()
        return ans
    except Exception as e:
        logger.error(f"Ollama API Error: {e}")
        raise HTTPException(status_code=503, detail="AI service unavailable. Is Ollama running?")

def detect_intent(question: str):
    """Detect intent using Qwen."""
    prompt = INTENT_PROMPT.replace("{question}", question)
    result = call_ollama(prompt, is_json=True)
    try:
        # Extract JSON if Qwen adds markdown blocks
        if "{" in result and "}" in result:
            result = result[result.find("{"):result.rfind("}")+1]
        data = json.loads(result)
        
        intent = data.get("intent", "UNRELATED")
        ticker = data.get("ticker", None)
        if isinstance(ticker, str) and ticker.strip().lower() in ["null", "none", "", "n/a"]:
            ticker = None
            
        return intent, ticker
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse intent JSON: {result}")
        return "UNRELATED", None

def get_data_for_intent(intent: str, ticker: str, db):
    """Route intent to database tools and retrieve raw data."""
    if intent == "HIGHEST_SENTIMENT":
        return db_tools.get_highest_sentiment_stock(db)
    elif intent == "LOWEST_SENTIMENT":
        return db_tools.get_lowest_sentiment_stock(db)
    elif intent == "STOCK_SENTIMENT":
        if not ticker: return {"error": "No ticker provided for sentiment."}
        return db_tools.get_stock_sentiment(db, ticker)
    elif intent == "ARTICLE_COUNT":
        return db_tools.get_article_count(db, ticker)
    elif intent == "TOP_POSITIVE":
        return db_tools.get_top_positive_stocks(db)
    elif intent == "TOP_NEGATIVE":
        return db_tools.get_top_negative_stocks(db)
    elif intent == "RECENT_ANOMALIES":
        return db_tools.get_anomalies(db)
    elif intent == "RECENT_NEWS":
        return db_tools.get_recent_headlines(db, ticker, limit=10)
    return None

RESPONSE_SYSTEM_PROMPT = """You are the FinPulse AI Assistant. Your job is to answer the user's question using ONLY the provided database data.
RULES:
1. The provided Database Data is the absolute source of truth.
2. DO NOT invent, hallucinate, or assume any information.
3. If the data contains an error or is empty, simply state that the data is not available.
4. NO INVESTMENT ADVICE. Do not give buy/sell recommendations or predict future prices.
5. Keep your response concise, professional, and directly answer the question.
6. Format your response using markdown.
"""

import traceback

@router.post("/chat")
def chat_with_assistant(req: ChatRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Empty question")

    # 1. Intent Detection
    intent, ticker = detect_intent(question)
    
    # 2. Strict Domain Restriction
    if intent == "UNRELATED":
        return {"response": "I can only answer questions related to FinPulse analytics and sentiment data."}

    # 3. Database Query
    db = get_db_session()
    try:
        raw_data = get_data_for_intent(intent, ticker, db)
    finally:
        db.close()

    # If data fetching failed (e.g., missing ticker)
    if isinstance(raw_data, dict) and "error" in raw_data:
        return {"response": f"I couldn't complete that request: {raw_data['error']}"}

    # 4. Generate Natural Language Response using Qwen
    prompt = f"""User Question: {question}

Database Data:
{json.dumps(raw_data, indent=2)}

Please formulate a helpful response based ONLY on the Database Data above."""

    final_response = call_ollama(prompt, system=RESPONSE_SYSTEM_PROMPT)
    
    return {"response": final_response, "debug": {"intent": intent, "ticker": ticker, "data": raw_data}}
