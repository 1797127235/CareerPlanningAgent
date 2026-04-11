"""
04_skill_frequency.py — 从真实招聘数据计算每个方向的技能出现频率。

输入:
  - E:/BaiduNetdiskDownload/智联招聘数据库2016-2025.7.csv
  - E:/BaiduNetdiskDownload/上市公司招聘大数据.../上市公司招聘大数据2014-2026.3.csv
  - data/graph.json (现有 must_skills)

输出:
  - data/skill_frequencies.json  (每个 role_family 的技能频率 + 分层)

用法:
    python etl/04_skill_frequency.py              # 全量 2021-2024
    python etl/04_skill_frequency.py --sample 50000  # 快速测试
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import duckdb
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RULES_PATH = PROJECT_ROOT / "etl" / "config" / "role_family_rules.yaml"
GRAPH_PATH = PROJECT_ROOT / "data" / "graph.json"
OUTPUT_PATH = PROJECT_ROOT / "data" / "skill_frequencies.json"

ZHAOPIN_CSV = Path("E:/BaiduNetdiskDownload/智联招聘数据库2016-2025.7.csv")
LISTED_CSV = Path("E:/BaiduNetdiskDownload/上市公司招聘大数据更新！（2014-2026.3）/上市公司招聘大数据2014-2026.3/上市公司招聘大数据2014-2026.3.csv")

# 只看近年数据（市场代表性最强）
YEAR_MIN = 2021
YEAR_MAX = 2024

# ── 技能关键词库 ──────────────────────────────────────────────────────────────
# 每个 role_family 的候选技能词（含常见缩写/变体）
# CONTAINS 做子串匹配，大小写不敏感
SKILL_CANDIDATES: dict[str, list[str]] = {
    "后端开发": [
        "Java", "Spring Boot", "SpringBoot", "Spring Cloud", "MyBatis",
        "MySQL", "Redis", "RocketMQ", "Kafka", "RabbitMQ",
        "消息队列", "微服务", "Docker", "Kubernetes", "K8s",
        "多线程", "并发", "JVM", "Netty", "Dubbo",
        "Python", "Golang", "Go语言", "gRPC", "Elasticsearch",
        "MongoDB", "PostgreSQL", "分布式", "高并发", "负载均衡",
        "Linux", "Git", "Maven", "Gradle", "设计模式",
    ],
    "前端开发": [
        "Vue", "React", "Angular", "TypeScript", "JavaScript",
        "HTML", "CSS", "Webpack", "Vite", "Node.js",
        "小程序", "uni-app", "Next.js", "Nuxt", "ElementUI",
        "Ant Design", "Axios", "Git", "ES6", "响应式",
        "性能优化", "跨端", "Flutter", "React Native",
    ],
    "AI/ML": [
        "Python", "PyTorch", "TensorFlow", "机器学习", "深度学习",
        "自然语言处理", "NLP", "计算机视觉", "CV", "大模型",
        "LLM", "BERT", "Transformer", "强化学习", "特征工程",
        "Pandas", "NumPy", "scikit-learn", "CUDA", "GPU",
        "推荐系统", "知识图谱", "语音识别", "目标检测", "AIGC",
    ],
    "数据": [
        "SQL", "MySQL", "Hive", "Spark", "Flink",
        "Hadoop", "数据仓库", "ETL", "Kafka", "ClickHouse",
        "Python", "Tableau", "PowerBI", "数据分析", "数据挖掘",
        "A/B测试", "统计学", "Excel", "Presto", "HBase",
        "实时计算", "离线计算", "数据治理", "指标体系",
    ],
    "系统开发": [
        "C++", "Rust", "Linux", "内核", "驱动",
        "音视频", "FFmpeg", "WebRTC", "网络协议", "TCP/IP",
        "性能优化", "内存管理", "多线程", "并发", "汇编",
        "嵌入式", "RTOS", "操作系统", "存储", "数据库内核",
    ],
    "移动开发": [
        "Android", "iOS", "Swift", "Kotlin", "Java",
        "Flutter", "React Native", "uni-app", "Objective-C",
        "性能优化", "内存优化", "热修复", "插件化", "NDK",
        "Jetpack", "SwiftUI", "Xcode", "Android Studio",
    ],
    "游戏开发": [
        "Unity", "Unreal", "UE4", "UE5", "C++",
        "C#", "Lua", "渲染", "Shader", "图形",
        "物理引擎", "网络同步", "服务端", "客户端", "性能优化",
        "DirectX", "OpenGL", "Vulkan", "游戏引擎", "战斗系统",
    ],
    "运维/DevOps": [
        "Linux", "Docker", "Kubernetes", "K8s", "Jenkins",
        "CI/CD", "Ansible", "Terraform", "Prometheus", "Grafana",
        "Shell", "Python", "Nginx", "负载均衡", "监控",
        "云计算", "AWS", "阿里云", "腾讯云", "网络",
        "故障排查", "自动化", "GitOps", "Helm", "Istio",
    ],
    "安全": [
        "渗透测试", "漏洞挖掘", "Web安全", "网络安全", "逆向",
        "Burp Suite", "Python", "CTF", "代码审计", "安全开发",
        "密码学", "防火墙", "入侵检测", "红队", "蓝队",
        "OWASP", "XSS", "SQL注入", "二进制", "移动安全",
    ],
    "质量保障": [
        "测试", "自动化测试", "Selenium", "Appium", "JMeter",
        "Python", "Java", "接口测试", "性能测试", "压力测试",
        "TestNG", "pytest", "Jenkins", "CI/CD", "测试用例",
        "黑盒测试", "白盒测试", "回归测试", "缺陷管理",
    ],
    "产品": [
        "产品设计", "需求分析", "原型设计", "Axure", "Figma",
        "用户研究", "数据分析", "SQL", "产品规划", "项目管理",
        "B端产品", "C端产品", "PRD", "竞品分析", "用户体验",
    ],
    "管理": [
        "团队管理", "项目管理", "技术规划", "架构设计", "研发管理",
        "敏捷", "Scrum", "OKR", "技术选型", "代码评审",
        "跨部门协作", "招聘", "绩效管理",
    ],
}


def load_classification_rules() -> list[dict]:
    with open(RULES_PATH, encoding="utf-8") as f:
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


def build_family_case_sql(rules: list[dict]) -> str:
    cases = []
    for rule in rules:
        inc = " OR ".join(f"CONTAINS(招聘岗位, '{kw}')" for kw in rule["include"])
        exc = " AND ".join(f"NOT CONTAINS(招聘岗位, '{kw}')" for kw in rule["exclude"]) if rule["exclude"] else "TRUE"
        cases.append(f"    WHEN ({inc}) AND ({exc}) THEN '{rule['name']}'")
    return "CASE\n" + "\n".join(cases) + "\n    ELSE NULL\nEND"


def extract_source_to_table(
    con: duckdb.DuckDBPyConnection,
    table_name: str,
    csv_path: Path,
    family_case: str,
    extra_cols: list[str],
    sample: int | None,
) -> None:
    """用 Python 注册 CSV 为 DuckDB 视图，绕过中文路径编码问题。"""
    import pandas as pd

    # 智联: 20 列；上市公司: 24 列（多 股票简称/关联股票代码/与上市公司关系/上市公司行业）
    base_cols = [
        "企业名称", "招聘岗位", "工作城市", "工作区域",
        "最低月薪", "最高月薪", "职位描述", "学历要求",
        "要求经验", "招聘人数", "招聘类别", "初级分类",
        "来源平台", "公司地点", "工作地点",
        "招聘发布日期", "招聘结束日期",
        "招聘发布年份", "招聘结束年份", "来源",
    ]
    all_cols = extra_cols + base_cols if extra_cols else base_cols

    print(f"  读取 {csv_path.name}...", end=" ", flush=True)
    t0 = time.time()

    chunks = []
    nrows = sample if sample else None
    for chunk in pd.read_csv(
        csv_path,
        header=0,
        usecols=["招聘岗位", "职位描述", "招聘发布年份"],
        dtype=str,
        chunksize=200_000,
        on_bad_lines="skip",
        encoding="utf-8",
        nrows=nrows,
    ):
        chunk = chunk[
            chunk["招聘发布年份"].apply(
                lambda y: str(y).strip().isdigit() and YEAR_MIN <= int(y) <= YEAR_MAX
            )
        ]
        chunk = chunk[
            chunk["职位描述"].notna() &
            chunk["招聘岗位"].notna() &
            (chunk["职位描述"].str.len() > 50)
        ]
        if not chunk.empty:
            chunks.append(chunk[["招聘岗位", "职位描述"]])

    if not chunks:
        print("无有效数据")
        con.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT NULL::VARCHAR AS role_family, NULL::VARCHAR AS description WHERE FALSE")
        return

    df = pd.concat(chunks, ignore_index=True)
    print(f"{len(df):,} 行 ({time.time()-t0:.1f}s)")

    # 注册 DataFrame 为 DuckDB relation，然后用 Python-side classification
    con.register("_raw_df", df)
    con.execute(f"""
        CREATE OR REPLACE TABLE {table_name} AS
        SELECT
            {family_case} AS role_family,
            职位描述 AS description
        FROM _raw_df
        WHERE role_family IS NOT NULL
    """)


def count_skill_frequencies(
    con: duckdb.DuckDBPyConnection,
    temp_table: str,
) -> dict[str, dict[str, dict]]:
    """
    对每个 role_family 统计各技能关键词的出现频率。
    返回: { role_family: { skill: { count, total, freq } } }
    """
    # 先统计各 family 的总 JD 数
    totals = con.execute(f"""
        SELECT role_family, COUNT(*) as cnt
        FROM {temp_table}
        WHERE role_family IS NOT NULL
        GROUP BY role_family
    """).fetchall()
    total_map = {row[0]: row[1] for row in totals}

    results: dict[str, dict[str, dict]] = {}

    for family, skills in SKILL_CANDIDATES.items():
        if family not in total_map:
            print(f"  [skip] {family} — 无数据")
            continue

        total = total_map[family]
        print(f"  {family}: {total:,} 条 JD，检测 {len(skills)} 个技能...", end=" ", flush=True)
        t0 = time.time()

        # 一次性查询所有技能的命中数
        skill_cases = ",\n        ".join(
            f"SUM(CASE WHEN CONTAINS(lower(description), lower('{skill.replace(chr(39), chr(39)+chr(39))}')) THEN 1 ELSE 0 END) AS s_{i}"
            for i, skill in enumerate(skills)
        )

        row = con.execute(f"""
            SELECT {skill_cases}
            FROM {temp_table}
            WHERE role_family = '{family}'
        """).fetchone()

        family_result = {}
        for i, skill in enumerate(skills):
            count = row[i] if row else 0
            freq = round(count / total, 4) if total > 0 else 0.0
            family_result[skill] = {
                "count": count,
                "total": total,
                "freq": freq,
                "tier": "core" if freq >= 0.5 else ("important" if freq >= 0.2 else ("bonus" if freq >= 0.05 else "rare")),
            }

        results[family] = family_result
        elapsed = time.time() - t0
        print(f"完成 ({elapsed:.1f}s)")

    return results


def build_output(freq_data: dict) -> dict:
    """转换为输出格式：按 tier 分组，排除 rare 技能。"""
    output = {}
    for family, skills in freq_data.items():
        core = sorted(
            [(s, d) for s, d in skills.items() if d["tier"] == "core"],
            key=lambda x: -x[1]["freq"]
        )
        important = sorted(
            [(s, d) for s, d in skills.items() if d["tier"] == "important"],
            key=lambda x: -x[1]["freq"]
        )
        bonus = sorted(
            [(s, d) for s, d in skills.items() if d["tier"] == "bonus"],
            key=lambda x: -x[1]["freq"]
        )
        output[family] = {
            "total_jds": list(skills.values())[0]["total"] if skills else 0,
            "year_range": f"{YEAR_MIN}-{YEAR_MAX}",
            "core": [{"name": s, "freq": d["freq"]} for s, d in core],
            "important": [{"name": s, "freq": d["freq"]} for s, d in important],
            "bonus": [{"name": s, "freq": d["freq"]} for s, d in bonus],
        }
    return output


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=None, help="每个CSV只取前N行（测试用）")
    args = parser.parse_args()

    print(f"=== 技能频率 ETL ({YEAR_MIN}-{YEAR_MAX}) ===")
    if args.sample:
        print(f"[测试模式] 每个CSV只读 {args.sample:,} 行")

    rules = load_classification_rules()
    family_case = build_family_case_sql(rules)

    con = duckdb.connect()

    # ── Step 1: 提取两个数据源，合并为临时表 ──
    print("\n[Step 1] 读取数据源，提取 role_family + 职位描述...")
    t0 = time.time()

    # 上市公司CSV有额外4列（股票简称/关联股票代码/与上市公司关系/上市公司行业）
    listed_extra_cols = ["股票简称", "关联股票代码", "与上市公司关系", "上市公司行业"]

    extract_source_to_table(con, "jd_zhaopin", ZHAOPIN_CSV, family_case, [], args.sample)
    extract_source_to_table(con, "jd_listed", LISTED_CSV, family_case, listed_extra_cols, args.sample)

    con.execute("""
        CREATE OR REPLACE TABLE jd_text AS
        SELECT * FROM jd_zhaopin
        UNION ALL
        SELECT * FROM jd_listed
    """)

    total_rows = con.execute("SELECT COUNT(*) FROM jd_text").fetchone()[0]
    print(f"  合并后有效 JD: {total_rows:,} 条 ({time.time()-t0:.1f}s)")

    # family 分布
    dist = con.execute("""
        SELECT role_family, COUNT(*) as cnt
        FROM jd_text GROUP BY role_family ORDER BY cnt DESC
    """).fetchall()
    print("  各方向分布:")
    for row in dist:
        print(f"    {row[0]:12s}: {row[1]:>10,}")

    # ── Step 2: 统计技能频率 ──
    print("\n[Step 2] 统计各方向技能频率...")
    freq_data = count_skill_frequencies(con, "jd_text")

    # ── Step 3: 输出 JSON ──
    output = build_output(freq_data)
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ 输出: {OUTPUT_PATH}")

    # 打印摘要
    print("\n=== 结果摘要 ===")
    for family, data in output.items():
        core_names = [s["name"] for s in data["core"][:5]]
        imp_names = [s["name"] for s in data["important"][:3]]
        print(f"\n{family} (共{data['total_jds']:,}条JD):")
        print(f"  核心技能: {core_names}")
        print(f"  重要技能: {imp_names}")


if __name__ == "__main__":
    main()
