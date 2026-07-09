"""ТАСС: экономический блок общей RSS-ленты."""
from ..categorizer import is_macro_relevant
from ..rss import FeedItem
from .base import RssCollector


class TassCollector(RssCollector):
    name = "tass"
    source_id = "tass"
    source_title = "ТАСС"
    verified = False  # информагентство: указывает первоисточник, но не является им
    feed_urls = ["https://tass.ru/rss/v2.xml"]

    def accept(self, item: FeedItem) -> bool:
        in_economy = any(
            "эконом" in c.lower() or "бизнес" in c.lower() for c in item.categories
        ) or "/ekonomika/" in item.link
        return in_economy and is_macro_relevant(f"{item.title} {item.summary}")
