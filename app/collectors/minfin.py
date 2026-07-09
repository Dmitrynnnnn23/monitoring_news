"""Минфин России (minfin.gov.ru): официальная RSS-лента пресс-центра."""
from .base import RssCollector


class MinfinCollector(RssCollector):
    name = "minfin"
    source_id = "minfin"
    source_title = "Минфин России"
    verified = True
    feed_urls = ["https://minfin.gov.ru/rss_news?mod=news&lim=50"]
