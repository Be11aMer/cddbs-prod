import requests
from typing import List, Dict
from src.cddbs.config import settings

def fetch_articles(outlet: str, country: str) -> List[Dict]:
    """Fetch top N news articles using SerpAPI (placeholder)."""
    if not settings.SERPAPI_KEY:
        # fallback mock for offline/testing
        return [{
            "title": f"Mock article from {outlet}",
            "link": "https://example.com/mock",
            "snippet": "This is a mock snippet",
            "date": "2025-01-01T00:00:00Z",
            "meta": {},
            "full_text": "Mock full text content for testing."
        }]
    params = {
        "engine": "google_news",
        "q": outlet,
        "gl": country.lower(),
        "api_key": settings.SERPAPI_KEY
    }
    res = requests.get("https://serpapi.com/search.json", params=params, timeout=30)
    data = res.json()
    return data.get("news_results", [])[:settings.ARTICLE_LIMIT]
