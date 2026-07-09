from datetime import timezone
from pathlib import Path

import pytest

from app.rss import parse_date, parse_rss, strip_html

FIXTURE = Path(__file__).parent / "fixtures" / "cbr_press_sample.xml"


def test_parse_real_cbr_feed():
    items = parse_rss(FIXTURE.read_bytes())
    assert len(items) == 3
    first = items[0]
    assert "мониторинга максимальных процентных ставок" in first.title
    assert first.link.startswith("https://www.cbr.ru/press/")
    assert first.published is not None
    assert first.published.tzinfo == timezone.utc
    # HTML из description должен быть вычищен
    assert "<" not in first.summary
    assert "&nbsp;" not in first.summary


def test_strip_html():
    assert strip_html("<p>Ставка&nbsp;&mdash; 16%</p>") == "Ставка — 16%"
    assert strip_html(None) == ""
    assert strip_html("  a \n b  ") == "a b"


def test_parse_date_rfc822_and_iso():
    d1 = parse_date("Thu, 02 Jul 2026 14:58:00 +0300")
    assert d1 is not None and d1.hour == 11 and d1.tzinfo == timezone.utc
    d2 = parse_date("2026-07-02T14:58:00+03:00")
    assert d2 == d1
    assert parse_date("мусор") is None
    assert parse_date(None) is None


def test_parse_rss_rejects_non_rss():
    with pytest.raises(ValueError):
        parse_rss(b"<html><body>not rss</body></html>")
