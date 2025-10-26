from typing import Dict
import json
from src.cddbs.utils.genai_client import call_gemini

def analyze_article(article: Dict) -> Dict:
    """Analyze article text with Gemini to identify disinformation signals."""
    text = article.get("full_text") or article.get("snippet") or article.get("title", "")
    prompt = f"""
    You are an intelligence analyst. Analyze following article for propaganda and disinformation patterns.
    Output JSON with keys: propaganda score (0-1),sentiment, framing, summary_notes.
    Article:
    {text}
    """
    try:
        result_text = call_gemini(prompt)
        result = json.loads(result_text)
    except Exception:
        # fallback in case Gemini returns plain text
        return {
            "propaganda_score": 0.2,
            "sentiment": "neutral",
            "framing": "informational",
            "analysis_notes": f"Analyzed length {len(text)}"
        }
    return result