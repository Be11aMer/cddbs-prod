"""Tests for the X (Twitter) social-media collection path.

Covers the X API v2 fetch layer (`fetch_twitter_data`) and the Gemini failure
handling in `run_social_media_pipeline`, which had the same C-3 defect as
`orchestrator.py` — the "[Gemini error: ...]" sentinel being persisted as a
finished briefing.
"""
import asyncio
import json
import logging
from unittest.mock import patch

import httpx
import pytest

from src.cddbs import models
from src.cddbs.database import SessionLocal
from src.cddbs.pipeline.social_media_pipeline import (
    XAPIError,
    fetch_twitter_data,
    run_social_media_pipeline,
)


PROFILE_PAYLOAD = {
    "data": {
        "id": "42",
        "username": "rt_com",
        "name": "RT",
        "description": "Russian state-controlled media",
        "created_at": "2009-03-14T00:00:00Z",
        "public_metrics": {
            "followers_count": 3180000,
            "following_count": 1247,
            "tweet_count": 245000,
            "listed_count": 15000,
        },
    }
}

TIMELINE_PAYLOAD = {
    "data": [
        {
            "id": "1",
            "text": "NATO expansion threatens European security",
            "created_at": "2026-02-10T12:00:00Z",
            "referenced_tweets": [{"type": "retweeted", "id": "999"}],
        }
    ],
    "includes": {
        "tweets": [{"id": "999", "author_id": "77"}],
        "users": [{"id": "77", "username": "SputnikInt"}],
    },
}


def _mock_transport(profile_status=200, timeline_status=200,
                    profile_body=None, timeline_body=None, headers=None):
    """Serve the two X API calls fetch_twitter_data makes, in order."""
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured[request.url.path] = request
        if "by/username" in request.url.path:
            return httpx.Response(
                profile_status,
                json=profile_body if profile_body is not None else PROFILE_PAYLOAD,
                headers=headers or {},
            )
        return httpx.Response(
            timeline_status,
            json=timeline_body if timeline_body is not None else TIMELINE_PAYLOAD,
            headers=headers or {},
        )

    return httpx.MockTransport(handler), captured


@pytest.fixture
def x_token(monkeypatch):
    from src.cddbs import config
    monkeypatch.setattr(config.settings, "TWITTER_BEARER_TOKEN", "test-bearer")
    # social_media_pipeline imports `settings` directly
    from src.cddbs.pipeline import social_media_pipeline
    monkeypatch.setattr(social_media_pipeline.settings, "TWITTER_BEARER_TOKEN", "test-bearer")


def _run_fetch(transport, handle="@rt_com"):
    real_client = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = transport
        return real_client(*args, **kwargs)

    with patch("src.cddbs.pipeline.social_media_pipeline.httpx.AsyncClient", factory):
        return asyncio.run(fetch_twitter_data(handle))


# ---------------------------------------------------------------------------
# Fetch layer
# ---------------------------------------------------------------------------

def test_fetch_requires_a_token(monkeypatch):
    from src.cddbs.pipeline import social_media_pipeline
    monkeypatch.setattr(social_media_pipeline.settings, "TWITTER_BEARER_TOKEN", "")
    with pytest.raises(ValueError, match="TWITTER_BEARER_TOKEN"):
        asyncio.run(fetch_twitter_data("@rt_com"))


def test_fetch_returns_profile_posts_and_includes(x_token):
    transport, _ = _mock_transport()
    data = _run_fetch(transport)

    assert data["profile"]["username"] == "rt_com"
    assert len(data["posts"]) == 1
    assert data["data_source"] == "x_api_v2"
    # `includes` must be carried through — the adapter needs it to attribute
    # amplification.
    assert data["includes"]["users"][0]["username"] == "SputnikInt"


def test_fetch_requests_the_referenced_tweet_expansions(x_token):
    """Without these expansions amplification_source can never be resolved."""
    transport, captured = _mock_transport()
    _run_fetch(transport)

    timeline_req = next(r for p, r in captured.items() if "tweets" in p)
    expansions = timeline_req.url.params["expansions"]
    assert "referenced_tweets.id" in expansions
    assert "referenced_tweets.id.author_id" in expansions


def test_fetch_uses_canonical_x_host(x_token):
    transport, captured = _mock_transport()
    _run_fetch(transport)
    assert all("api.x.com" in str(r.url) for r in captured.values())


def _fetch_with_max_posts(transport, max_posts):
    real_client = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = transport
        return real_client(*args, **kwargs)

    with patch("src.cddbs.pipeline.social_media_pipeline.httpx.AsyncClient", factory):
        asyncio.run(fetch_twitter_data("@rt_com", max_posts=max_posts))


@pytest.mark.parametrize(
    "requested,expected",
    [(500, "100"), (1, "5"), (30, "30")],
)
def test_fetch_clamps_max_results_to_api_range(x_token, requested, expected):
    """The API accepts 5-100; anything outside that is a 400 from X."""
    transport, captured = _mock_transport()
    _fetch_with_max_posts(transport, requested)

    timeline_req = next(r for p, r in captured.items() if "tweets" in p)
    assert timeline_req.url.params["max_results"] == expected


def test_fetch_defaults_to_configured_post_budget(x_token, monkeypatch):
    """X bills per post read, so the default must come from X_MAX_POSTS."""
    from src.cddbs.pipeline import social_media_pipeline
    monkeypatch.setattr(social_media_pipeline.settings, "X_MAX_POSTS", 25)

    transport, captured = _mock_transport()
    _run_fetch(transport)

    timeline_req = next(r for p, r in captured.items() if "tweets" in p)
    assert timeline_req.url.params["max_results"] == "25"


def test_explicit_max_posts_overrides_the_configured_default(x_token, monkeypatch):
    from src.cddbs.pipeline import social_media_pipeline
    monkeypatch.setattr(social_media_pipeline.settings, "X_MAX_POSTS", 25)

    transport, captured = _mock_transport()
    _fetch_with_max_posts(transport, 60)

    timeline_req = next(r for p, r in captured.items() if "tweets" in p)
    assert timeline_req.url.params["max_results"] == "60"


@pytest.mark.parametrize(
    "status,body,expected_cause",
    [
        (401, {"detail": "Unauthorized"}, "credentials"),
        (402, {"detail": "Payment Required"}, "billing"),
        (403, {"title": "Client Forbidden", "reason": "client-not-enrolled"}, "entitlement"),
        (403, {"detail": "Forbidden"}, "forbidden"),
        (429, {"title": "UsageCapExceeded", "period": "Monthly"}, "usage_cap"),
        (429, {"detail": "Too Many Requests"}, "rate_limit"),
        (404, {"detail": "Not Found"}, "not_found"),
        (500, {"detail": "boom"}, "unknown"),
    ],
)
def test_fetch_classifies_api_failures(x_token, status, body, expected_cause):
    transport, _ = _mock_transport(profile_status=status, profile_body=body)
    with pytest.raises(XAPIError) as exc:
        _run_fetch(transport)
    assert f"cause={expected_cause}" in str(exc.value)


@pytest.mark.parametrize(
    "status,body,credentials_accepted",
    [
        # Only a 401 means the token itself was rejected. Everything else is
        # X refusing an authenticated request.
        (401, {"detail": "Unauthorized"}, False),
        (402, {"detail": "Payment Required"}, True),
        (403, {"title": "Client Forbidden", "reason": "client-not-enrolled"}, True),
        (429, {"title": "UsageCapExceeded"}, True),
    ],
)
def test_failure_states_whether_credentials_were_accepted(
    x_token, status, body, credentials_accepted
):
    transport, _ = _mock_transport(profile_status=status, profile_body=body)
    with pytest.raises(XAPIError) as exc:
        _run_fetch(transport)
    assert f"credentials_accepted={credentials_accepted}" in str(exc.value)


def test_unfunded_pay_per_use_account_is_reported_as_billing_not_auth(x_token, caplog):
    """The exact case of a valid token on an account with no credits.

    Pay-per-use apps without credits return 403 client-not-enrolled. The logs
    must say the token authenticated, so this is not mistaken for a bad token.
    """
    transport, _ = _mock_transport(
        profile_status=403,
        profile_body={
            "title": "Client Forbidden",
            "reason": "client-not-enrolled",
            "required_enrollment": "Appropriate Level of API Access",
            "detail": "When authenticating requests to the X API v2 endpoints...",
        },
    )
    with caplog.at_level(logging.ERROR):
        with pytest.raises(XAPIError):
            _run_fetch(transport)

    log = caplog.text
    assert "x_auth=OK" in log
    assert "cause=entitlement" in log
    assert "authenticated successfully" in log
    assert "credits" in log
    # Must not imply the token is wrong
    assert "x_auth=FAILED" not in log


def test_bad_token_is_reported_as_an_auth_failure(x_token, caplog):
    transport, _ = _mock_transport(
        profile_status=401, profile_body={"detail": "Unauthorized"}
    )
    with caplog.at_level(logging.ERROR):
        with pytest.raises(XAPIError):
            _run_fetch(transport)

    log = caplog.text
    assert "x_auth=FAILED" in log
    assert "rejected the credentials" in log
    assert "x_auth=OK" not in log


def test_successful_call_logs_auth_ok(x_token, caplog):
    """Gives a positive signal that credentials work, not just failures."""
    transport, _ = _mock_transport()
    with caplog.at_level(logging.INFO):
        _run_fetch(transport)

    assert "x_auth=OK" in caplog.text
    assert "status=200" in caplog.text


def test_fetch_reports_rate_limit_with_reset_header(x_token, caplog):
    transport, _ = _mock_transport(
        profile_status=429,
        profile_body={"detail": "Too Many Requests"},
        headers={"x-rate-limit-reset": "1770000000"},
    )
    with caplog.at_level(logging.ERROR):
        with pytest.raises(XAPIError) as exc:
            _run_fetch(transport)

    assert "cause=rate_limit" in str(exc.value)
    assert "1770000000" in caplog.text


def test_fetch_raises_when_user_missing(x_token):
    transport, _ = _mock_transport(profile_body={"data": {}})
    with pytest.raises(ValueError, match="not found"):
        _run_fetch(transport)


# ---------------------------------------------------------------------------
# Amplification attribution, end to end through the adapter
# ---------------------------------------------------------------------------

def test_fetched_payload_resolves_amplification_source(x_token):
    from src.cddbs.adapters import TwitterAdapter

    transport, _ = _mock_transport()
    raw = _run_fetch(transport)

    briefing = TwitterAdapter().normalize(raw)
    assert briefing.posts[0].is_amplification is True
    assert briefing.posts[0].amplification_source == "SputnikInt"


# ---------------------------------------------------------------------------
# C-3 recurrence in the social pipeline
# ---------------------------------------------------------------------------

_HANDLE = "@c3-social-handle"


def _cleanup_reports():
    db = SessionLocal()
    try:
        for report in db.query(models.Report).filter(models.Report.outlet == _HANDLE).all():
            db.query(models.Briefing).filter(models.Briefing.report_id == report.id).delete()
            db.query(models.NarrativeMatch).filter(
                models.NarrativeMatch.report_id == report.id
            ).delete()
        db.query(models.Report).filter(models.Report.outlet == _HANDLE).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture
def clean_reports():
    _cleanup_reports()
    yield
    _cleanup_reports()


def _raw_data():
    return {
        "profile": PROFILE_PAYLOAD["data"],
        "posts": TIMELINE_PAYLOAD["data"],
        "includes": TIMELINE_PAYLOAD["includes"],
        "data_source": "x_api_v2",
        "collection_period": {},
    }


def test_social_pipeline_marks_failed_on_gemini_error(clean_reports):
    with patch("src.cddbs.pipeline.social_media_pipeline.call_gemini") as mock_gemini:
        mock_gemini.return_value = "[Gemini error: 503 Service Unavailable]"

        out = run_social_media_pipeline(
            platform="twitter", handle=_HANDLE, raw_data=_raw_data()
        )

    assert out["final_report"] is None

    db = SessionLocal()
    try:
        report = db.query(models.Report).filter(models.Report.outlet == _HANDLE).first()
        assert report.analysis_status == "failed"
        assert report.final_report is None
        assert report.data["status"] == "failed"
        assert "Gemini error" in report.raw_response
    finally:
        db.close()


def test_social_pipeline_skips_briefing_on_gemini_error(clean_reports):
    with patch("src.cddbs.pipeline.social_media_pipeline.call_gemini") as mock_gemini:
        mock_gemini.return_value = "[Gemini error: quota exhausted]"

        run_social_media_pipeline(
            platform="twitter", handle=_HANDLE, raw_data=_raw_data()
        )

    db = SessionLocal()
    try:
        report = db.query(models.Report).filter(models.Report.outlet == _HANDLE).first()
        count = db.query(models.Briefing).filter(
            models.Briefing.report_id == report.id
        ).count()
        assert count == 0
    finally:
        db.close()


def test_social_pipeline_completes_on_valid_output(clean_reports):
    payload = {
        "structured_briefing": {"section_1": "ok"},
        "final_briefing": "Real social briefing",
    }
    with patch("src.cddbs.pipeline.social_media_pipeline.call_gemini") as mock_gemini:
        mock_gemini.return_value = json.dumps(payload)

        out = run_social_media_pipeline(
            platform="twitter", handle=_HANDLE, raw_data=_raw_data()
        )

    assert out["final_report"] == "Real social briefing"

    db = SessionLocal()
    try:
        report = db.query(models.Report).filter(models.Report.outlet == _HANDLE).first()
        assert report.analysis_status == "completed"
        assert report.data["status"] == "completed"
    finally:
        db.close()


def test_social_pipeline_rejects_unknown_platform():
    with pytest.raises(ValueError, match="Unsupported platform"):
        run_social_media_pipeline(platform="mastodon", handle="@x", raw_data={})
