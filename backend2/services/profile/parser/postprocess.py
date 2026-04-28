"""防御性后处理 — 只做非语义清理和事实保真修复。

禁止：技能别名归一化、岗位方向映射、公司层级判断、职业信号推理。
允许：strip、去空、去重、删除空实习、回填 raw_text、日期精度保真。
"""
from __future__ import annotations

import logging
import re

from backend2.schemas.profile import (
    Education,
    Internship,
    ProfileData,
    Project,
    ResumeDocument,
    Skill,
)

logger = logging.getLogger(__name__)

_AWARD_NOISE = {"无", "暂无", "无奖项", "未填写", "—", "-", "/"}


def postprocess(
    profile: ProfileData,
    document: ResumeDocument | None = None,
) -> ProfileData:
    """对 LLM 产出的 ProfileData 做防御性清理。"""
    profile.name = _s(profile.name)
    profile.job_target_text = _s(profile.job_target_text)
    profile.domain_hint = _s(profile.domain_hint)

    profile.education = _norm_education(profile.education)
    profile.skills = _norm_skills(profile.skills)
    profile.projects = _norm_projects(profile.projects)
    profile.internships = _norm_internships(profile.internships)
    profile.awards = _norm_awards(profile.awards)
    profile.certificates = _dedupe_strings(profile.certificates)

    # 强制回填 raw_text，确保追溯链路不断
    if document and not profile.raw_text:
        profile.raw_text = document.raw_text

    # 日期精度保真：尝试从 raw_text 恢复被 LLM 简化掉的月份
    if document and document.raw_text:
        _recover_date_precision(profile, document.raw_text)

    logger.info(
        "后处理完成: edu=%d skills=%d projects=%d internships=%d awards=%d certs=%d",
        len(profile.education),
        len(profile.skills),
        len(profile.projects),
        len(profile.internships),
        len(profile.awards),
        len(profile.certificates),
    )
    return profile


def _s(v: str) -> str:
    return v.strip() if isinstance(v, str) else ""


def _dedupe_strings(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items or []:
        if isinstance(item, str) and (cleaned := item.strip()) and (key := cleaned.lower()) not in seen:
            seen.add(key)
            out.append(cleaned)
    return out


def _norm_education(edu_list: list[Education]) -> list[Education]:
    out: list[Education] = []
    for e in edu_list or []:
        if not isinstance(e, Education):
            continue
        degree = _s(e.degree)
        major = _s(e.major)
        school = _s(e.school)
        duration = _s(e.duration)
        if not any((degree, major, school)):
            continue
        out.append(Education(
            degree=degree,
            major=major,
            school=school,
            graduation_year=e.graduation_year,
            duration=duration,
        ))
    return out


def _norm_skills(skills: list[Skill]) -> list[Skill]:
    seen: set[str] = set()
    out: list[Skill] = []
    for s in skills or []:
        if not isinstance(s, Skill):
            continue
        name = _s(s.name)
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        out.append(Skill(name=name, level=s.level))
    return out


def _norm_projects(projects: list[Project]) -> list[Project]:
    out: list[Project] = []
    for p in projects or []:
        if not isinstance(p, Project):
            continue
        name = _s(p.name)
        desc = _s(p.description)
        duration = _s(p.duration)
        if not any((name, desc)):
            continue
        out.append(Project(
            name=name,
            description=desc,
            tech_stack=_dedupe_strings(p.tech_stack),
            duration=duration,
            highlights=_s(p.highlights),
        ))
    return out


def _norm_internships(interns: list[Internship]) -> list[Internship]:
    out: list[Internship] = []
    for entry in interns or []:
        if not isinstance(entry, Internship):
            continue
        company = _s(entry.company)
        role = _s(entry.role)
        # 删除 company 和 role 同时为空的实习
        if not company and not role:
            continue
        out.append(Internship(
            company=company,
            role=role,
            duration=_s(entry.duration),
            tech_stack=_dedupe_strings(entry.tech_stack),
            highlights=_s(entry.highlights),
        ))
    return out


def _norm_awards(awards: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in awards or []:
        if isinstance(item, str) and (cleaned := item.strip()) and cleaned not in _AWARD_NOISE and len(cleaned) >= 2:
            key = cleaned.lower()
            if key not in seen:
                seen.add(key)
                out.append(cleaned)
    return out


def _recover_date_precision(profile: ProfileData, raw_text: str) -> None:
    """尝试从 raw_text 中恢复被 LLM 简化掉的日期月份。

    例如 LLM 把 '2024.03 - 2024.08' 简化成 '2024 - 2024'，
    本函数在 raw_text 中搜索匹配模式并回填到 education / internships / projects。
    """
    # 常见日期格式：2024.03、2024-03、2024/03、2024年3月
    _DATE_RE = re.compile(
        r"(\d{4})[\.\-/年]\s*(\d{1,2})\s*[-~至]\s*(\d{4})[\.\-/年]\s*(\d{1,2})"
    )
    matches = _DATE_RE.findall(raw_text)
    if not matches:
        return

    # 简单启发式：为每个包含简化年份的字段尝试匹配最近的完整日期
    for edu in profile.education:
        if edu.duration and re.match(r"^\d{4}\s*-\s*\d{4}$", edu.duration):
            for m in matches:
                if m[0] in edu.duration and m[2] in edu.duration:
                    edu.duration = f"{m[0]}.{m[1]} - {m[2]}.{m[3]}"
                    break

    for it in profile.internships:
        if it.duration and re.match(r"^\d{4}\s*-\s*\d{4}$", it.duration):
            for m in matches:
                if m[0] in it.duration and m[2] in it.duration:
                    it.duration = f"{m[0]}.{m[1]} - {m[2]}.{m[3]}"
                    break

    for prj in profile.projects:
        if prj.duration and re.match(r"^\d{4}\s*-\s*\d{4}$", prj.duration):
            for m in matches:
                if m[0] in prj.duration and m[2] in prj.duration:
                    prj.duration = f"{m[0]}.{m[1]} - {m[2]}.{m[3]}"
                    break
