"""APScheduler integration — daily rescore with filelock for multi-worker safety."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from filelock import FileLock, Timeout

logger = logging.getLogger(__name__)

LOCK_PATH = Path(__file__).resolve().parent.parent / "data" / "app_state" / ".scheduler.lock"

scheduler = AsyncIOScheduler()
_scheduler_lock: FileLock | None = None


def start_scheduler() -> None:
    """Start the scheduler if we can acquire the filelock (one worker only)."""
    global _scheduler_lock
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    _scheduler_lock = FileLock(str(LOCK_PATH), timeout=0)
    try:
        _scheduler_lock.acquire(blocking=False)
    except Timeout:
        _scheduler_lock = None
        logger.info("Scheduler lock held by another worker — skipping")
        return

    scheduler.add_job(
        _rescore_job,
        trigger=CronTrigger(hour=3, minute=0),
        id="daily-rescore",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started — daily rescore at 03:00")


def stop_scheduler() -> None:
    """Shutdown scheduler and release filelock."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
    if _scheduler_lock is not None:
        _scheduler_lock.release()
        logger.info("Scheduler lock released")


async def _rescore_job() -> None:
    """Run rescore in a thread to avoid blocking the event loop."""
    await asyncio.to_thread(_sync_rescore)


def _sync_rescore() -> None:
    from backend.scorer_service import run_rescore
    logger.info("Scheduled rescore starting...")
    result = run_rescore(triggered_by="scheduler")
    if result:
        logger.info("Scheduled rescore done: %d changed, %d zone changes",
                     result["changed_nodes"], result["zone_changes"])
    else:
        logger.info("Scheduled rescore skipped or failed")
