"""Enhanced GDELT Project collector using Doc API v2."""

from datetime import datetime, UTC
from urllib.parse import urlparse

import httpx

from src.cddbs.collectors.base import BaseCollector, RawArticleData


# GDELT disinformation-relevant query terms
_GDELT_QUERY = (
    "disinformation OR propaganda OR misinformation OR cyberattack "
    "OR election interference OR fake news OR information warfare "
    "OR influence operation"
)

_GDELT_DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


class GDELTCollector(BaseCollector):
    """Collects articles from GDELT Project Doc API v2."""

    def __init__(
        self,
        query: str = _GDELT_QUERY,
        max_records: int = 50,
        timespan: str = "1d",
    ):
        self._query = query
        self._max_records = max_records
        self._timespan = timespan

    @property
    def name(self) -> str:
        return "gdelt"

    @property
    def source_type(self) -> str:
        return "gdelt"

    async def collect(self) -> list[RawArticleData]:
        """Fetch articles from GDELT Doc API v2."""
        params = {
            "query": self._query,
            "mode": "ArtList",
            "maxrecords": str(self._max_records),
            "format": "json",
            "timespan": self._timespan,
            "sort": "DateDesc",
        }

        articles: list[RawArticleData] = []
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(_GDELT_DOC_URL, params=params)
                if resp.status_code != 200:
                    print(f"GDELT collector: HTTP {resp.status_code}")
                    return articles

                payload = resp.json()

            for item in payload.get("articles", []):
                url = item.get("url", "")
                if not url:
                    continue

                published = self._parse_gdelt_date(item.get("seendate", ""))
                domain = urlparse(url).netloc

                articles.append(RawArticleData(
                    title=item.get("title", "").strip(),
                    url=url,
                    content=None,  # GDELT Doc API doesn't return full text
                    source_name=item.get("domain", domain),
                    source_domain=domain,
                    source_type="gdelt",
                    published_at=published,
                    language=item.get("language", None),
                    country=item.get("sourcecountry", None),
                    raw_meta={
                        "tone": item.get("tone", None),
                        "socialimage": item.get("socialimage", None),
                        "gdelt_domain": item.get("domain", None),
                    },
                ))

        except Exception as exc:
            print(f"GDELT collector: error: {exc}")

        return articles

    @staticmethod
    def _parse_gdelt_date(raw: str) -> datetime | None:
        """Parse GDELT seendate format: 'YYYYMMDDTHHMMSSZ' or similar."""
        if not raw:
            return None
        cleaned = raw.replace("T", "").replace("Z", "").strip()
        try:
            return datetime.strptime(cleaned, "%Y%m%d%H%M%S").replace(tzinfo=UTC)
        except ValueError:
            try:
                return datetime.strptime(cleaned[:8], "%Y%m%d").replace(tzinfo=UTC)
            except ValueError:
                return None
