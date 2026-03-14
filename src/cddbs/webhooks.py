"""Webhook delivery for CDDBS alerts (Sprint 6)."""
from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, UTC
from typing import Optional


SUPPORTED_EVENTS = [
    "pipeline_failure",
    "narrative_burst",
    "collector_failure",
    "batch_completed",
]


def sign_payload(payload: str, secret: str) -> str:
    """HMAC-SHA256 signature for webhook payload verification."""
    return hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


async def deliver_webhook(
    url: str,
    event_type: str,
    payload: dict,
    secret: Optional[str] = None,
) -> bool:
    """
    Deliver a webhook event to the configured URL.
    Returns True on success (2xx response), False otherwise.
    """
    body = json.dumps({
        "event": event_type,
        "timestamp": datetime.now(UTC).isoformat(),
        "data": payload,
    })

    headers = {"Content-Type": "application/json"}
    if secret:
        headers["X-CDDBS-Signature"] = sign_payload(body, secret)

    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, content=body, headers=headers)
            return 200 <= response.status_code < 300
    except Exception as e:
        print(f"Webhook delivery to {url} failed: {e}")
        return False


async def fire_event(
    event_type: str,
    payload: dict,
    db_session=None,
) -> int:
    """
    Find active webhooks subscribed to event_type and deliver to all of them.
    Returns count of successful deliveries.
    """
    if event_type not in SUPPORTED_EVENTS:
        raise ValueError(
            f"Unknown event type: {event_type}. Must be one of {SUPPORTED_EVENTS}"
        )

    if db_session is None:
        return 0

    from src.cddbs.models import WebhookConfig

    hooks = (
        db_session.query(WebhookConfig)
        .filter(WebhookConfig.active.is_(True))
        .all()
    )

    delivered = 0
    for hook in hooks:
        subscribed_events = hook.events or []
        if event_type not in subscribed_events and "*" not in subscribed_events:
            continue

        success = await deliver_webhook(
            url=hook.url,
            event_type=event_type,
            payload=payload,
            secret=hook.secret,
        )

        if success:
            hook.last_triggered_at = datetime.now(UTC).replace(tzinfo=None)
            hook.failure_count = 0
            delivered += 1
        else:
            hook.failure_count = (hook.failure_count or 0) + 1
            if hook.failure_count >= 10:
                hook.active = False  # disable after 10 consecutive failures

    db_session.commit()
    return delivered
