from fastapi.testclient import TestClient

from app.main import app


def _client(monkeypatch):
    from app import config

    monkeypatch.setattr(config, "DISABLE_SCHEDULER", True)
    return TestClient(app)


def test_news_endpoint(tmp_db, monkeypatch):
    with tmp_db.connect() as conn:
        tmp_db.insert_item(
            conn,
            {
                "title": "Инфляция замедлилась до 4%",
                "summary": "По данным Росстата.",
                "source": "rosstat",
                "url": "https://rosstat.gov.ru/n/1",
                "published_at": "2026-07-08T09:00:00Z",
                "category": "инфляция",
                "verified": True,
            },
        )
    with _client(monkeypatch) as client:
        r = client.get("/api/news")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 1
        item = data["items"][0]
        assert item["source_title"] == "Росстат"
        assert item["verified"] is True

        r = client.get("/api/news", params={"source": "tass"})
        assert r.json()["total"] == 0

        r = client.get("/api/news", params={"category": "инфляция", "q": "росстат"})
        assert r.json()["total"] == 1


def test_meta_endpoint(tmp_db, monkeypatch):
    with _client(monkeypatch) as client:
        r = client.get("/api/meta")
        assert r.status_code == 200
        meta = r.json()
        source_ids = {s["id"] for s in meta["sources"]}
        assert {"cbr", "rosstat", "minfin", "tass", "interfax"} <= source_ids
        assert "прочее" in meta["all_categories"]
        assert meta["collect_interval_minutes"] >= 5


def test_frontend_served(tmp_db, monkeypatch):
    with _client(monkeypatch) as client:
        r = client.get("/")
        assert r.status_code == 200
        assert "Мониторинг" in r.text
