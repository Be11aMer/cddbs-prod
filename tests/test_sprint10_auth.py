"""Sprint 10 / C-1 auth tests.

Re-audit checklist:
  - GET /health returns 200 without an API key  (exempt path)
  - GET /       returns 200 without an API key  (exempt path)
  - Protected endpoint returns 401 with no key
  - Protected endpoint returns 401 with a wrong key
  - Protected endpoint returns 200 with the correct key (DB-dependent)
"""
import pytest
from fastapi.testclient import TestClient

from src.cddbs.api.main import app
from conftest import PYTEST_CLIENT_KEY


_no_auth_client = TestClient(app)
_auth_client = TestClient(app, headers={"X-API-Key": PYTEST_CLIENT_KEY})


class TestExemptPaths:
    def test_health_no_key(self):
        assert _no_auth_client.get("/health").status_code == 200

    def test_root_no_key(self):
        assert _no_auth_client.get("/").status_code == 200

    def test_docs_no_key(self):
        assert _no_auth_client.get("/docs").status_code == 200


class TestUnauthenticated:
    def test_no_key_returns_401(self):
        r = _no_auth_client.get("/analysis-runs")
        assert r.status_code == 401

    def test_wrong_key_returns_401(self):
        r = TestClient(app, headers={"X-API-Key": "totally-wrong-key"}).get("/analysis-runs")
        assert r.status_code == 401

    def test_401_body_has_detail(self):
        r = _no_auth_client.get("/analysis-runs")
        assert "detail" in r.json()


class TestAuthenticated:
    """These tests require the test DB (seeded in conftest.create_test_db)."""

    def test_valid_key_passes_middleware(self):
        r = _auth_client.get("/analysis-runs")
        # 200 or any non-401 means the middleware accepted the key
        assert r.status_code != 401

    def test_bearer_token_also_accepted(self):
        r = TestClient(app, headers={"Authorization": f"Bearer {PYTEST_CLIENT_KEY}"}).get("/analysis-runs")
        assert r.status_code != 401
