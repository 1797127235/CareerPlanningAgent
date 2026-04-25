"""
01_classify.py — 从原始 CSV 读取数据，按 YAML 规则分类，输出 Parquet 中间文件。

用法:
    python etl/01_classify.py [--sample N]  # --sample 仅处理前 N 行，用于测试
    python etl/01_classify.py               # 处理全量数据

输出: data/classified.parquet
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import duckdb
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = Path("E:/BaiduNetdiskDownload/智联招聘数据库2016-2025.7.csv")
RULES_PATH = PROJECT_ROOT / "etl" / "config" / "role_family_rules.yaml"
OUTPUT_PATH = PROJECT_ROOT / "data" / "classified.parquet"

# AI 关键词分层
AI_KEYWORDS = {
    "tier1_core":    ["大模型", "LLM", "GPT", "AIGC", "Transformer", "ChatGPT", "生成式AI"],
    "tier2_applied": ["机器学习", "深度学习", "TensorFlow", "PyTorch", "Keras", "神经网络"],
    "tier3_general": ["人工智能", "AI", "智能化", "智能推荐", "智能客服"],
}


def load_rules(path: Path) -> list[dict]:
    """加载 YAML 分类规则，按 priority 排序。"""
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    families = cfg.get("families", {})
    rules = []
    for name, spec in families.items():
        rules.append({
            "name": name,
            "priority": spec.get("priority", 99),
            "include": spec.get("include_keywords", []),
            "exclude": spec.get("exclude_keywords", []),
        })
    return sorted(rules, key=lambda r: r["priority"])


def build_classify_sql(rules: list[dict], sample: int | None) -> str:
    """
    构造 DuckDB SQL：读 CSV → 打 role_family 标签 → 输出 Parquet。
    使用 CASE WHEN 实现有优先级的关键词匹配。
    """
    # AI keyword CASE expressions
    def ai_case(tier_keywords: list[str], col: str = "职位描述") -> str:
        conditions = " OR ".join(f"CONTAINS({col}, '{kw}')" for kw in tier_keywords)
        return f"CASE WHEN {conditions} THEN TRUE ELSE FALSE END"

    # role_family CASE expression (ordered by priority)
    family_cases = []
    for rule in rules:
        inc_conds = " OR ".join(f"CONTAINS(招聘岗位, '{kw}')" for kw in rule["include"])
        exc_conds = " AND ".join(f"NOT CONTAINS(招聘岗位, '{kw}')" for kw in rule["exclude"]) if rule["exclude"] else "TRUE"
        family_cases.append(f"    WHEN ({inc_conds}) AND ({exc_conds}) THEN '{rule['name']}'")

    family_case_sql = "CASE\n" + "\n".join(family_cases) + "\n    ELSE 'unclassified'\nEND"

    limit_clause = f"LIMIT {sample}" if sample else ""

    # Columns we need
    ai1 = ai_case(AI_KEYWORDS["tier1_core"])
    ai2 = ai_case(AI_KEYWORDS["tier1_core"] + AI_KEYWORDS["tier2_applied"])
    ai3 = ai_case(AI_KEYWORDS["tier1_core"] + AI_KEYWORDS["tier2_applied"] + AI_KEYWORDS["tier3_general"])

    sql = f"""
COPY (
    SELECT
        招聘发布年份::INTEGER       AS year,
        招聘岗位                    AS job_title,
        工作城市                    AS city,
        最低月薪::DOUBLE            AS salary_min,
        最高月薪::DOUBLE            AS salary_max,
        (最低月薪::DOUBLE + 最高月薪::DOUBLE) / 2.0 AS salary_mid,
        {family_case_sql}           AS role_family,
        {ai1}                       AS ai_tier1,
        {ai2}                       AS ai_tier2,
        {ai3}                       AS ai_tier3
    FROM read_csv(
        '{CSV_PATH}',
        header=true,
        ignore_errors=true,
        columns={{
            '企业名称': 'VARCHAR',
            '招聘岗位': 'VARCHAR',
            '工作城市': 'VARCHAR',
            '工作区域': 'VARCHAR',
            '最低月薪': 'VARCHAR',
            '最高月薪': 'VARCHAR',
            '职位描述': 'VARCHAR',
            '学历要求': 'VARCHAR',
            '要求经验': 'VARCHAR',
            '招聘人数': 'VARCHAR',
            '招聘类别': 'VARCHAR',
            '初级分类': 'VARCHAR',
            '来源平台': 'VARCHAR',
            '公司地点': 'VARCHAR',
            '工作地点': 'VARCHAR',
            '招聘发布日期': 'VARCHAR',
            '招聘结束日期': 'VARCHAR',
            '招聘发布年份': 'VARCHAR',
            '招聘结束年份': 'VARCHAR',
            '来源': 'VARCHAR'
        }}
    )
    WHERE 招聘发布年份 IS NOT NULL
      AND 招聘岗位 IS NOT NULL
      AND 最低月薪 IS NOT NULL
      AND TRY_CAST(招聘发布年份 AS INTEGER) BETWEEN 2016 AND 2025
      AND TRY_CAST(最低月薪 AS DOUBLE) > 0
      AND TRY_CAST(最高月薪 AS DOUBLE) > 0
    {limit_clause}
) TO '{OUTPUT_PATH}' (FORMAT PARQUET, COMPRESSION ZSTD);
"""
    return sql


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=None, help="只处理前N行（测试用）")
    args = parser.parse_args()

    print(f"[01_classify] 加载分类规则: {RULES_PATH}")
    rules = load_rules(RULES_PATH)
    print(f"  → {len(rules)} 个 family，按优先级: {[r['name'] for r in rules]}")

    sql = build_classify_sql(rules, args.sample)

    if args.sample:
        print(f"[01_classify] 测试模式: 处理前 {args.sample:,} 行")
    else:
        print(f"[01_classify] 全量模式: 处理 {CSV_PATH}")

    print(f"[01_classify] 输出: {OUTPUT_PATH}")
    print("[01_classify] 开始处理...")

    t0 = time.time()
    con = duckdb.connect()
    con.execute(sql)
    con.close()
    elapsed = time.time() - t0

    # 验证输出
    con = duckdb.connect()
    stats = con.execute(f"""
        SELECT
            COUNT(*) as total,
            COUNT(DISTINCT role_family) as families,
            SUM(CASE WHEN role_family = 'unclassified' THEN 1 ELSE 0 END) as unclassified,
            MIN(year) as year_min,
            MAX(year) as year_max
        FROM read_parquet('{OUTPUT_PATH}')
    """).fetchone()
    con.close()

    total, families, unclassified, year_min, year_max = stats
    classified_pct = (total - unclassified) / total * 100 if total else 0

    print(f"\n[01_classify] 完成！耗时 {elapsed:.1f}s")
    print(f"  总行数:     {total:>12,}")
    print(f"  已分类:     {total-unclassified:>12,}  ({classified_pct:.1f}%)")
    print(f"  未分类:     {unclassified:>12,}  ({100-classified_pct:.1f}%)")
    print(f"  Family数:   {families:>12}")
    print(f"  年份范围:   {year_min} → {year_max}")


if __name__ == "__main__":
    main()
