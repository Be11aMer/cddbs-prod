import requests
from typing import List, Dict
from src.cddbs.config import settings

def normalize_gl(country: str) -> str:
    country_map = {
        "russia": "ru",
        "united states": "us",
        "united kingdom": "uk",
        "france": "fr",
        "germany": "de",
        "china": "cn",
        "moldova": "md",
        "ukraine": "ua"
    }
    key = country.strip().lower()

    if key in country_map:
        return country_map[key]

    if len(key) == 2:
        return key

    # SAFE DEFAULT
    return "us"

def fetch_articles(outlet: str, country: str, num_articles: int = None, url: str = None, api_key: str = None, time_period: str = "m") -> List[Dict]:
    serpapi_key = api_key or settings.SERPAPI_KEY
    if not serpapi_key:
        # fallback mock for offline/testing
        print("DEBUG: No SerpAPI key found, using mock articles.")
        return [{
            "title": f"Mock article from {outlet}",
            "link": "https://example.com/mock",
            "snippet": "This is a mock snippet",
            "date": "2025-01-01T00:00:00Z",
            "meta": {},
            "full_text": "Mock full text content for testing."
        }]
    limit = num_articles if num_articles is not None else settings.ARTICLE_LIMIT

    gl_code = country.lower()
    gl_code = normalize_gl(gl_code)
    
    # Simple check: if still not 2 chars, SerpAPI will likely fail
    if len(gl_code) > 2:
        print(f"WARNING: Country code '{gl_code}' is longer than 2 chars, SerpAPI may fail.")

    query = outlet

    if url:
        clean_url = url.replace("https://", "").replace("http://", "").split("/")[0]
        query = f'"{outlet}" site:{clean_url}'
        
    params = {
        "engine": "google_news",
        "q": query,
        "gl": gl_code,
        "api_key": serpapi_key
    }
    
    # Add date filtering if provided
    # tbs values: qdr:h (hour), qdr:d (day), qdr:w (week), qdr:m (month), qdr:y (year)
    if time_period:
        params["tbs"] = f"qdr:{time_period}"

    print(f"DEBUG: fetch_articles calling SerpAPI with query: '{query}', gl: '{gl_code}', tbs: '{params.get('tbs')}'")
    try:
        res = requests.get("https://serpapi.com/search.json", params=params, timeout=20)
        res.raise_for_status()
        data = res.json()
        results = data.get("news_results", [])
        print(f"DEBUG: SerpAPI returned {len(results)} news_results")
        return results[:limit]
    except Exception as e:
        print(f"DEBUG: SerpAPI call failed: {e}")
        return []

