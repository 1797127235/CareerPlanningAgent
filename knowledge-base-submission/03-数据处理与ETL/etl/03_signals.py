"""
03_signals.py — 把时序数据转化为学生可读的决策信号。

输出: data/market_signals.json
格式:
{
  "role_family": {
    "demand_trend":    "growing"|"stable"|"shrinking",
    "demand_label":    "市场需求持续扩张",
    "salary_momentum": "strong"|"moderate"|"flat",
    "salary_label":    "薪资增长明显",
    "ai_window":       "accelerating"|"growing"|"stable",
    "ai_label":        "AI需求快速渗透",
    "timing":          "best"|"good"|"neutral"|"caution",
    "timing_label":    "现在进入正是时候",
    "timing_reason":   "具体原因（一句话）",
    "data_years":      [2016, ..., 2024],
    "baseline_year":   2021,
    "compare_year":    2024,
    "node_ids":        ["cpp", "rust", ...]
  }
}
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TIMELINE_PATH   = PROJECT_ROOT / "data" / "market_timeline.json"
GRAPH_PATH      = PROJECT_ROOT / "data" / "graph.json"
OUTPUT_PATH     = PROJECT_ROOT / "data" / "market_signals.json"
DB_PATH         = PROJECT_ROOT / "career_planning.db"

# 校准后的阈值（基于真实数据分布）
DEMAND_GROWING   = 1.10   # 2021→2024 岗位数 > +10%
DEMAND_SHRINKING = 0.80   # 2021→2024 岗位数 < -20%

SALARY_STRONG    = 5.0    # CAGR > 5%/yr
SALARY_MODERATE  = 2.0    # CAGR > 2%/yr

AI_ACCELERATING  = 3.0    # 2021→2024 增量 > 3pp
AI_GROWING       = 1.0    # 增量 > 1pp

# 无时间线数据的节点 → 最近似的 role_family（用于展示参考信号）
FALLBACK_FAMILY = {
    "全栈开发": "后端开发",
    "区块链":   None,          # 暂无可信近似，不展示
    "架构":     "系统开发",
    "系统软件":  "系统开发",
    "设计":     None,
    "文档":     None,
    "社区":     None,
}


def compute_signals(timeline: dict, graph_nodes: list) -> dict:
    signals: dict = {}

    for fam, years_data in timeline.items():
        # 只使用 data_quality = full 的年份
        full_years = {
            int(y): d for y, d in years_data.items()
            if d.get("data_quality") == "full"
        }
        if not full_years:
            continue

        # 基准年和比较年
        baseline_y = 2021
        compare_y  = 2024
        d_base = full_years.get(baseline_y) or full_years.get(2022)
        d_comp = full_years.get(compare_y) or full_years.get(2023)

        if not d_base or not d_comp:
            continue

        # ── 需求趋势 ──────────────────────────────────────────
        demand_ratio = d_comp["job_count"] / d_base["job_count"] if d_base["job_count"] else 1
        if demand_ratio >= DEMAND_GROWING:
            demand_trend = "growing"
            demand_label = "市场需求持续扩张"
        elif demand_ratio >= DEMAND_SHRINKING:
            demand_trend = "stable"
            demand_label = "市场需求相对平稳"
        else:
            demand_trend = "shrinking"
            demand_label = "竞争加剧，需技能差异化"

        # ── 薪资动能 ──────────────────────────────────────────
        s_base, s_comp = d_base["salary_p50"], d_comp["salary_p50"]
        years_gap = compare_y - baseline_y
        if s_base and s_comp and years_gap > 0:
            cagr = ((s_comp / s_base) ** (1 / years_gap) - 1) * 100
        else:
            cagr = 0

        if cagr >= SALARY_STRONG:
            salary_momentum = "strong"
            salary_label = f"薪资年增 {cagr:.0f}%，增长明显"
        elif cagr >= SALARY_MODERATE:
            salary_momentum = "moderate"
            salary_label = f"薪资温和增长（年均 {cagr:.0f}%）"
        else:
            salary_momentum = "flat"
            salary_label = f"薪资基本持平（年均 {cagr:.0f}%）"

        # ── AI窗口期 ──────────────────────────────────────────
        ai_delta = d_comp["ai_applied_ratio"] - d_base["ai_applied_ratio"]
        if ai_delta >= AI_ACCELERATING:
            ai_window = "accelerating"
            ai_label = f"AI需求快速渗透（+{ai_delta:.1f}pp）"
        elif ai_delta >= AI_GROWING:
            ai_window = "growing"
            ai_label = f"AI影响在扩大（+{ai_delta:.1f}pp）"
        else:
            ai_window = "stable"
            ai_label = f"AI影响相对稳定（{d_comp['ai_applied_ratio']:.1f}%）"

        # ── 综合时机判断 ──────────────────────────────────────
        if demand_trend == "growing" and salary_momentum in ("strong", "moderate"):
            timing = "best"
            timing_label = "现在进入正是时候"
            timing_reason = f"2021→2024需求增长{(demand_ratio-1)*100:.0f}%，薪资年增{cagr:.0f}%"
        elif demand_trend == "growing":
            timing = "good"
            timing_label = "市场仍在扩张"
            timing_reason = f"需求持续增长，薪资增速尚可"
        elif demand_trend == "stable" and salary_momentum in ("strong", "moderate"):
            timing = "good"
            timing_label = "竞争稳定，薪资有保障"
            timing_reason = f"需求平稳，薪资年增{cagr:.0f}%，存量竞争但可预期"
        elif demand_trend == "shrinking" and salary_momentum == "strong":
            timing = "neutral"
            timing_label = "需求收窄但薪资仍增"
            timing_reason = "裁员期高手留下，技能过硬仍有竞争力"
        elif demand_trend == "shrinking":
            timing = "caution"
            timing_label = "需求收紧，需更强差异化"
            timing_reason = f"2021→2024岗位数减少{(1-demand_ratio)*100:.0f}%，入场需有明显技能优势"
        else:
            timing = "neutral"
            timing_label = "市场趋势中性"
            timing_reason = "需更多数据判断"

        # ── 关联的图谱节点 ────────────────────────────────────
        node_ids = [n["node_id"] for n in graph_nodes if n.get("role_family") == fam]

        signals[fam] = {
            "demand_trend":    demand_trend,
            "demand_label":    demand_label,
            "demand_change_pct": round((demand_ratio - 1) * 100, 1),
            "salary_momentum": salary_momentum,
            "salary_label":    salary_label,
            "salary_cagr":     round(cagr, 1),
            "salary_p50_latest": d_comp["salary_p50"],
            "ai_window":       ai_window,
            "ai_label":        ai_label,
            "ai_delta_pp":     round(ai_delta, 1),
            "timing":          timing,
            "timing_label":    timing_label,
            "timing_reason":   timing_reason,
            "baseline_year":   baseline_y,
            "compare_year":    compare_y,
            "data_years":      sorted(full_years.keys()),
            "node_ids":        node_ids,
        }

    # ── 为无数据节点添加 fallback 条目 ─────────────────────
    all_graph_families = set(n.get("role_family","") for n in graph_nodes)
    for fam in all_graph_families:
        if fam in signals:
            continue
        fallback = FALLBACK_FAMILY.get(fam)
        if fallback and fallback in signals:
            proxy = dict(signals[fallback])
            proxy["is_proxy"] = True
            proxy["proxy_family"] = fallback
            proxy["node_ids"] = [n["node_id"] for n in graph_nodes if n.get("role_family") == fam]
            signals[fam] = proxy
        elif fam and fam not in FALLBACK_FAMILY:
            # Unknown family, mark as no data
            signals[fam] = {
                "timing": "no_data",
                "timing_label": "暂无市场数据",
                "node_ids": [n["node_id"] for n in graph_nodes if n.get("role_family") == fam],
            }

    return signals


def main():
    sys.stdout.reconfigure(encoding="utf-8")

    timeline = json.load(open(TIMELINE_PATH, encoding="utf-8"))
    graph = json.load(open(GRAPH_PATH, encoding="utf-8"))
    nodes = graph.get("nodes", [])

    print("[signals] 计算决策信号...")
    signals = compute_signals(timeline, nodes)

    # 写 JSON
    OUTPUT_PATH.write_text(json.dumps(signals, ensure_ascii=False, indent=2), encoding="utf-8")

    # 写 SQLite
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS role_family_signals (
            role_family TEXT PRIMARY KEY,
            demand_trend TEXT, demand_label TEXT, demand_change_pct REAL,
            salary_momentum TEXT, salary_label TEXT, salary_cagr REAL, salary_p50_latest REAL,
            ai_window TEXT, ai_label TEXT, ai_delta_pp REAL,
            timing TEXT, timing_label TEXT, timing_reason TEXT,
            node_ids TEXT, is_proxy INTEGER DEFAULT 0
        )
    """)
    conn.execute("DELETE FROM role_family_signals")
    for fam, s in signals.items():
        conn.execute("""
            INSERT OR REPLACE INTO role_family_signals VALUES
            (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            fam,
            s.get("demand_trend"), s.get("demand_label"), s.get("demand_change_pct"),
            s.get("salary_momentum"), s.get("salary_label"), s.get("salary_cagr"),
            s.get("salary_p50_latest"),
            s.get("ai_window"), s.get("ai_label"), s.get("ai_delta_pp"),
            s.get("timing"), s.get("timing_label"), s.get("timing_reason"),
            json.dumps(s.get("node_ids", []), ensure_ascii=False),
            1 if s.get("is_proxy") else 0,
        ))
    conn.commit()
    conn.close()

    # 预览
    print(f"\n[signals] 完成！共 {len(signals)} 个方向\n")
    print(f"{'方向':<12} {'需求':>8} {'薪资':>8} {'AI':>12} {'综合时机'}")
    print("-" * 60)
    for fam, s in sorted(signals.items(), key=lambda x: x[1].get("timing","z")):
        if s.get("timing") == "no_data":
            continue
        proxy_mark = " *" if s.get("is_proxy") else ""
        print(f"{fam+proxy_mark:<14} {s.get('demand_trend','?'):>8} "
              f"{s.get('salary_momentum','?'):>8} "
              f"{s.get('ai_window','?'):>12}  "
              f"{s.get('timing_label','')}")

    print("\n详细说明:")
    for fam, s in sorted(signals.items()):
        if "timing_reason" not in s:
            continue
        print(f"  {fam}: {s['timing_label']} — {s['timing_reason']}")


if __name__ == "__main__":
    main()
