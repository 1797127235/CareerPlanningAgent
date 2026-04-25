"""为 graph.json 的 40 个节点批量生成战略决策字段。

新增字段：
  - market_insight: 市场需求趋势和行业定位
  - ai_impact_narrative: AI 对这个方向的具体影响和应对策略
  - differentiation_advice: 应届生如何建立竞争力
  - typical_employers: 典型招聘公司列表
  - entry_barrier: 应届生进入门槛 (low/medium/high)
  - career_ceiling: 3-5 年发展路径
  - project_recommendations: 推荐实战项目

数据来源：
  - data/graph.json (现有节点数据)
  - data/roadmap_skills.json (详细技能树)
  - data/onet_mapping.json (O*NET 职业映射)

Usage:
    python scripts/enrich_graph_strategic.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# Force unbuffered output on Windows
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None

# ── Paths ──
ROOT = Path(__file__).resolve().parent.parent
GRAPH_PATH = ROOT / "data" / "graph.json"
ROADMAP_PATH = ROOT / "data" / "roadmap_skills.json"
ONET_PATH = ROOT / "data" / "onet_mapping.json"
OUTPUT_PATH = ROOT / "data" / "graph.json"  # overwrite in-place

# ── Load .env ──
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=True)
except ImportError:
    pass

# ── LLM client ──
from openai import OpenAI

API_KEY = os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")
BASE_URL = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
MODEL = "qwen-max"

client = OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=120)


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_prompt(node: dict, roadmap_skills: list[str] | None) -> str:
    """Build a prompt for one node."""
    label = node["label"]
    zone = node.get("zone", "?")
    rp = node.get("replacement_pressure", "?")
    hal = node.get("human_ai_leverage", "?")
    must_skills = node.get("must_skills", [])
    core_tasks = node.get("core_tasks", [])
    promo = node.get("promotion_path", [])
    desc = node.get("description", "")

    promo_str = " → ".join(p.get("title", "?") for p in promo) if promo else "无"
    roadmap_str = ", ".join(roadmap_skills[:40]) if roadmap_skills else "无"

    return f"""你是中国 CS 就业市场专家。为以下计算机岗位生成面向应届大学生的战略决策数据。

## 岗位信息
- 岗位名称: {label}
- AI替代压力: {rp}/100 (越低越安全)
- 人类杠杆: {hal}/100 (AI增强人类能力的程度)
- 安全区: {zone}
- 核心技能: {', '.join(must_skills)}
- 日常工作: {', '.join(core_tasks)}
- 晋升路线: {promo_str}
- 岗位描述: {desc}
- 详细技能树(来自 developer-roadmap): {roadmap_str}

## 请生成以下字段（JSON格式）

1. market_insight (string, 2-3句话): 2024-2025年这个方向在中国的市场需求趋势。具体说哪类公司在招、HC情况、应届生竞争激烈程度。不要泛泛而谈。

2. ai_impact_narrative (string, 2-3句话): AI 对这个岗位的具体影响。不要只说"AI替代压力X分"，要说清楚：AI 具体替代了哪些工作内容，哪些核心工作AI目前做不了，从业者应该把自己定位在什么层面。

3. differentiation_advice (string, 2-3句话): 一个计算机专业大三/大四学生，如何在这个方向建立差异化竞争力。不要说"学XX技术"，要说"做什么事情"——比如"贡献开源项目""做一个XX类型的项目""在XX方面建立深度"。

4. typical_employers (array of strings, 5-8个): 中国市场上招这个岗位的典型公司，包括大厂和有代表性的中型公司。

5. entry_barrier (string): 应届生进入门槛，只能是 "low", "medium", "high" 之一。

6. career_ceiling (string, 1-2句话): 3-5年的发展路径和天花板。要具体：从什么级别到什么级别，可能转向什么方向。

7. project_recommendations (array of objects, 2-3个): 推荐给应届生的实战项目。每个包含:
   - name: 项目名称
   - why: 为什么做这个项目对求职有帮助（1句话）
   - difficulty: "easy", "medium", "hard" 之一

## 要求
- 所有内容针对中国市场，用中文
- 具体、有洞察力，不要空话套话
- 直接返回 JSON 对象，不要 markdown 代码块
- 不要重复岗位描述中已有的信息"""


def parse_response(text: str) -> dict | None:
    """Parse JSON from LLM response."""
    text = text.strip()
    # Remove markdown fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                return None
    return None


def enrich_node(node: dict, roadmap_skills: list[str] | None) -> dict:
    """Call LLM to generate strategic fields for one node."""
    prompt = build_prompt(node, roadmap_skills)

    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2000,
            )
            text = resp.choices[0].message.content
            data = parse_response(text)
            if data:
                return data
            print(f"  [WARN] Parse failed for {node['label']}, attempt {attempt+1}")
        except Exception as e:
            print(f"  [ERROR] API call failed for {node['label']}: {e}")
            time.sleep(2)
    return {}


def main():
    print("Loading data files...")
    graph = load_json(GRAPH_PATH)
    roadmap = load_json(ROADMAP_PATH)
    onet = load_json(ONET_PATH)

    nodes = graph["nodes"]
    print(f"Loaded {len(nodes)} nodes, {len(roadmap)} roadmap entries")

    # Build roadmap skill lookup: node_id → skill list
    roadmap_lookup: dict[str, list[str]] = {}
    for key, val in roadmap.items():
        roadmap_lookup[key] = val.get("skills", [])

    # Track which nodes already have strategic fields
    STRATEGIC_FIELDS = [
        "market_insight", "ai_impact_narrative", "differentiation_advice",
        "typical_employers", "entry_barrier", "career_ceiling", "project_recommendations",
    ]

    enriched_count = 0
    skipped_count = 0

    for i, node in enumerate(nodes):
        node_id = node["node_id"]
        label = node["label"]

        # Skip if already enriched
        if node.get("market_insight"):
            print(f"[{i+1}/40] {label} — already enriched, skipping")
            skipped_count += 1
            continue

        # Find matching roadmap skills
        rm_skills = roadmap_lookup.get(node_id) or roadmap_lookup.get(node_id.replace("-", "_"))

        print(f"[{i+1}/40] {label} — generating strategic data...")
        data = enrich_node(node, rm_skills)

        if data:
            for field in STRATEGIC_FIELDS:
                if field in data:
                    node[field] = data[field]
            enriched_count += 1
            print(f"  [OK] Generated {len([f for f in STRATEGIC_FIELDS if f in data])} fields")
        else:
            print(f"  [FAIL] Failed to generate data")

        # Rate limiting: DashScope has RPM limits
        time.sleep(1)

    # Save
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)

    print(f"\nDone! Enriched {enriched_count} nodes, skipped {skipped_count}, saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
