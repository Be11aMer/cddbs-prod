"""Tests for configurable auto-analysis triggers.

Two paths, both driven by data/auto_analysis_rules.json:
  * a single article labelled BREAKING fires an analysis run on its outlet
  * an event cluster typed conflict (etc.) fires a SitRep + TopicRun

Both cost money per fire and run unattended, so the guards (per-cycle cap,
per-outlet cooldown, one-shot stamping) get as much coverage as the happy path.
"""
import json
from datetime import datetime, timedelta, UTC
from unittest.mock import patch

import pytest

from src.cddbs import models
from src.cddbs.database import SessionLocal
from src.cddbs.pipeline import article_labeling
from src.cddbs.pipeline.article_labeling import (
    classify_article_label,
    label_articles,
    load_rules,
)
from src.cddbs.pipeline.auto_trigger import auto_trigger_articles


@pytest.fixture(autouse=True)
def _reset_rules_cache():
    """Rules are cached at module level; keep tests from leaking into each other."""
    article_labeling._rules_cache = None
    yield
    article_labeling._rules_cache = None


@pytest.fixture
def rules(tmp_path, monkeypatch):
    """Point the loader at a rules file the test controls."""
    def _write(payload):
        path = tmp_path / "auto_analysis_rules.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        monkeypatch.setattr(article_labeling, "_RULES_PATH", str(path))
        article_labeling._rules_cache = None
        return path
    return _write


def _default_payload(**overrides):
    payload = {
        "enabled": True,
        "article_labels": {
            "BREAKING": ["attack", "missile", "killed"],
            "DISINFO": ["propaganda", "disinformation"],
            "INTEL": ["election", "cyber"],
        },
        "article_label_priority": ["BREAKING", "DISINFO", "INTEL"],
        "default_article_label": "NEWS",
        "article_triggers": {
            "labels": ["BREAKING"],
            "min_title_length": 10,
            "max_per_cycle": 3,
            "outlet_cooldown_hours": 24,
            "num_articles": 5,
        },
        "cluster_triggers": {
            "event_types": ["conflict", "info_warfare"],
            "min_articles": 3,
            "max_per_cycle": 5,
            "num_outlets": 5,
            "date_filter": "m",
        },
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# Shipped config
# ---------------------------------------------------------------------------

def test_shipped_rules_file_is_valid_and_matches_the_agreed_defaults():
    loaded = load_rules(force=True)
    assert loaded["enabled"] is True
    assert loaded["article_triggers"]["labels"] == ["BREAKING"]
    assert loaded["article_triggers"]["max_per_cycle"] == 3
    assert loaded["article_triggers"]["outlet_cooldown_hours"] == 24
    assert "conflict" in loaded["cluster_triggers"]["event_types"]
    # The pre-existing cluster types must not be dropped by adding conflict
    assert "info_warfare" in loaded["cluster_triggers"]["event_types"]
    assert "cyber" in loaded["cluster_triggers"]["event_types"]


def test_shipped_label_keywords_match_the_frontend_heuristic():
    """The backend classifier replaced a frontend if-chain; keep them aligned."""
    loaded = load_rules(force=True)
    breaking = set(loaded["article_labels"]["BREAKING"])
    assert {"attack", "missile", "war", "crisis", "killed", "bomb"} <= breaking


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "title,expected",
    [
        ("Missile attack on Kyiv", "BREAKING"),
        ("Russian propaganda campaign exposed", "DISINFO"),
        ("Election security review begins", "INTEL"),
        ("Quarterly earnings released", "NEWS"),
        ("", "NEWS"),
    ],
)
def test_classify_article_label(rules, title, expected):
    rules(_default_payload())
    assert classify_article_label(title) == expected


def test_label_priority_is_first_match_wins(rules):
    """A story matching several labels takes the highest-priority one."""
    rules(_default_payload())
    # matches BREAKING (attack) and INTEL (election)
    assert classify_article_label("Missile attack during the election") == "BREAKING"


def test_labels_are_configurable_without_code_changes(rules):
    """The point of the file: adding a label needs no deploy of new code."""
    payload = _default_payload()
    payload["article_labels"]["SANCTIONS"] = ["embargo", "tariff"]
    payload["article_label_priority"].append("SANCTIONS")
    rules(payload)
    assert classify_article_label("New embargo announced") == "SANCTIONS"


def test_label_defined_but_not_prioritised_is_still_reachable(rules):
    payload = _default_payload()
    payload["article_labels"]["SANCTIONS"] = ["embargo"]
    # deliberately not added to article_label_priority
    rules(payload)
    assert classify_article_label("New embargo announced") == "SANCTIONS"


def test_missing_rules_file_disables_triggering_but_still_labels(monkeypatch):
    monkeypatch.setattr(article_labeling, "_RULES_PATH", "/nonexistent/rules.json")
    article_labeling._rules_cache = None
    loaded = load_rules(force=True)
    assert loaded["enabled"] is False
    assert classify_article_label("Missile attack") == "NEWS"


def test_malformed_rules_file_does_not_raise(tmp_path, monkeypatch):
    path = tmp_path / "bad.json"
    path.write_text("{ not json", encoding="utf-8")
    monkeypatch.setattr(article_labeling, "_RULES_PATH", str(path))
    article_labeling._rules_cache = None
    loaded = load_rules(force=True)
    assert loaded["enabled"] is False


def test_partial_rules_file_is_filled_in(rules):
    """A user editing the file by hand must not be able to KeyError the collector."""
    rules({"enabled": True, "article_labels": {"BREAKING": ["attack"]}})
    loaded = load_rules(force=True)
    assert loaded["article_triggers"]["max_per_cycle"] == 0
    assert loaded["default_article_label"] == "NEWS"
    assert classify_article_label("attack reported") == "BREAKING"


# ---------------------------------------------------------------------------
# Article trigger
# ---------------------------------------------------------------------------

_DOMAIN = "auto-trigger-test.example"


def _cleanup():
    db = SessionLocal()
    try:
        db.query(models.RawArticle).filter(
            models.RawArticle.source_domain == _DOMAIN
        ).delete()
        for report in db.query(models.Report).filter(
            models.Report.outlet.like("auto-trigger%")
        ).all():
            db.query(models.Briefing).filter(models.Briefing.report_id == report.id).delete()
        db.query(models.Report).filter(models.Report.outlet.like("auto-trigger%")).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture
def db_session():
    _cleanup()
    session = SessionLocal()
    yield session
    session.close()
    _cleanup()


def _add_article(session, title, label="BREAKING", outlet="auto-trigger-outlet", **kw):
    article = models.RawArticle(
        url_hash=f"hash-{title}-{outlet}"[:64],
        title=title,
        url=f"https://{_DOMAIN}/{abs(hash(title))}",
        source_name=outlet,
        source_domain=_DOMAIN,
        source_type="rss",
        country="Testland",
        urgency_label=label,
        is_duplicate=kw.get("is_duplicate", False),
        auto_analyzed_at=kw.get("auto_analyzed_at"),
    )
    session.add(article)
    session.commit()
    session.refresh(article)
    return article


def test_breaking_article_fires_an_analysis_run(rules, db_session):
    rules(_default_payload())
    article = _add_article(db_session, "Missile attack on the capital city")

    with patch("src.cddbs.pipeline.auto_trigger.threading.Thread") as thread:
        count = auto_trigger_articles(db_session)

    assert count == 1
    assert thread.call_count == 1
    # Fires an outlet analysis run, not a topic run
    target = thread.call_args.kwargs.get("target") or thread.call_args.args[0]
    assert target.__name__ == "_run_analysis_job"
    args = thread.call_args.kwargs["args"]
    assert args[0] == "auto-trigger-outlet"   # outlet
    assert args[1] == "Testland"              # country

    db_session.refresh(article)
    assert article.auto_analyzed_at is not None


def test_non_matching_label_does_not_fire(rules, db_session):
    rules(_default_payload())
    _add_article(db_session, "Quarterly earnings released today", label="NEWS")

    with patch("src.cddbs.pipeline.auto_trigger.threading.Thread") as thread:
        assert auto_trigger_articles(db_session) == 0
    assert thread.call_count == 0


def test_adding_a_label_to_the_config_widens_the_trigger(rules, db_session):
    """The extensibility requirement: DISINFO fires once it is listed."""
    payload = _default_payload()
    payload["article_triggers"]["labels"] = ["BREAKING", "DISINFO"]
    rules(payload)
    _add_article(db_session, "Propaganda campaign uncovered", label="DISINFO")

    with patch("src.cddbs.pipeline.auto_trigger.threading.Thread"):
        assert auto_trigger_articles(db_session) == 1


def test_per_cycle_cap_is_enforced(rules, db_session):
    payload = _default_payload()
    payload["article_triggers"]["max_per_cycle"] = 2
    rules(payload)
    for i in range(5):
        _add_article(db_session, f"Missile attack number {i} today", outlet=f"outlet-{i}")

    with patch("src.cddbs.pipeline.auto_trigger.threading.Thread") as thread:
        count = auto_trigger_articles(db_session)

    assert count == 2
    assert thread.call_count == 2


def test_one_run_per_outlet_per_cycle(rules, db_session):
    """Breaking stories cluster by publisher; one event must not eat the budget."""
    rules(_default_payload())
    for i in range(3):
        _add_article(db_session, f"Missile attack story {i} today", outlet="same-outlet")

    with patch("src.cddbs.pipeline.auto_trigger.threading.Thread") as thread:
        count = auto_trigger_articles(db_session)

    assert count == 1
    assert thread.call_count == 1


def test_outlet_cooldown_skips_recently_analysed_outlets(rules, db_session):
    rules(_default_payload())
    db_session.add(models.Report(
        outlet="auto-trigger-outlet",
        country="Testland",
        created_at=datetime.now(UTC) - timedelta(hours=2),
    ))
    db_session.commit()

    article = _add_article(db_session, "Missile attack on the capital city")

    with patch("src.cddbs.pipeline.auto_trigger.threading.Thread") as thread:
        count = auto_trigger_articles(db_session)

    assert count == 0
    assert thread.call_count == 0
    # Still stamped, so it is not rescanned every cycle forever
    db_session.refresh(article)
    assert article.auto_analyzed_at is not None


def test_outlet_outside_the_cooldown_window_does_fire(rules, db_session):
    rules(_default_payload())
    db_session.add(models.Report(
        outlet="auto-trigger-outlet",
        country="Testland",
        created_at=datetime.now(UTC) - timedelta(hours=48),
    ))
    db_session.commit()
    _add_article(db_session, "Missile attack on the capital city")

    with patch("src.cddbs.pipeline.auto_trigger.threading.Thread"):
        assert auto_trigger_articles(db_session) == 1


def test_already_analysed_article_does_not_refire(rules, db_session):
    rules(_default_payload())
    _add_article(
        db_session, "Missile attack on the capital city",
        auto_analyzed_at=datetime.now(UTC),
    )

    with patch("src.cddbs.pipeline.auto_trigger.threading.Thread") as thread:
        assert auto_trigger_articles(db_session) == 0
    assert thread.call_count == 0


def test_duplicate_articles_are_skipped(rules, db_session):
    rules(_default_payload())
    _add_article(db_session, "Missile attack on the capital city", is_duplicate=True)

    with patch("src.cddbs.pipeline.auto_trigger.threading.Thread") as thread:
        assert auto_trigger_articles(db_session) == 0
    assert thread.call_count == 0


def test_short_titles_are_skipped(rules, db_session):
    """Placeholder headlines produce useless briefings."""
    payload = _default_payload()
    payload["article_triggers"]["min_title_length"] = 30
    rules(payload)
    article = _add_article(db_session, "Attack")

    with patch("src.cddbs.pipeline.auto_trigger.threading.Thread") as thread:
        assert auto_trigger_articles(db_session) == 0
    assert thread.call_count == 0
    db_session.refresh(article)
    assert article.auto_analyzed_at is not None


def test_disabled_rules_fire_nothing(rules, db_session):
    payload = _default_payload()
    payload["enabled"] = False
    rules(payload)
    _add_article(db_session, "Missile attack on the capital city")

    with patch("src.cddbs.pipeline.auto_trigger.threading.Thread") as thread:
        assert auto_trigger_articles(db_session) == 0
    assert thread.call_count == 0


# ---------------------------------------------------------------------------
# Labelling pass
# ---------------------------------------------------------------------------

def test_label_articles_fills_in_missing_labels(rules, db_session):
    rules(_default_payload())
    article = _add_article(db_session, "Missile attack on the capital city", label=None)

    assert label_articles(db_session) >= 1

    db_session.refresh(article)
    assert article.urgency_label == "BREAKING"


def test_label_articles_leaves_existing_labels_alone(rules, db_session):
    rules(_default_payload())
    article = _add_article(db_session, "Missile attack on the capital city", label="NEWS")

    label_articles(db_session)

    db_session.refresh(article)
    assert article.urgency_label == "NEWS"
