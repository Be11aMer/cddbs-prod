"""Pytest configuration and shared fixtures."""
import pytest
import os
from sqlalchemy import create_engine, text
from src.cddbs.database import Base, engine as prod_engine
from src.cddbs.config import settings

# Override settings for tests
TEST_DB_NAME = "cddbs_test"
# Parse current production URL and replace DB name
orig_url = settings.DATABASE_URL
parts = orig_url.rsplit("/", 1)
TEST_DATABASE_URL = f"{parts[0]}/{TEST_DB_NAME}"

# Update settings so the rest of the app uses the test DB
settings.DATABASE_URL = TEST_DATABASE_URL

@pytest.fixture(scope='session', autouse=True)
def create_test_db():
    """Create database and tables before all tests.

    Skips gracefully if PostgreSQL is not available (e.g., local dev
    without Docker). Tests that don't need a DB will still run.
    """
    try:
        base_url = parts[0]
        maintenance_url = f"{base_url}/postgres"
        main_engine = create_engine(maintenance_url, isolation_level="AUTOCOMMIT")
        with main_engine.connect() as conn:
            # Check if test db exists
            res = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname='{TEST_DB_NAME}'"))
            if not res.fetchone():
                conn.execute(text(f"CREATE DATABASE {TEST_DB_NAME}"))

        # Now create tables in the test DB
        test_engine = create_engine(TEST_DATABASE_URL)
        Base.metadata.create_all(bind=test_engine)

        # Also patch the global engine used in the app code
        from src.cddbs import database
        database.engine = test_engine
        database.SessionLocal.configure(bind=test_engine)
    except Exception as exc:
        import warnings
        warnings.warn(
            f"PostgreSQL not available — DB-dependent tests will fail: {exc}",
            stacklevel=1,
        )

    yield
