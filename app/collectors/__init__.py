"""Реестр коллекторов и запуск сбора."""
import json
import logging

from .. import config, db
from ..categorizer import is_macro_relevant
from ..rss import FeedItem
from .base import Collector, RssCollector
from .cbr import CbrCurrencyRatesCollector, CbrPressCollector
from .interfax import InterfaxCollector
from .minfin import MinfinCollector
from .rosstat import RosstatCollector
from .tass import TassCollector

log = logging.getLogger(__name__)

_REGISTRY: list[type[Collector]] = [
    CbrPressCollector,
    CbrCurrencyRatesCollector,
    RosstatCollector,
    MinfinCollector,
    TassCollector,
    InterfaxCollector,
]

# id источника -> человекочитаемое название (для API/интерфейса)
SOURCE_TITLES = {
    "cbr": "Банк России",
    "rosstat": "Росстат",
    "minfin": "Минфин России",
    "tass": "ТАСС",
    "interfax": "Интерфакс",
}


class _ExtraRssCollector(RssCollector):
    """RSS-источник, добавленный через EXTRA_RSS_SOURCES (например,
    лицензированная лента Reuters). Пропускает только макроэкономику."""

    def __init__(self, spec: dict):
        self.name = spec["id"]
        self.source_id = spec["id"]
        self.source_title = spec.get("title", spec["id"])
        self.verified = bool(spec.get("verified", False))
        self.feed_urls = [spec["url"]]

    def accept(self, item: FeedItem) -> bool:
        return is_macro_relevant(f"{item.title} {item.summary}")


def get_collectors() -> list[Collector]:
    collectors: list[Collector] = [
        cls() for cls in _REGISTRY if cls.source_id not in config.DISABLED_SOURCES
    ]
    if config.EXTRA_RSS_SOURCES:
        try:
            for spec in json.loads(config.EXTRA_RSS_SOURCES):
                collectors.append(_ExtraRssCollector(spec))
                SOURCE_TITLES.setdefault(spec["id"], spec.get("title", spec["id"]))
        except (ValueError, KeyError) as exc:
            log.error("EXTRA_RSS_SOURCES: некорректный JSON (%s)", exc)
    return collectors


def get_sources() -> list[dict]:
    """Описание источников для API (без дублей по source_id)."""
    seen: dict[str, dict] = {}
    for c in get_collectors():
        seen.setdefault(
            c.source_id,
            {"id": c.source_id, "title": c.source_title, "verified": c.verified},
        )
    return list(seen.values())


def run_collector(collector: Collector) -> dict:
    """Запуск одного коллектора с журналированием в collection_runs."""
    run_id = db.start_run(collector.name)
    try:
        items = collector.collect()
    except Exception as exc:  # noqa: BLE001 — ошибки источника не валят цикл сбора
        log.exception("[%s] сбор завершился ошибкой", collector.name)
        db.finish_run(run_id, "error", error=str(exc)[:500])
        return {"collector": collector.name, "status": "error", "error": str(exc)[:500]}

    added = 0
    with db.connect() as conn:
        for item in items:
            if db.insert_item(conn, item):
                added += 1
    db.finish_run(run_id, "ok", items_found=len(items), items_added=added)
    log.info("[%s] найдено %d, добавлено %d", collector.name, len(items), added)
    return {
        "collector": collector.name,
        "status": "ok",
        "items_found": len(items),
        "items_added": added,
    }


def run_all() -> list[dict]:
    """Полный цикл сбора по всем источникам."""
    db.init_db()
    return [run_collector(c) for c in get_collectors()]
