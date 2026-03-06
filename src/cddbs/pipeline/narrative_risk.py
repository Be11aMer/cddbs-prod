"""Narrative risk scoring for event clusters."""

import json
from datetime import timedelta
from pathlib import Path

from src.cddbs.models import EventCluster, RawArticle, NarrativeBurst


_KNOWN_NARRATIVES_PATH = Path(__file__).parent.parent / "data" / "known_narratives.json"


def compute_risk_score(cluster: EventCluster, session) -> float:
    """Compute narrative risk score (0.0 to 1.0) for an event cluster.

    Components:
    - source_concentration: inverse of source diversity (few sources, many articles = high)
    - burst_magnitude: normalized burst z-score
    - timing_sync: how tightly packed the publication times are
    - narrative_match: overlap with known disinformation narratives
    """
    source_conc = _source_concentration(cluster)
    burst_mag = _burst_magnitude(cluster, session)
    timing = _timing_synchronization(cluster, session)
    narrative = _narrative_match(cluster)

    score = (source_conc + burst_mag + timing + narrative) / 4.0
    return round(min(max(score, 0.0), 1.0), 3)


def update_cluster_risk_scores(session) -> int:
    """Recompute risk scores for all active clusters. Returns count updated."""
    clusters = session.query(EventCluster).filter_by(status="active").all()
    updated = 0

    for cluster in clusters:
        new_score = compute_risk_score(cluster, session)
        if cluster.narrative_risk_score != new_score:
            cluster.narrative_risk_score = new_score
            updated += 1

    if updated:
        session.commit()

    return updated


def _source_concentration(cluster: EventCluster) -> float:
    """High when many articles from few unique sources."""
    if not cluster.article_count or cluster.article_count <= 1:
        return 0.0
    if not cluster.source_count or cluster.source_count <= 0:
        return 1.0
    ratio = 1.0 - (cluster.source_count / cluster.article_count)
    return max(0.0, min(ratio, 1.0))


def _burst_magnitude(cluster: EventCluster, session) -> float:
    """Normalized burst score from associated NarrativeBurst records."""
    if cluster.burst_score and cluster.burst_score > 0:
        return min(cluster.burst_score / 10.0, 1.0)

    # Check if any bursts reference this cluster
    bursts = (
        session.query(NarrativeBurst)
        .filter_by(cluster_id=cluster.id)
        .all()
    )
    if not bursts:
        return 0.0

    max_z = max(b.z_score for b in bursts if b.z_score)
    return min(max_z / 10.0, 1.0) if max_z else 0.0


def _timing_synchronization(cluster: EventCluster, session) -> float:
    """High when articles are published in a tight time window."""
    if not cluster.first_seen or not cluster.last_seen:
        return 0.0

    spread = (cluster.last_seen - cluster.first_seen).total_seconds() / 3600.0  # hours
    if spread <= 0:
        return 1.0  # all at once = maximum sync

    # Normalize: anything within 1 hour is high, 24+ hours is low
    sync = 1.0 - min(spread / 24.0, 1.0)
    return max(0.0, sync)


def _narrative_match(cluster: EventCluster) -> float:
    """Check cluster keywords against known disinformation narratives."""
    if not cluster.keywords:
        return 0.0

    try:
        with open(_KNOWN_NARRATIVES_PATH) as f:
            narratives_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return 0.0

    cluster_text = " ".join(cluster.keywords).lower()
    max_score = 0.0

    categories = narratives_data if isinstance(narratives_data, list) else narratives_data.get("categories", [])
    for category in categories:
        narratives = category.get("narratives", []) if isinstance(category, dict) else []
        for narrative in narratives:
            kw_list = narrative.get("keywords", [])
            matches = sum(1 for kw in kw_list if kw.lower() in cluster_text)
            if kw_list and matches > 0:
                score = min(matches / len(kw_list), 1.0)
                max_score = max(max_score, score)

    return max_score
