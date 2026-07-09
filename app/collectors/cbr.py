"""Банк России (cbr.ru): пресс-релизы, события и официальные курсы валют."""
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from .base import Collector, RssCollector, http_get


class CbrPressCollector(RssCollector):
    """Официальные RSS-ленты Банка России: пресс-релизы (решения по ключевой
    ставке, инфляционные отчёты, резервы) и события/комментарии."""

    name = "cbr_press"
    source_id = "cbr"
    source_title = "Банк России"
    verified = True
    feed_urls = [
        "https://www.cbr.ru/rss/RssPress",
        "https://www.cbr.ru/rss/eventrss",
    ]


class CbrCurrencyRatesCollector(Collector):
    """Официальные курсы валют ЦБ РФ (XML_daily.asp) — одна запись в день."""

    name = "cbr_rates"
    source_id = "cbr"
    source_title = "Банк России"
    verified = True

    URL = "https://www.cbr.ru/scripts/XML_daily.asp"
    WANTED = ["USD", "EUR", "CNY"]

    def collect(self) -> list[dict]:
        root = ET.fromstring(http_get(self.URL))
        date_str = root.get("Date", "")  # ДД.ММ.ГГГГ
        rates: dict[str, str] = {}
        for valute in root.findall("Valute"):
            code = valute.findtext("CharCode")
            if code in self.WANTED:
                nominal = valute.findtext("Nominal", "1")
                value = (valute.findtext("Value") or "").strip()
                prefix = f"{nominal} " if nominal != "1" else ""
                rates[code] = f"{prefix}{code} = {value} ₽"
        if not rates or not date_str:
            return []
        try:
            published = datetime.strptime(date_str, "%d.%m.%Y").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            published = datetime.now(timezone.utc)
        summary = "Официальные курсы Банка России: " + "; ".join(
            rates[c] for c in self.WANTED if c in rates
        )
        return [
            {
                "title": f"Официальные курсы валют ЦБ РФ на {date_str}",
                "summary": summary,
                "source": self.source_id,
                "url": (
                    "https://www.cbr.ru/currency_base/daily/"
                    f"?UniDbQuery.Posted=True&UniDbQuery.To={date_str}"
                ),
                "published_at": published.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "category": "курс валют",
                "verified": True,
            }
        ]
