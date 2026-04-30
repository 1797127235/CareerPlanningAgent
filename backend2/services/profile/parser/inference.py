"""从简历事实推断分析字段 —— dimension_scores、tags、strengths、weaknesses。

本模块只基于已解析的 ProfileData 做确定性推断，不调用 LLM，
保证输出可预测、可测试。
"""
from __future__ import annotations

from datetime import datetime

from backend2.schemas.profile import DimensionScore, ProfileData


def _score_technical(skills: list) -> int:
    """技术能力：技能数量 + 多样性。"""
    n = len(skills)
    if n == 0:
        return 0
    if n >= 12:
        return 90
    if n >= 8:
        return 80
    if n >= 5:
        return 70
    if n >= 3:
        return 60
    return 45


def _score_projects(projects: list) -> int:
    """项目经验：项目数量 + 描述丰富度。"""
    n = len(projects)
    if n == 0:
        return 0
    desc_bonus = sum(1 for p in projects if len(p.description or "") > 20)
    base = {1: 50, 2: 65, 3: 75}.get(n, 85)
    return min(95, base + desc_bonus * 3)


def _score_internship(internships: list) -> int:
    """实习经验：有则无。"""
    n = len(internships)
    if n == 0:
        return 0
    if n >= 2:
        return 80
    return 65


def _score_education(education: list) -> int:
    """学历背景。"""
    if not education:
        return 0
    e = education[0]
    degree = (e.degree or "").lower()
    if "博" in degree or "phd" in degree or "博士" in degree:
        return 95
    if "硕" in degree or "master" in degree or "研究生" in degree:
        return 85
    if "本" in degree or "学士" in degree or "bachelor" in degree:
        return 75
    return 60


def infer_dimension_scores(profile: ProfileData) -> list[DimensionScore]:
    """基于简历事实推断能力维度分数。"""
    scores: list[DimensionScore] = [
        DimensionScore(name="技术能力", score=_score_technical(profile.skills), source="resume"),
        DimensionScore(name="项目经验", score=_score_projects(profile.projects), source="resume"),
        DimensionScore(name="实习经验", score=_score_internship(profile.internships), source="resume"),
        DimensionScore(name="学历背景", score=_score_education(profile.education), source="resume"),
    ]
    # 过滤掉 0 分的维度，保持展示整洁
    return [s for s in scores if s.score > 0]


def infer_tags(profile: ProfileData) -> list[str]:
    """基于简历事实生成标签。"""
    tags: set[str] = set()

    # 技术标签：取前 3 个技能
    for s in profile.skills[:3]:
        tags.add(s.name)

    # 职级/阶段标签
    degree = (profile.education[0].degree if profile.education else "").lower()
    if any(k in degree for k in ("博", "phd", "博士")):
        tags.add("博士")
    elif any(k in degree for k in ("硕", "master", "研究生")):
        tags.add("硕士")
    elif any(k in degree for k in ("本", "学士", "bachelor")):
        tags.add("本科")

    # 应届生判断（毕业年份 >= 当前年份 或 无实习）
    grad_year = profile.education[0].graduation_year if profile.education else None
    current_year = datetime.now().year
    if grad_year and grad_year >= current_year:
        tags.add("应届生")

    # 实习标签
    if profile.internships:
        tags.add("有实习")

    # 领域标签
    domain = profile.domain_hint
    if domain and domain not in tags:
        tags.add(domain)

    return list(tags)


def infer_strengths(profile: ProfileData) -> list[str]:
    """基于简历事实推断优势。"""
    strengths: list[str] = []

    skill_count = len(profile.skills)
    if skill_count >= 5:
        strengths.append(f"掌握 {skill_count} 项技术技能")
    elif skill_count >= 3:
        strengths.append("具备多技术栈能力")

    proj_count = len(profile.projects)
    if proj_count >= 2:
        strengths.append(f"有 {proj_count} 个项目经验")
    elif proj_count == 1:
        strengths.append("有项目实践经验")

    if profile.internships:
        strengths.append(f"有 {len(profile.internships)} 段实习经历")

    edu = profile.education[0] if profile.education else None
    if edu and edu.school:
        strengths.append(f"{edu.school} · {edu.major or ''}")

    # 项目中有亮点描述
    highlight_projects = [p for p in profile.projects if p.highlights]
    if highlight_projects:
        strengths.append("项目成果有量化描述")

    return strengths[:4]  # 最多 4 条


def infer_weaknesses(profile: ProfileData) -> list[str]:
    """基于简历事实推断短板/可提升点。"""
    weaknesses: list[str] = []

    if len(profile.projects) < 2:
        weaknesses.append("项目数量较少，建议补充更多实践")

    if not profile.internships:
        weaknesses.append("缺少实习经历")

    if len(profile.skills) < 3:
        weaknesses.append("技术栈展示较单一")

    if not profile.job_target_text:
        weaknesses.append("未明确求职意向")

    # 技能无等级区分（全是 familiar）
    has_level_variety = any(
        s.level in ("advanced", "intermediate") for s in profile.skills
    )
    if profile.skills and not has_level_variety:
        weaknesses.append("技能熟练度描述可更丰富")

    return weaknesses[:3]  # 最多 3 条


def enrich_profile(profile: ProfileData) -> ProfileData:
    """对 ProfileData 做推断增强，填充分析字段。"""
    if not profile.dimension_scores:
        profile.dimension_scores = infer_dimension_scores(profile)
    if not profile.tags:
        profile.tags = infer_tags(profile)
    if not profile.strengths:
        profile.strengths = infer_strengths(profile)
    if not profile.weaknesses:
        profile.weaknesses = infer_weaknesses(profile)
    # constraints / preferences 保持为空，由用户后续填写
    return profile
