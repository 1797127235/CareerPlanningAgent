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
        ms = ", ".join(str(s) for s in (n.get("must_skills") or [])[:6])
        line = f"- {nid}: {label}（核心技能: {ms}）"
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
    (["产品经理", "product manager", "pm", "产品实习"], "product-manager"),
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


def _load_node_embeddings() -> dict:
    global _NODE_EMBEDDINGS
    if _NODE_EMBEDDINGS is not None:
        return _NODE_EMBEDDINGS
    path = Path(__file__).resolve().parent.parent.parent / "data" / "node_embeddings.json"
    try:
        with open(path, "r", encoding="utf-8") as f:
            _NODE_EMBEDDINGS = json.load(f)
    except Exception:
        _NODE_EMBEDDINGS = {"nodes": {}}
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

【经验级别硬约束 — 违反视为严重错误】
- experience_years == 0 的用户（应届/在校学生）：
  * 禁止推荐 career_level == 4 的架构师岗位（software-architect、data-architect、ml-architect、security-architect、qa-lead、cloud-architect、engineering-manager）
  * 禁止推荐 career_level == 5 的总监/CTO（cto）
  * 即便技能栈似乎沾边，这些岗位永远不招应届生
- experience_years <= 1：career_level >= 4 岗位 affinity_pct ≤ 35

【技能家族亲和性】
- C/C++ 系统背景（Linux 网络/多线程/epoll/TCP/Reactor）用户：优先 cpp、systems-cpp、storage-database-kernel、search-engine-engineer、server-side-game-developer、infrastructure-engineer。不得推 data-analyst、data-engineer、bi-analyst（技能栈零交集）除非 job_target 明确写数据方向
- 数据背景（SQL/Python/统计）用户：不得推 cpp、systems-cpp、rust 等系统向
- 前端背景用户：不得推 ai-engineer、algorithm-engineer（硬核信号不够）

【匹配优先级规则 — 严格执行，违反视为严重错误】
0. **job_target 是最高优先级**：如果用户简历中有明确的求职意向（job_target 不为空），必须将最符合该意向的岗位排在推荐第一位，这是用户的主观选择，任何技能分析都不能覆盖它。例如：job_target="产品经理实习" → 产品经理必须出现在推荐里且排名靠前。
1. **primary_domain > 单项技能**：用户主方向是第二权重。
2. **career_signals 是区分相似岗位的关键信号**：
   - has_publication=true + research_vs_engineering=research → 算法工程师/研究岗优先于工程岗
   - competition_awards（Kaggle金牌/数学建模）→ 算法/数据科学岗加权
   - internship_company_tier=顶级大厂 → 整体上调
   - research_vs_engineering=engineering → 工程岗优先于研究岗
3. **工具技能不驱动主方向**：Docker/Linux/Git/CI/CD 是辅助技能，不能是 DevOps 匹配的主要依据（除非 primary_domain=系统/基础设施）。
4. **distinguishing_features 是决定因素**：当两个岗位技能相似时，对照每个岗位的"适合信号"和"不适合"来判断，而非单纯技能重叠度。

【熟练度折算（严格执行）】
每个技能括号里是熟练度，affinity_pct 计算时必须按折算系数考虑：
  - expert / proficient / advanced → 1.0 完整技能点
  - intermediate                    → 0.5 技能点
  - familiar                        → 0.3 技能点
  - beginner                        → 0.2 技能点
举例："机器学习(familiar)" = 只是了解过，不能作为推荐 ML 岗位的强信号。

【高门槛方向 affinity_pct 上限（违反视为严重错误）】
■ AI 数据科学家 / 机器学习工程师 / 算法工程师 / AI 工程师 / AI Agent 工程师：
  硬核信号定义（满足才能给高分）：
    (a) 论文发表（SCI / EI / CCF-A/B）
    (b) 学科竞赛奖（Kaggle 铜牌以上 / ACM / 数学建模国奖）
    (c) 独立实现过模型（不仅调 sklearn.cluster / fit_predict）
    (d) 深度学习框架（PyTorch/TensorFlow）完整项目经历
  - 零硬核信号：affinity_pct ≤ 50
  - 1 条硬核信号：affinity_pct ≤ 60
  - 2+ 条硬核信号：可以 70+
  ⚠ "在项目里用过聚类算法分类用户" 是数据分析的日常，不算硬核信号。

■ 数据分析师 / BI 分析师 / 数据工程师：
  门槛低得多，Python+Excel+SQL 其一 intermediate 以上 + 一段数据分析实习 → affinity_pct ≥ 80；
  全满足 + 真实业务产出（用户画像/销售分析/报表）→ affinity_pct ≥ 85

■ 产品经理：
  偏业务思维岗位，看业务理解而非硬技能。默认 50-65 区间，有产品实习或完整产品经历可到 75+

【语言专项岗位硬性上限 — 无该语言项目经验则严格执行，违反视为严重错误】
以下岗位要求以特定主力语言为核心，若用户技能列表和项目中均无该语言的实际使用，affinity_pct 不得超过上限：
  ■ Go 工程师：无 Go 项目经验 → affinity_pct ≤ 35，且不得出现在推荐前3位
  ■ Java 工程师：无 Java 项目经验 → affinity_pct ≤ 35，且不得出现在推荐前3位
  ■ Rust 工程师：无 Rust 项目经验 → affinity_pct ≤ 35，且不得出现在推荐前3位
  ■ Python 工程师：无 Python intermediate 以上项目经验 → affinity_pct ≤ 38
  ■ 基础架构工程师 / DevOps 工程师 / DevSecOps 工程师：
      无 Kubernetes/Docker 实际项目经验 → affinity_pct ≤ 40，且不得出现在推荐前3位
  ■ 嵌入式工程师：无硬件/驱动/RTOS 经验 → affinity_pct ≤ 38
  ■ Android / iOS / Flutter 工程师：无对应平台项目经验 → affinity_pct ≤ 35
理由：推荐一个用户完全不会的主力语言方向毫无价值，只会造成方向混乱。转型路径（C++→Go）
应通过图谱的 lateral 边展示，而不是进入 recommendations 推荐列表。

【not_this_role_if 强制执行】
每个岗位的"不适合"条件（not_this_role_if）如果与用户背景匹配，该岗位：
  - 推荐排名不得进入前3位
  - affinity_pct 不得超过 45%
举例：infrastructure-engineer 的 not_this_role_if 包含"无Go项目经验"，若用户无Go经验则该岗位排名≥4且分数≤45。

【岗位列表（含区分信号）】
{role_list}

【用户求职意向（最高优先级）】
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
    {{"role_id": "岗位ID", "label": "中文名", "reason": "一句话推荐理由（必须提到熟练度）", "affinity_pct": 匹配度0到100}}
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

    filtered: list[dict] = []
    for rec in recs:
        role_id = rec.get("role_id", "")
        affinity = rec.get("affinity_pct", 0)

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

        filtered.append(rec)

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
                gn = graph_nodes.get(rid, {})
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

            # ── Seniority hard filter on LLM result ────────────────────
            # 应届生绝不推 L4+ 架构师/经理岗位，即便 LLM 推了也过滤掉
            exp_years = profile_data.get("experience_years", 0) or 0
            if exp_years == 0:
                enriched = [r for r in enriched if (r.get("career_level") or 0) <= 3]
            elif exp_years <= 1:
                enriched = [r for r in enriched if (r.get("career_level") or 0) <= 4]

            # ── Add promotion targets（应届生不加，避免混淆）──────────
            # 应届生看到"L4 架构师 晋升方向"会误以为那是可达目标，但他们还在 L2 入场阶段
            # 晋升路径在 /role/:id 页面单独展示，不和入职推荐混在一起
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
                    # 不加超过用户现有级别 +1 的晋升目标（1 年经验看 L2-L3，不要直接看 L4+）
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
