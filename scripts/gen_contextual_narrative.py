"""
Generate `contextual_narrative` drafts for the MVP career-explore feature.

This runs the `contextual-narrative` skill against 5 core job nodes from
`data/graph.json` and writes the 30 field drafts (5 jobs × 6 fields) to
`data/contextual_narrative_draft.json` for human review.

Human review is NOT optional. The LLM's default register is too polite; the
second and fourth fields (`what_drains_you`, `who_fits`) almost always need
sharpening by a human reader.

Usage:
    python -m scripts.gen_contextual_narrative
    python -m scripts.gen_contextual_narrative --only ai-engineer       # 单跑一个
    python -m scripts.gen_contextual_narrative --merge                  # 直接合进 graph.json（审稿后用）
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.skills import invoke_skill, SkillOutputParseError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

GRAPH_PATH = PROJECT_ROOT / "data" / "graph.json"
DRAFT_PATH = PROJECT_ROOT / "data" / "contextual_narrative_draft.json"

MVP_NODE_IDS = [
    "java",
    "frontend",
    "ai-engineer",
    "algorithm-engineer",
    "data-analyst",
]

REQUIRED_FIELDS = [
    "what_you_actually_do",
    "what_drains_you",
    "three_year_outlook",
    "who_fits",
    "ai_impact_today",
    "common_entry_path",
]

FIELD_LENGTH_HINTS = {
    "what_you_actually_do": (80, 140),
    "what_drains_you":      (60, 120),
    "three_year_outlook":   (80, 140),
    "who_fits":             (60, 120),
    "ai_impact_today":      (80, 140),
    "common_entry_path":    (100, 160),
}


def load_graph() -> dict:
    return json.loads(GRAPH_PATH.read_text(encoding="utf-8"))


def find_node(graph: dict, node_id: str) -> dict | None:
    for n in graph["nodes"]:
        if n.get("node_id") == node_id:
            return n
    return None


def build_ctx(node: dict) -> dict:
    must_skills = node.get("must_skills") or []
    if must_skills and isinstance(must_skills[0], dict):
        must_skills = [s.get("name", "") for s in must_skills if s.get("name")]
    core_tasks = node.get("core_tasks") or []
    return {
        "label": node.get("label", node["node_id"]),
        "node_id": node["node_id"],
        "role_family": node.get("role_family", ""),
        "career_level": node.get("career_level", 3),
        "must_skills": "、".join(must_skills[:12]) or "（未填）",
        "core_tasks": "\n".join(f"- {t}" for t in core_tasks[:6]) or "（未填）",
        "human_ai_leverage": node.get("human_ai_leverage", 50),
        "replacement_pressure": node.get("replacement_pressure", 50),
    }


def validate_draft(nid: str, draft: dict) -> list[str]:
    """Return a list of warnings — non-blocking but shown to reviewer."""
    warnings = []
    missing = [f for f in REQUIRED_FIELDS if not draft.get(f)]
    if missing:
        warnings.append(f"缺字段: {missing}")
        return warnings
    for f in REQUIRED_FIELDS:
        text = draft[f].strip()
        lo, hi = FIELD_LENGTH_HINTS[f]
        length = len(text)
        if length < lo:
            warnings.append(f"{f} 偏短（{length} 字，建议 {lo}-{hi}）")
        elif length > hi + 40:
            warnings.append(f"{f} 偏长（{length} 字，建议 {lo}-{hi}）")
        # 免责句式
        for bad in ["截至 20", "根据数据", "统计显示", "调研表明", "近期报告"]:
            if bad in text:
                warnings.append(f"{f} 含免责句式「{bad}」")
                break
        # 四位数年份
        import re
        year_hits = re.findall(r"20[2-3][0-9]", text)
        if year_hits:
            warnings.append(f"{f} 含四位数年份 {year_hits}")
    return warnings


def gen_one(node: dict) -> dict:
    ctx = build_ctx(node)
    nid = node["node_id"]
    t0 = time.time()
    try:
        result = invoke_skill("contextual-narrative", **ctx)
    except SkillOutputParseError as e:
        logger.error("[%s] JSON parse failed: %s", nid, e)
        raise
    except Exception as e:
        logger.error("[%s] LLM call failed: %s", nid, e)
        raise
    elapsed = time.time() - t0
    logger.info("[%s] done in %.1fs", nid, elapsed)
    if not isinstance(result, dict):
        raise RuntimeError(f"[{nid}] expected dict, got {type(result)}")
    return result


def gen_all(only: str | None = None) -> dict:
    graph = load_graph()
    out: dict = {}
    # Preserve previous drafts so re-running `--only X` doesn't wipe others
    if DRAFT_PATH.exists():
        try:
            out = json.loads(DRAFT_PATH.read_text(encoding="utf-8"))
        except Exception:
            out = {}

    targets = [only] if only else MVP_NODE_IDS
    for nid in targets:
        node = find_node(graph, nid)
        if not node:
            logger.warning("[%s] node_id not found in graph.json — skipping", nid)
            continue
        logger.info("[%s] 生成中...（label=%s, family=%s, L%s）",
                    nid, node.get("label"), node.get("role_family"), node.get("career_level"))
        try:
            draft = gen_one(node)
        except Exception:
            logger.exception("[%s] 失败", nid)
            continue
        warnings = validate_draft(nid, draft)
        if warnings:
            logger.warning("[%s] 审稿提示:\n  - %s", nid, "\n  - ".join(warnings))
        else:
            logger.info("[%s] 所有字段长度/合规检查通过", nid)
        out[nid] = {
            "label": node.get("label"),
            "role_family": node.get("role_family"),
            "draft": draft,
            "warnings": warnings,
        }

    DRAFT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("草稿写入 %s", DRAFT_PATH)
    return out


def merge_to_graph() -> None:
    """After human review, merge the `draft` blocks back into data/graph.json."""
    if not DRAFT_PATH.exists():
        logger.error("%s 不存在 —— 先跑生成流程", DRAFT_PATH)
        sys.exit(1)
    drafts = json.loads(DRAFT_PATH.read_text(encoding="utf-8"))
    graph = load_graph()

    updated = 0
    for n in graph["nodes"]:
        nid = n.get("node_id")
        if nid in drafts and drafts[nid].get("draft"):
            n["contextual_narrative"] = drafts[nid]["draft"]
            updated += 1

    GRAPH_PATH.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("已合并 %d 个节点的 contextual_narrative 到 %s", updated, GRAPH_PATH)
    logger.info("下一步：python -m scripts.sync_graph_to_db")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--only", help="只跑指定 node_id")
    p.add_argument("--merge", action="store_true", help="审稿后把 draft 合入 graph.json")
    args = p.parse_args()
    if args.merge:
        merge_to_graph()
        return
    gen_all(only=args.only)


if __name__ == "__main__":
    main()
