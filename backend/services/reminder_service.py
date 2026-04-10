# -*- coding: utf-8 -*-
"""
ReminderService — APScheduler-based interview reminder.
Runs hourly, marks applications whose interview_at is within 24h as reminder_sent=True.
The guidance API reads this flag to surface the homepage banner.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

_scheduler = None


def _check_reminders() -> None:
    """Hourly job: mark upcoming interviews so guidance can surface a banner."""
    try:
        from backend.db import SessionLocal
        from backend.db_models import JobApplication

        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            window_end = now + timedelta(hours=24)

            upcoming = (
                db.query(JobApplication)
                .filter(
                    JobApplication.status == "scheduled",
                    JobApplication.reminder_sent == False,  # noqa: E712
                    JobApplication.interview_at.isnot(None),
                    JobApplication.interview_at <= window_end,
                )
                .all()
            )

            if upcoming:
                for app in upcoming:
                    app.reminder_sent = True
                db.commit()
                logger.info("Marked %d interview reminders", len(upcoming))
        finally:
            db.close()
    except Exception as e:
        logger.error("Reminder check failed: %s", e)


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    try:
        from apscheduler.schedulers.background import BackgroundScheduler

        _scheduler = BackgroundScheduler(timezone="UTC")
        _scheduler.add_job(_check_reminders, "interval", hours=1, id="interview_reminder")
        _scheduler.start()
        logger.info("Reminder scheduler started")
    except Exception as e:
        logger.warning("Could not start reminder scheduler: %s", e)


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        try:
            _scheduler.shutdown(wait=False)
        except Exception:
            pass
        _scheduler = None
