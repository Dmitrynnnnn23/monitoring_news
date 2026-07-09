"""Базовые классы коллекторов."""
import logging
from datetime import datetime, timezone

import requests

from .. import config
from ..categorizer import categorize
from ..rss import FeedItem, parse_rss

log = logging.getLogger(__name__)

_ca_bundle_cache: str | bool | None = None


def get_ca_bundle() -> str | bool:
    """Путь к бандлу CA для requests.

    Если задан EXTRA_CA_FILE (например, Russian Trusted Root CA для
    rosstat.gov.ru), он объединяется со стандартным бандлом certifi в один
    файл. Проверка сертификатов при этом остаётся включённой всегда.
    """
    global _ca_bundle_cache
    if _ca_bundle_cache is not None:
        return _ca_bundle_cache
    if not config.EXTRA_CA_FILE:
        _ca_bundle_cache = True
        return _ca_bundle_cache
    import certifi

    combined = config.DATA_DIR / "combined-ca.pem"
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(certifi.where(), "rb") as f:
        base = f.read()
    with open(config.EXTRA_CA_FILE, "rb") as f:
        extra = f.read()
    combined.write_bytes(base + b"\n" + extra)
    _ca_bundle_cache = str(combined)
    return _ca_bundle_cache


def http_get(url: str) -> bytes:
    resp = requests.get(
        url,
        headers={
            "User-Agent": config.USER_AGENT,
            "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
        },
        timeout=config.HTTP_TIMEOUT,
        verify=get_ca_bundle(),
    )
    resp.raise_for_status()
    return resp.content


class Collector:
    """Один канал сбора. name — уникальный id коллектора (для журнала запусков),
    source_id/source_title — источник, отображаемый в интерфейсе."""

    name: str
    source_id: str
    source_title: str
    verified: bool = False

    def collect(self) -> list[dict]:
        raise NotImplementedError


class RssCollector(Collector):
    feed_urls: list[str] = []
    max_summary = 1500

    def accept(self, item: FeedItem) -> bool:
        """Фильтр элементов ленты; переопределяется в наследниках."""
        return True

    def collect(self) -> list[dict]:
        out: list[dict] = []
        seen_links: set[str] = set()
        errors: list[str] = []
        for url in self.feed_urls:
            try:
                feed_items = parse_rss(http_get(url))
            except Exception as exc:  # noqa: BLE001 — одна лента не должна валить остальные
                log.warning("[%s] лента %s недоступна: %s", self.name, url, exc)
                errors.append(f"{url}: {exc}")
                continue
            for item in feed_items:
                if item.link in seen_links:
                    continue
                seen_links.add(item.link)
                if not self.accept(item):
                    continue
                out.append(self._to_record(item))
        if errors and not seen_links:
            # не удалась ни одна лента — это ошибка коллектора
            raise RuntimeError("; ".join(errors))
        return out

    def _to_record(self, item: FeedItem) -> dict:
        published = item.published or datetime.now(timezone.utc)
        text = f"{item.title} {item.summary}"
        return {
            "title": item.title,
            "summary": item.summary[: self.max_summary],
            "source": self.source_id,
            "url": item.link,
            "published_at": published.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "category": categorize(text),
            "verified": self.verified,
        }
