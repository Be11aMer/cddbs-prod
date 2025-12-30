"""Tests for API helper functions."""
import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from src.cddbs.api.main import _get_or_create_outlet
from src.cddbs.database import SessionLocal
from src.cddbs.models import Outlet


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
    db_session.query(Outlet).delete()
    db_session.commit()


def test_get_or_create_outlet_new(db_session, cleanup_db):
    """Test _get_or_create_outlet creates new outlet."""
    outlet = _get_or_create_outlet(db_session, "NewOutlet", "newoutlet.com")

    assert outlet.id is not None
    assert outlet.name == "NewOutlet"
    assert outlet.url == "newoutlet.com"


def test_get_or_create_outlet_existing(db_session, cleanup_db):
    """Test _get_or_create_outlet returns existing outlet."""
    existing = Outlet(name="ExistingOutlet", url="existing.com")
    db_session.add(existing)
    db_session.commit()

    outlet = _get_or_create_outlet(db_session, "ExistingOutlet", "existing.com")

    assert outlet.id == existing.id
    assert outlet.name == "ExistingOutlet"


def test_get_or_create_outlet_updates_url(db_session, cleanup_db):
    """Test _get_or_create_outlet updates URL if changed."""
    existing = Outlet(name="TestOutlet", url="old.com")
    db_session.add(existing)
    db_session.commit()

    outlet = _get_or_create_outlet(db_session, "TestOutlet", "new.com")

    assert outlet.id == existing.id
    assert outlet.url == "new.com"


def test_get_or_create_outlet_handles_none_url(db_session, cleanup_db):
    """Test _get_or_create_outlet handles None URL."""
    outlet = _get_or_create_outlet(db_session, "TestOutlet", None)

    assert outlet.name == "TestOutlet"
    assert outlet.url is None

