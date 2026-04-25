"""
02_aggregate.py — 从 classified.parquet 聚合时序指标，写入 SQLite market_timeline 表。
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PARQUET_PATH = PROJECT_ROOT / "data" / "classified.parquet"
DB_PATH = PROJECT_ROOT / "career_planning.db"
JSON_PATH = PROJECT_ROOT / "data" / "market_timeline.json"

YEAR_QUALITY = {
    2016: "full", 2017: "full", 2018: "full",
    2019: "gap",  2020: "gap",
    2021: "full", 2022: "full", 2023: "full",
    2024: "full", 2025: "partial",
}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"[02_aggregate] 读取: {PARQUET_PATH}")
    con = duckdb.connect()

    rows = con.execute(f"""
        SELECT
            role_family,
            year,
            COUNT(*)                                    AS job_count,
            ROUND(MEDIAN(salary_mid))                   AS salary_p50,
            ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY salary_mid)) AS salary_p25,
            ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY salary_mid)) AS salary_p75,
            ROUND(AVG(CAST(ai_tier1 AS INTEGER)) * 100, 3) AS ai_core_ratio,
            ROUND(AVG(CAST(ai_tier2 AS INTEGER)) * 100, 3) AS ai_applied_ratio,
            ROUND(AVG(CAST(ai_tier3 AS INTEGER)) * 100, 3) AS ai_general_ratio,
            COUNT(*) AS sample_size
        FROM read_parquet('{PARQUET_PATH}')
        WHERE role_family != 'unclassified'
          AND salary_mid > 1000
          AND salary_mid < 200000
          AND year BETWEEN 2016 AND 2025
        GROUP BY role_family, year
        ORDER BY role_family, year
    """).fetchall()

    con.close()
    print(f"[02_aggregate] 共 {len(rows)} 条聚合记录")

    # ── 写入 SQLite ──────────────────────────────────────────
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS market_timeline (
            role_family      TEXT,
            year             INTEGER,
            job_count        INTEGER,
            salary_p50       REAL,
            salary_p25       REAL,
            salary_p75       REAL,
            ai_core_ratio    REAL,
            ai_applied_ratio REAL,
            ai_general_ratio REAL,
            sample_size      INTEGER,
            data_quality     TEXT,
            PRIMARY KEY (role_family, year)
        )
    """)
    conn.execute("DELETE FROM market_timeline")

    for r in rows:
        role_family, year = r[0], r[1]
        quality = YEAR_QUALITY.get(year, "full")
        conn.execute("""
            INSERT OR REPLACE INTO market_timeline VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (*r, quality))

    conn.commit()
    conn.close()
    print(f"[02_aggregate] 写入 SQLite: {DB_PATH}")

    # ── 同时输出 JSON（前端可直接用）─────────────────────────
    timeline: dict = {}
    for r in rows:
        role_family, year = r[0], r[1]
        if role_family not in timeline:
            timeline[role_family] = {}
        timeline[role_family][str(year)] = {
            "job_count":        r[2],
            "salary_p50":       r[3],
            "salary_p25":       r[4],
            "salary_p75":       r[5],
            "ai_core_ratio":    r[6],
            "ai_applied_ratio": r[7],
            "ai_general_ratio": r[8],
            "sample_size":      r[9],
            "data_quality":     YEAR_QUALITY.get(year, "full"),
        }

    JSON_PATH.write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[02_aggregate] 写入 JSON: {JSON_PATH}")

    # ── 打印预览 ─────────────────────────────────────────────
    print("\n=== 市场时间线预览 ===")
    for family in sorted(timeline.keys()):
        years_data = timeline[family]
        years = sorted(years_data.keys())
        print(f"\n{family}:")
        print(f"  {'年份':>4}  {'岗位数':>6}  {'薪资P50':>7}  {'AI渗透':>7}  {'质量':>6}")
        print(f"  {'-'*40}")
        for y in years:
            d = years_data[y]
            quality_mark = "✓" if d["data_quality"] == "full" else ("△" if d["data_quality"] == "partial" else "✗")
            print(f"  {y}  {d['job_count']:>6,}  {d['salary_p50']:>7.0f}  {d['ai_applied_ratio']:>6.1f}%  {quality_mark}")


if __name__ == "__main__":
    main()
