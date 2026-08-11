"""Webhook delivery for CDDBS alerts (Sprint 6)."""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import socket
from datetime import datetime, UTC
from typing import Optional
from urllib.parse import urlparse


SUPPORTED_EVENTS = [
    "pipeline_failure",
    "narrative_burst",
    "collector_failure",
    "batch_completed",
]


class WebhookURLError(ValueError):
    """Raised when a webhook URL is rejected by the SSRF guard."""


def validate_webhook_url(url: str) -> None:
    """Reject webhook URLs that could drive server-side request forgery.

    The server POSTs to operator-supplied webhook URLs, so an unvalidated URL
    is an SSRF primitive (e.g. cloud metadata at 169.254.169.254, or internal
    services). Allow only http/https to publicly-routable hosts; reject every
    address a hostname resolves to that is private, loopback, link-local,
    reserved, multicast, or unspecified. Called both at registration and
    immediately before delivery (so DNS rebinding can't slip past).

    Raises WebhookURLError if the URL is not allowed.
    """
    if not url or not isinstance(url, str):
        raise WebhookURLError("Webhook URL is required")

    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        raise WebhookURLError("Webhook URL must use http or https")
    host = parsed.hostname
    if not host:
        raise WebhookURLError("Webhook URL must include a host")

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise WebhookURLError(f"Webhook host does not resolve: {host}") from exc

    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise WebhookURLError(
                f"Webhook host {host} resolves to a disallowed address ({ip})"
            )


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

    # SSRF guard at the egress point — re-validate here (not just at
    # registration) so DNS rebinding between registration and delivery is caught.
    try:
        validate_webhook_url(url)
    except WebhookURLError as exc:
        print(f"Webhook delivery to {url} blocked by SSRF guard: {exc}")
        return False

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
