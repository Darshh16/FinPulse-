from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
import torch
import logging
from typing import Dict, Tuple, Optional
import numpy as np

logger = logging.getLogger(__name__)


class FinBERTSentimentAnalyzer:
    """FinBERT-based sentiment analysis for financial text"""
    
    def __init__(self, model_name: str = "ProsusAI/finbert"):
        """
        Initialize FinBERT model
        
        Args:
            model_name: HuggingFace model identifier
        """
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {self.device}")
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name).to(self.device)
            self.sentiment_pipeline = pipeline(
                "sentiment-analysis",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if self.device == "cuda" else -1
            )
            logger.info(f"FinBERT model loaded successfully: {model_name}")
        except Exception as e:
            logger.error(f"Error loading FinBERT model: {str(e)}")
            raise
    
    def analyze_sentiment(self, text: str) -> Dict:
        """
        Analyze sentiment of a text
        
        Args:
            text: Input text to analyze
            
        Returns:
            Dictionary with sentiment label and score
        """
        try:
            # Truncate text if too long (FinBERT max is 512 tokens)
            max_length = 512
            tokens = self.tokenizer.encode(text)
            if len(tokens) > max_length:
                text = self.tokenizer.decode(tokens[:max_length])
            
            # Get sentiment prediction
            results = self.sentiment_pipeline(text)
            result = results[0]
            
            # Map FinBERT output to standard labels
            label_map = {
                "positive": "positive",
                "negative": "negative",
                "neutral": "neutral"
            }
            
            sentiment_label = label_map.get(result["label"].lower(), "neutral")
            sentiment_score = result["score"]
            
            # Convert to -1 to 1 scale
            if sentiment_label == "negative":
                normalized_score = -sentiment_score
            elif sentiment_label == "positive":
                normalized_score = sentiment_score
            else:
                normalized_score = 0.0
            
            return {
                "text": text[:100] + "..." if len(text) > 100 else text,
                "label": sentiment_label,
                "score": float(sentiment_score),
                "normalized_score": float(normalized_score)
            }
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            return {
                "text": text[:100] + "..." if len(text) > 100 else text,
                "label": "neutral",
                "score": 0.0,
                "normalized_score": 0.0
            }
    
    def batch_analyze(self, texts: list) -> list:
        """
        Analyze sentiment for multiple texts
        
        Args:
            texts: List of texts to analyze
            
        Returns:
            List of sentiment analysis results
        """
        results = []
        for text in texts:
            results.append(self.analyze_sentiment(text))
        
        logger.info(f"Analyzed {len(results)} texts")
        return results
    
    def get_sentiment_statistics(self, sentiment_results: list) -> Dict:
        """
        Calculate statistics from sentiment analysis results
        
        Args:
            sentiment_results: List of sentiment analysis results
            
        Returns:
            Dictionary with sentiment statistics
        """
        if not sentiment_results:
            return {
                "total_count": 0,
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0,
                "average_score": 0.0,
                "positive_percentage": 0.0,
                "negative_percentage": 0.0,
                "neutral_percentage": 0.0
            }
        
        scores = [r["normalized_score"] for r in sentiment_results]
        labels = [r["label"] for r in sentiment_results]
        
        total = len(labels)
        positive = labels.count("positive")
        negative = labels.count("negative")
        neutral = labels.count("neutral")
        
        return {
            "total_count": total,
            "positive_count": positive,
            "negative_count": negative,
            "neutral_count": neutral,
            "average_score": float(np.mean(scores)),
            "std_dev": float(np.std(scores)),
            "min_score": float(np.min(scores)),
            "max_score": float(np.max(scores)),
            "positive_percentage": (positive / total * 100) if total > 0 else 0.0,
            "negative_percentage": (negative / total * 100) if total > 0 else 0.0,
            "neutral_percentage": (neutral / total * 100) if total > 0 else 0.0
        }


# Global singleton instance
_analyzer: Optional[FinBERTSentimentAnalyzer] = None


def get_analyzer(model_name: str = "ProsusAI/finbert") -> FinBERTSentimentAnalyzer:
    """
    Get or create sentiment analyzer instance
    
    Args:
        model_name: HuggingFace model identifier
        
    Returns:
        FinBERTSentimentAnalyzer instance
    """
    global _analyzer
    if _analyzer is None:
        _analyzer = FinBERTSentimentAnalyzer(model_name)
    return _analyzer


def analyze_headline(headline: str) -> Dict:
    """
    Analyze sentiment of a single headline
    
    Args:
        headline: News headline
        
    Returns:
        Sentiment analysis result
    """
    analyzer = get_analyzer()
    return analyzer.analyze_sentiment(headline)


def batch_analyze_headlines(headlines: list) -> list:
    """
    Analyze sentiment for multiple headlines
    
    Args:
        headlines: List of news headlines
        
    Returns:
        List of sentiment analysis results
    """
    analyzer = get_analyzer()
    return analyzer.batch_analyze(headlines)


# Example usage
if __name__ == "__main__":
    # Test the sentiment analyzer
    test_headlines = [
        "Apple announces record profits and expansion plans",
        "Tech stocks plunge amid market uncertainty",
        "Tesla shares remain stable as company updates guidance"
    ]
    
    analyzer = get_analyzer()
    
    print("Individual Analysis:")
    for headline in test_headlines:
        result = analyzer.analyze_sentiment(headline)
        print(f"Headline: {result['text']}")
        print(f"Label: {result['label']}, Score: {result['score']:.4f}")
        print(f"Normalized: {result['normalized_score']:.4f}")
        print("---")
    
    print("\nBatch Analysis:")
    results = batch_analyze_headlines(test_headlines)
    stats = analyzer.get_sentiment_statistics(results)
    print(f"Average Sentiment: {stats['average_score']:.4f}")
    print(f"Positive: {stats['positive_percentage']:.2f}%")
    print(f"Negative: {stats['negative_percentage']:.2f}%")
    print(f"Neutral: {stats['neutral_percentage']:.2f}%")
