"""Интерфакс: экономический блок общей RSS-ленты."""
from ..categorizer import is_macro_relevant
from ..rss import FeedItem
from .base import RssCollector


class InterfaxCollector(RssCollector):
    name = "interfax"
    source_id = "interfax"
    source_title = "Интерфакс"
    verified = False  # информагентство: указывает первоисточник, но не является им
    feed_urls = ["https://www.interfax.ru/rss.asp"]

    def accept(self, item: FeedItem) -> bool:
        in_economy = any(
            "эконом" in c.lower() or "бизнес" in c.lower() for c in item.categories
        ) or "/business/" in item.link
        return in_economy and is_macro_relevant(f"{item.title} {item.summary}")
