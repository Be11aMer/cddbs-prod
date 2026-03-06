"""Multi-source news collectors for OSINT event intelligence pipeline."""

from src.cddbs.collectors.base import BaseCollector, RawArticleData
from src.cddbs.collectors.rss import RSSCollector
from src.cddbs.collectors.gdelt import GDELTCollector
from src.cddbs.collectors.manager import CollectorManager

__all__ = [
    "BaseCollector",
    "RawArticleData",
    "RSSCollector",
    "GDELTCollector",
    "CollectorManager",
]
