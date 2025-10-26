from typing import Dict
import json
from src.cddbs.utils.genai_client import call_gemini

def digest_content(article: Dict, analysis: Dict) -> Dict:
    """Extract key claims and actors using Gemini."""
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
        return {
            "KEY_CLAIMS": [article.get("title")],
            "KEY_ACTORS": [],
            "NARRATIVE_THEMES": [],
            "UNVERIFIED_STATEMENTS": []
        }
    return result

