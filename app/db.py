"""Схема БД (SQLite) и все операции с ней.

Таблица news_items соответствует ТЗ:
id, title, summary, source, url, published_at, collected_at, category, verified.
Дополнительно хранится dedup_hash (SHA-256 от нормализованного заголовка + даты
публикации) с UNIQUE-ограничением — защита от дубликатов на уровне БД.
"""
import hashlib
import re
import sqlite3
from datetime import datetime, timezone

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS news_items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    title        TEXT NOT NULL,
    summary      TEXT NOT NULL DEFAULT '',
    source       TEXT NOT NULL,
    url          TEXT NOT NULL,
    published_at TEXT NOT NULL,               -- ISO 8601, UTC
    collected_at TEXT NOT NULL,               -- ISO 8601, UTC
    category     TEXT NOT NULL DEFAULT 'прочее',
    verified     INTEGER NOT NULL DEFAULT 0,  -- 1 = официальный первоисточник
    dedup_hash   TEXT NOT NULL UNIQUE
);
CREATE INDEX IF NOT EXISTS idx_news_published ON news_items (published_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_source    ON news_items (source);
CREATE INDEX IF NOT EXISTS idx_news_category  ON news_items (category);

CREATE TABLE IF NOT EXISTS collection_runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    collector   TEXT NOT NULL,
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    status      TEXT NOT NULL DEFAULT 'running',  -- running | ok | error
    items_found INTEGER NOT NULL DEFAULT 0,
    items_added INTEGER NOT NULL DEFAULT 0,
    error       TEXT
);
CREATE INDEX IF NOT EXISTS idx_runs_collector ON collection_runs (collector, id DESC);
"""

_WS_RE = re.compile(r"\s+")


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect() -> sqlite3.Connection:
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    # LIKE в SQLite не учитывает регистр только для ASCII — для кириллицы
    # нужна собственная функция приведения регистра.
    conn.create_function(
        "cfold", 1, lambda s: s.casefold() if isinstance(s, str) else s
    )
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


def make_dedup_hash(title: str, published_at: str) -> str:
    """Хэш заголовка + даты публикации (только дата, без времени).

    Нормализация заголовка (регистр, пробелы, «ё») делает дедупликацию
    устойчивой к косметическим правкам, а усечение до даты — к небольшим
    сдвигам времени публикации в ленте.
    """
    norm_title = _WS_RE.sub(" ", title).strip().lower().replace("ё", "е")
    date_part = (published_at or "")[:10]
    return hashlib.sha256(f"{norm_title}|{date_part}".encode("utf-8")).hexdigest()


def insert_item(conn: sqlite3.Connection, item: dict) -> bool:
    """Вставляет новость; возвращает False, если такая уже есть (дубликат)."""
    cur = conn.execute(
        """INSERT OR IGNORE INTO news_items
           (title, summary, source, url, published_at, collected_at,
            category, verified, dedup_hash)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            item["title"],
            item.get("summary", ""),
            item["source"],
            item["url"],
            item["published_at"],
            item.get("collected_at") or utcnow_iso(),
            item.get("category", "прочее"),
            1 if item.get("verified") else 0,
            make_dedup_hash(item["title"], item["published_at"]),
        ),
    )
    return cur.rowcount > 0


def query_news(
    sources: list[str] | None = None,
    categories: list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    where, params = [], []
    if sources:
        where.append(f"source IN ({','.join('?' * len(sources))})")
        params.extend(sources)
    if categories:
        where.append(f"category IN ({','.join('?' * len(categories))})")
        params.extend(categories)
    if date_from:
        where.append("published_at >= ?")
        params.append(date_from)
    if date_to:
        # включительно до конца дня
        where.append("published_at <= ?")
        params.append(date_to + "T23:59:59Z" if len(date_to) == 10 else date_to)
    if q:
        where.append("(cfold(title) LIKE ? OR cfold(summary) LIKE ?)")
        like = f"%{q.casefold()}%"
        params.extend([like, like])

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    with connect() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM news_items {where_sql}", params
        ).fetchone()[0]
        rows = conn.execute(
            f"""SELECT id, title, summary, source, url, published_at,
                       collected_at, category, verified
                FROM news_items {where_sql}
                ORDER BY published_at DESC, id DESC
                LIMIT ? OFFSET ?""",
            params + [limit, offset],
        ).fetchall()
    items = [dict(r, verified=bool(r["verified"])) for r in rows]
    return items, total


def start_run(collector: str) -> int:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO collection_runs (collector, started_at) VALUES (?, ?)",
            (collector, utcnow_iso()),
        )
        return cur.lastrowid


def finish_run(
    run_id: int,
    status: str,
    items_found: int = 0,
    items_added: int = 0,
    error: str | None = None,
) -> None:
    with connect() as conn:
        conn.execute(
            """UPDATE collection_runs
               SET finished_at = ?, status = ?, items_found = ?,
                   items_added = ?, error = ?
               WHERE id = ?""",
            (utcnow_iso(), status, items_found, items_added, error, run_id),
        )


def get_meta() -> dict:
    with connect() as conn:
        total = conn.execute("SELECT COUNT(*) FROM news_items").fetchone()[0]
        by_source = {
            r["source"]: r["n"]
            for r in conn.execute(
                "SELECT source, COUNT(*) AS n FROM news_items GROUP BY source"
            )
        }
        by_category = [
            {"name": r["category"], "items": r["n"]}
            for r in conn.execute(
                "SELECT category, COUNT(*) AS n FROM news_items "
                "GROUP BY category ORDER BY n DESC"
            )
        ]
        last_updated = conn.execute(
            "SELECT MAX(finished_at) FROM collection_runs WHERE status = 'ok'"
        ).fetchone()[0]
        # последний запуск каждого коллектора
        runs = [
            dict(r)
            for r in conn.execute(
                """SELECT collector, started_at, finished_at, status,
                          items_found, items_added, error
                   FROM collection_runs
                   WHERE id IN (SELECT MAX(id) FROM collection_runs GROUP BY collector)
                   ORDER BY collector"""
            )
        ]
    return {
        "total_items": total,
        "items_by_source": by_source,
        "categories": by_category,
        "last_updated": last_updated,
        "runs": runs,
    }
