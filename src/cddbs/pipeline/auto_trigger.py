"""Auto-analysis trigger for high-priority event clusters.

Fires a SitRep + TopicRun whenever a new EventCluster with
event_type IN ('info_warfare', 'cyber') is detected with article_count >= 3
and has not yet been auto-analyzed (auto_analyzed_at IS NULL).

Called by CollectorManager._run_processing() after risk scores are updated.
"""

import logging
import threading
from datetime import datetime, UTC

from src.cddbs.models import EventCluster, TopicRun
from src.cddbs.pipeline.sitrep import generate_sitrep

logger = logging.getLogger(__name__)

# Only these event types trigger auto-analysis:
# info_warfare = primary target (disinformation focus)
# cyber = secondary target (hybrid threat)
AUTO_TRIGGER_TYPES = {"info_warfare", "cyber"}
AUTO_TRIGGER_MIN_ARTICLES = 3


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


def auto_trigger_analysis(session) -> int:
    """Trigger SitRep + TopicRun for every qualifying cluster not yet auto-analyzed.

    Returns the number of clusters that triggered analysis.
    """
    candidates = (
        session.query(EventCluster)
        .filter(
            EventCluster.event_type.in_(AUTO_TRIGGER_TYPES),
            EventCluster.article_count >= AUTO_TRIGGER_MIN_ARTICLES,
            EventCluster.auto_analyzed_at.is_(None),
            EventCluster.status == "active",
        )
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

        # 2. TopicRun — create row synchronously, execute in daemon thread
        topic = cluster.title or f"cluster_{cluster.id}"
        try:
            topic_run = TopicRun(
                topic=topic,
                num_outlets=5,
                date_filter="m",
                status="pending",
            )
            session.add(topic_run)
            session.flush()  # get topic_run.id without committing yet

            thread = threading.Thread(
                target=_run_topic_job,
                args=(topic_run.id, topic, 5, "m"),
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
