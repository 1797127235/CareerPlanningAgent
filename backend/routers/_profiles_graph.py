"""Graph positioning, embedding pre-filter, LLM matching, and recommendations."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from backend.config import DASHSCOPE_API_KEY, LLM_BASE_URL
from backend.db_models import CareerGoal, Profile

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
    global _GRAPH_NODES_CACHE, _ROLE_LIST_CACHE, _skill_vocab_cache, _NODE_EMBEDDINGS
    _GRAPH_NODES_CACHE = None
    _ROLE_LIST_CACHE = None
    _skill_vocab_cache = None
    _NODE_EMBEDDINGS = None
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

    logger.info("Embedding prefilter: %d/%d nodes selected", len(candidates), len(all_node_ids))
    return candidates


_ROLE_MATCH_PROMPT = """你是一个职业匹配 AI。根据用户的完整背景，完成两件事：

1. 从以下 {role_count} 个岗位中选出最匹配的 1 个作为用户**当前定位**（current_position）
2. 推荐 5-6 个最适合的方向，按匹配度从高到低排序
   - 只推荐和用户背景有真实关联的岗位，宁少勿滥
   - 每个推荐附一句话理由，说明用户的哪些经历/信号匹配该方向
   - affinity_pct 反映综合契合度（0-100）

【基本原则】
- 根据用户的技能列表、项目经历、教育背景，判断其最可能的主攻方向
- 有 C/C++ + Linux → 系统开发/基础设施/存储引擎/游戏服务端
- 有 PyTorch/深度学习/计算机视觉 → AI/算法
- 有 Java/Spring → 后端开发
- 有 React/Vue → 前端开发
- SQL/MySQL 是通用辅助技能，不能单独驱动主方向
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
        prompt = _ROLE_MATCH_PROMPT.format(
            role_count=len(candidate_ids),
            role_list=role_list,
            job_target=job_target,
            primary_domain=primary_domain,
            career_signals=career_signals_text,
            user_skills=skills_with_level,
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

        # ── Recalculate affinity based on must_skills overlap ──
        # LLM-generated affinity is unstable; use deterministic skill overlap
        # so the ranking is transparent and explainable.
        node = graph_nodes.get(role_id, {})
        node_skills = [
            (s if isinstance(s, str) else s.get("name", "")).lower().strip()
            for s in (node.get("must_skills") or [])
        ]
        if node_skills:
            # Substring match: 'linux' matches 'linux 网络编程', 'c++' matches 'c/c++'
            overlap = 0
            for ns in node_skills:
                for us in user_skills:
                    if ns in us or us in ns:
                        overlap += 1
                        break
            base = int((overlap / len(node_skills)) * 70)  # max 70 from overlap
            bonus = 10 if overlap >= 2 else 0
            rec["affinity_pct"] = min(base + bonus + 10, 92)  # +10 baseline
            rec["_overlap"] = overlap
            rec["_total"] = len(node_skills)
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

            # ── Use locator scores for deterministic ranking ──
            from backend.services.profile.locator import locate_on_graph
            try:
                loc_result = locate_on_graph(profile_data, graph)
                loc_scores = {nid: s for nid, s in loc_result.get("all_scores", [])}
                for rec in enriched:
                    nid = rec["role_id"]
                    if nid in loc_scores:
                        rec["affinity_pct"] = min(int(loc_scores[nid] * 100), 95)
                enriched.sort(key=lambda r: r.get("affinity_pct", 0), reverse=True)
                logger.info("Locator-based ranking applied to %d recommendations", len(enriched))
            except Exception as e:
                logger.warning("Locator ranking failed: %s", e)

            # ── Seniority hard filter on LLM result ────────────────────
            # 应届生绝不推 L4+ 架构师/经理岗位，即便 LLM 推了也过滤掉
            exp_years = profile_data.get("experience_years", 0) or 0
            if exp_years == 0:
                enriched = [r for r in enriched if (r.get("career_level") or 0) <= 3]
            elif exp_years <= 1:
                enriched = [r for r in enriched if (r.get("career_level") or 0) <= 4]

            # ── Backfill: if LLM returns too few, supplement by skill overlap ──
            user_skill_set = {
                (s.get("name") or "").lower().strip()
                for s in profile_data.get("skills", [])
                if isinstance(s, dict) and s.get("name")
            }
            existing_ids = {r["role_id"] for r in enriched}
            backfill_candidates = []
            for nid, node in graph_nodes.items():
                if nid in existing_ids:
                    continue
                cl = node.get("career_level", 0) or 0
                if exp_years == 0 and cl > 3:
                    continue
                if exp_years <= 1 and cl > 4:
                    continue
                node_skills = {
                    (s if isinstance(s, str) else s.get("name", "")).lower().strip()
                    for s in (node.get("must_skills") or [])
                }
                overlap = len(user_skill_set & node_skills)
                if overlap == 0:
                    continue
                backfill_candidates.append((overlap, nid, node))
            backfill_candidates.sort(key=lambda x: -x[0])

            backfilled = 0
            for overlap, nid, node in backfill_candidates:
                if len(enriched) >= 6:
                    break
                enriched.append({
                    "role_id": nid,
                    "label": node.get("label", nid),
                    "affinity_pct": min(60 + overlap * 5, 78),
                    "matched_skills": [],
                    "gap_skills": (node.get("must_skills") or [])[:4],
                    "gap_hours": 0,
                    "zone": node.get("zone", "safe"),
                    "salary_p50": node.get("salary_p50", 0),
                    "reason": f"技能画像与该方向有 {overlap} 项重合",
                    "channel": "growth",
                    "career_level": node.get("career_level", 0),
                    "replacement_pressure": node.get("replacement_pressure", 50),
                    "human_ai_leverage": node.get("human_ai_leverage", 50),
                })
                backfilled += 1
            if backfilled:
                logger.info("Auto-locate backfill: added %d candidates by skill overlap", backfilled)

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

            profile = db.query(Profile).filter(Profile.id == profile_id).first()
            if profile:
                p_hash = profile_hash(profile_data)
                rec_resp = {"recommendations": enriched, "user_skill_count": len(skills)}
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
