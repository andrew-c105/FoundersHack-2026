from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

import database as db
from services.pipeline import refresh_signals_for_location

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def scheduled_refresh() -> None:
    try:
        for loc in db.list_locations():
            refresh_signals_for_location(loc["id"])
    except Exception:
        logger.exception("scheduled_refresh failed")


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(scheduled_refresh, "interval", hours=6, id="poll_signals", replace_existing=True)
    scheduler.start()


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
