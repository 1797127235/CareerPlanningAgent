#!/usr/bin/env python3
"""
Import Anthropic Economic Index data into SQLite.

Sources:
  1. data/EconomicIndex/labor_market_impacts/job_exposure.csv     → onet_jobs
  2. data/EconomicIndex/labor_market_impacts/task_penetration.csv → onet_tasks
  3. data/EconomicIndex/release_2025_03_27/automation_vs_augmentation_by_task.csv
                                                                  → task_automation
  4. data/onet_mapping.json                                        → job_nodes.onet_soc_codes

Usage:
    python -m scripts.import_onet_data       # from project root
    python scripts/import_onet_data.py       # direct run
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

# ── bootstrap path ────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import text

from backend.db import engine, init_db, SessionLocal
from backend.models import OnetJob, OnetTask, TaskAutomation, JobNode

# ── data file paths ───────────────────────────────────────────
JOB_EXPOSURE_CSV = (
    PROJECT_ROOT / "data" / "EconomicIndex" / "labor_market_impacts" / "job_exposure.csv"
)
TASK_PENETRATION_CSV = (
    PROJECT_ROOT / "data" / "EconomicIndex" / "labor_market_impacts" / "task_penetration.csv"
)
AUTOMATION_CSV = (
    PROJECT_ROOT
    / "data"
    / "EconomicIndex"
    / "release_2025_03_27"
    / "automation_vs_augmentation_by_task.csv"
)
ONET_MAPPING_JSON = PROJECT_ROOT / "data" / "onet_mapping.json"


# ── helpers ───────────────────────────────────────────────────

def _safe_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


# ── import functions ──────────────────────────────────────────

def import_onet_jobs(session) -> int:
    """Import job_exposure.csv → onet_jobs table (upsert)."""
    if not JOB_EXPOSURE_CSV.exists():
        print(f"[WARN] Not found, skipping onet_jobs: {JOB_EXPOSURE_CSV}")
        return 0

    inserted = updated = 0
    with open(JOB_EXPOSURE_CSV, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            occ_code = row["occ_code"].strip()
            title = row["title"].strip()
            observed_exposure = _safe_float(row["observed_exposure"])

            existing = session.query(OnetJob).filter_by(occ_code=occ_code).first()
            if existing:
                existing.title = title
                existing.observed_exposure = observed_exposure
                updated += 1
            else:
                session.add(
                    OnetJob(
                        occ_code=occ_code,
                        title=title,
                        observed_exposure=observed_exposure,
                    )
                )
                inserted += 1

    session.flush()
    total = inserted + updated
    print(f"  [onet_jobs]       {total:>6} rows  (inserted={inserted}, updated={updated})")
    return total


def import_onet_tasks(session) -> int:
    """Import task_penetration.csv → onet_tasks table (upsert)."""
    if not TASK_PENETRATION_CSV.exists():
        print(f"[WARN] Not found, skipping onet_tasks: {TASK_PENETRATION_CSV}")
        return 0

    inserted = updated = 0
    with open(TASK_PENETRATION_CSV, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            task_name = row["task"].strip()
            penetration = _safe_float(row["penetration"])

            if not task_name:
                continue

            existing = session.query(OnetTask).filter_by(task_name=task_name).first()
            if existing:
                existing.penetration = penetration
                updated += 1
            else:
                session.add(OnetTask(task_name=task_name, penetration=penetration))
                inserted += 1

    session.flush()
    total = inserted + updated
    print(f"  [onet_tasks]      {total:>6} rows  (inserted={inserted}, updated={updated})")
    return total


def import_task_automation(session) -> int:
    """Import automation_vs_augmentation_by_task.csv → task_automation table (upsert)."""
    if not AUTOMATION_CSV.exists():
        print(f"[WARN] Not found, skipping task_automation: {AUTOMATION_CSV}")
        return 0

    inserted = updated = 0
    with open(AUTOMATION_CSV, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            task_name = row["task_name"].strip()
            if not task_name:
                continue

            values = dict(
                directive=_safe_float(row.get("directive", "")),
                feedback_loop=_safe_float(row.get("feedback_loop", "")),
                task_iteration=_safe_float(row.get("task_iteration", "")),
                validation=_safe_float(row.get("validation", "")),
                learning=_safe_float(row.get("learning", "")),
                filtered=_safe_float(row.get("filtered", "")),
            )

            existing = session.query(TaskAutomation).filter_by(task_name=task_name).first()
            if existing:
                for k, v in values.items():
                    setattr(existing, k, v)
                updated += 1
            else:
                session.add(TaskAutomation(task_name=task_name, **values))
                inserted += 1

    session.flush()
    total = inserted + updated
    print(
        f"  [task_automation] {total:>6} rows  (inserted={inserted}, updated={updated})"
    )
    return total


def import_onet_mapping(session) -> int:
    """Import onet_mapping.json → job_nodes.onet_soc_codes (update existing nodes)."""
    if not ONET_MAPPING_JSON.exists():
        print(f"[WARN] Not found, skipping onet_mapping: {ONET_MAPPING_JSON}")
        return 0

    with open(ONET_MAPPING_JSON, encoding="utf-8") as fh:
        raw = json.load(fh)

    mappings: dict = raw.get("mappings", {})
    if not mappings:
        print("[WARN] onet_mapping.json has no 'mappings' key, skipping")
        return 0

    updated = skipped = 0
    for label, soc_codes in mappings.items():
        label = label.strip()
        # Match job_nodes by label (node label is the Chinese job title)
        node = session.query(JobNode).filter_by(label=label).first()
        if node is None:
            skipped += 1
            continue
        node.onet_soc_codes = soc_codes
        updated += 1

    session.flush()
    total_mappings = len(mappings)
    print(
        f"  [onet_mapping]    {total_mappings:>6} entries  "
        f"(nodes_updated={updated}, nodes_not_found={skipped})"
    )
    return updated


# ── main ──────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("O*NET Economic Index — Data Import to SQLite")
    print("=" * 60)

    # Ensure all tables exist (creates new tables; won't alter existing ones)
    init_db()
    db_path = PROJECT_ROOT / "data" / "app_state" / "app.db"
    print(f"[OK] Database ready: {db_path}")

    # Ensure onet_soc_codes column exists (SQLite ALTER TABLE migration)
    with engine.connect() as conn:
        cols = [
            row[1]
            for row in conn.execute(text("PRAGMA table_info(job_nodes)")).fetchall()
        ]
        if "onet_soc_codes" not in cols:
            conn.execute(
                text("ALTER TABLE job_nodes ADD COLUMN onet_soc_codes JSON DEFAULT '[]'")
            )
            conn.commit()
            print("[OK] Added missing column: job_nodes.onet_soc_codes")
        else:
            print("[OK] Column job_nodes.onet_soc_codes already present")
    print()

    session = SessionLocal()
    try:
        print("Importing data ...")
        n_jobs = import_onet_jobs(session)
        n_tasks = import_onet_tasks(session)
        n_automation = import_task_automation(session)
        n_mapping = import_onet_mapping(session)

        session.commit()
        print("\n[OK] All imports committed.\n")

        # Summary stats
        print("─" * 40)
        print(f"  onet_jobs       : {session.query(OnetJob).count():>6}")
        print(f"  onet_tasks      : {session.query(OnetTask).count():>6}")
        print(f"  task_automation : {session.query(TaskAutomation).count():>6}")
        nodes_with_soc = (
            session.query(JobNode)
            .filter(JobNode.onet_soc_codes.isnot(None))
            .count()
        )
        print(f"  job_nodes with onet_soc_codes: {nodes_with_soc:>6}")
        print("─" * 40)

    except Exception as exc:
        session.rollback()
        print(f"\n[ERROR] Import failed: {exc}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
