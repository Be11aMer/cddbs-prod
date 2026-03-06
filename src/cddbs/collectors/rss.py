"""RSS feed collector using feedparser."""

import json
import os
from datetime import datetime, UTC
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse

import feedparser

from src.cddbs.collectors.base import BaseCollector, RawArticleData


# Default path to feeds config — can be overridden for testing
_DEFAULT_FEEDS_PATH = Path(__file__).parent.parent / "data" / "rss_feeds.json"


class RSSCollector(BaseCollector):
    """Collects articles from configured RSS feeds."""

    def __init__(self, feeds_path: str | Path | None = None):
        self._feeds_path = Path(feeds_path) if feeds_path else _DEFAULT_FEEDS_PATH
        self._feeds: list[dict] | None = None

    @property
    def name(self) -> str:
        return "rss"

    @property
    def source_type(self) -> str:
        return "rss"

    def _load_feeds(self) -> list[dict]:
        if self._feeds is None:
            with open(self._feeds_path) as f:
                data = json.load(f)
            self._feeds = data.get("feeds", [])
        return self._feeds

    async def collect(self) -> list[RawArticleData]:
        """Parse all configured RSS feeds and return normalized articles."""
        feeds = self._load_feeds()
        articles: list[RawArticleData] = []

        for feed_config in feeds:
            try:
                feed_articles = self._parse_feed(feed_config)
                articles.extend(feed_articles)
            except Exception as exc:
                print(f"RSS collector: error parsing {feed_config.get('name', '?')}: {exc}")

        return articles

    def _parse_feed(self, feed_config: dict) -> list[RawArticleData]:
        """Parse a single RSS feed into RawArticleData list."""
        url = feed_config["url"]
        parsed = feedparser.parse(url)
        domain = urlparse(url).netloc
        articles = []

        for entry in parsed.entries:
            published = self._parse_date(entry)
            link = getattr(entry, "link", "")
            if not link:
                continue

            articles.append(RawArticleData(
                title=getattr(entry, "title", "").strip(),
                url=link,
                content=getattr(entry, "summary", None),
                source_name=feed_config.get("name", domain),
                source_domain=domain,
                source_type="rss",
                published_at=published,
                language=feed_config.get("language"),
                country=None,
                raw_meta={
                    "feed_url": url,
                    "feed_category": feed_config.get("category", ""),
                    "reliability": feed_config.get("reliability", "unknown"),
                },
            ))

        return articles

    @staticmethod
    def _parse_date(entry) -> datetime | None:
        """Try to parse the published date from an RSS entry."""
        for attr in ("published", "updated"):
            raw = getattr(entry, attr, None)
            if not raw:
                continue
            try:
                return parsedate_to_datetime(raw)
            except Exception:
                pass
            # feedparser also provides *_parsed as time structs
            parsed_struct = getattr(entry, f"{attr}_parsed", None)
            if parsed_struct:
                try:
                    return datetime(*parsed_struct[:6], tzinfo=UTC)
                except Exception:
                    pass
        return None
