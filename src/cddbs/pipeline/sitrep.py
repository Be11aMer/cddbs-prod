"""Automated SitRep & cross-source framing analysis generator.

Generates AI threat briefings for high-risk EventClusters.
When a cluster has articles from multiple sources, the prompt
includes a cross-source framing comparison at zero extra API cost.

See docs/SCHEDULING.md for interval configuration.
See docs/RESOURCE_CONSTRAINTS.md for budget limits.
"""

import json
import logging
from datetime import datetime, UTC

from src.cddbs.config import settings
from src.cddbs.models import EventCluster, RawArticle, ThreatBriefing
from src.cddbs.utils.genai_client import call_gemini

logger = logging.getLogger(__name__)


def _build_sitrep_prompt(cluster: EventCluster, articles: list[RawArticle]) -> str:
    """Build a compact Gemini prompt for SitRep + optional framing analysis.

    This prompt is deliberately shorter than the full outlet analysis prompt
    to minimise token usage (~500 input / ~800 output).
    """
    # Group articles by source domain for framing comparison
    sources: dict[str, list[RawArticle]] = {}
    for a in articles:
        domain = a.source_domain or "unknown"
        sources.setdefault(domain, []).append(a)

    # Build articles section
    articles_text = ""
    for i, a in enumerate(articles[:20], 1):  # cap at 20 articles
        published = a.published_at.strftime("%Y-%m-%d %H:%M") if a.published_at else "unknown"
        articles_text += (
            f"--- Article {i} ---\n"
            f"Title: {a.title}\n"
            f"Source: {a.source_name} ({a.source_domain})\n"
            f"Source Type: {a.source_type}\n"
            f"Country: {a.country or 'unknown'}\n"
            f"Published: {published}\n"
            f"Language: {a.language or 'unknown'}\n"
        )
        if a.content:
            articles_text += f"Content: {a.content[:300]}\n"
        articles_text += "\n"

    # Determine if cross-source framing analysis applies
    unique_sources = len(sources)
    unique_source_types = len({a.source_type for a in articles if a.source_type})
    include_framing = unique_sources >= 3 or unique_source_types >= 2

    framing_section = ""
    if include_framing:
        framing_section = """
    "framing_analysis": {
        "source_framings": [
            {
                "source_domain": "example.com",
                "source_type": "rss or gdelt",
                "framing_summary": "How this source frames the event",
                "key_claims": ["Claim 1"],
                "omitted_facts": ["Important fact not mentioned"],
                "emotional_language_score": 0.0-1.0,
                "bias_direction": "pro-X / anti-Y / neutral"
            }
        ],
        "discrepancies": [
            {
                "topic": "What the discrepancy is about",
                "source_a": "source_a.com says X",
                "source_b": "source_b.com says Y",
                "assessment": "unverified / contradictory / selective_omission / spin"
            }
        ],
        "coordination_indicators": [
            "Description of any coordinated behavior patterns"
        ],
        "framing_divergence_score": 0.0-1.0
    },"""
    else:
        framing_section = '"framing_analysis": null,'

    return f"""You are a threat intelligence analyst for a Cyber Disinformation Detection system.

Analyze the following event cluster and produce a situational report (SitRep).

Event: {cluster.title or "Unknown event"}
Event Type: {cluster.event_type or "other"}
Countries: {", ".join(cluster.countries or [])}
Keywords: {", ".join(cluster.keywords or [])}
Articles: {len(articles)} from {unique_sources} distinct sources
Risk Score: {cluster.narrative_risk_score:.2f}
First Seen: {cluster.first_seen}
Last Seen: {cluster.last_seen}

Articles:
{articles_text}

STRICT RULES:
1. DO NOT invent claims, actors, or events not present in the articles.
2. ALWAYS attribute statements to their source.
3. Clearly separate facts from analytical assessment.
4. Flag unverified claims explicitly.

Output MUST be a valid JSON object:
{{
    "title": "Concise event title (max 15 words)",
    "executive_summary": "3-5 sentence intelligence-grade summary. State what happened, who is involved, and the assessed disinformation risk.",
    "event_assessment": {{
        "what_happened": "Factual summary of the event",
        "key_actors": ["Actor 1", "Actor 2"],
        "affected_regions": ["Region 1"],
        "timeline": "Brief chronological summary"
    }},
    "disinformation_risk": {{
        "risk_level": "critical / high / moderate / low",
        "risk_factors": ["Factor 1", "Factor 2"],
        "unverified_claims": ["Claim 1"],
        "propaganda_indicators": ["Indicator 1"],
        "narrative_alignment": "Which known disinformation narratives this event aligns with, if any"
    }},
    "source_diversity": {{
        "total_sources": {unique_sources},
        "source_types": {list({a.source_type for a in articles if a.source_type})},
        "geographic_spread": {list({a.country for a in articles if a.country})},
        "assessment": "How diverse and reliable are the reporting sources?"
    }},
    {framing_section}
    "analyst_notes": "Any additional observations, caveats, or recommended follow-up actions."
}}
"""


def generate_sitrep(
    cluster: EventCluster,
    session,
) -> ThreatBriefing | None:
    """Generate an automated SitRep (+ framing analysis) for a high-risk cluster.

    Returns the persisted ThreatBriefing, or None if generation fails.
    """
    # Check if already briefed
    existing = (
        session.query(ThreatBriefing)
        .filter_by(cluster_id=cluster.id, briefing_type="sitrep")
        .first()
    )
    if existing:
        logger.info("SitRep already exists for cluster %d, skipping", cluster.id)
        return None

    # Fetch articles in this cluster
    articles = (
        session.query(RawArticle)
        .filter_by(cluster_id=cluster.id, is_duplicate=False)
        .order_by(RawArticle.published_at.desc())
        .all()
    )

    if len(articles) < settings.CDDBS_SITREP_MIN_ARTICLES:
        logger.info(
            "Cluster %d has only %d articles (min %d), skipping",
            cluster.id, len(articles), settings.CDDBS_SITREP_MIN_ARTICLES,
        )
        return None

    prompt = _build_sitrep_prompt(cluster, articles)

    try:
        logger.info(
            "Generating SitRep for cluster %d (%s, %d articles, risk %.2f)",
            cluster.id, cluster.title, len(articles), cluster.narrative_risk_score,
        )
        raw_response = call_gemini(prompt, api_key=settings.GOOGLE_API_KEY)
    except Exception as exc:
        logger.error("SitRep Gemini call failed for cluster %d: %s", cluster.id, exc)
        return None

    # Parse response
    try:
        import re
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_response, re.DOTALL)
        if json_match:
            payload = json.loads(json_match.group(1))
        else:
            json_match = re.search(r'(\{.*\})', raw_response, re.DOTALL)
            payload = json.loads(json_match.group(1)) if json_match else {}
    except Exception as exc:
        logger.warning("SitRep JSON parse failed for cluster %d: %s", cluster.id, exc)
        payload = {}

    # Extract framing analysis separately
    framing = payload.pop("framing_analysis", None)

    # Determine briefing type
    briefing_type = "sitrep"
    if framing:
        briefing_type = "sitrep"  # still a sitrep, with framing embedded

    # Count unique sources
    unique_sources = len({a.source_domain for a in articles if a.source_domain})

    briefing = ThreatBriefing(
        cluster_id=cluster.id,
        briefing_type=briefing_type,
        title=payload.get("title", cluster.title),
        executive_summary=payload.get("executive_summary"),
        briefing_json=payload,
        framing_analysis=framing,
        raw_response=raw_response,
        articles_analyzed=len(articles),
        sources_compared=unique_sources,
        created_at=datetime.now(UTC),
    )

    session.add(briefing)
    session.commit()
    session.refresh(briefing)

    logger.info(
        "SitRep generated for cluster %d → briefing %d (framing: %s)",
        cluster.id, briefing.id, "yes" if framing else "no",
    )
    return briefing


def run_sitrep_cycle(session) -> list[ThreatBriefing]:
    """Run one SitRep generation cycle.

    Finds the top N highest-risk un-briefed clusters and generates SitReps.
    N is controlled by CDDBS_SITREP_MAX_PER_CYCLE (default 3).

    Returns list of generated ThreatBriefings.
    """
    from sqlalchemy import and_

    max_per_cycle = settings.CDDBS_SITREP_MAX_PER_CYCLE
    min_risk = settings.CDDBS_SITREP_MIN_RISK_SCORE
    min_articles = settings.CDDBS_SITREP_MIN_ARTICLES

    # Find qualifying clusters: active, high-risk, enough articles, not yet briefed
    already_briefed_ids = [
        row[0] for row in
        session.query(ThreatBriefing.cluster_id)
        .filter(ThreatBriefing.briefing_type == "sitrep")
        .filter(ThreatBriefing.cluster_id.isnot(None))
        .all()
    ]

    query = (
        session.query(EventCluster)
        .filter(
            and_(
                EventCluster.status == "active",
                EventCluster.narrative_risk_score >= min_risk,
                EventCluster.article_count >= min_articles,
            )
        )
        .order_by(EventCluster.narrative_risk_score.desc())
    )

    if already_briefed_ids:
        query = query.filter(EventCluster.id.notin_(already_briefed_ids))

    candidates = query.limit(max_per_cycle).all()

    if not candidates:
        logger.info("SitRep cycle: no qualifying clusters found (0 API calls)")
        return []

    logger.info(
        "SitRep cycle: found %d qualifying clusters (max %d per cycle)",
        len(candidates), max_per_cycle,
    )

    results = []
    for cluster in candidates:
        briefing = generate_sitrep(cluster, session)
        if briefing:
            results.append(briefing)

    logger.info("SitRep cycle complete: generated %d briefings", len(results))
    return results
