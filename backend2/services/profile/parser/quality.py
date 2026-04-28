"""解析质量评分 — 只评估结构完整性，不判断用户好坏。

返回结构完整度分数和检查项，供前端展示和下游模块参考。
Parser 层不定义"多少分通过"。
"""
from __future__ import annotations

from backend2.schemas.profile import ParseMeta, ProfileData


def score_profile(profile: ProfileData) -> ParseMeta:
    """对 ProfileData 做结构完整性评分，返回 ParseMeta。"""
    checks: dict[str, bool] = {
        "has_name": bool(profile.name.strip()),
        "has_job_target_text": bool(profile.job_target_text.strip()),
        "has_education": len(profile.education) > 0,
        "has_skills": len(profile.skills) > 0,
        "has_projects": len(profile.projects) > 0,
        "has_internships": len(profile.internships) > 0,
        "has_awards_or_certificates": len(profile.awards) > 0 or len(profile.certificates) > 0,
        "has_raw_text": bool(profile.raw_text.strip()),
    }

    total = len(checks)
    passed = sum(1 for v in checks.values() if v)
    score = int((passed / total) * 100) if total else 0

    return ParseMeta(
        quality_score=score,
        quality_checks=checks,
    )
