"""Sprint 10 API key authentication (C-1).

Implements:
- Argon2id hashing for stored API keys (OWASP recommended parameters)
- FastAPI middleware enforcing key on all routes except /health and /
- In-memory 5-min cache keyed by sha256(key) to avoid Argon2 per request
- Bootstrap: creates first key from CDDBS_BOOTSTRAP_API_KEY env var on startup

Re-audit checklist (C-1):
  - GET /health returns 200 without key  (exempt path)
  - All other endpoints return 401 without valid key  (middleware enforced)
"""
import hashlib
import os
from datetime import datetime, UTC, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.cddbs.database import SessionLocal
from src.cddbs.models import ApiKey

# Paths that bypass authentication
_EXEMPT_PATHS = {"/health", "/", "/docs", "/openapi.json", "/redoc"}

# Argon2id hasher — OWASP recommended parameters for interactive logins
_ph = PasswordHasher(
    time_cost=2,
    memory_cost=65536,  # 64 MiB
    parallelism=2,
    hash_len=32,
    salt_len=16,
)

# Short-lived cache: maps sha256(plaintext_key) -> expiry datetime.
# Never stores plaintext. Prevents Argon2 execution on every request.
_cache: dict[str, datetime] = {}
_CACHE_TTL = timedelta(minutes=5)


def _cache_hit(key: str) -> bool:
    fp = hashlib.sha256(key.encode()).hexdigest()
    expiry = _cache.get(fp)
    return expiry is not None and datetime.now(UTC) < expiry


def _cache_set(key: str) -> None:
    fp = hashlib.sha256(key.encode()).hexdigest()
    _cache[fp] = datetime.now(UTC) + _CACHE_TTL


def _verify_key_against_db(db, api_key: str) -> bool:
    """Verify api_key against all active DB records. Updates last_used_at on match."""
    if _cache_hit(api_key):
        return True

    try:
        active_keys = db.query(ApiKey).filter(ApiKey.is_active.is_(True)).all()
    except Exception:
        return False  # fail-closed: DB unavailable → deny

    for record in active_keys:
        try:
            _ph.verify(record.key_hash, api_key)
            record.last_used_at = datetime.now(UTC)
            db.commit()
            _cache_set(api_key)
            return True
        except (VerifyMismatchError, VerificationError):
            continue
        except Exception:
            continue
    return False


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Enforce X-API-Key authentication on all non-exempt endpoints."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        api_key = (
            request.headers.get("X-API-Key")
            or request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        )

        if not api_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required. Provide X-API-Key header."},
            )

        db = SessionLocal()
        try:
            valid = _verify_key_against_db(db, api_key)
        finally:
            db.close()

        if not valid:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or inactive API key."},
            )

        return await call_next(request)


def bootstrap_api_key() -> None:
    """On startup: if CDDBS_BOOTSTRAP_API_KEY is set and no keys exist, insert the hashed record."""
    plaintext = os.getenv("CDDBS_BOOTSTRAP_API_KEY", "").strip()
    if not plaintext:
        return

    db = SessionLocal()
    try:
        existing = db.query(ApiKey).first()
        if existing:
            return

        key_hash = _ph.hash(plaintext)
        prefix = plaintext[:8]
        record = ApiKey(
            name="bootstrap",
            key_prefix=prefix,
            key_hash=key_hash,
            is_active=True,
        )
        db.add(record)
        db.commit()
        print(f"INFO: Bootstrap API key created (prefix={prefix}...)")
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
