"""Tests for FastAPI endpoints."""
import pytest
from datetime import datetime, UTC
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.cddbs.api.main import app
from src.cddbs.database import SessionLocal
from src.cddbs.models import Report, Outlet, Article, Briefing, NarrativeMatch


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def db_session():
    """Provide a database session for tests."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def cleanup_db(db_session):
    """Clean up test data after each test."""
    yield
    # Delete in FK-safe order: children before parents
    db_session.query(NarrativeMatch).delete()
    db_session.query(Briefing).delete()
    db_session.query(Article).delete()
    db_session.query(Report).delete()
    db_session.query(Outlet).delete()
    db_session.commit()


def test_root_endpoint(client):
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "cddbs"
    assert data["status"] == "ok"


def test_health_endpoint(client, db_session):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_create_analysis_run(client, db_session, cleanup_db, monkeypatch):
    """Test creating a new analysis run."""
    # Mock the pipeline to avoid actual API calls
    def mock_run_pipeline(outlet: str, country: str):
        return {
            "outlet": outlet,
            "country": country,
            "articles": [{"title": "Test Article", "link": "http://test.com"}],
            "summaries": ["Summary 1"],
            "final_report": "Test Report",
        }

    from src.cddbs.pipeline import orchestrator
    monkeypatch.setattr(orchestrator, "run_pipeline", mock_run_pipeline)

    payload = {
        "outlet": "TestOutlet",
        "url": "test.com",
        "country": "US",
        "num_articles": 5,
    }

    response = client.post("/analysis-runs", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["outlet"] == "TestOutlet"
    assert data["country"] == "US"
    assert data["status"] == "queued"
    assert "id" in data
    assert "created_at" in data


def test_create_analysis_run_validation(client):
    """Test validation of analysis run creation."""
    # Test invalid num_articles (too high)
    payload = {
        "outlet": "Test",
        "url": "test.com",
        "country": "US",
        "num_articles": 25,  # Should be max 20
    }
    response = client.post("/analysis-runs", json=payload)
    assert response.status_code == 422

    # Test invalid num_articles (too low)
    payload["num_articles"] = 0
    response = client.post("/analysis-runs", json=payload)
    assert response.status_code == 422

    # Test missing required fields
    response = client.post("/analysis-runs", json={"outlet": "Test"})
    assert response.status_code == 422


def test_list_analysis_runs(client, db_session, cleanup_db):
    """Test listing analysis runs."""
    # Create some test reports
    report1 = Report(
        outlet="Outlet1",
        country="US",
        final_report="Report 1",
        data={"outlet": "Outlet1", "url": "outlet1.com", "country": "US", "articles_analyzed": 3},
    )
    report2 = Report(
        outlet="Outlet2",
        country="UK",
        final_report=None,
        data={"outlet": "Outlet2", "url": "outlet2.com", "country": "UK", "articles_analyzed": 0},
    )
    report3 = Report(
        outlet="Outlet3",
        country="RU",
        final_report="Report 3",
        data={
            "outlet": "Outlet3",
            "url": "outlet3.com",
            "country": "RU",
            "articles_analyzed": 5,
            "errors": ["Error message"],
        },
    )

    db_session.add(report1)
    db_session.add(report2)
    db_session.add(report3)
    db_session.commit()

    response = client.get("/analysis-runs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3

    # Check status determination
    statuses = {r["outlet"]: r["status"] for r in data}
    assert statuses["Outlet1"] == "completed"
    assert statuses["Outlet2"] == "running"
    assert statuses["Outlet3"] == "failed"


def test_get_analysis_run(client, db_session, cleanup_db):
    """Test getting a specific analysis run."""
    # Create test data
    outlet = Outlet(name="TestOutlet", url="test.com")
    db_session.add(outlet)
    db_session.commit()

    article = Article(
        outlet_id=outlet.id,
        title="Test Article",
        link="http://test.com/article",
        snippet="Test snippet",
        date="2025-01-01",
    )
    db_session.add(article)

    report = Report(
        outlet="TestOutlet",
        country="US",
        final_report="Test Report Content",
        data={
            "outlet": "TestOutlet",
            "url": "test.com",
            "country": "US",
            "analysis_date": datetime.now(UTC).isoformat(),
            "articles_analyzed": 1,
        },
    )
    report.articles.append(article)
    db_session.add(report)
    db_session.commit()

    response = client.get(f"/analysis-runs/{report.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == report.id
    assert data["outlet"] == "TestOutlet"
    assert data["final_report"] == "Test Report Content"
    assert data["meta"] is not None
    assert data["meta"]["outlet"] == "TestOutlet"
    assert len(data["articles"]) == 1
    assert data["articles"][0]["title"] == "Test Article"


def test_get_analysis_run_not_found(client):
    """Test getting a non-existent analysis run."""
    response = client.get("/analysis-runs/99999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_analysis_run_without_meta(client, db_session, cleanup_db):
    """Test getting a run with missing or invalid meta data."""
    report = Report(
        outlet="TestOutlet",
        country="US",
        final_report="Test Report",
        data=None,  # No meta data
    )
    db_session.add(report)
    db_session.commit()

    response = client.get(f"/analysis-runs/{report.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["meta"] is not None
    assert data["meta"]["outlet"] == "TestOutlet"


def test_get_analysis_run_with_invalid_meta(client, db_session, cleanup_db):
    """Test getting a run with invalid meta data format."""
    report = Report(
        outlet="TestOutlet",
        country="US",
        final_report="Test Report",
        data={"invalid": "data"},  # Missing required fields
    )
    db_session.add(report)
    db_session.commit()

    response = client.get(f"/analysis-runs/{report.id}")
    assert response.status_code == 200
    data = response.json()
    # Should handle gracefully
    assert data["id"] == report.id

