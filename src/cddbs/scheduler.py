"""Central scheduler for all automated CDDBS background jobs.

Provides a single, documentable, monitorable place for all scheduled tasks.
Each job has its own configurable interval via environment variables
(see config.py and docs/SCHEDULING.md).

Usage:
    scheduler = CddbsScheduler(db_session_factory=SessionLocal)
    scheduler.start()   # starts all background asyncio tasks
    scheduler.stop()    # graceful shutdown

Jobs managed:
    1. Article Collection  (RSS + GDELT)       → CDDBS_COLLECTOR_INTERVAL_HOURS
    2. SitRep Generation   (Gemini API call)   → CDDBS_SITREP_INTERVAL_HOURS
    3. Daily Threat Digest (Gemini API call)   → CDDBS_THREAT_DIGEST_INTERVAL_HOURS
"""

import asyncio
import logging
from datetime import datetime, UTC

from src.cddbs.config import settings

logger = logging.getLogger(__name__)


class ScheduledJob:
    """Metadata and state for a single scheduled job."""

    def __init__(self, name: str, interval_hours: float, description: str):
        self.name = name
        self.interval_hours = interval_hours
        self.description = description
        self.last_run: datetime | None = None
        self.next_run: datetime | None = None
        self.run_count: int = 0
        self.last_error: str | None = None
        self.is_running: bool = False
        self._task: asyncio.Task | None = None

    @property
    def interval_seconds(self) -> float:
        return self.interval_hours * 3600

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "interval_hours": self.interval_hours,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "run_count": self.run_count,
            "last_error": self.last_error,
            "is_running": self.is_running,
        }


class CddbsScheduler:
    """Central scheduler for all automated CDDBS background jobs.

    All intervals are configurable via environment variables with the
    CDDBS_ prefix. Defaults are free-tier-friendly.
    """

    def __init__(self, db_session_factory=None):
        self._db_session_factory = db_session_factory
        self._running = False
        self._collector_manager = None

        # Define all scheduled jobs
        self.jobs: dict[str, ScheduledJob] = {
            "collector": ScheduledJob(
                name="collector",
                interval_hours=settings.CDDBS_COLLECTOR_INTERVAL_HOURS,
                description="RSS + GDELT article collection, dedup, clustering, burst detection",
            ),
            "sitrep": ScheduledJob(
                name="sitrep",
                interval_hours=settings.CDDBS_SITREP_INTERVAL_HOURS,
                description="Automated SitRep + cross-source framing for high-risk clusters",
            ),
            "threat_digest": ScheduledJob(
                name="threat_digest",
                interval_hours=settings.CDDBS_THREAT_DIGEST_INTERVAL_HOURS,
                description="Daily executive threat intelligence digest",
            ),
        }

    @property
    def statuses(self) -> list[dict]:
        """Return status of all scheduled jobs."""
        return [job.to_dict() for job in self.jobs.values()]

    def start(self):
        """Start all scheduled background tasks."""
        self._running = True
        loop = asyncio.get_event_loop()

        # 1. Collector job (uses existing CollectorManager)
        from src.cddbs.collectors.manager import CollectorManager
        self._collector_manager = CollectorManager(db_session_factory=self._db_session_factory)
        self.jobs["collector"]._task = loop.create_task(
            self._run_periodic("collector", self._collector_run)
        )

        # 2. SitRep job
        self.jobs["sitrep"]._task = loop.create_task(
            self._run_periodic("sitrep", self._sitrep_run)
        )

        # 3. Daily digest job
        self.jobs["threat_digest"]._task = loop.create_task(
            self._run_periodic("threat_digest", self._threat_digest_run)
        )

        logger.info(
            "CddbsScheduler started %d jobs: %s",
            len(self.jobs),
            ", ".join(f"{j.name} (every {j.interval_hours}h)" for j in self.jobs.values()),
        )

    def stop(self):
        """Gracefully stop all scheduled tasks."""
        self._running = False
        if self._collector_manager:
            self._collector_manager.stop()
        for job in self.jobs.values():
            if job._task and not job._task.done():
                job._task.cancel()
        logger.info("CddbsScheduler stopped")

    async def _run_periodic(self, job_name: str, func):
        """Generic periodic runner for any job."""
        job = self.jobs[job_name]
        while self._running:
            job.is_running = True
            job.last_run = datetime.now(UTC)
            try:
                await func()
                job.last_error = None
            except Exception as exc:
                job.last_error = str(exc)
                logger.error("Scheduler job '%s' failed: %s", job_name, exc)
            finally:
                job.is_running = False
                job.run_count += 1
                job.next_run = datetime.now(UTC)

            await asyncio.sleep(job.interval_seconds)

    async def _collector_run(self):
        """Run article collection cycle."""
        if self._collector_manager:
            await self._collector_manager.run_once()

    async def _sitrep_run(self):
        """Run SitRep generation cycle."""
        if not self._db_session_factory:
            return

        session = self._db_session_factory()
        try:
            from src.cddbs.pipeline.sitrep import run_sitrep_cycle
            results = run_sitrep_cycle(session)
            if results:
                logger.info("SitRep cycle produced %d briefings", len(results))
        except Exception as exc:
            logger.error("SitRep cycle error: %s", exc)
        finally:
            session.close()

    async def _threat_digest_run(self):
        """Run daily threat digest generation."""
        if not self._db_session_factory:
            return

        session = self._db_session_factory()
        try:
            from src.cddbs.pipeline.threat_digest import generate_daily_digest
            digest = generate_daily_digest(session)
            if digest:
                logger.info("Daily digest generated: briefing %d", digest.id)
            else:
                logger.info("Daily digest skipped: nothing significant to report")
        except Exception as exc:
            logger.error("Daily digest error: %s", exc)
        finally:
            session.close()

    @property
    def collector_statuses(self) -> list[dict]:
        """Return collector-level statuses (for backward compatibility)."""
        if self._collector_manager:
            return self._collector_manager.statuses
        return []
