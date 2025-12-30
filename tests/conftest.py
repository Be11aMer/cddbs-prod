"""Pytest configuration and shared fixtures."""
import pytest
from src.cddbs.database import Base, engine, SessionLocal
from src.cddbs import models


@pytest.fixture(scope='session', autouse=True)
def create_test_db():
    """Create database tables before all tests."""
    # Create tables (uses DATABASE_URL from env)
    Base.metadata.create_all(bind=engine)
    yield
    # Cleanup could go here if needed, but we're using test DB isolation
