"""
01_classify_listed.py — 处理上市公司招聘大数据，额外提取行业字段。

输出: data/classified_listed.parquet
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import duckdb
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path("E:/BaiduNetdiskDownload/上市公司招聘大数据更新！（2014-2026.3）/分年份保存数据")
RULES_PATH = PROJECT_ROOT / "etl" / "config" / "role_family_rules.yaml"
OUTPUT_PATH = PROJECT_ROOT / "data" / "classified_listed.parquet"

AI_KEYWORDS = {
    "tier1_core":    ["大模型", "LLM", "GPT", "AIGC", "Transformer"],
    "tier2_applied": ["机器学习", "深度学习", "TensorFlow", "PyTorch", "神经网络"],
    "tier3_general": ["人工智能", "AI", "智能化"],
}


def load_rules(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    rules = []
    for name, spec in cfg.get("families", {}).items():
        rules.append({
            "name": name,
            "priority": spec.get("priority", 99),
            "include": spec.get("include_keywords", []),
            "exclude": spec.get("exclude_keywords", []),
        })
    return sorted(rules, key=lambda r: r["priority"])


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    rules = load_rules(RULES_PATH)
    print(f"[listed] 分类规则: {len(rules)} 个 family")

    # Build CASE expression for role_family
    family_cases = []
    for rule in rules:
        inc = " OR ".join(f"CONTAINS(招聘岗位, '{kw}')" for kw in rule["include"])
        exc = " AND ".join(f"NOT CONTAINS(招聘岗位, '{kw}')" for kw in rule["exclude"]) if rule["exclude"] else "TRUE"
        family_cases.append(f"    WHEN ({inc}) AND ({exc}) THEN '{rule['name']}'")
    family_case_sql = "CASE\n" + "\n".join(family_cases) + "\n    ELSE 'unclassified'\nEND"

    def ai_case(kws):
        conds = " OR ".join(f"CONTAINS(职位描述, '{kw}')" for kw in kws)
        return f"CASE WHEN {conds} THEN TRUE ELSE FALSE END"

    ai1 = ai_case(AI_KEYWORDS["tier1_core"])
    ai2 = ai_case(AI_KEYWORDS["tier1_core"] + AI_KEYWORDS["tier2_applied"])
    ai3 = ai_case(AI_KEYWORDS["tier1_core"] + AI_KEYWORDS["tier2_applied"] + AI_KEYWORDS["tier3_general"])

    # Use glob to read all yearly CSV files at once
    csv_glob = str(DATA_DIR / "上市公司招聘数据*.csv").replace("\\", "/")

    sql = f"""
COPY (
    SELECT
        TRY_CAST(招聘发布年份 AS INTEGER)          AS year,
        招聘岗位                                    AS job_title,
        工作城市                                    AS city,
        TRY_CAST(最低月薪 AS DOUBLE)               AS salary_min,
        TRY_CAST(最高月薪 AS DOUBLE)               AS salary_max,
        (TRY_CAST(最低月薪 AS DOUBLE) + TRY_CAST(最高月薪 AS DOUBLE)) / 2.0 AS salary_mid,
        {family_case_sql}                           AS role_family,
        {ai1}                                       AS ai_tier1,
        {ai2}                                       AS ai_tier2,
        {ai3}                                       AS ai_tier3,
        COALESCE(上市公司行业, '')                   AS listed_industry,
        COALESCE(股票简称, '')                       AS stock_name,
        COALESCE(与上市公司关系, '')                 AS company_relation
    FROM read_csv(
        '{csv_glob}',
        header=true,
        ignore_errors=true,
        union_by_name=true
    )
    WHERE 招聘发布年份 IS NOT NULL
      AND 招聘岗位 IS NOT NULL
      AND TRY_CAST(招聘发布年份 AS INTEGER) BETWEEN 2014 AND 2026
      AND TRY_CAST(最低月薪 AS DOUBLE) > 0
      AND TRY_CAST(最高月薪 AS DOUBLE) > 0
) TO '{OUTPUT_PATH}' (FORMAT PARQUET, COMPRESSION ZSTD);
"""

    print(f"[listed] 处理: {csv_glob}")
    print(f"[listed] 输出: {OUTPUT_PATH}")
    print("[listed] 开始处理（9.7GB，预计3-5分钟）...")

    t0 = time.time()
    con = duckdb.connect()
    con.execute(sql)
    con.close()
    elapsed = time.time() - t0

    # Stats
    con = duckdb.connect()
    stats = con.execute(f"""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN role_family<>'unclassified' THEN 1 ELSE 0 END) as cs_jobs,
            MIN(year) as y_min, MAX(year) as y_max,
            COUNT(DISTINCT year) as year_count
        FROM read_parquet('{OUTPUT_PATH}')
    """).fetchone()

    print(f"\n[listed] 完成！耗时 {elapsed:.0f}s")
    print(f"  总行数:   {stats[0]:>12,}")
    print(f"  CS岗位:   {stats[1]:>12,}  ({stats[1]/stats[0]*100:.1f}%)")
    print(f"  年份范围: {stats[2]} → {stats[3]}  ({stats[4]} 年)")

    # Year + CS distribution
    print("\n[listed] 年度分布:")
    rows = con.execute(f"""
        SELECT year, COUNT(*) as total,
               SUM(CASE WHEN role_family<>'unclassified' THEN 1 ELSE 0 END) as cs
        FROM read_parquet('{OUTPUT_PATH}')
        GROUP BY year ORDER BY year
    """).fetchall()
    gaps = {2019, 2020}
    for y, total, cs in rows:
        gap_mark = " ← 智联断层年份，此处补全" if y in gaps else ""
        print(f"  {y}: {total:>8,}条  CS={cs:>6,}{gap_mark}")

    # Top industries for CS jobs
    print("\n[listed] CS岗位行业分布 TOP10:")
    ind_rows = con.execute(f"""
        SELECT listed_industry, COUNT(*) as cnt
        FROM read_parquet('{OUTPUT_PATH}')
        WHERE role_family<>'unclassified' AND listed_industry<>''
        GROUP BY listed_industry ORDER BY cnt DESC LIMIT 10
    """).fetchall()
    for ind, cnt in ind_rows:
        print(f"  {str(ind)[:25]:27s} {cnt:>6,}")

    con.close()


if __name__ == "__main__":
    main()
