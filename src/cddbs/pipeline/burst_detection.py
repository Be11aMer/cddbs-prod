"""Burst detection — identify keyword frequency spikes using z-score."""

import statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta, UTC

from src.cddbs.models import RawArticle, NarrativeBurst, EventCluster


Z_SCORE_THRESHOLD = 3.0
MIN_BASELINE_HOURS = 6  # need at least 6 hours of data for baseline


def detect_bursts(session, window_hours: int = 24) -> list[NarrativeBurst]:
    """Detect keyword frequency bursts in recent articles.

    Computes hourly keyword frequencies over the window, then flags
    keywords whose current frequency is > Z_SCORE_THRESHOLD standard
    deviations above the rolling mean.
    """
    cutoff = datetime.now(UTC) - timedelta(hours=window_hours)
    articles = (
        session.query(RawArticle)
        .filter(
            RawArticle.is_duplicate == False,
            RawArticle.created_at >= cutoff,
        )
        .order_by(RawArticle.created_at)
        .all()
    )

    if len(articles) < 10:
        return []

    # Extract keywords from titles (simple word frequency)
    hourly_keywords = _compute_hourly_frequencies(articles, window_hours)

    # Detect bursts
    new_bursts = []
    now = datetime.now(UTC)

    for keyword, hourly_counts in hourly_keywords.items():
        if len(hourly_counts) < MIN_BASELINE_HOURS:
            continue

        baseline = hourly_counts[:-1]
        current = hourly_counts[-1]

        if current == 0:
            continue

        mean = statistics.mean(baseline)
        std = statistics.stdev(baseline) if len(baseline) > 1 else 1.0
        z = (current - mean) / max(std, 0.1)

        if z >= Z_SCORE_THRESHOLD:
            burst = NarrativeBurst(
                keyword=keyword,
                baseline_frequency=round(mean, 2),
                current_frequency=round(current, 2),
                z_score=round(z, 2),
                detected_at=now,
            )
            new_bursts.append(burst)

    # Store bursts
    for burst in new_bursts:
        session.add(burst)

    if new_bursts:
        session.commit()

    return new_bursts


def _compute_hourly_frequencies(articles: list[RawArticle], window_hours: int) -> dict[str, list[float]]:
    """Compute per-keyword hourly article counts."""
    now = datetime.now(UTC)

    # Extract significant words from titles
    stop_words = {"the", "a", "an", "in", "on", "at", "to", "for", "of", "and", "or", "is",
                  "are", "was", "were", "be", "been", "has", "have", "had", "will", "with",
                  "by", "from", "that", "this", "it", "its", "as", "not", "but", "no", "new",
                  "says", "said", "after", "over", "more", "than", "up", "out", "about"}

    # Bucket articles by hour and extract keywords
    hourly_buckets: dict[int, list[str]] = defaultdict(list)

    for article in articles:
        ts = article.published_at or article.created_at
        if ts is None:
            continue
        hours_ago = int((now - ts).total_seconds() / 3600)
        if hours_ago < 0 or hours_ago >= window_hours:
            continue

        words = (article.title or "").lower().split()
        keywords = [w.strip(".,!?\"'()[]") for w in words if len(w) > 3 and w.lower() not in stop_words]
        hourly_buckets[hours_ago].extend(keywords)

    # Count keywords per hour
    all_keywords = Counter()
    for words in hourly_buckets.values():
        all_keywords.update(words)

    # Only track keywords appearing at least 5 times total
    significant_keywords = {kw for kw, count in all_keywords.items() if count >= 5}

    # Build hourly frequency arrays (oldest to newest)
    result: dict[str, list[float]] = {}
    for keyword in significant_keywords:
        counts = []
        for hour in range(window_hours - 1, -1, -1):  # oldest to newest
            hour_words = hourly_buckets.get(hour, [])
            count = hour_words.count(keyword)
            counts.append(float(count))
        result[keyword] = counts

    return result
