"""Regression tests for the 2026-07-04 technical re-audit remediation.

Covers three findings from `docs/TECHNICAL_AUDIT_2026-07-04.md`:

* **N-4** — rate limits on the remaining expensive / mutation endpoints.
* **C-3** — the Gemini failure sentinel must never be stored as a briefing.
* **N-5** — a failed baseline must never be written to the TopicBaseline cache.

C-3 and N-5 share a root cause: ``call_gemini()`` signals failure by *returning*
``"[Gemini error: ...]"`` rather than raising, so every caller that persists
model output has to check for it explicitly.
"""
import pytest
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.cddbs import models
from src.cddbs.api.main import app, limiter
from src.cddbs.database import SessionLocal
from src.cddbs.utils.genai_client import GEMINI_ERROR_PREFIX, is_gemini_error
from conftest import PYTEST_CLIENT_KEY


@pytest.fixture
def client():
    return TestClient(app, headers={"X-API-Key": PYTEST_CLIENT_KEY})


@pytest.fixture
def reset_limiter():
    """Rate limits are process-global; clear them so tests don't bleed."""
    limiter.reset()
    yield
    limiter.reset()


# ---------------------------------------------------------------------------
# Sentinel detection (shared helper behind C-3 and N-5)
# ---------------------------------------------------------------------------

def test_is_gemini_error_detects_both_sentinel_forms():
    assert is_gemini_error("[Gemini error: No Google API key provided]")
    assert is_gemini_error("[Gemini error: 503 Service Unavailable]")
    # call_gemini() builds the sentinel from this prefix
    assert is_gemini_error(f"{GEMINI_ERROR_PREFIX} boom]")


def test_is_gemini_error_tolerates_leading_whitespace():
    assert is_gemini_error("\n  [Gemini error: timeout]")


def test_is_gemini_error_rejects_real_output_and_non_strings():
    assert not is_gemini_error('{"final_briefing": "Real analysis"}')
    assert not is_gemini_error("")
    assert not is_gemini_error(None)
    assert not is_gemini_error({"final_briefing": "x"})
    # A briefing that merely *mentions* the phrase is not a failure
    assert not is_gemini_error("The outlet reported a [Gemini error: ...] string.")


# ---------------------------------------------------------------------------
# C-3 — orchestrator must record a failed run, not a fake briefing
# ---------------------------------------------------------------------------

def _cleanup_outlet(name):
    db = SessionLocal()
    try:
        outlet = db.query(models.Outlet).filter(models.Outlet.name == name).first()
        report_q = db.query(models.Report).filter(models.Report.outlet == name)
        for report in report_q.all():
            db.query(models.Article).filter(models.Article.report_id == report.id).delete()
            db.query(models.Briefing).filter(models.Briefing.report_id == report.id).delete()
            db.query(models.NarrativeMatch).filter(
                models.NarrativeMatch.report_id == report.id
            ).delete()
        report_q.delete()
        if outlet:
            db.delete(outlet)
        db.commit()
    finally:
        db.close()


@pytest.fixture
def failing_outlet(monkeypatch):
    from src.cddbs import config
    monkeypatch.setattr(config.settings, "SERPAPI_KEY", None)
    monkeypatch.setattr(config.settings, "GOOGLE_API_KEY", None)
    name = "c3-failing-outlet"
    _cleanup_outlet(name)
    yield name
    _cleanup_outlet(name)


def test_orchestrator_marks_run_failed_on_gemini_error(failing_outlet):
    """The sentinel must produce analysis_status='failed', never 'completed'."""
    from src.cddbs.pipeline.orchestrator import run_pipeline

    with patch("src.cddbs.pipeline.orchestrator.call_gemini") as mock_gemini:
        mock_gemini.return_value = "[Gemini error: 503 Service Unavailable]"

        out = run_pipeline(failing_outlet, "US", num_articles=1)

    assert out["final_report"] is None
    assert out["quality_score"] is None

    db = SessionLocal()
    try:
        report = (
            db.query(models.Report)
            .filter(models.Report.outlet == failing_outlet)
            .first()
        )
        assert report is not None
        assert report.analysis_status == "failed"
        assert report.data["status"] == "failed"
        assert report.data["analysis_status"] == "failed"
    finally:
        db.close()


def test_orchestrator_never_stores_sentinel_as_final_report(failing_outlet):
    """The regression the audit flagged: error string persisted as a briefing."""
    from src.cddbs.pipeline.orchestrator import run_pipeline

    with patch("src.cddbs.pipeline.orchestrator.call_gemini") as mock_gemini:
        mock_gemini.return_value = "[Gemini error: quota exhausted]"

        run_pipeline(failing_outlet, "US", num_articles=1)

    db = SessionLocal()
    try:
        report = (
            db.query(models.Report)
            .filter(models.Report.outlet == failing_outlet)
            .first()
        )
        assert report.final_report is None
        # raw_response is kept deliberately, for diagnostics
        assert "Gemini error" in report.raw_response
        assert report.data["error"] == "[Gemini error: quota exhausted]"
    finally:
        db.close()


def test_orchestrator_skips_briefing_row_on_gemini_error(failing_outlet):
    """No Briefing (and so no quality score) should be produced for a failed run."""
    from src.cddbs.pipeline.orchestrator import run_pipeline

    with patch("src.cddbs.pipeline.orchestrator.call_gemini") as mock_gemini:
        mock_gemini.return_value = "[Gemini error: transport closed]"

        run_pipeline(failing_outlet, "US", num_articles=1)

    db = SessionLocal()
    try:
        report = (
            db.query(models.Report)
            .filter(models.Report.outlet == failing_outlet)
            .first()
        )
        briefings = (
            db.query(models.Briefing)
            .filter(models.Briefing.report_id == report.id)
            .count()
        )
        assert briefings == 0
    finally:
        db.close()


def test_orchestrator_still_completes_on_valid_output(failing_outlet):
    """Guard against the C-3 check swallowing healthy runs."""
    from src.cddbs.pipeline.orchestrator import run_pipeline

    with patch("src.cddbs.pipeline.orchestrator.call_gemini") as mock_gemini:
        mock_gemini.return_value = (
            '{"individual_analyses": [{"title": "A", "propaganda_score": 0.5}],'
            ' "final_briefing": "Real briefing text"}'
        )

        out = run_pipeline(failing_outlet, "US", num_articles=1)

    assert out["final_report"] == "Real briefing text"

    db = SessionLocal()
    try:
        report = (
            db.query(models.Report)
            .filter(models.Report.outlet == failing_outlet)
            .first()
        )
        assert report.analysis_status in ("completed", "partial")
        assert report.data["status"] == "completed"
    finally:
        db.close()


# ---------------------------------------------------------------------------
# N-5 — a failed baseline must not poison the cache
# ---------------------------------------------------------------------------

_N5_TOPIC = "n5-cache-guard-topic"


def _cleanup_baseline():
    db = SessionLocal()
    try:
        db.query(models.TopicBaseline).filter(
            models.TopicBaseline.topic_key == _N5_TOPIC.strip().lower()
        ).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture
def topic_run():
    """A TopicRun row plus a clean baseline cache for `_N5_TOPIC`."""
    _cleanup_baseline()
    db = SessionLocal()
    try:
        run = models.TopicRun(topic=_N5_TOPIC, status="pending")
        db.add(run)
        db.commit()
        db.refresh(run)
        run_id = run.id
    finally:
        db.close()

    yield run_id

    db = SessionLocal()
    try:
        db.query(models.TopicOutletResult).filter_by(topic_run_id=run_id).delete()
        db.query(models.TopicRun).filter_by(id=run_id).delete()
        db.commit()
    finally:
        db.close()
    _cleanup_baseline()


def _run_baseline_step(topic_run_id, baseline_response, monkeypatch):
    """Drive run_topic_pipeline far enough to exercise the baseline step.

    Outlet discovery is stubbed to empty so the run stops right after the
    baseline is (or is not) cached — that is the only stage N-5 concerns.
    Returns the mock so callers can assert the baseline call actually happened.
    """
    from src.cddbs import config
    from src.cddbs.pipeline import topic_pipeline

    monkeypatch.setattr(config.settings, "SERPAPI_KEY", None)
    monkeypatch.setattr(config.settings, "GOOGLE_API_KEY", None)

    with (
        patch.object(topic_pipeline, "call_gemini") as mock_gemini,
        patch.object(topic_pipeline, "discover_outlets", return_value=[]),
    ):
        mock_gemini.return_value = baseline_response
        topic_pipeline.run_topic_pipeline(
            topic_run_id=topic_run_id,
            topic=_N5_TOPIC,
            num_outlets=1,
            date_filter="m",
        )

    # Fails loudly if the pipeline never reached the baseline Gemini call,
    # which would make the cache assertions below pass vacuously.
    assert mock_gemini.call_count >= 1, "baseline step was never reached"
    return mock_gemini


def _cached_baselines():
    db = SessionLocal()
    try:
        return (
            db.query(models.TopicBaseline)
            .filter(models.TopicBaseline.topic_key == _N5_TOPIC.strip().lower())
            .all()
        )
    finally:
        db.close()


def test_failed_baseline_is_not_cached(topic_run, monkeypatch):
    """A '[Gemini error: ...]' baseline must never reach TopicBaseline.

    Before this guard the sentinel was cached and, because the cache is only
    invalidated by hand, reused for that topic indefinitely.
    """
    _run_baseline_step(topic_run, "[Gemini error: baseline call failed]", monkeypatch)

    assert _cached_baselines() == [], "failed baseline was written to the cache"


def test_successful_baseline_is_still_cached(topic_run, monkeypatch):
    """Guard against the N-5 check disabling caching altogether."""
    _run_baseline_step(
        topic_run, '{"baseline_summary": "Neutral wire coverage."}', monkeypatch
    )

    cached = _cached_baselines()
    assert len(cached) == 1
    assert cached[0].baseline_summary == "Neutral wire coverage."


# ---------------------------------------------------------------------------
# N-4 — rate limits on the remaining expensive / mutation endpoints
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "path",
    [
        "/feedback",
        "/stats/source-credibility/refresh",
        "/threat-briefings/quarterly",
    ],
)
def test_flagged_endpoints_are_rate_limited(path):
    """Each N-4 endpoint must carry a slowapi limit.

    slowapi records limits against the endpoint's qualified name, so this
    asserts the decorator is actually attached to the route we think it is.
    """
    route = next(r for r in app.routes if getattr(r, "path", None) == path
                 and "POST" in getattr(r, "methods", set()))
    key = f"{route.endpoint.__module__}.{route.endpoint.__qualname__}"
    limits = limiter._route_limits.get(key)
    assert limits, f"POST {path} has no rate limit (N-4)"


def test_feedback_returns_429_when_limit_exceeded(client, reset_limiter):
    """Behavioural check that the limiter actually fires."""
    payload = {
        "tester_name": "rate-limit-probe",
        "tester_role": "qa",
        "overall_rating": 4,
        "accuracy_rating": 4,
        "usability_rating": 4,
        "bugs_encountered": "none observed",
    }

    statuses = [client.post("/feedback", json=payload).status_code for _ in range(12)]

    # The first calls must actually succeed, otherwise a validation error could
    # mask the limiter never being reached.
    assert statuses[0] == 200, f"first request failed: {statuses[0]}"
    assert 429 in statuses, f"limiter never fired; saw {sorted(set(statuses))}"

    db = SessionLocal()
    try:
        db.query(models.Feedback).filter(
            models.Feedback.tester_name == "rate-limit-probe"
        ).delete()
        db.commit()
    finally:
        db.close()
