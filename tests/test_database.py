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



def test_failed_migration_does_not_skip_the_rest():
    """One bad migration must not silently disable every migration after it.

    PostgreSQL aborts the surrounding transaction on a failed statement, so
    running all migrations in one transaction meant the first failure caused
    every later one to fail with "current transaction is aborted" — logged as
    "skipped" while actually being unrecoverable. Each statement therefore gets
    its own transaction.
    """
    from sqlalchemy import inspect, text
    from src.cddbs import database

    marker = "migration_isolation_probe"
    with database.engine.begin() as conn:
        conn.execute(text(f"DROP TABLE IF EXISTS {marker}"))

    original = database._MIGRATIONS
    database._MIGRATIONS = [
        "ALTER TABLE table_that_does_not_exist ADD COLUMN IF NOT EXISTS x INT",
        f"CREATE TABLE IF NOT EXISTS {marker} (id INT)",
    ]
    try:
        database._run_migrations()
        # The statement after the failing one must still have been applied.
        assert inspect(database.engine).has_table(marker)
    finally:
        database._MIGRATIONS = original
        with database.engine.begin() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS {marker}"))
