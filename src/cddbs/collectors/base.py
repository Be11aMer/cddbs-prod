"""Base collector interface and common data structures."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha256


@dataclass
class RawArticleData:
    """Normalized article from any collector source."""
    title: str
    url: str
    content: str | None = None
    source_name: str = ""
    source_domain: str = ""
    source_type: str = ""  # "rss", "gdelt", "news_api"
    published_at: datetime | None = None
    language: str | None = None
    country: str | None = None
    raw_meta: dict = field(default_factory=dict)

    @property
    def url_hash(self) -> str:
        """SHA-256 hash of normalized URL for deduplication."""
        normalized = self.url.strip().rstrip("/").lower()
        return sha256(normalized.encode()).hexdigest()


class BaseCollector(ABC):
    """Abstract base for all news collectors."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Collector identifier (e.g., 'rss', 'gdelt')."""
        ...

    @property
    @abstractmethod
    def source_type(self) -> str:
        """Source type tag stored on articles."""
        ...

    @abstractmethod
    async def collect(self) -> list[RawArticleData]:
        """Fetch articles from this source. Must handle errors internally."""
        ...
