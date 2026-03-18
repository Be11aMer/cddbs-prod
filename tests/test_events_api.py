"""Tests for Sprint 7 Events API endpoints."""
from datetime import datetime, UTC
import pytest

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.cddbs.api.main import app
from src.cddbs.database import SessionLocal
from src.cddbs.models import EventCluster, NarrativeBurst, RawArticle


client = TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def sample_cluster(db: Session):
    """Create a sample event cluster for testing."""
    cluster = EventCluster(
        title="Test Event: Conflict in Region",
        event_type="conflict",
        countries=["Ukraine", "Russia"],
        entities=None,
        keywords=["missile", "attack", "conflict"],
        first_seen=datetime.now(UTC),
        last_seen=datetime.now(UTC),
        article_count=5,
        source_count=3,
        burst_score=2.0,
        narrative_risk_score=0.65,
        status="active",
    )
    db.add(cluster)
    db.commit()
    db.refresh(cluster)
    yield cluster
    # Cleanup: delete articles linked to this cluster, then the cluster
    db.query(RawArticle).filter_by(cluster_id=cluster.id).update({"cluster_id": None})
    db.query(NarrativeBurst).filter_by(cluster_id=cluster.id).delete()
    db.delete(cluster)
    db.commit()


@pytest.fixture
def sample_burst(db: Session, sample_cluster):
    """Create a sample narrative burst for testing."""
    burst = NarrativeBurst(
        keyword="missile",
        baseline_frequency=1.5,
        current_frequency=8.0,
        z_score=4.3,
        cluster_id=sample_cluster.id,
        detected_at=datetime.now(UTC),
    )
    db.add(burst)
    db.commit()
    db.refresh(burst)
    yield burst
    db.delete(burst)
    db.commit()


class TestEventsListEndpoint:
    def test_get_events_returns_200(self):
        resp = client.get("/events")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_events_with_status_filter(self):
        resp = client.get("/events", params={"status": "active"})
        assert resp.status_code == 200

    def test_get_events_with_limit(self):
        resp = client.get("/events", params={"limit": 5})
        assert resp.status_code == 200
        assert len(resp.json()) <= 5

    def test_get_events_contains_cluster(self, sample_cluster):
        resp = client.get("/events", params={"status": "active"})
        assert resp.status_code == 200
        events = resp.json()
        ids = [e["id"] for e in events]
        assert sample_cluster.id in ids


class TestEventDetailEndpoint:
    def test_get_event_detail_returns_200(self, sample_cluster):
        resp = client.get(f"/events/{sample_cluster.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == sample_cluster.id
        assert data["title"] == "Test Event: Conflict in Region"
        assert data["event_type"] == "conflict"
        assert "Ukraine" in data["countries"]
        assert "missile" in data["keywords"]

    def test_get_event_detail_not_found(self):
        resp = client.get("/events/999999")
        assert resp.status_code == 404

    def test_event_detail_has_articles_list(self, sample_cluster):
        resp = client.get(f"/events/{sample_cluster.id}")
        data = resp.json()
        assert "articles" in data
        assert isinstance(data["articles"], list)


class TestEventsMapEndpoint:
    def test_get_events_map_returns_200(self):
        resp = client.get("/events/map")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_map_includes_country_with_events(self, sample_cluster):
        resp = client.get("/events/map")
        data = resp.json()
        countries = [item["country"] for item in data]
        # At least one of the cluster's countries should appear
        assert any(c in countries for c in ["Ukraine", "Russia"])

    def test_map_items_have_required_fields(self, sample_cluster):
        resp = client.get("/events/map")
        data = resp.json()
        if data:
            item = data[0]
            assert "country" in item
            assert "event_count" in item
            assert "avg_risk_score" in item


class TestBurstsEndpoint:
    def test_get_bursts_returns_200(self):
        resp = client.get("/events/bursts")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_burst_appears_in_list(self, sample_burst):
        resp = client.get("/events/bursts")
        data = resp.json()
        ids = [b["id"] for b in data]
        assert sample_burst.id in ids

    def test_burst_has_required_fields(self, sample_burst):
        resp = client.get("/events/bursts")
        data = resp.json()
        burst = next((b for b in data if b["id"] == sample_burst.id), None)
        assert burst is not None
        assert burst["keyword"] == "missile"
        assert burst["z_score"] == pytest.approx(4.3, abs=0.1)
        assert burst["baseline_frequency"] == pytest.approx(1.5, abs=0.1)
        assert burst["current_frequency"] == pytest.approx(8.0, abs=0.1)
