"""Tests for the X (Twitter) social-media collection path.

Covers the X API v2 fetch layer (`fetch_twitter_data`) and the Gemini failure
handling in `run_social_media_pipeline`, which had the same C-3 defect as
`orchestrator.py` — the "[Gemini error: ...]" sentinel being persisted as a
finished briefing.
"""
import asyncio
import json
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


def test_fetch_clamps_max_results_to_api_range(x_token):
    transport, captured = _mock_transport()
    real_client = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = transport
        return real_client(*args, **kwargs)

    with patch("src.cddbs.pipeline.social_media_pipeline.httpx.AsyncClient", factory):
        asyncio.run(fetch_twitter_data("@rt_com", max_posts=500))

    timeline_req = next(r for p, r in captured.items() if "tweets" in p)
    assert timeline_req.url.params["max_results"] == "100"


@pytest.mark.parametrize(
    "status,expected",
    [
        (401, "credentials"),
        (403, "access tier"),
        (404, "not found"),
    ],
)
def test_fetch_translates_api_errors(x_token, status, expected):
    transport, _ = _mock_transport(
        profile_status=status, profile_body={"detail": "denied"}
    )
    with pytest.raises(XAPIError, match=expected):
        _run_fetch(transport)


def test_fetch_reports_rate_limit_with_reset_header(x_token):
    transport, _ = _mock_transport(
        profile_status=429,
        profile_body={"detail": "Too Many Requests"},
        headers={"x-rate-limit-reset": "1770000000"},
    )
    with pytest.raises(XAPIError) as exc:
        _run_fetch(transport)

    message = str(exc.value)
    assert "429" in message
    assert "1770000000" in message


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
