"""Role matching and recommendation filtering."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from backend.config import DASHSCOPE_API_KEY, LLM_BASE_URL
from backend.services.graph.query import _get_graph_nodes, _get_role_list_text
from backend.services.graph.embedding import embedding_prefilter
from backend.services.graph.skills import _build_graph_skill_tokens, _build_work_content_summary, _expand_chinese_tokens, _extract_implied_skills_from_text

logger = logging.getLogger(__name__)

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

