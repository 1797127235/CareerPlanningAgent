"""
Enrich graph nodes with per-level skill requirements.

For each node that has a promotion_path (all 45 nodes), calls LLM once to
distribute skills across career levels (1-5). Results are saved to
data/level_skills.json for zero-latency report rendering.

Data sources per node:
  - roadmap_skills.json : full skill tree (available for 38 nodes after import)
  - skill_tiers         : core/important/bonus skills from JD frequency data
  - career_ceiling      : narrative text describing salary/progression by level
  - promotion_path      : level titles (e.g. "初级前端 → 高级前端 → 架构师")

Usage:
    python -m scripts.enrich_level_skills              # process all nodes
    python -m scripts.enrich_level_skills --force      # re-process all (ignore cache)
    python -m scripts.enrich_level_skills frontend     # process single node

Output: data/level_skills.json
Format:
{
  "frontend": {
    "label": "前端工程师",
    "levels": {
      "1": { "title": "初级前端工程师", "skills": ["HTML", "CSS", ...] },
      "2": { "title": "前端工程师",     "skills": ["Vue", "React", ...] },
      ...
    },
    "source": "roadmap"   # or "skill_tiers"
  }
}
"""
from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_DATA_DIR = Path("data")
_GRAPH_PATH = _DATA_DIR / "graph.json"
_ROADMAP_SKILLS_PATH = _DATA_DIR / "roadmap_skills.json"
_OUTPUT_PATH = _DATA_DIR / "level_skills.json"

_RETRY_DELAY = 3   # seconds between retries
_MAX_RETRIES = 3


# ── LLM setup ─────────────────────────────────────────────────────────────────

def _get_client():
    from backend.llm import get_llm_client
    return get_llm_client(timeout=60)


def _get_model() -> str:
    from backend.llm import get_model
    return get_model("strong")


# ── Prompt ────────────────────────────────────────────────────────────────────

_SYSTEM = """你是一位专业的职业发展顾问，熟悉中国IT行业的职业晋升体系。
你的任务是将一个岗位的完整技能清单，按照职业晋升阶段进行合理分配。
要求：
- 严格遵循JSON格式输出，不要输出任何其他内容
- 技能分配要符合实际职场逻辑：初级掌握基础，高级掌握进阶，专家掌握架构和领导力
- 每个级别保留5-12个最有代表性的技能，避免堆砌
- 使用中文或英文（保持原始技能名称格式）"""


def _build_prompt(node: dict, skills: list[str]) -> str:
    label = node["label"]
    pp = node.get("promotion_path", [])
    ceiling = node.get("career_ceiling", "")
    tiers = node.get("skill_tiers", {})

    # Build promotion path text
    path_text = " → ".join(f"level{p['level']}:{p['title']}" for p in pp)

    # Build tier hints
    core_skills = [s["name"] for s in tiers.get("core", []) if isinstance(s, dict)]
    tier_hint = f"核心高频技能（JD出现率最高）：{', '.join(core_skills[:8])}" if core_skills else ""

    skills_text = "\n".join(f"- {s}" for s in skills[:120])  # cap at 120 to avoid token overflow

    return f"""岗位：{label}
晋升路径：{path_text}
天花板描述：{ceiling[:300] if ceiling else '无'}
{tier_hint}

完整技能清单：
{skills_text}

请将以上技能按晋升阶段分配，输出以下JSON格式（key为level数字字符串）：
{{
  "1": {{"title": "{pp[0]['title'] if pp else 'level1'}", "skills": ["技能A", "技能B", ...]}},
  "2": {{"title": "{pp[1]['title'] if len(pp) > 1 else 'level2'}", "skills": [...]}},
  "3": {{"title": "{pp[2]['title'] if len(pp) > 2 else 'level3'}", "skills": [...]}},
  "4": {{"title": "{pp[3]['title'] if len(pp) > 3 else 'level4'}", "skills": [...]}},
  "5": {{"title": "{pp[4]['title'] if len(pp) > 4 else 'level5'}", "skills": [...]}}
}}"""


# ── Post-processing: clean skill entries ─────────────────────────────────────

_GENERIC_CATEGORIES = {
    # Roadmap category/section names (too broad to be actionable skills)
    "cloud providers", "data management", "design & architecture",
    "interface & navigation", "version control", "the fundamentals",
    "storage", "network", "distribution", "testing", "networking & protocols",
    "provisioning", "operating system", "vcs hosting", "package managers",
    "build tools", "module bundlers", "design and implementation",
    "management and monitoring", "version control systems", "cloud specific tools",
    "application lifecycle management", "user interface", "debugging",
    "data and backend", "app release", "keep learning", "others",
    "profiling", "theming", "internationalization", "accessibility",
    "common ux patterns", "state management", "reactive programming",
    "navigation patterns", "app architecture", "development tools",
    "live data & viewmodel", "dependency injection", "jetpack libraries",
    "important to know", "learn the basics", "internet", "browsers",
}

def _clean_skills(levels: dict) -> dict:
    """Remove noise: question strings, generic category names, empty entries."""
    cleaned = {}
    for lv, lv_data in levels.items():
        raw_skills = lv_data.get("skills", [])
        kept = []
        for s in raw_skills:
            if not isinstance(s, str) or not s.strip():
                continue
            s = s.strip()
            # Remove question-format noise
            if s.endswith("?"):
                continue
            # Remove instructional phrases
            if any(s.startswith(p) for p in ("Learn ", "Pick ", "Using ", "What ", "How ", "Why ")):
                continue
            # Remove generic category names (case-insensitive)
            if s.lower() in _GENERIC_CATEGORIES:
                continue
            kept.append(s)
        cleaned[lv] = {"title": lv_data.get("title", f"Level {lv}"), "skills": kept}
    return cleaned


# ── LLM call ──────────────────────────────────────────────────────────────────

def _call_llm(prompt: str) -> dict | None:
    """Call LLM and parse JSON response. Returns None on failure."""
    client = _get_client()
    model = _get_model()

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": _SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=1200,
            )
            raw = resp.choices[0].message.content.strip()

            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()

            return json.loads(raw)

        except json.JSONDecodeError as e:
            logger.warning("Attempt %d: JSON parse error: %s", attempt, e)
        except Exception as e:
            logger.warning("Attempt %d: LLM call failed: %s", attempt, e)

        if attempt < _MAX_RETRIES:
            time.sleep(_RETRY_DELAY)

    return None


# ── Fallback: build from skill_tiers only ────────────────────────────────────

def _build_from_tiers(node: dict) -> dict:
    """For nodes without roadmap_skills, distribute tier skills across levels."""
    pp = node.get("promotion_path", [])
    tiers = node.get("skill_tiers", {})

    core = [s["name"] for s in tiers.get("core", []) if isinstance(s, dict)]
    important = [s["name"] for s in tiers.get("important", []) if isinstance(s, dict)]
    bonus = [s["name"] for s in tiers.get("bonus", []) if isinstance(s, dict)]

    def _title(level: int) -> str:
        for p in pp:
            if p.get("level") == level:
                return p["title"]
        return f"Level {level}"

    # Simple heuristic distribution
    return {
        "1": {"title": _title(1), "skills": core[:4] + important[:2]},
        "2": {"title": _title(2), "skills": core[:6] + important[:3]},
        "3": {"title": _title(3), "skills": core + important[:4]},
        "4": {"title": _title(4), "skills": core + important + bonus[:2]},
        "5": {"title": _title(5), "skills": core + important + bonus},
    }


# ── Main processing ───────────────────────────────────────────────────────────

_ROADMAP_ALIASES: dict[str, str] = {
    # split nodes → parent roadmap entries (125+ skills each)
    "systems-cpp":            "cpp",
    "server-side-game-developer": "backend",
    "storage-database-kernel":"postgresql-dba",
    # architecture/senior nodes → closest base discipline
    "cto":                    "engineering-manager",
    "ml-architect":           "machine-learning",
    "qa-lead":                "qa",
    "security-architect":     "cyber-security",
    "cloud-architect":        "devops",
    "infrastructure-engineer":"devops",
    "data-architect":         "data-engineer",
    "algorithm-engineer":     "machine-learning",
    "search-engine-engineer": "data-engineer",
    # thin roadmap nodes → richer equivalent
    "ai-data-scientist":      "machine-learning",
    "full-stack":             "backend",
}


def process_node(node: dict, roadmap_skills: dict) -> dict | None:
    """Process a single node. Returns level map or None on failure."""
    nid = node["node_id"]
    label = node["label"]

    lookup_key = _ROADMAP_ALIASES.get(nid, nid)
    if lookup_key in roadmap_skills:
        skills = roadmap_skills[lookup_key].get("skills", [])
        source = "roadmap"
    else:
        # Fall back to skill_tiers
        tiers = node.get("skill_tiers", {})
        skills = []
        for tier_items in tiers.values():
            if isinstance(tier_items, list):
                skills += [s["name"] for s in tier_items if isinstance(s, dict)]
        source = "skill_tiers"

    if not skills and not node.get("skill_tiers"):
        logger.warning("SKIP %s: no skill data", nid)
        return None

    if source == "skill_tiers" and len(skills) < 5:
        # Not enough data for meaningful LLM call, use heuristic
        logger.info("  %s: using heuristic (only %d tier skills)", label, len(skills))
        levels = _build_from_tiers(node)
    else:
        prompt = _build_prompt(node, skills)
        levels = _call_llm(prompt)

        if levels is None:
            logger.warning("  %s: LLM failed, falling back to heuristic", label)
            if source == "skill_tiers":
                levels = _build_from_tiers(node)
            else:
                # Build simple split from skill list
                chunk = max(1, len(skills) // 5)
                pp = node.get("promotion_path", [])
                def _title(i: int) -> str:
                    return pp[i]["title"] if i < len(pp) else f"Level {i+1}"
                levels = {
                    str(i + 1): {"title": _title(i), "skills": skills[i*chunk:(i+1)*chunk]}
                    for i in range(5)
                }

    levels = _clean_skills(levels)
    return {"label": label, "levels": levels, "source": source}


def main():
    force = "--force" in sys.argv
    target_node = next((a for a in sys.argv[1:] if not a.startswith("--")), None)

    # Load data
    graph = json.loads(_GRAPH_PATH.read_text(encoding="utf-8"))
    roadmap_skills = json.loads(_ROADMAP_SKILLS_PATH.read_text(encoding="utf-8"))
    nodes = {n["node_id"]: n for n in graph["nodes"]}

    # Load existing output — always load when targeting a single node so we don't
    # overwrite the full file with just one entry.  --force only skips the cache
    # check (re-processes even cached nodes), it does NOT discard existing data.
    existing: dict = {}
    if _OUTPUT_PATH.exists() and (not force or target_node):
        existing = json.loads(_OUTPUT_PATH.read_text(encoding="utf-8"))

    # Determine which nodes to process
    if target_node:
        if target_node not in nodes:
            logger.error("Node '%s' not found in graph.json", target_node)
            sys.exit(1)
        to_process = [nodes[target_node]]
    else:
        to_process = [n for n in graph["nodes"] if n.get("promotion_path")]

    logger.info("Processing %d nodes (force=%s)", len(to_process), force)

    results = dict(existing)
    done = skipped = failed = 0

    for node in to_process:
        nid = node["node_id"]
        label = node["label"]

        if nid in existing and not force and not target_node:
            skipped += 1
            continue

        logger.info("[%d/%d] %s (%s)...", done + skipped + 1, len(to_process), label, nid)

        result = process_node(node, roadmap_skills)
        if result:
            results[nid] = result
            done += 1
            # Save progressively
            _OUTPUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            failed += 1

        # Small delay to avoid rate limiting
        if done % 5 == 0:
            time.sleep(1)

    logger.info("\nDone: %d processed, %d skipped (cached), %d failed", done, skipped, failed)
    logger.info("Output: %s (%d nodes)", _OUTPUT_PATH, len(results))


if __name__ == "__main__":
    main()
