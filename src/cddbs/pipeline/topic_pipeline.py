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
from src.cddbs.pipeline.output_validator import validate_topic_comparative
from src.cddbs.pipeline.technique_taxonomy import normalize_techniques
from src.cddbs.utils.input_sanitizer import sanitize_text
from src.cddbs.utils.logger import get_logger

logger = get_logger(__name__)

# Length caps for externally-sourced article fields before prompt interpolation
_MAX_ARTICLE_TITLE_LENGTH = 500
_MAX_ARTICLE_SNIPPET_LENGTH = 2000


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


# Map short date_filter codes to Google News 'when:' query values
_WHEN_MAP = {
    "h": "1h",
    "d": "1d",
    "w": "7d",
    "m": "30d",
    "y": "1y",
}


def _serpapi_news(query: str, date_filter: str, limit: int, api_key: str) -> List[Dict]:
    # google_news engine does NOT support the tbs parameter.
    # Date filtering must be done via 'when:' operator in the query string.
    if date_filter:
        when_value = _WHEN_MAP.get(date_filter, date_filter)
        query = f"{query} when:{when_value}"
    params = {
        "engine": "google_news",
        "q": query,
        "api_key": api_key,
    }
    try:
        res = requests.get("https://serpapi.com/search.json", params=params, timeout=20)
        res.raise_for_status()
        data = res.json()
        results = data.get("news_results", [])
        logger.debug(f"SerpAPI q='{query}' returned {len(results)} results")
        return results[:limit]
    except Exception as e:
        logger.warning(f"SerpAPI call failed q='{query}': {e}")
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
        logger.warning(f"JSON parse error: {e}")
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
    logger.info(f"run_topic_pipeline start topic_run_id={topic_run_id} topic='{topic}'")
    api_key = serpapi_key or settings.SERPAPI_KEY

    session = SessionLocal()
    try:
        topic_run = session.query(models.TopicRun).filter(models.TopicRun.id == topic_run_id).first()
        if not topic_run:
            logger.warning(f"TopicRun topic_run_id={topic_run_id} not found")
            return

        # ------------------------------------------------------------------
        # Step 1/2 — Baseline: reuse cached TopicBaseline or generate fresh
        #
        # M-2: baselines are cached per-topic (keyed by a normalised topic_key)
        # and reused across runs so comparative results stay comparable —
        # regenerating the baseline on every run made scores non-comparable
        # since each run was scored against a different reference.
        # ------------------------------------------------------------------
        topic_key = topic.strip().lower()
        cached_baseline = (
            session.query(models.TopicBaseline)
            .filter(models.TopicBaseline.topic_key == topic_key)
            .first()
        )

        if cached_baseline:
            logger.info(f"Step 1/2 — reusing cached baseline topic_run_id={topic_run_id} topic_baseline_id={cached_baseline.id}")
            baseline_summary = cached_baseline.baseline_summary
            baseline_raw = cached_baseline.baseline_raw
            topic_run.baseline_id = cached_baseline.id
            topic_run.baseline_summary = baseline_summary
            topic_run.baseline_raw = baseline_raw
            topic_run.status = "running"
            session.commit()
            logger.info(f"Baseline reused from cache topic_run_id={topic_run_id} summary_length={len(baseline_summary or '')}")
        else:
            logger.info(f"Step 1 — fetching reference baseline articles topic_run_id={topic_run_id}")
            baseline_articles: List[Dict] = []

            if api_key:
                for ref in REFERENCE_OUTLETS:
                    arts = fetch_topic_articles(topic, ref["domain"], date_filter, limit=3, api_key=api_key)
                    for a in arts:
                        a["_source"] = ref["name"]
                    baseline_articles.extend(arts)
            else:
                logger.warning(f"No SerpAPI key — using mock baseline topic_run_id={topic_run_id}")
                baseline_articles = [{
                    "_source": "Reuters (mock)",
                    "title": f"Mock Reuters article on {topic}",
                    "link": "https://reuters.com/mock",
                    "snippet": "This is a mock snippet for testing without a live API key.",
                }]

            # Reference-outlet article title/snippet are externally sourced (SerpAPI) and
            # untrusted — sanitise and structurally fence before prompt interpolation
            # to defend against embedded prompt-injection payloads (OWASP LLM01).
            baseline_articles_data = ""
            for a in baseline_articles:
                safe_title = sanitize_text(a.get('title') or '', _MAX_ARTICLE_TITLE_LENGTH)
                safe_snippet = sanitize_text(a.get('snippet') or '', _MAX_ARTICLE_SNIPPET_LENGTH)
                baseline_articles_data += f"--- [{a.get('_source', 'Reference')}] ---\n"
                baseline_articles_data += "[BEGIN UNTRUSTED ARTICLE DATA]\n"
                baseline_articles_data += f"Title: {safe_title}\n"
                baseline_articles_data += f"Snippet: {safe_snippet}\n"
                baseline_articles_data += "[END UNTRUSTED ARTICLE DATA]\n\n"

            if not baseline_articles_data.strip():
                baseline_articles_data = f"No reference articles found for topic: {topic}"

            # ------------------------------------------------------------------
            # Step 2 — Gemini baseline call
            # ------------------------------------------------------------------
            logger.info(f"Step 2 — calling Gemini for baseline topic_run_id={topic_run_id}")
            baseline_prompt = get_baseline_prompt(topic, baseline_articles_data)
            baseline_raw = call_gemini(baseline_prompt, api_key=google_api_key)
            baseline_parsed = _parse_json_response(baseline_raw)

            baseline_summary = (
                baseline_parsed.get("baseline_summary")
                or f"Neutral wire-service coverage of '{topic}'. Reference articles analyzed: {len(baseline_articles)}."
            )

            new_baseline = models.TopicBaseline(
                topic=topic,
                topic_key=topic_key,
                baseline_summary=baseline_summary,
                baseline_raw=baseline_raw,
                reference_article_count=len(baseline_articles),
                model_version=settings.GEMINI_MODEL,
            )
            session.add(new_baseline)
            session.flush()  # get new_baseline.id

            topic_run.baseline_id = new_baseline.id
            topic_run.baseline_summary = baseline_summary
            topic_run.baseline_raw = baseline_raw
            topic_run.status = "running"
            session.commit()
            logger.info(f"Baseline generated and cached topic_run_id={topic_run_id} topic_baseline_id={new_baseline.id} summary_length={len(baseline_summary)}")

        # ------------------------------------------------------------------
        # Step 3 — Discover outlets
        # ------------------------------------------------------------------
        logger.info(f"Step 3 — discovering outlets topic_run_id={topic_run_id}")
        if api_key:
            discovered = discover_outlets(topic, date_filter, num_outlets, api_key)
        else:
            # Mock discovery when no API key
            discovered = [
                {"domain": "example-propaganda.com", "article_count": 8,
                 "examples": [{"title": f"Mock article on {topic}", "url": "https://example-propaganda.com/mock", "date": ""}]},
            ]
        logger.info(f"Discovered {len(discovered)} outlets topic_run_id={topic_run_id}: {[d['domain'] for d in discovered]}")

        # ------------------------------------------------------------------
        # Step 4 — Per-outlet comparative analysis
        # ------------------------------------------------------------------
        for i, outlet_info in enumerate(discovered):
            domain = outlet_info["domain"]
            logger.info(f"Step 4.{i+1} — analysing outlet={domain} topic_run_id={topic_run_id}")

            # Fetch outlet articles on topic
            if api_key:
                outlet_articles = fetch_topic_articles(topic, domain, date_filter, limit=5, api_key=api_key)
            else:
                outlet_articles = outlet_info.get("examples", [])

            # Outlet article title/snippet are externally sourced (SerpAPI) and
            # untrusted — sanitise and structurally fence before prompt interpolation
            # to defend against embedded prompt-injection payloads (OWASP LLM01).
            articles_data = ""
            article_links = []
            for a in outlet_articles:
                safe_title = sanitize_text(a.get('title') or '', _MAX_ARTICLE_TITLE_LENGTH)
                safe_snippet = sanitize_text(a.get('snippet') or a.get('title') or '', _MAX_ARTICLE_SNIPPET_LENGTH)
                articles_data += "[BEGIN UNTRUSTED ARTICLE DATA]\n"
                articles_data += f"Title: {safe_title}\n"
                articles_data += f"Snippet: {safe_snippet}\n"
                articles_data += "[END UNTRUSTED ARTICLE DATA]\n\n"
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
                logger.warning(f"Gemini call failed outlet={domain} topic_run_id={topic_run_id}: {e}")
                comp = {}
                comp_raw = str(e)

            # --- Output validation (H-2 / C-3) ---
            validation = validate_topic_comparative(comp)
            if not comp:
                analysis_status = "failed"
            elif not validation.is_valid:
                analysis_status = "partial"
                logger.warning(f"Validation errors outlet={domain} topic_run_id={topic_run_id}: {validation.errors}")
            else:
                analysis_status = "completed"
            validation_warnings = (validation.errors + validation.warnings) or None

            # --- Technique taxonomy normalisation (M-1) ---
            # Gemini returns free-text technique tags ("loaded language" vs
            # "emotionally loaded terminology" — same construct, different strings).
            # Map them onto a closed taxonomy so the coordination signal can match
            # techniques across outlets reliably; raw tags are preserved alongside.
            raw_techniques = comp.get("propaganda_techniques") or []
            normalized_techniques = normalize_techniques(raw_techniques) or None

            result = models.TopicOutletResult(
                topic_run_id=topic_run_id,
                outlet_name=domain,
                outlet_domain=domain,
                articles_analyzed=len(outlet_articles),
                divergence_score=comp.get("divergence_score"),
                amplification_signal=comp.get("amplification_signal"),
                propaganda_techniques=comp.get("propaganda_techniques"),
                propaganda_techniques_normalized=normalized_techniques,
                framing_summary=comp.get("framing_summary"),
                divergence_explanation=comp.get("divergence_explanation"),
                key_claims=comp.get("key_claims_by_outlet"),
                omissions=comp.get("omissions"),
                gemini_raw=comp_raw,
                article_links=article_links,
                analysis_status=analysis_status,
                validation_warnings=validation_warnings,
                model_version=settings.GEMINI_MODEL,
            )
            session.add(result)
            session.commit()
            logger.info(
                f"Committed result outlet={domain} topic_run_id={topic_run_id} "
                f"divergence_score={result.divergence_score} status={analysis_status}"
            )

        # ------------------------------------------------------------------
        # Step 5 — Coordination signal
        # Detect potential coordinated narrative pushing: outlets with divergence ≥60
        # that share ≥2 propaganda techniques are flagged as a coordination cluster.
        # ------------------------------------------------------------------
        logger.info(f"Step 5 — computing coordination signal topic_run_id={topic_run_id}")
        all_results = (
            session.query(models.TopicOutletResult)
            .filter(models.TopicOutletResult.topic_run_id == topic_run_id)
            .all()
        )
        high_divergence = [
            r for r in all_results
            if r.divergence_score is not None and r.divergence_score >= 60
            and r.propaganda_techniques
        ]

        coordination_signal = 0.0
        coordination_detail: Dict = {}
        if len(high_divergence) >= 2:
            # Build a frequency map of NORMALISED propaganda technique codes across
            # high-divergence outlets (M-1: matching on closed-taxonomy codes instead
            # of raw `.lower().strip()` strings catches synonymous tags — e.g. "loaded
            # language" and "emotionally loaded terminology" both normalise to
            # `loaded_language` — that previously caused the signal to be undercounted).
            technique_outlets: Dict[str, List[str]] = {}
            technique_names: Dict[str, str] = {}
            for r in high_divergence:
                for entry in normalize_techniques(r.propaganda_techniques or []):
                    code = entry["code"]
                    technique_names[code] = entry["name"]
                    outlets = technique_outlets.setdefault(code, [])
                    outlet_id = r.outlet_domain or r.outlet_name
                    if outlet_id not in outlets:
                        outlets.append(outlet_id)

            # Techniques shared by ≥2 high-divergence outlets
            shared = {code: outlets for code, outlets in technique_outlets.items() if len(outlets) >= 2}

            if shared:
                # Coordination signal = fraction of high-divergence outlets involved in any shared technique
                coordinated_outlet_set = {o for outlets in shared.values() for o in outlets}
                coordination_signal = round(len(coordinated_outlet_set) / max(len(all_results), 1), 3)
                coordination_detail = {
                    "shared_techniques": [technique_names[code] for code in shared],
                    "shared_technique_codes": list(shared.keys()),
                    "coordinated_outlets": list(coordinated_outlet_set),
                    "high_divergence_outlet_count": len(high_divergence),
                    "total_outlet_count": len(all_results),
                }
                logger.info(
                    f"Coordination signal topic_run_id={topic_run_id} "
                    f"signal={coordination_signal} shared={list(shared.keys())}"
                )

        topic_run.coordination_signal = coordination_signal
        topic_run.coordination_detail = coordination_detail if coordination_detail else None

        # ------------------------------------------------------------------
        # Step 6 — Finalize
        # ------------------------------------------------------------------
        topic_run.status = "completed"
        topic_run.completed_at = datetime.now(UTC)
        session.commit()
        logger.info(f"TopicRun topic_run_id={topic_run_id} completed")

    except Exception as e:
        logger.error(f"run_topic_pipeline error topic_run_id={topic_run_id}: {e}", exc_info=True)
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
