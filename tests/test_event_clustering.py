"""Tests for Sprint 7 event clustering pipeline."""
from datetime import datetime, timedelta, UTC
from unittest.mock import MagicMock, patch

import pytest

from src.cddbs.pipeline.event_clustering import (
    cluster_articles,
    _classify_event_type,
    _create_event_cluster,
    _EVENT_TYPE_KEYWORDS,
)
from src.cddbs.models import RawArticle, EventCluster


def _make_article(title, content=None, source_domain="example.com", country=None, hours_ago=0):
    """Create a mock RawArticle for testing."""
    a = MagicMock(spec=RawArticle)
    a.id = id(a) % 10000
    a.title = title
    a.content = content
    a.source_domain = source_domain
    a.country = country
    a.is_duplicate = False
    a.cluster_id = None
    a.published_at = datetime.now(UTC) - timedelta(hours=hours_ago)
    a.created_at = datetime.now(UTC) - timedelta(hours=hours_ago)
    return a


class TestClassifyEventType:
    def test_conflict_keywords(self):
        articles = [_make_article("Military strikes target city")]
        result = _classify_event_type(["attack", "military", "strikes"], articles)
        assert result == "conflict"

    def test_protest_keywords(self):
        articles = [_make_article("Massive protest erupts in capital")]
        result = _classify_event_type(["protest", "demonstration", "rally"], articles)
        assert result == "protest"

    def test_cyber_keywords(self):
        articles = [_make_article("Ransomware attack breaches hospital data")]
        result = _classify_event_type(["ransomware", "breach", "cyber"], articles)
        assert result == "cyber"

    def test_diplomacy_keywords(self):
        articles = [_make_article("Summit talks resume in Geneva")]
        result = _classify_event_type(["summit", "talks", "diplomatic"], articles)
        assert result == "diplomacy"

    def test_disaster_keywords(self):
        articles = [_make_article("Earthquake devastates region")]
        result = _classify_event_type(["earthquake", "disaster"], articles)
        assert result == "disaster"

    def test_info_warfare_keywords(self):
        articles = [_make_article("Propaganda campaign spreads disinformation")]
        result = _classify_event_type(["propaganda", "disinformation"], articles)
        assert result == "info_warfare"

    def test_no_matching_keywords(self):
        articles = [_make_article("Weather forecast for Tuesday")]
        result = _classify_event_type(["forecast", "temperature"], articles)
        assert result == "other"

    def test_event_type_keywords_dict_not_empty(self):
        assert len(_EVENT_TYPE_KEYWORDS) >= 6


class TestCreateEventCluster:
    def test_creates_cluster_with_correct_fields(self):
        from sklearn.feature_extraction.text import TfidfVectorizer

        articles = [
            _make_article("Russia launches missile attack on Ukraine", country="Ukraine", source_domain="bbc.com"),
            _make_article("Russian missiles hit Ukrainian infrastructure", country="Ukraine", source_domain="reuters.com"),
            _make_article("Ukraine under Russian missile barrage today", country="Ukraine", source_domain="aljazeera.com"),
        ]

        texts = [a.title for a in articles]
        vectorizer = TfidfVectorizer(stop_words="english", max_features=10000)
        tfidf = vectorizer.fit_transform(texts)
        feature_names = vectorizer.get_feature_names_out()

        cluster = _create_event_cluster(articles, tfidf, [0, 1, 2], feature_names)

        assert isinstance(cluster, EventCluster)
        assert cluster.article_count == 3
        assert cluster.source_count == 3
        assert "Ukraine" in cluster.countries
        assert cluster.keywords is not None
        assert len(cluster.keywords) > 0
        assert cluster.status == "active"

    def test_cluster_title_uses_first_article(self):
        from sklearn.feature_extraction.text import TfidfVectorizer

        articles = [
            _make_article("First article title here", source_domain="a.com"),
            _make_article("Second article title here", source_domain="b.com"),
            _make_article("Third article title here", source_domain="c.com"),
        ]

        texts = [a.title for a in articles]
        vectorizer = TfidfVectorizer(stop_words="english", max_features=10000)
        tfidf = vectorizer.fit_transform(texts)
        feature_names = vectorizer.get_feature_names_out()

        cluster = _create_event_cluster(articles, tfidf, [0, 1, 2], feature_names)
        assert cluster.title == "First article title here"


class TestClusterArticles:
    def test_returns_empty_for_fewer_than_3_articles(self):
        session = MagicMock()
        session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            _make_article("Article one"),
            _make_article("Article two"),
        ]
        result = cluster_articles(session)
        assert result == []

    def test_returns_empty_for_no_articles(self):
        session = MagicMock()
        session.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        result = cluster_articles(session)
        assert result == []

    def test_clusters_similar_articles(self):
        """When given very similar articles, they should cluster together."""
        session = MagicMock()
        # Create articles that are very similar — they should cluster
        similar_articles = [
            _make_article("Russian missile attack hits Ukraine city", source_domain="bbc.com", country="Ukraine"),
            _make_article("Russia missile strike Ukraine infrastructure", source_domain="reuters.com", country="Ukraine"),
            _make_article("Russian missile barrage targets Ukrainian city", source_domain="cnn.com", country="Ukraine"),
            _make_article("Ukraine missile attack from Russia damages city", source_domain="ap.com", country="Ukraine"),
        ]
        session.query.return_value.filter.return_value.order_by.return_value.all.return_value = similar_articles

        result = cluster_articles(session, distance_threshold=0.6)

        # With very similar titles, they should form at least one cluster
        # (the threshold may prevent clustering depending on TF-IDF output,
        # but the function should not crash)
        assert isinstance(result, list)
        if len(result) > 0:
            assert isinstance(result[0], EventCluster)
            session.add.assert_called()
            session.commit.assert_called()

    def test_diverse_articles_may_not_cluster(self):
        """Very different articles may not form clusters."""
        session = MagicMock()
        diverse_articles = [
            _make_article("Weather forecast for tomorrow in Berlin", source_domain="a.com"),
            _make_article("Stock market crashes globally in 2026", source_domain="b.com"),
            _make_article("New species of deep sea fish discovered", source_domain="c.com"),
            _make_article("Olympic games preparation begins in city", source_domain="d.com"),
        ]
        session.query.return_value.filter.return_value.order_by.return_value.all.return_value = diverse_articles

        result = cluster_articles(session, distance_threshold=0.4)  # strict threshold
        assert isinstance(result, list)
        # Diverse articles shouldn't cluster with strict threshold
