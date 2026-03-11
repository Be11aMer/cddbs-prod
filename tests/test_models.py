"""Tests for SQLAlchemy models."""
import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from src.cddbs.database import SessionLocal
from src.cddbs.models import Outlet, Article, Report, Briefing, NarrativeMatch


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


def test_create_outlet(db_session, cleanup_db):
    """Test creating an outlet."""
    outlet = Outlet(name="TestOutlet", url="test.com")
    db_session.add(outlet)
    db_session.commit()

    assert outlet.id is not None
    assert outlet.name == "TestOutlet"
    assert outlet.url == "test.com"


def test_outlet_unique_constraint(db_session, cleanup_db):
    """Test that outlet names must be unique."""
    outlet1 = Outlet(name="Duplicate", url="test1.com")
    db_session.add(outlet1)
    db_session.commit()

    outlet2 = Outlet(name="Duplicate", url="test2.com")
    db_session.add(outlet2)

    with pytest.raises(Exception):  # Should raise IntegrityError
        db_session.commit()
    db_session.rollback()


def test_create_article(db_session, cleanup_db):
    """Test creating an article."""
    outlet = Outlet(name="TestOutlet", url="test.com")
    db_session.add(outlet)
    db_session.commit()

    article = Article(
        outlet_id=outlet.id,
        title="Test Article",
        link="http://test.com/article",
        snippet="Test snippet",
        date="2025-01-01",
        meta={"key": "value"},
        full_text="Full article text",
    )
    db_session.add(article)
    db_session.commit()

    assert article.id is not None
    assert article.title == "Test Article"
    assert article.outlet_id == outlet.id
    assert article.outlet == outlet


def test_article_relationship(db_session, cleanup_db):
    """Test article-outlet relationship."""
    outlet = Outlet(name="TestOutlet", url="test.com")
    db_session.add(outlet)
    db_session.commit()

    article1 = Article(outlet_id=outlet.id, title="Article 1")
    article2 = Article(outlet_id=outlet.id, title="Article 2")
    db_session.add(article1)
    db_session.add(article2)
    db_session.commit()

    # Test relationship
    assert len(outlet.articles) == 2
    assert article1.outlet == outlet
    assert article2.outlet == outlet


def test_create_report(db_session, cleanup_db):
    """Test creating a report."""
    report = Report(
        outlet="TestOutlet",
        country="US",
        final_report="Test Report Content",
        data={"key": "value"},
    )
    db_session.add(report)
    db_session.commit()

    assert report.id is not None
    assert report.outlet == "TestOutlet"
    assert report.country == "US"
    assert report.final_report == "Test Report Content"
    assert report.data == {"key": "value"}
    assert isinstance(report.created_at, datetime)


def test_report_with_null_fields(db_session, cleanup_db):
    """Test report with optional fields as None."""
    report = Report(
        outlet="TestOutlet",
        country=None,
        final_report=None,
        data=None,
    )
    db_session.add(report)
    db_session.commit()

    assert report.id is not None
    assert report.country is None
    assert report.final_report is None
    assert report.data is None


def test_article_requires_title(db_session, cleanup_db):
    """Test that article title is required."""
    outlet = Outlet(name="TestOutlet", url="test.com")
    db_session.add(outlet)
    db_session.commit()

    article = Article(outlet_id=outlet.id)  # Missing title
    db_session.add(article)

    with pytest.raises(Exception):  # Should raise IntegrityError
        db_session.commit()
    db_session.rollback()

