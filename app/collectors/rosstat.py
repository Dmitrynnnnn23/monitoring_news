"""Росстат (rosstat.gov.ru) + официальная лента ведомства на портале
Правительства РФ.

Сертификат rosstat.gov.ru выпущен УЦ «Russian Trusted Root CA» (Минцифры),
которого нет в стандартных хранилищах доверия. Чтобы прямая лента работала,
укажите путь к этому сертификату в переменной EXTRA_CA_FILE (см. README).
Если прямая лента недоступна, коллектор продолжает работать через
government.ru — ленту событий Росстата на официальном портале Правительства.
"""
from ..categorizer import is_macro_relevant
from ..rss import FeedItem
from .base import RssCollector


class RosstatCollector(RssCollector):
    name = "rosstat"
    source_id = "rosstat"
    source_title = "Росстат"
    verified = True
    feed_urls = [
        # Прямая лента Росстата (требует Russian Trusted Root CA, см. README)
        "https://rosstat.gov.ru/rss",
        # Официальная лента событий ведомства на портале Правительства РФ
        "http://government.ru/department/456/events/rss/",
    ]

    def accept(self, item: FeedItem) -> bool:
        # Лента government.ru содержит и протокольные события (поздравления,
        # назначения) — берём только макроэкономические сообщения.
        if "government.ru" in item.link:
            return is_macro_relevant(f"{item.title} {item.summary}")
        return True
