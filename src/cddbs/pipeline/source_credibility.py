"""Source Credibility Index — Phase 4A.

Computes a per-domain reliability score using data already present in the DB.
Zero Gemini API cost: entirely local aggregation from:
  - RawArticle (volume, cluster membership)
  - EventCluster.narrative_risk_score (propaganda signal proxy)
  - ThreatBriefing.framing_analysis (divergence + coordination signals)
  - NarrativeBurst (burst participation)

Runs on a configurable schedule (default 24h) via CddbsScheduler.

See docs/RESOURCE_CONSTRAINTS.md for budget notes.
See docs/SCHEDULING.md for interval configuration.
"""

import logging
from datetime import datetime, UTC
from collections import defaultdict

from sqlalchemy import func

from src.cddbs.models import (
    RawArticle,
    EventCluster,
    ThreatBriefing,
    NarrativeBurst,
    SourceCredibility,
)

logger = logging.getLogger(__name__)

# Minimum articles from a domain before we include it in scoring
MIN_ARTICLES_THRESHOLD = 5

# Weight factors for reliability_index formula (must sum to 1.0)
W_PROPAGANDA = 0.40   # avg_propaganda_score (most important signal)
W_DIVERGENCE = 0.30   # framing_divergence_score
W_COORDINATION = 0.20 # coordination_count (normalized)
W_BURST = 0.10        # burst_participation (normalized)

# Normalization cap for coordination_count and burst_participation
MAX_COORDINATION = 10   # 10+ coordination flags → max score
MAX_BURST = 20          # 20+ burst participations → max score


def _extract_coordination_domains(framing_analysis: dict) -> list[str]:
    """Extract source domains mentioned in coordination_indicators."""
    indicators = framing_analysis.get("coordination_indicators", [])
    # Indicators are free text — we can't reliably parse domain names from them.
    # Instead we count participation by looking at source_framings present in the cluster.
    # Return domains that appear in source_framings of clusters flagged with coordination.
    domains = []
    if indicators:
        for sf in framing_analysis.get("source_framings", []):
            domain = sf.get("source_domain")
            if domain:
                domains.append(domain)
    return domains


def compute_all_source_credibility(session) -> int:
    """Recompute SourceCredibility for every domain with sufficient data.

    Returns number of domain records created or updated.
    """
    now = datetime.now(UTC)

    # ── 1. Article volume per domain ────────────────────────────────────────
    article_counts: dict[str, int] = {}
    rows = (
        session.query(RawArticle.source_domain, func.count(RawArticle.id))
        .filter(RawArticle.is_duplicate == False, RawArticle.source_domain.isnot(None))
        .group_by(RawArticle.source_domain)
        .all()
    )
    for domain, count in rows:
        article_counts[domain] = count

    # Filter to domains with enough data
    qualifying = {d for d, c in article_counts.items() if c >= MIN_ARTICLES_THRESHOLD}
    if not qualifying:
        logger.info("Source credibility: no domains with >= %d articles, skipping", MIN_ARTICLES_THRESHOLD)
        return 0

    # ── 2. Propaganda score proxy: avg narrative_risk_score of clusters ─────
    # Per domain: find all clusters that contain articles from that domain,
    # take the average risk score.
    domain_risk_scores: dict[str, list[float]] = defaultdict(list)
    cluster_rows = (
        session.query(RawArticle.source_domain, EventCluster.narrative_risk_score)
        .join(EventCluster, RawArticle.cluster_id == EventCluster.id)
        .filter(
            RawArticle.is_duplicate == False,
            RawArticle.source_domain.isnot(None),
            RawArticle.cluster_id.isnot(None),
        )
        .all()
    )
    for domain, risk in cluster_rows:
        if domain in qualifying and risk is not None:
            domain_risk_scores[domain].append(float(risk))

    # ── 3. Framing divergence + coordination from ThreatBriefing.framing_analysis ──
    domain_divergence: dict[str, list[float]] = defaultdict(list)
    domain_coordination_count: dict[str, int] = defaultdict(int)

    briefings = (
        session.query(ThreatBriefing)
        .filter(
            ThreatBriefing.briefing_type == "sitrep",
            ThreatBriefing.framing_analysis.isnot(None),
        )
        .all()
    )

    for briefing in briefings:
        fa = briefing.framing_analysis
        if not fa or not isinstance(fa, dict):
            continue

        # Global divergence score for this cluster — assign to all sources in framing
        cluster_divergence = fa.get("framing_divergence_score")
        source_framings = fa.get("source_framings", [])

        for sf in source_framings:
            domain = sf.get("source_domain")
            if not domain or domain not in qualifying:
                continue
            if cluster_divergence is not None:
                domain_divergence[domain].append(float(cluster_divergence))

        # Coordination: if indicators are non-empty, all sources in that cluster
        # get a coordination_count increment
        coordination_indicators = fa.get("coordination_indicators", [])
        if coordination_indicators:
            coordinated_domains = _extract_coordination_domains(fa)
            for domain in coordinated_domains:
                if domain in qualifying:
                    domain_coordination_count[domain] += 1

    # ── 4. Burst participation: how often a domain's articles were present ───
    # during an active NarrativeBurst window
    domain_burst_count: dict[str, int] = defaultdict(int)
    burst_rows = (
        session.query(RawArticle.source_domain)
        .join(EventCluster, RawArticle.cluster_id == EventCluster.id)
        .join(NarrativeBurst, NarrativeBurst.cluster_id == EventCluster.id)
        .filter(
            RawArticle.is_duplicate == False,
            RawArticle.source_domain.isnot(None),
        )
        .all()
    )
    for (domain,) in burst_rows:
        if domain in qualifying:
            domain_burst_count[domain] += 1

    # ── 5. Compute reliability_index per domain and upsert ──────────────────
    updated = 0
    for domain in qualifying:
        # Propaganda score (0.0–1.0, higher = more propaganda)
        risk_list = domain_risk_scores.get(domain, [])
        avg_propaganda = sum(risk_list) / len(risk_list) if risk_list else 0.0

        # Framing divergence (0.0–1.0)
        div_list = domain_divergence.get(domain, [])
        avg_divergence = sum(div_list) / len(div_list) if div_list else 0.0

        # Coordination count (normalized to 0.0–1.0)
        coord_count = domain_coordination_count.get(domain, 0)
        coord_norm = min(coord_count / MAX_COORDINATION, 1.0)

        # Burst participation (normalized to 0.0–1.0)
        burst_count = domain_burst_count.get(domain, 0)
        burst_norm = min(burst_count / MAX_BURST, 1.0)

        # Reliability index: 1 = clean, 0 = adversarial
        # All component scores are "badness" (higher = worse), so:
        adversarial_score = (
            W_PROPAGANDA * avg_propaganda
            + W_DIVERGENCE * avg_divergence
            + W_COORDINATION * coord_norm
            + W_BURST * burst_norm
        )
        reliability = round(1.0 - min(adversarial_score, 1.0), 3)

        # Upsert
        existing = (
            session.query(SourceCredibility)
            .filter_by(source_domain=domain)
            .first()
        )

        if existing:
            prev = existing.reliability_index
            if prev is not None:
                delta = reliability - prev
                if delta > 0.02:
                    trend = "improving"
                elif delta < -0.02:
                    trend = "degrading"
                else:
                    trend = "stable"
                existing.previous_reliability_index = prev
                existing.trend_direction = trend
            existing.total_articles = article_counts[domain]
            existing.avg_propaganda_score = round(avg_propaganda, 3)
            existing.framing_divergence_score = round(avg_divergence, 3)
            existing.coordination_count = coord_count
            existing.burst_participation_count = burst_count
            existing.reliability_index = reliability
            existing.last_computed_at = now
        else:
            record = SourceCredibility(
                source_domain=domain,
                total_articles=article_counts[domain],
                avg_propaganda_score=round(avg_propaganda, 3),
                framing_divergence_score=round(avg_divergence, 3),
                coordination_count=coord_count,
                burst_participation_count=burst_count,
                reliability_index=reliability,
                trend_direction="stable",
                previous_reliability_index=None,
                last_computed_at=now,
            )
            session.add(record)

        updated += 1

    session.commit()
    logger.info("Source credibility updated for %d domains", updated)
    return updated
