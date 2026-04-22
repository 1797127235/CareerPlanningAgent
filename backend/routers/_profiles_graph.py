"""Graph positioning, embedding pre-filter, LLM matching, and recommendations."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from backend.config import DASHSCOPE_API_KEY, LLM_BASE_URL
from backend.models import CareerGoal, Profile

logger = logging.getLogger(__name__)

_ROLE_LIST_CACHE: str | None = None    # invalidated when graph.json mtime changes
_GRAPH_NODES_CACHE: dict | None = None
_skill_vocab_cache: str | None = None
_graph_mtime: float = 0.0             # tracks graph.json modification time

_GRAPH_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "graph.json"


def _graph_changed() -> bool:
    """Return True if graph.json was modified since last load."""
    global _graph_mtime
    try:
        mtime = _GRAPH_PATH.stat().st_mtime
    except OSError:
        return False
    if mtime != _graph_mtime:
        _graph_mtime = mtime
        return True
    return False


def _invalidate_graph_cache() -> None:
    """Clear all module-level graph caches (called when graph.json changes)."""
    global _GRAPH_NODES_CACHE, _ROLE_LIST_CACHE, _skill_vocab_cache, _NODE_EMBEDDINGS, _GRAPH_SKILL_TOKENS_CACHE
    _GRAPH_NODES_CACHE = None
    _ROLE_LIST_CACHE = None
    _skill_vocab_cache = None
    _NODE_EMBEDDINGS = None
    _GRAPH_SKILL_TOKENS_CACHE = None
    logger.info("Graph caches invalidated due to graph.json update")


def _get_graph_nodes() -> dict:
    """Load graph.json nodes as dict keyed by node_id (cache invalidated on file change)."""
    global _GRAPH_NODES_CACHE
    if _graph_changed():
        _invalidate_graph_cache()
    if _GRAPH_NODES_CACHE is not None:
        return _GRAPH_NODES_CACHE
    with open(_GRAPH_PATH, "r", encoding="utf-8") as f:
        _GRAPH_NODES_CACHE = {n["node_id"]: n for n in json.load(f).get("nodes", [])}
    return _GRAPH_NODES_CACHE


def _get_role_list_text(node_ids: list[str] | None = None) -> str:
    """Build a role list string for the LLM prompt, including distinguishing_features."""
    global _ROLE_LIST_CACHE
    graph_nodes = _get_graph_nodes()

    def _format_node(nid: str, n: dict) -> str:
        label = n.get("label", nid)
        cl = n.get("career_level", 0)
        ms = ", ".join(str(s) for s in (n.get("must_skills") or [])[:6])
        line = f"- {nid}: {label}（L{cl}，核心技能: {ms}）"
        df = n.get("distinguishing_features") or []
        if df:
            line += f"\n  适合信号: {'; '.join(df[:3])}"
        ntrf = n.get("not_this_role_if") or []
        if ntrf:
            line += f"\n  不适合: {'; '.join(ntrf[:2])}"
        return line

    if node_ids is not None:
        return "\n".join(_format_node(nid, graph_nodes.get(nid, {})) for nid in node_ids)

    if _ROLE_LIST_CACHE:
        return _ROLE_LIST_CACHE
    _ROLE_LIST_CACHE = "\n".join(_format_node(nid, n) for nid, n in graph_nodes.items())
    return _ROLE_LIST_CACHE


# ── Job-target → node_id keyword mapping ────────────────────────────────────

_JOB_TARGET_ROLE_MAP = [
    (["产品经理", "product manager", "产品实习"], "product-manager"),
    # '项目管理' 映射到产品经理（L3，应届生可达），engineering-manager 是 L4 应届生进不去
    (["项目管理", "项目经理", "项目管家", "project manager"], "product-manager"),
    (["前端", "frontend", "front-end", "web开发"], "frontend"),
    (["后端", "backend", "服务端", "java开发"], "java"),
    (["全栈", "full stack", "full-stack"], "full-stack"),
    (["算法", "algorithm", "研究员", "研究岗"], "algorithm-engineer"),
    (["机器学习", "ml工程", "machine learning"], "machine-learning"),
    (["ai工程", "ai engineer", "大模型", "llm"], "ai-engineer"),
    (["数据分析", "data analyst", "数据分析师"], "data-analyst"),
    (["数据科学", "data scientist", "ai数据"], "ai-data-scientist"),
    (["数据工程", "data engineer", "数据工程师"], "data-engineer"),
    (["bi", "商业智能", "bi分析"], "bi-analyst"),
    (["搜索引擎", "search engine"], "search-engine-engineer"),
    (["运维", "devops", "sre"], "devops"),
    (["安全", "security", "网络安全"], "cyber-security"),
    (["游戏", "game"], "game-developer"),
    (["c++", "c plus"], "cpp"),
    (["go", "golang"], "golang"),
    (["python工程师", "python developer"], "python"),
]


def find_role_id_for_job_target(job_target: str) -> str | None:
    """Map job_target text to a node_id using keyword matching."""
    if not job_target or job_target == "未指定":
        return None
    target_lower = job_target.lower()
    for keywords, role_id in _JOB_TARGET_ROLE_MAP:
        if any(kw in target_lower for kw in keywords):
            return role_id
    return None


# ── Text-scanned skill vocabulary ────────────────────────────────────────────

_GRAPH_SKILL_TOKENS_CACHE: set[str] | None = None


def _build_graph_skill_tokens() -> set[str]:
    """Build tokenized skill vocabulary from all graph node must_skills.

    Returns lowercase tokens/phrases that can be searched for in resume text.
    Includes both full skill names and individual tokens split by separators,
    plus 2-character prefixes for pure-Chinese phrases so that e.g.
    "缺陷管理" produces "缺陷" which can match text mentioning "缺陷".
    """
    global _GRAPH_SKILL_TOKENS_CACHE
    if _GRAPH_SKILL_TOKENS_CACHE is not None:
        return _GRAPH_SKILL_TOKENS_CACHE
    graph_nodes = _get_graph_nodes()
    tokens: set[str] = set()
    for node in graph_nodes.values():
        for s in node.get("must_skills", []):
            if not s or not s.strip():
                continue
            sl = s.strip().lower()
            tokens.add(sl)
            normalized = sl
            for sep in ["/", "&", "、", "，", "(", ")", "（", "）", " "]:
                normalized = normalized.replace(sep, "|")
            for token in normalized.split("|"):
                token = token.strip()
                if token and len(token) >= 2:
                    tokens.add(token)
            # For pure Chinese phrases (e.g. "缺陷管理"), also add the
            # first 2 chars as a prefix token so "缺陷" hits "缺陷管理".
            if len(sl) >= 4 and all("\u4e00" <= c <= "\u9fff" for c in sl):
                tokens.add(sl[:2])
    _GRAPH_SKILL_TOKENS_CACHE = tokens
    return tokens


def _expand_chinese_tokens(phrases: list[str]) -> set[str]:
    """Expand phrases with Chinese prefix/bigram tokens for robust matching.

    Pure-Chinese phrases (e.g. '缺陷管理', '性能测试') have no separators,
    so exact substring matching misses them when user text only contains
    the prefix (e.g. '缺陷' instead of '缺陷管理').
    """
    expanded: set[str] = set()
    for p in phrases:
        p = p.strip().lower()
        if not p or len(p) < 2:
            continue
        expanded.add(p)
        # Split by separators (same as _node_skill_set)
        for sep in ["/", "&", "、", "，", "(", ")", "（", "）", " "]:
            p = p.replace(sep, "|")
        for token in p.split("|"):
            token = token.strip()
            if token and len(token) >= 2:
                expanded.add(token)
        # For pure Chinese phrases, add all prefix n-grams (len>=2)
        original = p.replace("|", "")
        if len(original) >= 4 and all("\u4e00" <= c <= "\u9fff" for c in original):
            for i in range(2, len(original)):
                expanded.add(original[:i])
    return expanded


def _extract_implied_skills_from_text(profile_data: dict) -> set[str]:
    """Scan resume text for graph skill vocabulary mentions.

    Dynamically discovers skill signals from raw_text, projects, internships,
    and work experiences without hard-coding tool→skill mappings.
    """
    parts: list[str] = []

    raw_text = (profile_data.get("raw_text") or "").lower()
    if raw_text:
        parts.append(raw_text)

    for proj in profile_data.get("projects", []):
        if isinstance(proj, dict):
            parts.append(str(proj.get("name", "")).lower())
            parts.append(str(proj.get("description", "") or proj.get("highlights", "")).lower())
        elif isinstance(proj, str):
            parts.append(proj.lower())

    for intern in profile_data.get("internships", []):
        if isinstance(intern, dict):
            parts.append(str(intern.get("role", "")).lower())
            parts.append(str(intern.get("description", "") or intern.get("highlights", "")).lower())
        elif isinstance(intern, str):
            parts.append(intern.lower())

    for work in profile_data.get("work_experiences", []):
        if isinstance(work, dict):
            parts.append(str(work.get("description", "")).lower())
        elif isinstance(work, str):
            parts.append(work.lower())

    combined = " ".join(parts)
    if not combined.strip():
        return set()

    tokens = _build_graph_skill_tokens()
    implied: set[str] = set()
    for token in tokens:
        if len(token) < 2:
            continue
        if token in combined:
            implied.add(token)
    return implied


def _build_work_content_summary(profile_data: dict) -> str:
    """Generate a summary of work-content keywords from user text.

    Scans all graph node core_tasks against user project/internship/raw_text
    and returns a sentence listing the most frequently matched task tokens.
    This gives the LLM an objective, data-driven signal of what the user
    actually does (as opposed to what skills they claim to have).
    """
    parts: list[str] = []
    rt = (profile_data.get("raw_text") or "").lower()
    if rt:
        parts.append(rt)
    for p in profile_data.get("projects", []):
        if isinstance(p, dict):
            parts.append(str(p.get("name", "")).lower())
            parts.append(str(p.get("description", "") or p.get("highlights", "")).lower())
        elif isinstance(p, str):
            parts.append(p.lower())
    for i in profile_data.get("internships", []):
        if isinstance(i, dict):
            parts.append(str(i.get("role", "")).lower())
            parts.append(str(i.get("description", "") or i.get("highlights", "")).lower())
        elif isinstance(i, str):
            parts.append(i.lower())
    user_text = " ".join(parts)
    if not user_text.strip():
        return "未提取到工作内容关键词"

    graph_nodes = _get_graph_nodes()
    # Collect all core_tasks, count hits
    task_hits: dict[str, int] = {}
    for node in graph_nodes.values():
        for t in node.get("core_tasks", []):
            if not t or len(t.strip()) < 3:
                continue
            expanded = _expand_chinese_tokens([t])
            for token in expanded:
                if len(token) >= 2 and token in user_text:
                    task_hits[token] = task_hits.get(token, 0) + 1

    if not task_hits:
        return "未提取到工作内容关键词"

    # Sort by hit count, keep top unique tokens (prefer longer phrases)
    sorted_tokens = sorted(task_hits.items(), key=lambda x: (-x[1], -len(x[0])))
    seen_roots: set[str] = set()
    unique: list[str] = []
    for token, count in sorted_tokens:
        # Skip if a shorter version is already included (e.g. skip "测试" if "测试用例" is in)
        if any(token in u and token != u for u in unique):
            continue
        unique.append(token)
        if len(unique) >= 8:
            break

    return "、".join(unique)


# ── Embedding pre-filter ─────────────────────────────────────────────────────

_NODE_EMBEDDINGS: dict | None = None
_NODE_EMBEDDINGS_MTIME: float = 0.0


def _load_node_embeddings() -> dict:
    global _NODE_EMBEDDINGS, _NODE_EMBEDDINGS_MTIME
    path = Path(__file__).resolve().parent.parent.parent / "data" / "node_embeddings.json"
    try:
        mtime = path.stat().st_mtime
    except OSError:
        mtime = 0.0
    if _NODE_EMBEDDINGS is not None and mtime == _NODE_EMBEDDINGS_MTIME:
        return _NODE_EMBEDDINGS
    try:
        with open(path, "r", encoding="utf-8") as f:
            _NODE_EMBEDDINGS = json.load(f)
        _NODE_EMBEDDINGS_MTIME = mtime
    except Exception:
        _NODE_EMBEDDINGS = {"nodes": {}}
        _NODE_EMBEDDINGS_MTIME = 0.0
    return _NODE_EMBEDDINGS


def embedding_prefilter(
    profile_data: dict,
    *,
    pin_node_ids: list[str] | None = None,
    min_k: int = 12,
    max_k: int = 18,
    ratio: float = 0.65,
) -> list[str]:
    """Use cosine similarity to narrow candidate nodes before LLM matching.

    Args:
        profile_data: User profile dict (skills, projects, job_target, …).
        pin_node_ids: Node IDs that MUST appear in the result (e.g. job_target match).
        min_k / max_k: Floor / ceiling on how many candidates to return.
        ratio: Relative similarity threshold (keep nodes with sim >= top_sim * ratio).

    Returns sorted list of node_ids (best match first). Falls back to all nodes
    if embeddings are unavailable or the API call fails.
    """
    import numpy as np

    all_node_ids = list(_get_graph_nodes().keys())

    emb_data = _load_node_embeddings()
    node_embs = emb_data.get("nodes", {})
    if not node_embs:
        return all_node_ids

    skills = [s.get("name", "") for s in profile_data.get("skills", []) if isinstance(s, dict) and s.get("name")]
    if not skills:
        return all_node_ids

    parts = [" ".join(skills)]
    jt = profile_data.get("job_target") or ""
    if jt:
        parts.append(jt)
    for p in profile_data.get("projects", [])[:3]:
        if not isinstance(p, dict):
            continue
        pname = p.get("name", "")
        tech = p.get("tech_stack", "") or p.get("technologies", "")
        desc = p.get("description", "") or p.get("highlights", "")
        if pname:
            line = pname
            if tech:
                line += f"({str(tech)[:60]})"
            if desc:
                line += f": {str(desc)[:80]}"
            parts.append(line)

    user_text = " | ".join(parts)

    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=DASHSCOPE_API_KEY,
            base_url=LLM_BASE_URL,
            timeout=15,
        )
        resp = client.embeddings.create(
            model=emb_data.get("embedding_model", "text-embedding-v4"),
            input=[user_text],
        )
        user_vec = np.array(resp.data[0].embedding)
    except Exception as e:
        logger.warning("Embedding pre-filter failed, falling back to all nodes: %s", e)
        return all_node_ids

    node_ids = list(node_embs.keys())
    node_vecs = np.array([node_embs[nid] for nid in node_ids])
    norms = np.linalg.norm(node_vecs, axis=1, keepdims=True)
    node_vecs_normed = node_vecs / norms
    user_normed = user_vec / np.linalg.norm(user_vec)

    sims = node_vecs_normed @ user_normed
    ranking = np.argsort(sims)[::-1]

    top_sim = sims[ranking[0]]
    threshold = top_sim * ratio
    candidates = [node_ids[i] for i in ranking if sims[i] >= threshold]

    if len(candidates) < min_k:
        candidates = [node_ids[i] for i in ranking[:min_k]]
    elif len(candidates) > max_k:
        candidates = candidates[:max_k]

    if pin_node_ids:
        for nid in pin_node_ids:
            if nid in all_node_ids and nid not in candidates:
                candidates.append(nid)

    # ── Core-tasks text-match layer (work-content driven, not skill-name driven) ──
    # Some resumes have rich project/internship descriptions that clearly signal
    # a direction (e.g. "测试用例/缺陷/功能测试" for QA) but their generic
    # skill list (Python/SQL) causes embedding similarity to drown the signal.
    # We scan user text against each node's core_tasks and force-match nodes
    # with >= 2 task hits into the candidate pool so the LLM sees them.
    user_text_parts: list[str] = []
    raw_text = (profile_data.get("raw_text") or "").lower()
    if raw_text:
        user_text_parts.append(raw_text)
    for p in profile_data.get("projects", []):
        if isinstance(p, dict):
            user_text_parts.append(str(p.get("name", "")).lower())
            user_text_parts.append(str(p.get("description", "") or p.get("highlights", "")).lower())
        elif isinstance(p, str):
            user_text_parts.append(p.lower())
    for i in profile_data.get("internships", []):
        if isinstance(i, dict):
            user_text_parts.append(str(i.get("role", "")).lower())
            user_text_parts.append(str(i.get("description", "") or i.get("highlights", "")).lower())
        elif isinstance(i, str):
            user_text_parts.append(i.lower())
    user_text_combined = " ".join(user_text_parts)

    graph_nodes = _get_graph_nodes()
    task_forced: list[str] = []
    for nid, node in graph_nodes.items():
        core_tasks = [t.strip() for t in node.get("core_tasks", []) if t and len(t.strip()) >= 3]
        if not core_tasks:
            continue
        # Use expanded tokens (Chinese prefixes etc.) for robust matching
        expanded = _expand_chinese_tokens(core_tasks)
        hits = sum(1 for token in expanded if len(token) >= 2 and token in user_text_combined)
        # Threshold: >=2 distinct task-token hits, or strong proportional match
        if hits >= 2 or (len(core_tasks) >= 3 and hits / len(core_tasks) >= 0.3):
            task_forced.append(nid)

    forced_count = 0
    for nid in task_forced:
        if nid not in candidates:
            candidates.append(nid)
            forced_count += 1
    if forced_count:
        logger.info("Task-match layer forced %d nodes into prefilter candidates", forced_count)

    logger.info("Embedding prefilter: %d/%d nodes selected", len(candidates), len(all_node_ids))
    return candidates


_ROLE_MATCH_PROMPT = """你是一个职业匹配 AI。根据用户的完整背景，完成两件事：

1. 从以下 {role_count} 个岗位中选出最匹配的 1 个作为用户**当前定位**（current_position）
2. 推荐 5-6 个最适合的方向，按匹配度从高到低排序
   - 只推荐和用户背景有真实关联的岗位，宁少勿滥
   - 每个推荐附一句话理由，说明用户的哪些经历/信号匹配该方向
   - affinity_pct 反映综合契合度（0-100）

【基本原则】
- **项目/实习经历是判断主攻方向的首要依据，技能列表仅作辅助**。如果一个用户的项目/实习全部围绕某个方向（如测试、数据分析、后端开发），即使技能列表里有 Python/SQL 等通用技能，也不得因这些通用技能就推荐其他方向。
- **技能必须结合上下文理解**：SQL 在"测试用例编写"中出现 → 测试方向；SQL 在"数据分析报表"中出现 → 数据方向。不要只看技能名称。
- 有 C/C++ + Linux → 系统开发/基础设施/存储引擎/游戏服务端
- 有 PyTorch/深度学习/计算机视觉 → AI/算法
- 有 Java/Spring → 后端开发
- 有 React/Vue → 前端开发
- SQL/MySQL 是通用辅助技能，不能单独驱动主方向，必须看使用场景
- GitHub/Docker/Git 是通用工具，不能单独驱动主方向

【经验级别约束】
- experience_years == 0（应届生）：不推架构师/总监级别岗位（career_level 4/5）
- experience_years <= 1：career_level >= 4 的岗位 affinity 不超过 35

【岗位列表】
{role_list}

【用户求职意向】
{job_target}

【用户主方向】
{primary_domain}

【用户职业信号】
{career_signals}

【用户工作内容关键词（从项目/实习文本中提取）】
{work_content_summary}

【用户项目经历】
{user_projects}

【用户实习/工作经历】
{user_internships}

【用户技能（含熟练度）】
{user_skills}

【用户背景】
专业：{major}，学历：{degree}，工作年限：{exp_years}

返回严格 JSON，不要任何其他文字：
{{
  "current_position": {{"role_id": "最匹配岗位ID", "reason": "一句话理由"}},
  "recommendations": [
    {{"role_id": "岗位ID", "label": "中文名", "reason": "一句话推荐理由", "affinity_pct": 匹配度0到100}}
  ]
}}"""


def _llm_match_role(profile_data: dict) -> dict | None:
    """LLM role matching with embedding prefilter to reduce prompt size."""
    try:
        from backend.llm import llm_chat, parse_json_response

        skill_objs = [s for s in profile_data.get("skills", []) if isinstance(s, dict) and s.get("name")]
        if skill_objs:
            skills_with_level = ", ".join(
                f"{s.get('name')}({s.get('level') or 'unspecified'})" for s in skill_objs
            )
        else:
            ka = (profile_data.get("knowledge_areas") or [])[:10]
            if not ka:
                return None
            skills_with_level = ", ".join(ka)

        job_target = profile_data.get("job_target", "") or "未指定"
        pin_ids = []
        target_role = find_role_id_for_job_target(job_target)
        if target_role:
            pin_ids.append(target_role)

        candidate_ids = embedding_prefilter(profile_data, pin_node_ids=pin_ids)
        role_list = _get_role_list_text(candidate_ids)

        # Build project/internship text for LLM context
        projects = profile_data.get("projects", [])
        project_texts = []
        for p in projects:
            if isinstance(p, dict):
                line = p.get("name", "")
                if p.get("description"):
                    line += f"：{p['description']}"
                if line:
                    project_texts.append(line)
            elif isinstance(p, str) and p.strip():
                project_texts.append(p.strip())
        user_projects = "\n".join(project_texts[:6]) or "无"

        internships = profile_data.get("internships", [])
        intern_texts = []
        for i in internships:
            if isinstance(i, dict):
                line = f"{i.get('company', '')} - {i.get('role', '')}"
                if i.get("highlights"):
                    line += f"：{i['highlights']}"
                if line.strip(" -"):
                    intern_texts.append(line)
            elif isinstance(i, str) and i.strip():
                intern_texts.append(i.strip())
        user_internships = "\n".join(intern_texts[:4]) or "无"

        edu = profile_data.get("education", {})
        primary_domain = profile_data.get("primary_domain", "未知")
        cs = profile_data.get("career_signals", {})
        career_signals_text = (
            f"论文发表: {'有（' + cs.get('publication_level','') + '）' if cs.get('has_publication') else '无'}，"
            f"竞赛获奖: {'/'.join(cs.get('competition_awards') or []) or '无'}，"
            f"领域专精: {cs.get('domain_specialization') or '无'}，"
            f"研究/工程倾向: {cs.get('research_vs_engineering','未知')}，"
            f"开源贡献: {'有' if cs.get('open_source') else '无'}，"
            f"实习公司: {cs.get('internship_company_tier','未知')}"
        ) if cs else "未提取到职业信号"
        work_content_summary = _build_work_content_summary(profile_data)
        prompt = _ROLE_MATCH_PROMPT.format(
            role_count=len(candidate_ids),
            role_list=role_list,
            job_target=job_target,
            primary_domain=primary_domain,
            career_signals=career_signals_text,
            user_skills=skills_with_level,
            user_projects=user_projects,
            user_internships=user_internships,
            work_content_summary=work_content_summary,
            major=edu.get("major", "未知"),
            degree=edu.get("degree", "未知"),
            exp_years=profile_data.get("experience_years", 0),
        )

        # Step 2: LLM generates initial match
        result = llm_chat([{"role": "user", "content": prompt}], temperature=0, timeout=60)
        parsed = parse_json_response(result)
        if parsed and parsed.get("current_position", {}).get("role_id"):
            # Step 3: Deterministic post-processing — hard rules that LLM cannot override
            parsed["recommendations"] = _filter_recommendations(
                parsed.get("recommendations", []), profile_data
            )
            return parsed
        if parsed and parsed.get("role_id"):
            return {"current_position": parsed, "recommendations": []}
        return None
    except Exception as e:
        logger.warning("LLM role matching failed: %s", e)
        return None


# ── Deterministic recommendation filter ──────────────────────────────────────
# Language and tool requirements per role: user must have at least one of these
# to receive a recommendation above the floor cap.
_ROLE_PRIMARY_REQUIREMENTS: dict[str, dict] = {
    # node_id → {"skills": set of alternatives (any one suffices), "cap": affinity floor}
    "golang":              {"skills": {"Go", "golang"},                    "cap": 35},
    "java":                {"skills": {"Java", "Spring Boot", "SpringBoot"},"cap": 35},
    "python":              {"skills": {"Python"},                           "cap": 38},
    "rust":                {"skills": {"Rust"},                             "cap": 35},
    "flutter":             {"skills": {"Dart", "Flutter"},                  "cap": 35},
    "ios":                 {"skills": {"Swift", "SwiftUI", "UIKit"},        "cap": 35},
    "android":             {"skills": {"Android", "Kotlin"},                "cap": 35},
    "react-native":        {"skills": {"React Native", "JavaScript"},       "cap": 38},
    "devops":              {"skills": {"Kubernetes", "Docker", "Jenkins"},  "cap": 40},
    "devsecops":           {"skills": {"Kubernetes", "Docker", "Vault"},    "cap": 40},
    "infrastructure-engineer": {"skills": {"Kubernetes", "Go", "Docker"},  "cap": 40},
    "cpp":                 {"skills": {"嵌入式", "RTOS", "驱动", "单片机"},  "cap": 38},
    "blockchain":          {"skills": {"Solidity", "Web3.js", "Ethereum"},  "cap": 35},
    "mlops":               {"skills": {"Kubernetes", "MLflow", "Airflow"},  "cap": 40},
}

# Roles requiring career signals (not just skills) as hard gates.
# These roles need verifiable achievement signals — skill names alone are insufficient.
# Format: role_id → list of signal checks (any one passing suffices)
_ROLE_SIGNAL_REQUIREMENTS: dict[str, dict] = {
    # Algorithm / ML research roles: need hard academic/competition signals
    "algorithm-engineer": {
        "description": "算法工程师",
        "check": lambda cs, skills, proj: (
            cs.get("has_publication") or
            bool(cs.get("competition_awards")) or
            any(s in skills for s in {"pytorch", "tensorflow", "深度学习", "机器学习"}) or
            any(kw in proj for kw in ("pytorch", "tensorflow", "深度学习", "神经网络", "模型训练"))
        ),
    },
    "machine-learning": {
        "description": "机器学习工程师",
        "check": lambda cs, skills, proj: (
            cs.get("has_publication") or
            bool(cs.get("competition_awards")) or
            any(s in skills for s in {"pytorch", "tensorflow", "scikit-learn", "深度学习"}) or
            any(kw in proj for kw in ("pytorch", "tensorflow", "深度学习", "模型训练", "训练集"))
        ),
    },
    "ai-data-scientist": {
        "description": "AI数据科学家",
        "check": lambda cs, skills, proj: (
            cs.get("has_publication") or
            bool(cs.get("competition_awards")) or
            any(s in skills for s in {"pytorch", "tensorflow", "pandas", "scikit-learn"}) or
            any(kw in proj for kw in ("pytorch", "tensorflow", "数据分析", "特征工程", "模型"))
        ),
    },
}


def _filter_recommendations(
    recs: list[dict], profile_data: dict
) -> list[dict]:
    """Apply deterministic hard rules to LLM-generated recommendations.

    Architecture: O*NET-inspired two-layer gate.
    Layer 1 (skill gate): user must have the primary language/tool for the role.
    Layer 2 (signal gate): certain roles require verifiable career signals
                           (publications, competitions, framework experience).
    The LLM handles nuance; this function enforces hard constraints
    that LLMs tend to hallucinate around.
    """
    # Build user skill name set (case-insensitive)
    skill_objs = profile_data.get("skills", [])
    user_skills: set[str] = set()
    for s in skill_objs:
        if isinstance(s, dict):
            user_skills.add(s.get("name", "").lower())
        elif isinstance(s, str):
            user_skills.add(s.lower())

    # Augment with skills implied by text (project/internship/raw_text scanning)
    implied_skills = _extract_implied_skills_from_text(profile_data)
    user_skills |= implied_skills

    # Project text for broader language/tool detection
    project_text = " ".join(str(p) for p in profile_data.get("projects", []) or []).lower()

    # Career signals dict
    cs = profile_data.get("career_signals", {}) or {}

    def _user_has_any(required_skills: set[str]) -> bool:
        for sk in required_skills:
            if sk.lower() in user_skills:
                return True
            if len(sk) >= 3 and sk.lower() in project_text:
                return True
        return False

    graph_nodes = _get_graph_nodes()

    filtered: list[dict] = []
    for rec in recs:
        role_id = rec.get("role_id", "")
        affinity = rec.get("affinity_pct", 0)

        # ── Layer 0: Graph existence gate ─────────────────────────────────────
        if role_id not in graph_nodes:
            logger.warning("LLM hallucinated role_id=%s, skipping", role_id)
            continue

        # ── Layer 1: Primary skill gate ────────────────────────────────────────
        req = _ROLE_PRIMARY_REQUIREMENTS.get(role_id)
        if req and not _user_has_any(req["skills"]):
            logger.info(
                "Skill-gate filtered %s (affinity=%d, missing: %s)",
                role_id, affinity, list(req["skills"])[:2],
            )
            continue

        # ── Layer 2: Career signal gate ────────────────────────────────────────
        sig_req = _ROLE_SIGNAL_REQUIREMENTS.get(role_id)
        if sig_req:
            passes = sig_req["check"](cs, user_skills, project_text)
            if not passes:
                logger.info(
                    "Signal-gate filtered %s (affinity=%d, no hard signals for %s)",
                    role_id, affinity, sig_req["description"],
                )
                continue

        # ── Sanity-check LLM affinity with must_skills overlap ──
        # LLM now receives full project/internship text, so its judgment is
        # more context-aware than raw skill overlap. We only cap obviously
        # hallucinated scores, not override reasonable ones.
        # user_skills already includes text-scanned implied skills.
        node = graph_nodes.get(role_id, {})
        node_skills = [
            (s if isinstance(s, str) else s.get("name", "")).lower().strip()
            for s in (node.get("must_skills") or [])
        ]
        if node_skills:
            overlap = 0
            for ns in node_skills:
                for us in user_skills:
                    if ns in us or us in ns:
                        overlap += 1
                        break
            rec["_overlap"] = overlap
            rec["_total"] = len(node_skills)
            # Cap LLM affinity if it wildly overestimates (no skill overlap)
            if overlap == 0 and rec.get("affinity_pct", 0) > 50:
                rec["affinity_pct"] = min(rec["affinity_pct"], 35)
        else:
            # Nodes with no must_skills get low affinity (they're too vague)
            rec["affinity_pct"] = min(rec.get("affinity_pct", 0), 25)

        filtered.append(rec)

    filtered.sort(key=lambda r: r.get("affinity_pct", 0), reverse=True)

    # ── Layer 3: Force-include + boost job_target role ────────────────────
    # 用户明确写了求职意向，必须排在推荐第1位（即使技能和它冲突）。
    # 策略: 把 affinity_pct 提到 max(现有)+5，确保前端按 affinity 排序后仍在首位。
    # 注意: 前端会按 affinity_pct 重新排序 (ProfilePage.tsx:395)，所以数值控制比代码顺序更可靠。
    job_target = profile_data.get("job_target") or ""
    target_role_id = find_role_id_for_job_target(job_target)
    if target_role_id and target_role_id in graph_nodes:
        # Determine top affinity in current list
        top_affinity = max(
            (r.get("affinity_pct", 0) for r in filtered), default=60
        )
        boost_affinity = min(99, top_affinity + 5)

        existing = next(
            (r for r in filtered if r.get("role_id") == target_role_id), None
        )
        if existing:
            # Boost existing to top
            existing["affinity_pct"] = boost_affinity
            existing["reason"] = (
                f"与你的求职意向'{job_target}'匹配"
                + ("；" + existing["reason"] if existing.get("reason") else "")
            )
            logger.info(
                "Boosted existing job_target role %s to affinity=%d",
                target_role_id, boost_affinity,
            )
        else:
            # Force-insert at top
            gn = graph_nodes[target_role_id]
            req = _ROLE_PRIMARY_REQUIREMENTS.get(target_role_id)
            skill_gate_pass = (not req) or _user_has_any(req["skills"])
            if skill_gate_pass:
                filtered.insert(0, {
                    "role_id": target_role_id,
                    "label": gn.get("label", target_role_id),
                    "reason": f"与你的求职意向'{job_target}'匹配",
                    "affinity_pct": boost_affinity,
                })
            else:
                # Skill gate blocks but still show as aspirational (low affinity)
                filtered.insert(0, {
                    "role_id": target_role_id,
                    "label": gn.get("label", target_role_id),
                    "reason": f"求职意向：{job_target}（技能储备不足，建议优先补足相关技能）",
                    "affinity_pct": min(35, boost_affinity),
                })
            logger.info(
                "Force-included job_target role: %s (affinity=%d)",
                target_role_id, boost_affinity,
            )

    # Re-sort by affinity so job_target ends up on top
    filtered.sort(key=lambda r: r.get("affinity_pct", 0), reverse=True)

    return filtered


# ── Graph positioning ─────────────────────────────────────────────────────────

def _auto_locate_on_graph(
    profile_id: int, user_id: int, profile_data: dict, db: Session
) -> dict | None:
    """Locate profile on career graph + generate recommendations in one LLM call.

    Returns current position dict and caches recommendations for instant loading.
    """
    logger.info(
        "[AUTO-LOCATE-START] profile_id=%d job_target=%r skills=%d",
        profile_id,
        profile_data.get("job_target", ""),
        len(profile_data.get("skills", [])),
    )
    try:
        from backend.services.graph_service import get_graph_service

        graph = get_graph_service(db)

        llm_result = _llm_match_role(profile_data)
        if not llm_result:
            return None

        current_pos = llm_result.get("current_position", llm_result)
        node_id = current_pos["role_id"]

        node = graph.get_node(node_id)
        if not node:
            return None
        node_label = node.get("label", node_id)

        existing_goal = (
            db.query(CareerGoal)
            .filter_by(user_id=user_id, profile_id=profile_id, is_active=True)
            .first()
        )
        if existing_goal:
            db.query(CareerGoal).filter_by(
                user_id=user_id, profile_id=profile_id, is_active=True
            ).update({"from_node_id": node_id})
        else:
            goal = CareerGoal(
                user_id=user_id,
                profile_id=profile_id,
                from_node_id=node_id,
                target_node_id="",
                target_label="",
                target_zone="",
                is_primary=True,
            )
            db.add(goal)

        # Cache recommendations from the same LLM call
        recs_raw = llm_result.get("recommendations", [])
        if recs_raw:
            from backend.routers.recommendations import _save_rec_cache
            from backend.services.gap_analyzer import profile_hash

            # Enrich with graph data
            graph_path = Path(__file__).resolve().parent.parent.parent / "data" / "graph.json"
            graph_nodes: dict = {}
            try:
                nodes_list = json.loads(graph_path.read_text(encoding="utf-8")).get("nodes", [])
                graph_nodes = {n["node_id"]: n for n in nodes_list}
            except Exception:
                pass

            skills = [s.get("name", "") for s in profile_data.get("skills", []) if s.get("name")]
            enriched = []
            for r in recs_raw[:6]:
                rid = r.get("role_id", "")
                if rid not in graph_nodes:
                    logger.warning("LLM hallucinated role_id=%s in auto_locate, skipping", rid)
                    continue
                gn = graph_nodes[rid]
                enriched.append({
                    "role_id": rid,
                    "label": r.get("label", gn.get("label", rid)),
                    "affinity_pct": r.get("affinity_pct", 50),
                    "matched_skills": [],
                    "gap_skills": gn.get("must_skills", [])[:4],
                    "gap_hours": 0,
                    "zone": gn.get("zone", "safe"),
                    "salary_p50": gn.get("salary_p50", 0),
                    "reason": r.get("reason", ""),
                    "channel": r.get("channel", "entry"),
                    "career_level": gn.get("career_level", 0),
                    "replacement_pressure": gn.get("replacement_pressure", 50),
                    "human_ai_leverage": gn.get("human_ai_leverage", 50),
                })

            # ── Locator only for backfill ranking, NOT override LLM ──
            # LLM now receives full project/internship text; its judgment is
            # more context-aware than skill-name-only IDF matching.
            from backend.services.profile.locator import locate_on_graph
            try:
                loc_result = locate_on_graph(profile_data, graph)
                loc_scores = {nid: s for nid, s in loc_result.get("all_scores", [])}
                # Store locator scores for backfill use, but keep LLM ranking
                for rec in enriched:
                    nid = rec["role_id"]
                    if nid in loc_scores:
                        rec["_loc_score"] = loc_scores[nid]
                logger.info("Locator scores computed for %d recommendations (not overriding LLM)", len(enriched))
            except Exception as e:
                logger.warning("Locator ranking failed: %s", e)

            # ── Seniority hard filter on LLM result ────────────────────
            # 应届生绝不推 L4+ 架构师/经理岗位，即便 LLM 推了也过滤掉
            exp_years = profile_data.get("experience_years", 0) or 0
            if exp_years == 0:
                enriched = [r for r in enriched if (r.get("career_level") or 0) <= 3]
            elif exp_years <= 1:
                enriched = [r for r in enriched if (r.get("career_level") or 0) <= 4]

            # ── Backfill: if LLM returns too few, supplement by skill+task overlap ──
            # Two-layer scoring:
            #   1) must_skills overlap (incl. text-scanned implied skills)
            #   2) core_tasks match against user project/internship text
            # A node with high task-match but low skill-overlap (e.g. QA where
            # user has generic Python/SQL but rich test descriptions) can still
            # rank high and be backfilled.
            user_skill_set = {
                (s.get("name") or "").lower().strip()
                for s in profile_data.get("skills", [])
                if isinstance(s, dict) and s.get("name")
            }
            user_skill_set |= _extract_implied_skills_from_text(profile_data)
            existing_ids = {r["role_id"] for r in enriched}

            # Build user text for task matching (same logic as prefilter)
            text_parts: list[str] = []
            rt = (profile_data.get("raw_text") or "").lower()
            if rt:
                text_parts.append(rt)
            for p in profile_data.get("projects", []):
                if isinstance(p, dict):
                    text_parts.append(str(p.get("name", "")).lower())
                    text_parts.append(str(p.get("description", "") or p.get("highlights", "")).lower())
                elif isinstance(p, str):
                    text_parts.append(p.lower())
            for i in profile_data.get("internships", []):
                if isinstance(i, dict):
                    text_parts.append(str(i.get("role", "")).lower())
                    text_parts.append(str(i.get("description", "") or i.get("highlights", "")).lower())
                elif isinstance(i, str):
                    text_parts.append(i.lower())
            user_text_combined = " ".join(text_parts)

            backfill_candidates = []
            for nid, node in graph_nodes.items():
                if nid in existing_ids:
                    continue
                cl = node.get("career_level", 0) or 0
                if exp_years == 0 and cl > 3:
                    continue
                if exp_years <= 1 and cl > 4:
                    continue
                # Expand node skills with Chinese prefix tokens for robust matching
                raw_skills = [
                    (s if isinstance(s, str) else s.get("name", "")).lower().strip()
                    for s in (node.get("must_skills") or [])
                ]
                expanded_skills = _expand_chinese_tokens(raw_skills)
                overlap = len(user_skill_set & expanded_skills)
                core_tasks = [t.strip() for t in node.get("core_tasks", []) if t and len(t.strip()) >= 3]
                expanded_tasks = _expand_chinese_tokens(core_tasks)
                task_hits = sum(1 for t in expanded_tasks if len(t) >= 2 and t in user_text_combined) if core_tasks else 0
                # Combined score: task hits weighted 2x, skill overlap 1x
                total_score = overlap + task_hits * 2
                if total_score == 0:
                    continue
                backfill_candidates.append((total_score, overlap, task_hits, nid, node))
            backfill_candidates.sort(key=lambda x: -x[0])

            backfilled = 0
            for total_score, overlap, task_hits, nid, node in backfill_candidates:
                if len(enriched) >= 6:
                    break
                # Higher base affinity when task-matches dominate
                base_affinity = min(60 + total_score * 5, 78)
                reason_parts = []
                if overlap:
                    reason_parts.append(f"技能画像与该方向有 {overlap} 项重合")
                if task_hits:
                    reason_parts.append(f"项目/实习经历与该岗位核心任务有 {task_hits} 项匹配")
                enriched.append({
                    "role_id": nid,
                    "label": node.get("label", nid),
                    "affinity_pct": base_affinity,
                    "matched_skills": [],
                    "gap_skills": (node.get("must_skills") or [])[:4],
                    "gap_hours": 0,
                    "zone": node.get("zone", "safe"),
                    "salary_p50": node.get("salary_p50", 0),
                    "reason": "；".join(reason_parts) or f"技能画像与该方向有 {overlap} 项重合",
                    "channel": "growth",
                    "career_level": node.get("career_level", 0),
                    "replacement_pressure": node.get("replacement_pressure", 50),
                    "human_ai_leverage": node.get("human_ai_leverage", 50),
                })
                backfilled += 1
            if backfilled:
                logger.info("Auto-locate backfill: added %d candidates (task+skill)", backfilled)

            # ── Add promotion targets（应届生不加，避免混淆）──────────
            if exp_years >= 1:
                graph_edges = json.loads(graph_path.read_text(encoding="utf-8")).get("edges", [])
                rec_ids = {r["role_id"] for r in enriched}
                promotion_targets = set()
                for e in graph_edges:
                    if e.get("edge_type") == "vertical" and e["source"] in rec_ids:
                        promotion_targets.add(e["target"])
                for e in graph_edges:
                    if e.get("edge_type") == "vertical" and e["source"] == node_id:
                        promotion_targets.add(e["target"])
                for pid in promotion_targets:
                    if pid in rec_ids:
                        continue
                    pn = graph_nodes.get(pid, {})
                    if not pn:
                        continue
                    cl = pn.get("career_level", 0) or 0
                    if exp_years <= 1 and cl > 3:
                        continue
                    if exp_years <= 3 and cl > 4:
                        continue
                    enriched.append({
                        "role_id": pid,
                        "label": pn.get("label", pid),
                        "affinity_pct": 0,
                        "matched_skills": [],
                        "gap_skills": pn.get("must_skills", [])[:4],
                        "gap_hours": 0,
                        "zone": pn.get("zone", "safe"),
                        "salary_p50": pn.get("salary_p50", 0),
                        "reason": "晋升方向",
                        "channel": "promotion",
                        "career_level": cl,
                        "replacement_pressure": pn.get("replacement_pressure", 50),
                        "human_ai_leverage": pn.get("human_ai_leverage", 50),
                    })

            # ── Programmatic job_target override (triple insurance) ────────────────
            # Locator re-ranking may have pushed the job_target role down or out.
            # Force it to rank #1 with affinity >= 88, same as _generate_recommendations.
            job_target = profile_data.get("job_target", "") or ""
            target_role_id = find_role_id_for_job_target(job_target)
            if target_role_id and target_role_id in graph_nodes:
                existing_ids = [r["role_id"] for r in enriched]
                if target_role_id in existing_ids:
                    idx = existing_ids.index(target_role_id)
                    target_rec = enriched.pop(idx)
                    target_rec["affinity_pct"] = max(target_rec.get("affinity_pct", 0), 88)
                    target_rec["channel"] = "entry"
                    target_rec["reason"] = target_rec.get("reason") or f"与求职意向「{job_target}」高度吻合"
                    enriched.insert(0, target_rec)
                else:
                    node = graph_nodes[target_role_id]
                    enriched.insert(0, {
                        "role_id": target_role_id,
                        "label": node.get("label", target_role_id),
                        "affinity_pct": 88,
                        "matched_skills": [],
                        "gap_skills": node.get("must_skills", [])[:4],
                        "gap_hours": 0,
                        "zone": node.get("zone", "safe"),
                        "salary_p50": node.get("salary_p50", 0),
                        "reason": f"与求职意向「{job_target}」高度吻合",
                        "channel": "entry",
                        "career_level": node.get("career_level", 0),
                        "replacement_pressure": node.get("replacement_pressure", 50),
                        "human_ai_leverage": node.get("human_ai_leverage", 50),
                    })
                logger.info(
                    "Auto-locate job_target override: moved %s to rank #1 (job_target=%s)",
                    target_role_id, job_target,
                )

            profile = db.query(Profile).filter(Profile.id == profile_id).first()
            if profile:
                p_hash = profile_hash(profile_data)
                rec_resp = {"recommendations": enriched, "user_skill_count": len(skills)}
                logger.info(
                    "[AUTO-LOCATE-SAVED] profile_id=%d top_rec=%r job_target=%r",
                    profile_id,
                    enriched[0]["label"] if enriched else "none",
                    profile_data.get("job_target", ""),
                )

        db.commit()
        # Cache only after successful commit to avoid inconsistency on rollback
        if profile:
            _save_rec_cache(profile, p_hash, rec_resp, db)
            db.commit()
        return {"node_id": node_id, "label": node_label}
    except Exception as e:
        import traceback
        print(f"[auto_locate] FAILED for user={user_id}: {e}")
        traceback.print_exc()
        return None


def _build_skill_vocab() -> str:
    """Collect all unique must_skills from graph as standard vocabulary (module-level cached)."""
    global _skill_vocab_cache
    if _skill_vocab_cache is not None:
        return _skill_vocab_cache
    graph_nodes = _get_graph_nodes()
    all_skills: set[str] = set()
    for n in graph_nodes.values():
        for s in n.get("must_skills", []):
            all_skills.add(s)
    _skill_vocab_cache = ", ".join(sorted(all_skills))
    return _skill_vocab_cache
