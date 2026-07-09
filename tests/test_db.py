def _item(**kw):
    base = {
        "title": "Банк России сохранил ключевую ставку",
        "summary": "Совет директоров принял решение.",
        "source": "cbr",
        "url": "https://www.cbr.ru/press/pr/1",
        "published_at": "2026-07-09T10:30:00Z",
        "category": "ставка ЦБ",
        "verified": True,
    }
    base.update(kw)
    return base


def test_insert_and_dedup(tmp_db):
    with tmp_db.connect() as conn:
        assert tmp_db.insert_item(conn, _item()) is True
        # тот же заголовок и дата (другое время/URL) — дубликат
        assert (
            tmp_db.insert_item(
                conn,
                _item(url="https://example.org/copy", published_at="2026-07-09T11:00:00Z"),
            )
            is False
        )
        # косметические отличия заголовка — тоже дубликат
        assert (
            tmp_db.insert_item(
                conn, _item(title="  БАНК  РОССИИ сохранил ключевую ставку ")
            )
            is False
        )
        # другая дата — уже не дубликат
        assert tmp_db.insert_item(conn, _item(published_at="2026-07-10T10:30:00Z")) is True

    items, total = tmp_db.query_news()
    assert total == 2


def test_query_filters(tmp_db):
    with tmp_db.connect() as conn:
        tmp_db.insert_item(conn, _item())
        tmp_db.insert_item(
            conn,
            _item(
                title="Инфляция замедлилась",
                source="rosstat",
                category="инфляция",
                published_at="2026-07-01T09:00:00Z",
                url="https://rosstat.gov.ru/n/1",
            ),
        )

    items, total = tmp_db.query_news(sources=["rosstat"])
    assert total == 1 and items[0]["source"] == "rosstat"

    items, total = tmp_db.query_news(categories=["ставка ЦБ"])
    assert total == 1 and items[0]["category"] == "ставка ЦБ"

    items, total = tmp_db.query_news(date_from="2026-07-05")
    assert total == 1 and items[0]["published_at"].startswith("2026-07-09")

    items, total = tmp_db.query_news(date_to="2026-07-01")
    assert total == 1 and items[0]["published_at"].startswith("2026-07-01")

    items, total = tmp_db.query_news(q="инфляция")
    assert total == 1

    # сортировка по дате: свежее первым
    items, _ = tmp_db.query_news()
    assert items[0]["published_at"] > items[1]["published_at"]


def test_runs_meta(tmp_db):
    run_id = tmp_db.start_run("cbr_press")
    tmp_db.finish_run(run_id, "ok", items_found=10, items_added=3)
    meta = tmp_db.get_meta()
    assert meta["last_updated"] is not None
    assert meta["runs"][0]["collector"] == "cbr_press"
    assert meta["runs"][0]["items_added"] == 3
