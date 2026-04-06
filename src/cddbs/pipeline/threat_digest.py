"""Daily threat intelligence digest generator.

Produces an executive summary of the threat landscape by aggregating
existing SitReps and NarrativeBursts — NOT raw articles.
This means very low token cost (~300 input / ~500 output).

If nothing significant happened, skips entirely (zero API cost).

See docs/SCHEDULING.md for interval configuration.
"""

import json
import logging
from datetime import datetime, timedelta, UTC

from src.cddbs.config import settings
from src.cddbs.models import ThreatBriefing, NarrativeBurst, EventCluster
from src.cddbs.utils.genai_client import call_gemini

logger = logging.getLogger(__name__)


def _build_digest_prompt(
    sitreps: list[ThreatBriefing],
    bursts: list[NarrativeBurst],
    period_start: datetime,
    period_end: datetime,
) -> str:
    """Build a compact prompt that summarises existing AI outputs."""

    sitrep_summaries = ""
    for i, s in enumerate(sitreps, 1):
        risk = s.briefing_json.get("disinformation_risk", {}) if s.briefing_json else {}
        sitrep_summaries += (
            f"--- SitRep {i}: {s.title or 'Untitled'} ---\n"
            f"Summary: {s.executive_summary or 'N/A'}\n"
            f"Risk Level: {risk.get('risk_level', 'unknown')}\n"
            f"Articles: {s.articles_analyzed}, Sources: {s.sources_compared}\n"
            f"Has Framing Analysis: {'Yes' if s.framing_analysis else 'No'}\n\n"
        )

    burst_summaries = ""
    for i, b in enumerate(bursts[:5], 1):
        burst_summaries += (
            f"- Keyword '{b.keyword}': z-score {b.z_score:.1f} "
            f"(baseline {b.baseline_frequency:.1f}/h → current {b.current_frequency:.1f}/h)\n"
        )

    return f"""You are a threat intelligence analyst. Write an executive daily threat digest.

Period: {period_start.strftime("%Y-%m-%d %H:%M UTC")} to {period_end.strftime("%Y-%m-%d %H:%M UTC")}

Recent automated SitReps:
{sitrep_summaries or "No SitReps generated in this period."}

Active keyword bursts (frequency spikes):
{burst_summaries or "No significant keyword bursts detected."}

RULES:
1. Summarise the threat landscape concisely — this is for executive consumption.
2. Highlight the most critical events and disinformation risks.
3. DO NOT invent information not present in the SitReps above.
4. If nothing significant is reported, state that clearly.

Output MUST be valid JSON:
{{
    "title": "Daily Threat Intel Digest — {period_end.strftime('%Y-%m-%d')}",
    "executive_summary": "3-5 sentence overview of today's threat landscape",
    "top_threats": [
        {{
            "event": "Event name",
            "risk_level": "critical/high/moderate/low",
            "key_concern": "Why this matters",
            "recommended_action": "What an analyst should do"
        }}
    ],
    "narrative_activity": {{
        "trending_keywords": ["keyword1", "keyword2"],
        "emerging_narratives": "Description of any emerging disinformation patterns",
        "declining_narratives": "Description of any declining patterns"
    }},
    "outlook": "Forward-looking assessment: what to watch for in the next 24-48 hours"
}}
"""


def generate_daily_digest(session) -> ThreatBriefing | None:
    """Generate a daily executive threat digest from recent SitReps and bursts.

    Returns None if nothing significant happened (saves API call).
    """
    now = datetime.now(UTC)
    interval_hours = settings.CDDBS_THREAT_DIGEST_INTERVAL_HOURS
    period_start = now - timedelta(hours=interval_hours)

    # Check if a digest was already generated in this period
    existing = (
        session.query(ThreatBriefing)
        .filter(
            ThreatBriefing.briefing_type == "daily_digest",
            ThreatBriefing.created_at >= period_start,
        )
        .first()
    )
    if existing:
        logger.info("Daily digest already exists for this period, skipping")
        return None

    # Gather recent SitReps
    sitreps = (
        session.query(ThreatBriefing)
        .filter(
            ThreatBriefing.briefing_type == "sitrep",
            ThreatBriefing.created_at >= period_start,
        )
        .order_by(ThreatBriefing.created_at.desc())
        .limit(5)
        .all()
    )

    # Gather active bursts
    bursts = (
        session.query(NarrativeBurst)
        .filter(
            NarrativeBurst.detected_at >= period_start,
            NarrativeBurst.resolved_at.is_(None),
        )
        .order_by(NarrativeBurst.z_score.desc())
        .limit(5)
        .all()
    )

    # Skip if nothing to report (zero API cost)
    if not sitreps and not bursts:
        logger.info("Daily digest: no SitReps or bursts in period, skipping (0 API calls)")
        return None

    prompt = _build_digest_prompt(sitreps, bursts, period_start, now)

    try:
        logger.info(
            "Generating daily digest (%d SitReps, %d bursts)",
            len(sitreps), len(bursts),
        )
        raw_response = call_gemini(prompt, api_key=settings.GOOGLE_API_KEY)
    except Exception as exc:
        logger.error("Daily digest Gemini call failed: %s", exc)
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
        logger.warning("Daily digest JSON parse failed: %s", exc)
        payload = {}

    digest = ThreatBriefing(
        cluster_id=None,  # digest spans multiple clusters
        briefing_type="daily_digest",
        title=payload.get("title", f"Daily Threat Intel Digest — {now.strftime('%Y-%m-%d')}"),
        executive_summary=payload.get("executive_summary"),
        briefing_json=payload,
        framing_analysis=None,
        raw_response=raw_response,
        articles_analyzed=sum(s.articles_analyzed for s in sitreps),
        sources_compared=sum(s.sources_compared for s in sitreps),
        period_start=period_start,
        period_end=now,
        created_at=now,
    )

    session.add(digest)
    session.commit()
    session.refresh(digest)

    logger.info("Daily digest generated: briefing %d", digest.id)
    return digest


def generate_quarterly_report(session, year: int, quarter: int) -> ThreatBriefing | None:
    """Compile a quarterly threat assessment from daily digests and SitReps.

    Triggered manually from the UI, not scheduled.

    Args:
        year: e.g. 2026
        quarter: 1-4
    """
    import calendar

    # Calculate quarter date range
    start_month = (quarter - 1) * 3 + 1
    end_month = start_month + 2
    _, last_day = calendar.monthrange(year, end_month)
    period_start = datetime(year, start_month, 1, tzinfo=UTC)
    period_end = datetime(year, end_month, last_day, 23, 59, 59, tzinfo=UTC)

    quarter_label = f"Q{quarter} {year}"

    # Gather all digests and sitreps in the quarter
    digests = (
        session.query(ThreatBriefing)
        .filter(
            ThreatBriefing.briefing_type == "daily_digest",
            ThreatBriefing.created_at >= period_start,
            ThreatBriefing.created_at <= period_end,
        )
        .order_by(ThreatBriefing.created_at)
        .all()
    )

    sitreps = (
        session.query(ThreatBriefing)
        .filter(
            ThreatBriefing.briefing_type == "sitrep",
            ThreatBriefing.created_at >= period_start,
            ThreatBriefing.created_at <= period_end,
        )
        .order_by(ThreatBriefing.created_at)
        .all()
    )

    # Build digest summaries
    digest_text = ""
    for d in digests:
        digest_text += f"- {d.title}: {d.executive_summary or 'N/A'}\n"

    sitrep_text = ""
    for s in sitreps:
        risk = s.briefing_json.get("disinformation_risk", {}) if s.briefing_json else {}
        sitrep_text += (
            f"- {s.title} (Risk: {risk.get('risk_level', '?')}, "
            f"{s.articles_analyzed} articles): {s.executive_summary or 'N/A'}\n"
        )

    # Get cluster stats
    total_clusters = (
        session.query(EventCluster)
        .filter(
            EventCluster.created_at >= period_start,
            EventCluster.created_at <= period_end,
        )
        .count()
    )

    prompt = f"""You are a senior threat intelligence analyst. Write a quarterly threat assessment report.

Period: {quarter_label} ({period_start.strftime('%Y-%m-%d')} to {period_end.strftime('%Y-%m-%d')})

Statistics:
- Daily digests generated: {len(digests)}
- SitReps generated: {len(sitreps)}
- Event clusters detected: {total_clusters}

Daily Digest Summaries:
{digest_text or "No daily digests available for this quarter."}

SitRep Summaries:
{sitrep_text or "No SitReps available for this quarter."}

Write a professional, publishable quarterly threat assessment. Output valid JSON:
{{
    "title": "CDDBS Quarterly Threat Assessment — {quarter_label}",
    "executive_summary": "5-8 sentence overview of the quarter's threat landscape",
    "key_themes": [
        {{
            "theme": "Theme name",
            "description": "Detailed description",
            "frequency": "How often this appeared",
            "trend": "increasing / stable / decreasing"
        }}
    ],
    "top_events": [
        {{
            "event": "Event name",
            "date_range": "When it occurred",
            "significance": "Why it matters",
            "disinformation_impact": "How disinformation actors exploited this"
        }}
    ],
    "source_landscape": {{
        "most_active_sources": ["source1", "source2"],
        "emerging_actors": "New disinformation actors observed",
        "reliability_trends": "Changes in source reliability"
    }},
    "recommendations": [
        "Recommendation for analysts and decision-makers"
    ],
    "outlook": "Forward-looking assessment for the next quarter"
}}
"""

    try:
        logger.info("Generating quarterly report for %s", quarter_label)
        raw_response = call_gemini(prompt, api_key=settings.GOOGLE_API_KEY)
    except Exception as exc:
        logger.error("Quarterly report Gemini call failed: %s", exc)
        return None

    try:
        import re
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_response, re.DOTALL)
        if json_match:
            payload = json.loads(json_match.group(1))
        else:
            json_match = re.search(r'(\{.*\})', raw_response, re.DOTALL)
            payload = json.loads(json_match.group(1)) if json_match else {}
    except Exception:
        payload = {}

    report = ThreatBriefing(
        cluster_id=None,
        briefing_type="quarterly_report",
        title=payload.get("title", f"CDDBS Quarterly Threat Assessment — {quarter_label}"),
        executive_summary=payload.get("executive_summary"),
        briefing_json=payload,
        raw_response=raw_response,
        articles_analyzed=sum(s.articles_analyzed for s in sitreps),
        sources_compared=sum(s.sources_compared for s in sitreps),
        period_start=period_start,
        period_end=period_end,
        created_at=datetime.now(UTC),
    )

    session.add(report)
    session.commit()
    session.refresh(report)

    logger.info("Quarterly report generated: briefing %d for %s", report.id, quarter_label)
    return report
