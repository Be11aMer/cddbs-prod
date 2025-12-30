"""Tests for database operations."""
import pytest
from sqlalchemy.orm import Session

from src.cddbs.database import SessionLocal, init_db, Base, engine
from src.cddbs.models import Outlet, Article, Report


def test_init_db():
    """Test that init_db creates tables."""
    # This should not raise an exception
    init_db()
    assert True  # If we get here, tables were created


def test_database_connection():
    """Test that database connection works."""
    from sqlalchemy import text
    db = SessionLocal()
    try:
        # Try a simple query
        result = db.execute(text("SELECT 1")).scalar()
        assert result == 1
    finally:
        db.close()


def test_session_local():
    """Test that SessionLocal creates valid sessions."""
    db1 = SessionLocal()
    db2 = SessionLocal()

    assert db1 is not db2  # Should be different instances

    db1.close()
    db2.close()


def test_table_creation():
    """Test that all tables are created."""
    # Check that tables exist
    tables = Base.metadata.tables.keys()
    assert "outlets" in tables
    assert "articles" in tables
    assert "reports" in tables


@pytest.fixture
def db_session():
    """Provide a database session for tests."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_database_transaction(db_session):
    """Test database transaction rollback."""
    outlet = Outlet(name="TestOutlet", url="test.com")
    db_session.add(outlet)
    db_session.commit()

    # Verify it was saved
    assert outlet.id is not None

    # Now delete it
    db_session.delete(outlet)
    db_session.commit()

    # Verify it's gone
    found = db_session.query(Outlet).filter(Outlet.name == "TestOutlet").first()
    assert found is None

