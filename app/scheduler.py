"""Планировщик периодического сбора (APScheduler)."""
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from . import config
from .collectors import run_all

log = logging.getLogger(__name__)


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        run_all,
        "interval",
        minutes=config.COLLECT_INTERVAL_MINUTES,
        id="collect_news",
        max_instances=1,       # не запускать новый цикл, пока идёт предыдущий
        coalesce=True,         # пропущенные срабатывания схлопываются в одно
        next_run_time=datetime.now(timezone.utc),  # первый сбор сразу при старте
    )
    scheduler.start()
    log.info(
        "Планировщик запущен: сбор каждые %d мин.", config.COLLECT_INTERVAL_MINUTES
    )
    return scheduler
