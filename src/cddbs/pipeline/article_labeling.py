"""Urgency labelling for single collected articles, and the rules that use it.

The Intel Feed badge (BREAKING / DISINFO / INTEL / NEWS) was originally computed
in the frontend at render time, so the backend had no idea it existed and could
not act on it. This module is the backend's definition: it classifies a
`RawArticle` from its title and stores the result on the row, so the label the
analyst sees and the label the auto-trigger acts on are the same value.

Rules live in `src/cddbs/data/auto_analysis_rules.json` so labels and thresholds
can be changed without touching code.
"""

import json
import logging
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

# Lives under src/ so it ships in the Docker image (the Dockerfile copies only
# src/, and the repo-root data/ directory is gitignored). Same home as
# rss_feeds.json and known_narratives.json.
_RULES_PATH = Path(__file__).parent.parent / "data" / "auto_analysis_rules.json"

# Used when the rules file is missing or unreadable. Deliberately conservative:
# labelling still works so the feed renders, but nothing auto-fires.
_FALLBACK_RULES = {
    "enabled": False,
    "article_labels": {},
    "article_label_priority": [],
    "default_article_label": "NEWS",
    "article_triggers": {
        "labels": [],
        "min_title_length": 20,
        "max_per_cycle": 0,
        "outlet_cooldown_hours": 24,
        "num_articles": 5,
    },
    "cluster_triggers": {
        "event_types": [],
        "min_articles": 3,
        "max_per_cycle": 0,
        "num_outlets": 5,
        "date_filter": "m",
    },
}

_rules_cache = None
_rules_lock = threading.Lock()


def _coerce(rules: dict) -> dict:
    """Fill in anything the file omits, so callers never KeyError on user edits."""
    merged = {**_FALLBACK_RULES, **rules}
    for section in ("article_triggers", "cluster_triggers"):
        merged[section] = {**_FALLBACK_RULES[section], **(rules.get(section) or {})}

    # A label listed in priority but never defined would silently never match;
    # one defined but not prioritised would never be reachable. Reconcile both.
    labels = merged.get("article_labels") or {}
    priority = [lbl for lbl in (merged.get("article_label_priority") or []) if lbl in labels]
    for label in labels:
        if label not in priority:
            priority.append(label)
    merged["article_label_priority"] = priority
    return merged


def load_rules(force: bool = False) -> dict:
    """Load (and cache) the rules file.

    A malformed or missing file must not take the collector down, so failures
    fall back to rules that label articles but trigger nothing.
    """
    global _rules_cache
    with _rules_lock:
        if _rules_cache is not None and not force:
            return _rules_cache
        try:
            with open(_RULES_PATH, encoding="utf-8") as fh:
                loaded = json.load(fh)
            _rules_cache = _coerce(loaded)
            logger.info(
                "auto-analysis rules loaded: enabled=%s article_labels=%s cluster_types=%s",
                _rules_cache["enabled"],
                _rules_cache["article_triggers"]["labels"],
                _rules_cache["cluster_triggers"]["event_types"],
            )
        except Exception as exc:
            logger.error(
                "auto-analysis rules unreadable at %s (%s) — auto-triggering disabled",
                _RULES_PATH, exc,
            )
            _rules_cache = dict(_FALLBACK_RULES)
        return _rules_cache


def classify_article_label(title: str) -> str:
    """Return the urgency label for an article title.

    First match in `article_label_priority` wins, mirroring the original
    frontend if-chain: a 'missile attack during the election' is BREAKING,
    not INTEL.
    """
    rules = load_rules()
    text = (title or "").lower()
    if not text:
        return rules["default_article_label"]

    labels = rules["article_labels"]
    for label in rules["article_label_priority"]:
        if any(keyword in text for keyword in labels.get(label, [])):
            return label
    return rules["default_article_label"]


def label_articles(session, limit: int = 500) -> int:
    """Assign `urgency_label` to any article that does not have one yet.

    Runs before the triggers so newly collected rows carry a label the trigger
    can filter on. Returns the number labelled.
    """
    from src.cddbs.models import RawArticle

    pending = (
        session.query(RawArticle)
        .filter(RawArticle.urgency_label.is_(None))
        .order_by(RawArticle.created_at.desc())
        .limit(limit)
        .all()
    )
    if not pending:
        return 0

    for article in pending:
        article.urgency_label = classify_article_label(article.title)

    session.commit()
    logger.info("Labelled %d article(s)", len(pending))
    return len(pending)
