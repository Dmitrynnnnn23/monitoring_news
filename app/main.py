"""FastAPI-приложение: REST API + раздача веб-интерфейса."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles

from . import config, db
from .categorizer import CATEGORIES
from .collectors import SOURCE_TITLES, get_sources, run_all
from .scheduler import start_scheduler

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    scheduler = None
    if not config.DISABLE_SCHEDULER:
        scheduler = start_scheduler()
    yield
    if scheduler:
        scheduler.shutdown(wait=False)


app = FastAPI(
    title="Мониторинг макроэкономических новостей России",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/api/news")
def api_news(
    source: str | None = Query(None, description="id источников через запятую"),
    category: str | None = Query(None, description="категории через запятую"),
    date_from: str | None = Query(None, description="YYYY-MM-DD"),
    date_to: str | None = Query(None, description="YYYY-MM-DD"),
    q: str | None = Query(None, description="поиск по заголовку и тексту"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    items, total = db.query_news(
        sources=[s.strip() for s in source.split(",") if s.strip()] if source else None,
        categories=[c.strip() for c in category.split(",") if c.strip()]
        if category
        else None,
        date_from=date_from,
        date_to=date_to,
        q=q,
        limit=limit,
        offset=offset,
    )
    for item in items:
        item["source_title"] = SOURCE_TITLES.get(item["source"], item["source"])
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@app.get("/api/meta")
def api_meta():
    meta = db.get_meta()
    meta["sources"] = get_sources()
    meta["all_categories"] = CATEGORIES
    meta["collect_interval_minutes"] = config.COLLECT_INTERVAL_MINUTES
    return meta


@app.post("/api/collect")
def api_collect():
    """Ручной запуск сбора (кнопка «Обновить сейчас» в интерфейсе)."""
    try:
        return {"results": run_all()}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# Статика фронтенда — монтируется последней, чтобы не перекрывать /api/*.
app.mount("/", StaticFiles(directory=config.FRONTEND_DIR, html=True), name="frontend")
