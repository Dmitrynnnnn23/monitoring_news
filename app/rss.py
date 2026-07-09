"""Минимальный парсер RSS 2.0 на стандартной библиотеке.

Все подключённые источники (ЦБ РФ, Минфин, ТАСС, Интерфакс, портал
Правительства РФ) отдают классический RSS 2.0, поэтому вместо feedparser
используется xml.etree + email.utils — меньше зависимостей, предсказуемое
поведение.
"""
import html
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


@dataclass
class FeedItem:
    title: str
    link: str
    summary: str = ""
    published: datetime | None = None
    categories: list[str] = field(default_factory=list)


def strip_html(text: str | None) -> str:
    """Убирает HTML-разметку и схлопывает пробелы (описания ЦБ содержат HTML)."""
    if not text:
        return ""
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    return _WS_RE.sub(" ", text).strip()


def parse_date(value: str | None) -> datetime | None:
    """RFC 822 (`pubDate`) или ISO 8601 → datetime в UTC."""
    if not value:
        return None
    value = value.strip()
    dt = None
    try:
        dt = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_rss(content: bytes) -> list[FeedItem]:
    root = ET.fromstring(content)
    if root.tag != "rss":
        raise ValueError(f"Не RSS-документ: корневой элемент <{root.tag}>")
    items = []
    for node in root.findall("./channel/item"):
        title = strip_html(node.findtext("title"))
        link = (node.findtext("link") or "").strip()
        if not title or not link:
            continue
        items.append(
            FeedItem(
                title=title,
                link=link,
                summary=strip_html(node.findtext("description")),
                published=parse_date(node.findtext("pubDate")),
                categories=[
                    c.text.strip() for c in node.findall("category") if c.text
                ],
            )
        )
    return items
