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
from argon2.exceptions import VerifyMismatchError

from src.cddbs.api.main import app
from src.cddbs.api.auth import bootstrap_api_key, _ph
from src.cddbs.database import SessionLocal
from src.cddbs.models import ApiKey
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


class TestBootstrapKeyRotation:
    """bootstrap_api_key() must rotate when CDDBS_BOOTSTRAP_API_KEY changes.

    Regression guard: the previous implementation bailed out whenever *any*
    key row existed, so changing the env var and redeploying silently did
    nothing and the old key stayed valid. These tests require the DB seeded
    by conftest.create_test_db and skip gracefully if it is unavailable.
    """

    OLD_KEY = "bootstrap-rotation-test-OLD-000000"
    NEW_KEY = "bootstrap-rotation-test-NEW-111111"

    @staticmethod
    def _clear_bootstrap(db):
        db.query(ApiKey).filter(ApiKey.name == "bootstrap").delete()
        db.commit()

    @pytest.fixture(autouse=True)
    def _clean_env_and_db(self, monkeypatch):
        try:
            db = SessionLocal()
        except Exception:
            pytest.skip("test DB unavailable")
        try:
            self._clear_bootstrap(db)
        except Exception:
            pytest.skip("test DB unavailable")
        yield
        self._clear_bootstrap(db)
        db.close()

    def _active_bootstrap(self, db):
        return db.query(ApiKey).filter(
            ApiKey.name == "bootstrap", ApiKey.is_active.is_(True)
        ).all()

    def test_first_time_seed(self, monkeypatch):
        monkeypatch.setenv("CDDBS_BOOTSTRAP_API_KEY", self.OLD_KEY)
        bootstrap_api_key()
        db = SessionLocal()
        try:
            active = self._active_bootstrap(db)
            assert len(active) == 1
            _ph.verify(active[0].key_hash, self.OLD_KEY)  # raises if mismatch
        finally:
            db.close()

    def test_idempotent_no_duplicate(self, monkeypatch):
        monkeypatch.setenv("CDDBS_BOOTSTRAP_API_KEY", self.OLD_KEY)
        bootstrap_api_key()
        bootstrap_api_key()  # same key again — must not add a second row
        db = SessionLocal()
        try:
            assert len(self._active_bootstrap(db)) == 1
        finally:
            db.close()

    def test_rotation_retires_old_key(self, monkeypatch):
        monkeypatch.setenv("CDDBS_BOOTSTRAP_API_KEY", self.OLD_KEY)
        bootstrap_api_key()
        monkeypatch.setenv("CDDBS_BOOTSTRAP_API_KEY", self.NEW_KEY)
        bootstrap_api_key()  # rotate

        db = SessionLocal()
        try:
            active = self._active_bootstrap(db)
            assert len(active) == 1
            # New key validates; old key no longer validates against active rows.
            _ph.verify(active[0].key_hash, self.NEW_KEY)
            with pytest.raises(VerifyMismatchError):
                _ph.verify(active[0].key_hash, self.OLD_KEY)
            # Old key row kept as audit trail but deactivated.
            all_bootstrap = db.query(ApiKey).filter(ApiKey.name == "bootstrap").all()
            assert any(not k.is_active for k in all_bootstrap)
        finally:
            db.close()
