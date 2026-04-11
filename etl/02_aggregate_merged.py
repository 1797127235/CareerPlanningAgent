"""
02_aggregate_merged.py — 合并智联 + 上市公司两份 parquet，生成完整时间线。
额外输出 industry_signals.json（每个方向的行业分布）。
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ZHILIAN_PARQUET  = PROJECT_ROOT / "data" / "classified.parquet"
LISTED_PARQUET   = PROJECT_ROOT / "data" / "classified_listed.parquet"
DB_PATH          = PROJECT_ROOT / "career_planning.db"
TIMELINE_JSON    = PROJECT_ROOT / "data" / "market_timeline.json"
INDUSTRY_JSON    = PROJECT_ROOT / "data" / "industry_signals.json"

YEAR_QUALITY = {
    2014:"partial", 2015:"partial",
    2016:"full", 2017:"full", 2018:"full",
    2019:"full",  # 上市公司数据补全
    2020:"full",  # 上市公司数据补全
    2021:"full", 2022:"full", 2023:"full",
    2024:"full", 2025:"partial", 2026:"partial",
}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    con = duckdb.connect()

    print("[merge] 合并两份数据源...")

    # ── 时间线聚合（合并两份 parquet）──────────────────────────
    timeline_rows = con.execute(f"""
        SELECT
            role_family, year,
            COUNT(*)                                    AS job_count,
            ROUND(MEDIAN(salary_mid))                   AS salary_p50,
            ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY salary_mid)) AS salary_p25,
            ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY salary_mid)) AS salary_p75,
            ROUND(AVG(CAST(ai_tier1 AS INTEGER)) * 100, 3) AS ai_core_ratio,
            ROUND(AVG(CAST(ai_tier2 AS INTEGER)) * 100, 3) AS ai_applied_ratio,
            ROUND(AVG(CAST(ai_tier3 AS INTEGER)) * 100, 3) AS ai_general_ratio
        FROM (
            SELECT role_family, year, salary_mid, ai_tier1, ai_tier2, ai_tier3
            FROM read_parquet('{ZHILIAN_PARQUET}')
            WHERE role_family<>'unclassified'
              AND salary_mid BETWEEN 1000 AND 200000
              AND year BETWEEN 2016 AND 2025
            UNION ALL
            SELECT role_family, year, salary_mid, ai_tier1, ai_tier2, ai_tier3
            FROM read_parquet('{LISTED_PARQUET}')
            WHERE role_family<>'unclassified'
              AND salary_mid BETWEEN 1000 AND 200000
              AND year BETWEEN 2014 AND 2026
        )
        GROUP BY role_family, year
        ORDER BY role_family, year
    """).fetchall()

    print(f"[merge] 时间线: {len(timeline_rows)} 条记录")

    # ── 行业信号（仅上市公司数据有行业字段）──────────────────
    industry_rows = con.execute(f"""
        SELECT role_family, listed_industry, COUNT(*) as cnt
        FROM read_parquet('{LISTED_PARQUET}')
        WHERE role_family<>'unclassified'
          AND listed_industry<>''
          AND year BETWEEN 2021 AND 2024
        GROUP BY role_family, listed_industry
        ORDER BY role_family, cnt DESC
    """).fetchall()

    con.close()

    # ── 写 SQLite ─────────────────────────────────────────────
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS market_timeline (
            role_family TEXT, year INTEGER,
            job_count INTEGER, salary_p50 REAL, salary_p25 REAL, salary_p75 REAL,
            ai_core_ratio REAL, ai_applied_ratio REAL, ai_general_ratio REAL,
            sample_size INTEGER, data_quality TEXT,
            PRIMARY KEY (role_family, year)
        )
    """)
    conn.execute("DELETE FROM market_timeline")
    for r in timeline_rows:
        quality = YEAR_QUALITY.get(r[1], "full")
        conn.execute("INSERT OR REPLACE INTO market_timeline VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                     (*r, r[2], quality))

    conn.execute("""
        CREATE TABLE IF NOT EXISTS industry_signals (
            role_family TEXT, industry TEXT, job_count INTEGER,
            PRIMARY KEY (role_family, industry)
        )
    """)
    conn.execute("DELETE FROM industry_signals")
    conn.executemany("INSERT OR REPLACE INTO industry_signals VALUES (?,?,?)", industry_rows)
    conn.commit()
    conn.close()

    # ── 写 JSON ──────────────────────────────────────────────
    timeline: dict = {}
    for r in timeline_rows:
        fam, year = r[0], r[1]
        timeline.setdefault(fam, {})[str(year)] = {
            "job_count": r[2], "salary_p50": r[3],
            "salary_p25": r[4], "salary_p75": r[5],
            "ai_core_ratio": r[6], "ai_applied_ratio": r[7], "ai_general_ratio": r[8],
            "sample_size": r[2], "data_quality": YEAR_QUALITY.get(year, "full"),
        }
    TIMELINE_JSON.write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")

    industry: dict = {}
    for fam, ind, cnt in industry_rows:
        industry.setdefault(fam, []).append({"industry": ind, "count": cnt})
    INDUSTRY_JSON.write_text(json.dumps(industry, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── 预览 ─────────────────────────────────────────────────
    print("\n=== 合并后时间线（薪资P50 + AI渗透率）===")
    for fam in sorted(timeline.keys()):
        yrs = sorted(timeline[fam].keys())
        print(f"\n{fam}:")
        print(f"  {'年':>4}  {'岗位':>6}  {'薪资P50':>7}  {'AI%':>6}  质量")
        for y in yrs:
            d = timeline[fam][y]
            q = "✓" if d["data_quality"]=="full" else "△"
            print(f"  {y}  {d['job_count']:>6,}  {d['salary_p50']:>7.0f}  {d['ai_applied_ratio']:>5.1f}%  {q}")

    print("\n=== 行业信号 TOP3（2021-2024）===")
    for fam in sorted(industry.keys()):
        top3 = industry[fam][:3]
        names = " | ".join(f"{i['industry'][:8]}({i['count']:,})" for i in top3)
        print(f"  {fam:<12}: {names}")


if __name__ == "__main__":
    main()
