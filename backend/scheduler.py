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

    # 新增：每天 09:00 跑 heartbeat
    scheduler.add_job(
        _heartbeat_job,
        trigger=CronTrigger(hour=9, minute=0),
        id="daily-heartbeat",
        replace_existing=True,
    )

    # 新增：每周日 04:00 跑 pattern analysis
    scheduler.add_job(
        _pattern_analysis_job,
        trigger=CronTrigger(day_of_week="sun", hour=4, minute=0),
        id="weekly-pattern-analysis",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started — daily rescore at 03:00, heartbeat at 09:00, weekly pattern analysis at Sun 04:00")


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


async def _heartbeat_job() -> None:
    await asyncio.to_thread(_sync_heartbeat)


def _sync_heartbeat() -> None:
    from backend.services.heartbeat_service import run_heartbeat
    run_heartbeat()


async def _pattern_analysis_job() -> None:
    await asyncio.to_thread(_sync_pattern_analysis)


def _sync_pattern_analysis() -> None:
    from backend.services.pattern_analyzer import run_pattern_analysis_all
    run_pattern_analysis_all()
