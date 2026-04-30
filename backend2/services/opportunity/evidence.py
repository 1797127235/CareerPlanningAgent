"""backend2/services/opportunity/evidence.py — 本地规则匹配证据。

不调用 LLM，不查数据库，纯本地计算：
- 从 ProfileData 提取所有技能（skills + projects.tech_stack + internships.tech_stack）
- 与 JDExtract.required_skills / preferred_skills 做交集和差集
- 结果作为 LLM 的输入证据
"""
from __future__ import annotations

import logging

from backend2.schemas.opportunity import JDExtract
from backend2.schemas.profile import ProfileData

logger = logging.getLogger(__name__)


def _collect_user_skills(profile: ProfileData) -> set[str]:
    """收集用户画像中所有技能名称（去重、小写）。"""
    skills: set[str] = set()

    for item in profile.skills or []:
        name = item.name.strip()
        if name:
            skills.add(name.lower())

    for project in profile.projects or []:
        for tech in project.tech_stack:
            if tech:
                skills.add(tech.strip().lower())

    for internship in profile.internships or []:
        for tech in internship.tech_stack:
            if tech:
                skills.add(tech.strip().lower())

    return skills


def _match_skill(jd_skill: str, user_skills: set[str]) -> bool:
    """判断 JD 技能是否在用户技能中（标准化后精确匹配，大小写不敏感）。

    保守策略：只做精确匹配，不做子串/语义推断。
    例如 "Go" 不会命中 "MongoDB"，"C" 不会命中 "React"。
    """
    jd_lower = jd_skill.strip().lower()
    if not jd_lower:
        return False
    return jd_lower in user_skills


def build_skill_evidence(profile: ProfileData, jd: JDExtract) -> dict:
    """构建技能匹配证据。

    返回：
    {
        "user_skills": ["python", "go", ...],
        "required_skills": ["Python", "Kubernetes", ...],
        "preferred_skills": ["Redis", "Kafka", ...],
        "matched_required": ["Python"],
        "gap_required": ["Kubernetes"],
        "matched_preferred": ["Redis"],
        "gap_preferred": ["Kafka"],
        "required_coverage": "50%",
        "preferred_coverage": "50%",
    }
    """
    user_skills = _collect_user_skills(profile)

    required = [s.strip() for s in (jd.required_skills or []) if s.strip()]
    preferred = [s.strip() for s in (jd.preferred_skills or []) if s.strip()]

    matched_required = [s for s in required if _match_skill(s, user_skills)]
    gap_required = [s for s in required if not _match_skill(s, user_skills)]
    matched_preferred = [s for s in preferred if _match_skill(s, user_skills)]
    gap_preferred = [s for s in preferred if not _match_skill(s, user_skills)]

    req_cov = f"{len(matched_required)}/{len(required)} ({len(matched_required)*100//max(len(required),1)}%)"
    pref_cov = f"{len(matched_preferred)}/{len(preferred)} ({len(matched_preferred)*100//max(len(preferred),1)}%)"

    return {
        "user_skills": sorted(user_skills),
        "required_skills": required,
        "preferred_skills": preferred,
        "matched_required": matched_required,
        "gap_required": gap_required,
        "matched_preferred": matched_preferred,
        "gap_preferred": gap_preferred,
        "required_coverage": req_cov,
        "preferred_coverage": pref_cov,
    }
