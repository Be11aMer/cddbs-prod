"""Topic Mode pipeline.

Discovers which outlets are using a given topic to push narratives,
by comparing their coverage against a neutral wire-service baseline.

Flow:
  1. Fetch reference articles (Reuters, BBC, AP, AFP) → Gemini baseline
  2. Broad SerpAPI search on topic → discover top non-reference outlets by frequency
  3. Per-outlet: fetch articles → Gemini comparative analysis → divergence score
  4. Persist results incrementally, mark TopicRun completed
"""
import json
import re
from datetime import datetime, UTC
from typing import List, Dict, Optional
from urllib.parse import urlparse

import requests

from src.cddbs.database import SessionLocal
from src.cddbs.config import settings
from src.cddbs import models
from src.cddbs.utils.genai_client import call_gemini
from src.cddbs.pipeline.topic_prompt_templates import get_baseline_prompt, get_comparative_prompt


# ---------------------------------------------------------------------------
# Reference outlet domains (neutral wire services used for baseline)
# ---------------------------------------------------------------------------

REFERENCE_OUTLETS = [
    {"name": "Reuters", "domain": "reuters.com"},
    {"name": "BBC", "domain": "bbc.com"},
    {"name": "Associated Press", "domain": "apnews.com"},
    {"name": "AFP", "domain": "afp.com"},
]

REFERENCE_DOMAINS = {o["domain"] for o in REFERENCE_OUTLETS}

# Additional well-known domains to exclude from discovery (mainstream neutral-ish)
EXCLUDED_DOMAINS = REFERENCE_DOMAINS | {
    "bbc.co.uk", "theguardian.com", "nytimes.com", "washingtonpost.com",
    "wsj.com", "economist.com", "ft.com", "dw.com", "france24.com",
    "aljazeera.com", "euronews.com", "politico.eu", "politico.com",
    "npr.org", "pbs.org", "cbc.ca", "abc.net.au", "google.com",
    "youtube.com", "twitter.com", "facebook.com", "reddit.com",
    # Non-news / reference / aggregator domains
    "wikipedia.org", "en.wikipedia.org", "britannica.com",
    "academia.edu", "researchgate.net", "jstor.org",
    "amazon.com", "goodreads.com", "imdb.com",
    "linkedin.com", "instagram.com", "tiktok.com", "pinterest.com",
    "medium.com", "substack.com", "quora.com",
    "archive.org", "web.archive.org",
}


# ---------------------------------------------------------------------------
# SerpAPI helpers
# ---------------------------------------------------------------------------

def _extract_domain(url: str) -> Optional[str]:
    try:
        parsed = urlparse(url)
        host = (parsed.netloc or parsed.path).lower()
        # Remove www. prefix properly (lstrip strips characters, not prefix)
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return None


def _serpapi_news(query: str, date_filter: str, limit: int, api_key: str) -> List[Dict]:
    params = {
        "engine": "google_news",
        "q": query,
        "api_key": api_key,
    }
    if date_filter:
        params["tbs"] = f"qdr:{date_filter}"
    try:
        res = requests.get("https://serpapi.com/search.json", params=params, timeout=20)
        res.raise_for_status()
        data = res.json()
        results = data.get("news_results", [])
        print(f"DEBUG topic: SerpAPI q='{query}' → {len(results)} results")
        return results[:limit]
    except Exception as e:
        print(f"DEBUG topic: SerpAPI call failed for q='{query}': {e}")
        return []


def fetch_topic_articles(topic: str, domain: str, date_filter: str, limit: int, api_key: str) -> List[Dict]:
    """Fetch articles about a topic from a specific domain via SerpAPI."""
    query = f'"{topic}" site:{domain}'
    return _serpapi_news(query, date_filter, limit, api_key)


def discover_outlets(topic: str, date_filter: str, num_outlets: int, api_key: str) -> List[Dict]:
    """Broad search for the topic → rank non-reference domains by article frequency."""
    results = _serpapi_news(topic, date_filter, 40, api_key)

    domain_counts: Dict[str, int] = {}
    domain_examples: Dict[str, List[Dict]] = {}

    for item in results:
        link = item.get("link") or ""
        domain = _extract_domain(link)
        if not domain or domain in EXCLUDED_DOMAINS:
            continue
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
        domain_examples.setdefault(domain, []).append({
            "title": item.get("title", ""),
            "url": link,
            "date": item.get("date", ""),
        })

    # Sort by article frequency descending (amplification proxy)
    ranked = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)
    return [
        {"domain": domain, "article_count": count, "examples": domain_examples[domain][:5]}
        for domain, count in ranked[:num_outlets]
    ]


# ---------------------------------------------------------------------------
# JSON parsing helper
# ---------------------------------------------------------------------------

def _parse_json_response(raw: str) -> Dict:
    try:
        m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL)
        if m:
            return json.loads(m.group(1).strip())
        m = re.search(r'(\{.*\})', raw, re.DOTALL)
        if m:
            return json.loads(m.group(1).strip())
        return json.loads(raw.strip())
    except Exception as e:
        print(f"DEBUG topic: JSON parse error: {e}")
        return {}


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_topic_pipeline(
    topic_run_id: int,
    topic: str,
    num_outlets: int,
    date_filter: str,
    serpapi_key: Optional[str] = None,
    google_api_key: Optional[str] = None,
):
    print(f"DEBUG topic: run_topic_pipeline start — topic_run_id={topic_run_id}, topic='{topic}'")
    api_key = serpapi_key or settings.SERPAPI_KEY

    session = SessionLocal()
    try:
        topic_run = session.query(models.TopicRun).filter(models.TopicRun.id == topic_run_id).first()
        if not topic_run:
            print(f"DEBUG topic: TopicRun {topic_run_id} not found")
            return

        # ------------------------------------------------------------------
        # Step 1 — Baseline: fetch from reference outlets
        # ------------------------------------------------------------------
        print("DEBUG topic: Step 1 — fetching reference baseline articles")
        baseline_articles: List[Dict] = []

        if api_key:
            for ref in REFERENCE_OUTLETS:
                arts = fetch_topic_articles(topic, ref["domain"], date_filter, limit=3, api_key=api_key)
                for a in arts:
                    a["_source"] = ref["name"]
                baseline_articles.extend(arts)
        else:
            print("DEBUG topic: No SerpAPI key — using mock baseline")
            baseline_articles = [{
                "_source": "Reuters (mock)",
                "title": f"Mock Reuters article on {topic}",
                "link": "https://reuters.com/mock",
                "snippet": "This is a mock snippet for testing without a live API key.",
            }]

        baseline_articles_data = ""
        for a in baseline_articles:
            baseline_articles_data += f"--- [{a.get('_source', 'Reference')}] ---\n"
            baseline_articles_data += f"Title: {a.get('title', '')}\n"
            baseline_articles_data += f"Snippet: {a.get('snippet', '')}\n\n"

        if not baseline_articles_data.strip():
            baseline_articles_data = f"No reference articles found for topic: {topic}"

        # ------------------------------------------------------------------
        # Step 2 — Gemini baseline call
        # ------------------------------------------------------------------
        print("DEBUG topic: Step 2 — calling Gemini for baseline")
        baseline_prompt = get_baseline_prompt(topic, baseline_articles_data)
        baseline_raw = call_gemini(baseline_prompt, api_key=google_api_key)
        baseline_parsed = _parse_json_response(baseline_raw)

        baseline_summary = (
            baseline_parsed.get("baseline_summary")
            or f"Neutral wire-service coverage of '{topic}'. Reference articles analyzed: {len(baseline_articles)}."
        )

        topic_run.baseline_summary = baseline_summary
        topic_run.baseline_raw = baseline_raw
        topic_run.status = "running"
        session.commit()
        print(f"DEBUG topic: Baseline committed. summary length={len(baseline_summary)}")

        # ------------------------------------------------------------------
        # Step 3 — Discover outlets
        # ------------------------------------------------------------------
        print("DEBUG topic: Step 3 — discovering outlets")
        if api_key:
            discovered = discover_outlets(topic, date_filter, num_outlets, api_key)
        else:
            # Mock discovery when no API key
            discovered = [
                {"domain": "example-propaganda.com", "article_count": 8,
                 "examples": [{"title": f"Mock article on {topic}", "url": "https://example-propaganda.com/mock", "date": ""}]},
            ]
        print(f"DEBUG topic: Discovered {len(discovered)} outlets: {[d['domain'] for d in discovered]}")

        # ------------------------------------------------------------------
        # Step 4 — Per-outlet comparative analysis
        # ------------------------------------------------------------------
        for i, outlet_info in enumerate(discovered):
            domain = outlet_info["domain"]
            print(f"DEBUG topic: Step 4.{i+1} — analysing outlet: {domain}")

            # Fetch outlet articles on topic
            if api_key:
                outlet_articles = fetch_topic_articles(topic, domain, date_filter, limit=5, api_key=api_key)
            else:
                outlet_articles = outlet_info.get("examples", [])

            articles_data = ""
            article_links = []
            for a in outlet_articles:
                articles_data += f"Title: {a.get('title', '')}\n"
                articles_data += f"Snippet: {a.get('snippet', a.get('title', ''))}\n\n"
                article_links.append({
                    "title": a.get("title", ""),
                    "url": a.get("link") or a.get("url", ""),
                    "date": a.get("date", ""),
                })

            if not articles_data.strip():
                articles_data = f"No articles found for {domain} on topic '{topic}'."

            # Gemini comparative call
            comp_prompt = get_comparative_prompt(topic, baseline_summary, domain, articles_data)
            try:
                comp_raw = call_gemini(comp_prompt, api_key=google_api_key)
                comp = _parse_json_response(comp_raw)
            except Exception as e:
                print(f"DEBUG topic: Gemini call failed for {domain}: {e}")
                comp = {}
                comp_raw = str(e)

            result = models.TopicOutletResult(
                topic_run_id=topic_run_id,
                outlet_name=domain,
                outlet_domain=domain,
                articles_analyzed=len(outlet_articles),
                divergence_score=comp.get("divergence_score"),
                amplification_signal=comp.get("amplification_signal"),
                propaganda_techniques=comp.get("propaganda_techniques"),
                framing_summary=comp.get("framing_summary"),
                divergence_explanation=comp.get("divergence_explanation"),
                gemini_raw=comp_raw,
                article_links=article_links,
            )
            session.add(result)
            session.commit()
            print(f"DEBUG topic: Committed result for {domain}, divergence_score={result.divergence_score}")

        # ------------------------------------------------------------------
        # Step 5 — Finalize
        # ------------------------------------------------------------------
        topic_run.status = "completed"
        topic_run.completed_at = datetime.now(UTC)
        session.commit()
        print(f"DEBUG topic: TopicRun {topic_run_id} completed.")

    except Exception as e:
        print(f"DEBUG topic: run_topic_pipeline ERROR: {e}")
        try:
            topic_run = session.query(models.TopicRun).filter(models.TopicRun.id == topic_run_id).first()
            if topic_run:
                topic_run.status = "failed"
                topic_run.error = str(e)
                session.commit()
        except Exception:
            pass
        session.rollback()
        raise e
    finally:
        session.close()
