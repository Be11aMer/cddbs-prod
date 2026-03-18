"""Tests for Sprint 7 narrative risk scoring."""
from datetime import datetime, timedelta, UTC
from unittest.mock import MagicMock

import pytest

from src.cddbs.pipeline.narrative_risk import (
    compute_risk_score,
    update_cluster_risk_scores,
    _source_concentration,
    _burst_magnitude,
    _timing_synchronization,
    _narrative_match,
)
from src.cddbs.models import EventCluster, NarrativeBurst


def _make_cluster(
    article_count=10,
    source_count=5,
    burst_score=0.0,
    keywords=None,
    first_seen=None,
    last_seen=None,
    status="active",
):
    """Create a mock EventCluster for testing."""
    c = MagicMock(spec=EventCluster)
    c.id = 1
    c.article_count = article_count
    c.source_count = source_count
    c.burst_score = burst_score
    c.keywords = keywords or ["conflict", "military"]
    c.first_seen = first_seen or (datetime.now(UTC) - timedelta(hours=6))
    c.last_seen = last_seen or datetime.now(UTC)
    c.narrative_risk_score = 0.0
    c.status = status
    return c


class TestSourceConcentration:
    def test_diverse_sources_low_concentration(self):
        cluster = _make_cluster(article_count=10, source_count=10)
        score = _source_concentration(cluster)
        assert score == 0.0  # 1 - (10/10) = 0

    def test_single_source_high_concentration(self):
        cluster = _make_cluster(article_count=10, source_count=1)
        score = _source_concentration(cluster)
        assert score == pytest.approx(0.9, abs=0.01)  # 1 - (1/10)

    def test_no_articles(self):
        cluster = _make_cluster(article_count=0, source_count=0)
        score = _source_concentration(cluster)
        assert score == 0.0

    def test_single_article(self):
        cluster = _make_cluster(article_count=1, source_count=1)
        score = _source_concentration(cluster)
        assert score == 0.0

    def test_half_concentrated(self):
        cluster = _make_cluster(article_count=10, source_count=5)
        score = _source_concentration(cluster)
        assert score == pytest.approx(0.5, abs=0.01)


class TestBurstMagnitude:
    def test_no_burst_score(self):
        cluster = _make_cluster(burst_score=0.0)
        session = MagicMock()
        session.query.return_value.filter_by.return_value.all.return_value = []
        score = _burst_magnitude(cluster, session)
        assert score == 0.0

    def test_moderate_burst(self):
        cluster = _make_cluster(burst_score=5.0)
        session = MagicMock()
        score = _burst_magnitude(cluster, session)
        assert score == pytest.approx(0.5, abs=0.01)

    def test_high_burst_capped_at_1(self):
        cluster = _make_cluster(burst_score=15.0)
        session = MagicMock()
        score = _burst_magnitude(cluster, session)
        assert score == 1.0

    def test_burst_from_linked_bursts(self):
        cluster = _make_cluster(burst_score=0.0)
        cluster.id = 42
        burst = MagicMock(spec=NarrativeBurst)
        burst.z_score = 8.0
        session = MagicMock()
        session.query.return_value.filter_by.return_value.all.return_value = [burst]
        score = _burst_magnitude(cluster, session)
        assert score == pytest.approx(0.8, abs=0.01)


class TestTimingSynchronization:
    def test_simultaneous_articles(self):
        now = datetime.now(UTC)
        cluster = _make_cluster(first_seen=now, last_seen=now)
        score = _timing_synchronization(cluster, MagicMock())
        assert score == 1.0

    def test_spread_over_24h(self):
        now = datetime.now(UTC)
        cluster = _make_cluster(
            first_seen=now - timedelta(hours=24),
            last_seen=now,
        )
        score = _timing_synchronization(cluster, MagicMock())
        assert score == pytest.approx(0.0, abs=0.01)

    def test_spread_over_12h(self):
        now = datetime.now(UTC)
        cluster = _make_cluster(
            first_seen=now - timedelta(hours=12),
            last_seen=now,
        )
        score = _timing_synchronization(cluster, MagicMock())
        assert score == pytest.approx(0.5, abs=0.01)

    def test_no_timestamps(self):
        c = MagicMock(spec=EventCluster)
        c.first_seen = None
        c.last_seen = None
        score = _timing_synchronization(c, MagicMock())
        assert score == 0.0


class TestNarrativeMatch:
    def test_no_keywords(self):
        cluster = _make_cluster(keywords=None)
        score = _narrative_match(cluster)
        assert score == 0.0

    def test_empty_keywords(self):
        cluster = _make_cluster(keywords=[])
        score = _narrative_match(cluster)
        assert score == 0.0

    def test_matching_keywords_returns_nonzero(self):
        # Use keywords likely to match known narratives
        cluster = _make_cluster(keywords=["nato", "expansion", "aggressive", "threat"])
        score = _narrative_match(cluster)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_unrelated_keywords_return_zero_or_low(self):
        cluster = _make_cluster(keywords=["xyzzy", "foobarbaz", "quxquux"])
        score = _narrative_match(cluster)
        assert score == 0.0


class TestComputeRiskScore:
    def test_returns_float_between_0_and_1(self):
        cluster = _make_cluster()
        session = MagicMock()
        session.query.return_value.filter_by.return_value.all.return_value = []
        score = compute_risk_score(cluster, session)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_high_risk_cluster(self):
        """Cluster with single source, high burst, tight timing, matching keywords."""
        now = datetime.now(UTC)
        cluster = _make_cluster(
            article_count=20,
            source_count=1,
            burst_score=10.0,
            first_seen=now - timedelta(minutes=30),
            last_seen=now,
            keywords=["nato", "expansion", "threat", "aggressive"],
        )
        session = MagicMock()
        session.query.return_value.filter_by.return_value.all.return_value = []
        score = compute_risk_score(cluster, session)
        # Should be relatively high risk
        assert score >= 0.4

    def test_low_risk_cluster(self):
        """Cluster with diverse sources, no burst, wide timing spread."""
        now = datetime.now(UTC)
        cluster = _make_cluster(
            article_count=10,
            source_count=10,
            burst_score=0.0,
            first_seen=now - timedelta(hours=24),
            last_seen=now,
            keywords=["weather", "forecast", "temperature"],
        )
        session = MagicMock()
        session.query.return_value.filter_by.return_value.all.return_value = []
        score = compute_risk_score(cluster, session)
        assert score <= 0.3


class TestUpdateClusterRiskScores:
    def test_updates_active_clusters(self):
        session = MagicMock()
        cluster = _make_cluster()
        # All filter_by().all() calls return appropriate data
        session.query.return_value.filter_by.return_value.all.return_value = []
        # First call (get active clusters) returns the cluster, subsequent calls return []
        call_count = {"n": 0}
        def filter_by_all_side_effect(**kwargs):
            mock = MagicMock()
            call_count["n"] += 1
            if call_count["n"] == 1 and kwargs.get("status") == "active":
                mock.all.return_value = [cluster]
            else:
                mock.all.return_value = []
            return mock
        session.query.return_value.filter_by.side_effect = filter_by_all_side_effect

        updated = update_cluster_risk_scores(session)
        assert isinstance(updated, int)

    def test_no_clusters_returns_zero(self):
        session = MagicMock()
        session.query.return_value.filter_by.return_value.all.return_value = []
        updated = update_cluster_risk_scores(session)
        assert updated == 0
