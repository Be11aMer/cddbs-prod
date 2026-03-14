"""Tests for Sprint 6 webhook delivery and endpoints."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.cddbs.webhooks import deliver_webhook, fire_event, SUPPORTED_EVENTS, sign_payload


# ---------------------------------------------------------------------------
# Unit tests for webhook module
# ---------------------------------------------------------------------------


def test_supported_events_list():
    assert "pipeline_failure" in SUPPORTED_EVENTS
    assert "narrative_burst" in SUPPORTED_EVENTS
    assert "collector_failure" in SUPPORTED_EVENTS
    assert "batch_completed" in SUPPORTED_EVENTS


def test_sign_payload_returns_hex_string():
    sig = sign_payload("hello world", "my-secret")
    assert isinstance(sig, str)
    assert len(sig) == 64  # SHA-256 hex digest


def test_sign_payload_is_deterministic():
    sig1 = sign_payload("same payload", "same secret")
    sig2 = sign_payload("same payload", "same secret")
    assert sig1 == sig2


def test_sign_payload_differs_with_different_secrets():
    sig1 = sign_payload("payload", "secret1")
    sig2 = sign_payload("payload", "secret2")
    assert sig1 != sig2


def test_sign_payload_differs_with_different_payloads():
    sig1 = sign_payload("payload A", "secret")
    sig2 = sign_payload("payload B", "secret")
    assert sig1 != sig2


@pytest.mark.asyncio
async def test_deliver_webhook_success():
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock(
            post=AsyncMock(return_value=mock_response)
        ))
        result = await deliver_webhook(
            "https://example.com/hook",
            "pipeline_failure",
            {"message": "test"},
        )
    assert result is True


@pytest.mark.asyncio
async def test_deliver_webhook_failure_status():
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock(
            post=AsyncMock(return_value=mock_response)
        ))
        result = await deliver_webhook(
            "https://example.com/hook",
            "narrative_burst",
            {},
        )
    assert result is False


@pytest.mark.asyncio
async def test_deliver_webhook_network_error():
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock(
            post=AsyncMock(side_effect=Exception("connection refused"))
        ))
        result = await deliver_webhook(
            "https://example.com/hook",
            "collector_failure",
            {},
        )
    assert result is False


@pytest.mark.asyncio
async def test_fire_event_invalid_type():
    with pytest.raises(ValueError, match="Unknown event type"):
        await fire_event("not_a_real_event", {})


@pytest.mark.asyncio
async def test_fire_event_no_db():
    """fire_event with no db_session returns 0 deliveries."""
    result = await fire_event("pipeline_failure", {"message": "test"}, db_session=None)
    assert result == 0
