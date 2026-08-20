"""Auto-analysis triggers, driven by src/cddbs/data/auto_analysis_rules.json.

Two independent paths, both called by CollectorManager._run_processing() after
clustering and risk scoring:

  Article path  a single RSS/GDELT article whose urgency_label is in
                article_triggers.labels (default: BREAKING) fires an analysis
                run against the outlet that published it.

  Cluster path  an EventCluster whose event_type is in
                cluster_triggers.event_types (default: info_warfare, cyber,
                conflict) fires a SitRep plus a comparative TopicRun.

Both paths cost money per fire — an analysis run is one SerpAPI call plus one
Gemini call — and run unattended on a loop, so both are bounded by a
per-cycle cap and an idempotency stamp, and the article path additionally by a
per-outlet cooldown. Widening the rules is a config edit; the guards stay.
"""

import logging
import threading
from datetime import datetime, timedelta, UTC

from src.cddbs.models import EventCluster, RawArticle, Report, TopicRun
from src.cddbs.pipeline.article_labeling import load_rules
from src.cddbs.pipeline.sitrep import generate_sitrep
from src.cddbs.utils.input_sanitizer import sanitize_topic

logger = logging.getLogger(__name__)


def _run_topic_job(topic_run_id: int, topic: str, num_outlets: int, date_filter: str) -> None:
    """Run topic pipeline in a daemon thread — opens its own DB session."""
    from src.cddbs.database import SessionLocal
    from src.cddbs.pipeline.topic_pipeline import run_topic_pipeline

    db = SessionLocal()
    try:
        run_topic_pipeline(
            topic_run_id=topic_run_id,
            topic=topic,
            num_outlets=num_outlets,
            date_filter=date_filter,
        )
    except Exception as exc:
        logger.error("Auto-trigger TopicRun %d failed: %s", topic_run_id, exc)
        topic_run = db.query(TopicRun).filter(TopicRun.id == topic_run_id).first()
        if topic_run:
            topic_run.status = "failed"
            topic_run.error = str(exc)
            db.commit()
    finally:
        db.close()


def _run_analysis_job(outlet: str, country: str, num_articles: int, url: str) -> None:
    """Run the outlet analysis pipeline in a daemon thread."""
    from src.cddbs.pipeline.orchestrator import run_pipeline

    try:
        run_pipeline(
            outlet=outlet,
            country=country,
            num_articles=num_articles,
            url=url or None,
        )
    except Exception as exc:
        logger.error("Auto-trigger analysis run for outlet=%r failed: %s", outlet, exc)


# ---------------------------------------------------------------------------
# Article path
# ---------------------------------------------------------------------------

def auto_trigger_articles(session) -> int:
    """Fire an analysis run for qualifying single articles.

    Returns the number of runs started.
    """
    rules = load_rules()
    if not rules.get("enabled"):
        return 0

    cfg = rules["article_triggers"]
    labels = cfg.get("labels") or []
    max_per_cycle = int(cfg.get("max_per_cycle", 0))
    if not labels or max_per_cycle <= 0:
        return 0

    candidates = (
        session.query(RawArticle)
        .filter(
            RawArticle.urgency_label.in_(labels),
            RawArticle.auto_analyzed_at.is_(None),
            RawArticle.is_duplicate == False,  # noqa: E712 — SQLAlchemy needs ==
        )
        .order_by(RawArticle.created_at.desc())
        .limit(max_per_cycle * 20)  # scan a window; the cap is applied below
        .all()
    )
    if not candidates:
        return 0

    cooldown_hours = int(cfg.get("outlet_cooldown_hours", 24))
    cooldown_cutoff = datetime.now(UTC) - timedelta(hours=cooldown_hours)
    min_title_length = int(cfg.get("min_title_length", 0))
    num_articles = int(cfg.get("num_articles", 5))

    triggered = 0
    outlets_this_cycle = set()

    for article in candidates:
        if triggered >= max_per_cycle:
            break

        outlet = (article.source_name or article.source_domain or "").strip()
        if not outlet:
            # Nothing to analyse against; stamp so it isn't rescanned forever.
            article.auto_analyzed_at = datetime.now(UTC)
            continue

        # Placeholder/truncated headlines produce useless briefings.
        if len(article.title or "") < min_title_length:
            article.auto_analyzed_at = datetime.now(UTC)
            continue

        # One run per outlet per cycle — breaking stories cluster heavily by
        # publisher, so without this a single event burns the whole budget on
        # one outlet.
        if outlet in outlets_this_cycle:
            continue

        # Cooldown: skip if this outlet was analysed recently, by this trigger
        # or by hand. Re-profiling the same outlet hourly adds no signal.
        recent = (
            session.query(Report)
            .filter(Report.outlet == outlet, Report.created_at >= cooldown_cutoff)
            .first()
        )
        if recent:
            logger.info(
                "Auto-trigger: skipping outlet=%r — analysed within %dh (report %d)",
                outlet, cooldown_hours, recent.id,
            )
            article.auto_analyzed_at = datetime.now(UTC)
            continue

        logger.info(
            "Auto-trigger: article %d (label=%s, outlet=%r) -> analysis run",
            article.id, article.urgency_label, outlet,
        )
        thread = threading.Thread(
            target=_run_analysis_job,
            args=(outlet, article.country or "", num_articles, article.source_domain or ""),
            daemon=True,
        )
        thread.start()

        article.auto_analyzed_at = datetime.now(UTC)
        outlets_this_cycle.add(outlet)
        triggered += 1

    session.commit()
    if triggered:
        logger.info("Auto-trigger: started %d article analysis run(s)", triggered)
    return triggered


# ---------------------------------------------------------------------------
# Cluster path
# ---------------------------------------------------------------------------

def auto_trigger_analysis(session) -> int:
    """Trigger SitRep + TopicRun for every qualifying cluster not yet analysed.

    Returns the number of clusters that triggered analysis.
    """
    rules = load_rules()
    if not rules.get("enabled"):
        return 0

    cfg = rules["cluster_triggers"]
    event_types = cfg.get("event_types") or []
    max_per_cycle = int(cfg.get("max_per_cycle", 0))
    if not event_types or max_per_cycle <= 0:
        return 0

    min_articles = int(cfg.get("min_articles", 3))
    num_outlets = int(cfg.get("num_outlets", 5))
    date_filter = cfg.get("date_filter", "m")

    candidates = (
        session.query(EventCluster)
        .filter(
            EventCluster.event_type.in_(event_types),
            EventCluster.article_count >= min_articles,
            EventCluster.auto_analyzed_at.is_(None),
            EventCluster.status == "active",
        )
        .order_by(EventCluster.article_count.desc())
        .limit(max_per_cycle)
        .all()
    )

    if not candidates:
        return 0

    triggered = 0
    for cluster in candidates:
        logger.info(
            "Auto-trigger: cluster %d (%s, type=%s, %d articles)",
            cluster.id, cluster.title, cluster.event_type, cluster.article_count,
        )

        # 1. SitRep — synchronous, uses same session; skips silently if one exists
        try:
            briefing = generate_sitrep(cluster, session)
            if briefing:
                logger.info("Auto-trigger: SitRep %d generated for cluster %d", briefing.id, cluster.id)
        except Exception as exc:
            logger.error("Auto-trigger: SitRep failed for cluster %d: %s", cluster.id, exc)

        # 2. TopicRun — create row synchronously, execute in daemon thread.
        # cluster.title is derived from untrusted article text; the manual
        # /topic-runs endpoint sanitises the topic but this automated path
        # bypasses it, so sanitise here before it reaches the Gemini prompt.
        topic = sanitize_topic(cluster.title or f"cluster_{cluster.id}")
        try:
            topic_run = TopicRun(
                topic=topic,
                num_outlets=num_outlets,
                date_filter=date_filter,
                status="pending",
            )
            session.add(topic_run)
            session.flush()  # get topic_run.id without committing yet

            thread = threading.Thread(
                target=_run_topic_job,
                args=(topic_run.id, topic, num_outlets, date_filter),
                daemon=True,
            )
            thread.start()
            logger.info(
                "Auto-trigger: TopicRun %d started for cluster %d (topic=%r)",
                topic_run.id, cluster.id, topic,
            )
        except Exception as exc:
            logger.error("Auto-trigger: TopicRun creation failed for cluster %d: %s", cluster.id, exc)

        # 3. Stamp the cluster so it isn't triggered again
        cluster.auto_analyzed_at = datetime.now(UTC)
        triggered += 1

    session.commit()
    logger.info("Auto-trigger: triggered analysis on %d cluster(s)", triggered)
    return triggered
