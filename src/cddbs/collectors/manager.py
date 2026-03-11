"""Collector manager — runs all collectors and stores results."""

import asyncio
from datetime import datetime, UTC

from src.cddbs.collectors.base import BaseCollector, RawArticleData
from src.cddbs.collectors.rss import RSSCollector
from src.cddbs.collectors.gdelt import GDELTCollector


class CollectorStatus:
    """Health status for a single collector."""
    def __init__(self, name: str):
        self.name = name
        self.last_run: datetime | None = None
        self.last_article_count: int = 0
        self.total_articles_collected: int = 0
        self.last_error: str | None = None
        self.is_running: bool = False

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_article_count": self.last_article_count,
            "total_articles_collected": self.total_articles_collected,
            "last_error": self.last_error,
            "is_running": self.is_running,
        }


class CollectorManager:
    """Manages all collectors and persists articles to database."""

    def __init__(self, db_session_factory=None):
        self._collectors: list[BaseCollector] = [
            RSSCollector(),
            GDELTCollector(),
        ]
        self._status: dict[str, CollectorStatus] = {
            c.name: CollectorStatus(c.name) for c in self._collectors
        }
        self._db_session_factory = db_session_factory
        self._running = False
        self._task: asyncio.Task | None = None

    @property
    def statuses(self) -> list[dict]:
        return [s.to_dict() for s in self._status.values()]

    async def run_once(self) -> list[RawArticleData]:
        """Run all collectors once and store results. Returns all collected articles."""
        all_articles: list[RawArticleData] = []

        for collector in self._collectors:
            status = self._status[collector.name]
            status.is_running = True
            try:
                articles = await collector.collect()
                status.last_run = datetime.now(UTC)
                status.last_article_count = len(articles)
                status.total_articles_collected += len(articles)
                status.last_error = None
                all_articles.extend(articles)
            except Exception as exc:
                status.last_error = str(exc)
                print(f"CollectorManager: {collector.name} failed: {exc}")
            finally:
                status.is_running = False

        # Persist to database if session factory available
        if self._db_session_factory and all_articles:
            stored = self._store_articles(all_articles)
            print(f"CollectorManager: collected {len(all_articles)}, stored {stored} new articles")

            # Run processing pipeline on newly stored articles
            if stored > 0:
                self._run_processing()

        return all_articles

    def _run_processing(self):
        """Run deduplication, clustering, and burst detection on stored articles."""
        session = self._db_session_factory()
        try:
            from src.cddbs.pipeline.deduplication import find_title_duplicates
            from src.cddbs.pipeline.event_clustering import cluster_articles
            from src.cddbs.pipeline.burst_detection import detect_bursts
            from src.cddbs.pipeline.narrative_risk import update_cluster_risk_scores

            dupes = find_title_duplicates(session)
            if dupes:
                print(f"CollectorManager: marked {dupes} title duplicates")

            new_clusters = cluster_articles(session)
            if new_clusters:
                print(f"CollectorManager: created {len(new_clusters)} event clusters")

            bursts = detect_bursts(session)
            if bursts:
                print(f"CollectorManager: detected {len(bursts)} narrative bursts")

            updated = update_cluster_risk_scores(session)
            if updated:
                print(f"CollectorManager: updated {updated} cluster risk scores")

        except Exception as exc:
            print(f"CollectorManager: processing error: {exc}")
        finally:
            session.close()

    def _store_articles(self, articles: list[RawArticleData]) -> int:
        """Store articles in database, skipping duplicates. Returns count stored."""
        # Import here to avoid circular dependency
        from src.cddbs.models import RawArticle as RawArticleModel

        stored = 0
        session = self._db_session_factory()
        try:
            for article in articles:
                url_hash = article.url_hash
                # Check for existing by URL hash
                existing = session.query(RawArticleModel).filter_by(url_hash=url_hash).first()
                if existing:
                    continue

                db_article = RawArticleModel(
                    url_hash=url_hash,
                    title=article.title,
                    url=article.url,
                    content=article.content,
                    source_name=article.source_name,
                    source_domain=article.source_domain,
                    source_type=article.source_type,
                    published_at=article.published_at,
                    language=article.language,
                    country=article.country,
                    raw_meta=article.raw_meta,
                )
                session.add(db_article)
                stored += 1

            session.commit()
        except Exception as exc:
            session.rollback()
            print(f"CollectorManager: DB error: {exc}")
        finally:
            session.close()

        return stored

    async def start_periodic(self, interval_seconds: int = 180):
        """Start periodic collection loop (default: every 3 minutes)."""
        self._running = True
        print(f"CollectorManager: starting periodic collection every {interval_seconds}s")
        while self._running:
            try:
                await self.run_once()
            except Exception as exc:
                print(f"CollectorManager: periodic run error: {exc}")
            await asyncio.sleep(interval_seconds)

    def stop(self):
        """Stop periodic collection."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()

    def start_background(self, interval_seconds: int = 180):
        """Start collection as a background asyncio task."""
        loop = asyncio.get_event_loop()
        self._task = loop.create_task(self.start_periodic(interval_seconds))
        return self._task
