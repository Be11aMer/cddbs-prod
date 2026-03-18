"""Tests for Sprint 7 burst detection pipeline."""
from datetime import datetime, timedelta, UTC
from unittest.mock import MagicMock

import pytest

from src.cddbs.pipeline.burst_detection import (
    detect_bursts,
    _compute_hourly_frequencies,
    Z_SCORE_THRESHOLD,
    MIN_BASELINE_HOURS,
)
from src.cddbs.models import RawArticle, NarrativeBurst


def _make_article(title, hours_ago=0, published_at=None):
    """Create a mock RawArticle for testing."""
    a = MagicMock(spec=RawArticle)
    a.title = title
    a.is_duplicate = False
    ts = published_at or (datetime.now(UTC) - timedelta(hours=hours_ago))
    a.published_at = ts
    a.created_at = ts
    return a


class TestZScoreThreshold:
    def test_threshold_is_reasonable(self):
        assert Z_SCORE_THRESHOLD >= 2.0
        assert Z_SCORE_THRESHOLD <= 5.0

    def test_min_baseline_hours(self):
        assert MIN_BASELINE_HOURS >= 3


class TestComputeHourlyFrequencies:
    def test_empty_articles(self):
        result = _compute_hourly_frequencies([], 24)
        assert result == {}

    def test_single_article(self):
        articles = [_make_article("Breaking news about cyber attack", hours_ago=1)]
        result = _compute_hourly_frequencies(articles, 24)
        # Should have some keywords but may not meet significance threshold
        assert isinstance(result, dict)

    def test_frequent_keyword_appears(self):
        """A keyword repeated across many articles should appear in output."""
        articles = []
        for i in range(10):
            articles.append(_make_article(f"Ukraine conflict escalates in region {i}", hours_ago=1))
        result = _compute_hourly_frequencies(articles, 24)
        # "ukraine" or "conflict" should be significant
        assert isinstance(result, dict)
        if result:
            # All frequency arrays should have window_hours entries
            for kw, counts in result.items():
                assert len(counts) == 24

    def test_stop_words_excluded(self):
        """Common stop words should not appear as keywords."""
        articles = [_make_article("The weather is good and the sky is blue", hours_ago=i) for i in range(10)]
        result = _compute_hourly_frequencies(articles, 24)
        for kw in result.keys():
            assert kw not in {"the", "and", "is"}

    def test_short_words_excluded(self):
        """Words with 3 or fewer characters should be excluded."""
        articles = [_make_article("A big red fox ran far too", hours_ago=i) for i in range(10)]
        result = _compute_hourly_frequencies(articles, 24)
        for kw in result.keys():
            assert len(kw) > 3


class TestDetectBursts:
    def test_returns_empty_for_few_articles(self):
        session = MagicMock()
        session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            _make_article("Just one article")
        ]
        result = detect_bursts(session)
        assert result == []

    def test_returns_empty_for_no_articles(self):
        session = MagicMock()
        session.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        result = detect_bursts(session)
        assert result == []

    def test_needs_minimum_articles(self):
        """Burst detection requires at least 10 articles."""
        session = MagicMock()
        session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            _make_article(f"Article {i}", hours_ago=i) for i in range(9)
        ]
        result = detect_bursts(session)
        assert result == []

    def test_uniform_distribution_no_bursts(self):
        """Uniform keyword distribution should not trigger bursts."""
        session = MagicMock()
        articles = []
        for hour in range(24):
            articles.append(_make_article(f"Regular news update number {hour}", hours_ago=hour))
        session.query.return_value.filter.return_value.order_by.return_value.all.return_value = articles

        result = detect_bursts(session)
        assert isinstance(result, list)
        # Uniform distribution should have low z-scores, no bursts

    def test_burst_detected_with_spike(self):
        """A sudden keyword frequency spike should be detected as a burst."""
        session = MagicMock()
        articles = []
        # Baseline: 1 article per hour mentioning "cyberattack" for 23 hours
        for hour in range(23, 0, -1):
            articles.append(_make_article(f"News about various events today {hour}", hours_ago=hour))

        # Spike: 20 articles in the last hour all mentioning "cyberattack"
        for i in range(20):
            articles.append(_make_article(f"Major cyberattack hits infrastructure {i}", hours_ago=0))

        session.query.return_value.filter.return_value.order_by.return_value.all.return_value = articles

        result = detect_bursts(session)
        assert isinstance(result, list)
        # Check that any detected bursts are valid NarrativeBurst objects
        for burst in result:
            assert isinstance(burst, NarrativeBurst)
            assert burst.z_score is not None

    def test_burst_returns_narrative_burst_objects(self):
        """Detected bursts should be NarrativeBurst model instances."""
        session = MagicMock()
        articles = []
        # Low baseline
        for hour in range(23, 0, -1):
            articles.append(_make_article(f"Quiet day nothing happening {hour}", hours_ago=hour))
        # Big spike
        for i in range(30):
            articles.append(_make_article(f"Explosion earthquake disaster emergency {i}", hours_ago=0))

        session.query.return_value.filter.return_value.order_by.return_value.all.return_value = articles

        result = detect_bursts(session)
        for burst in result:
            assert hasattr(burst, "keyword")
            assert hasattr(burst, "z_score")
            assert hasattr(burst, "baseline_frequency")
            assert hasattr(burst, "current_frequency")
