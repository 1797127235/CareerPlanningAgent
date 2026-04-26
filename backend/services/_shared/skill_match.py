"""Shared skill matching utilities — canonical implementation.

Used by both report and growth modules.
"""

from __future__ import annotations


def norm_skill(s: str) -> str:
    """Normalize a skill name for fuzzy comparison."""
    return s.lower().strip().replace(" ", "").replace("-", "").replace("_", "")


def skill_matches(skill_name: str, user_skills: set[str]) -> bool:
    """Case-insensitive substring match for a skill keyword against user skill set.

    Handles variants like "Spring Boot" vs "SpringBoot", "Redis缓存" vs "Redis".
    Normalization removes spaces/hyphens/underscores before comparison.
    Short keywords (≤2 chars) require exact match to avoid false positives.
    """
    name = skill_name.lower().strip()
    name_norm = norm_skill(skill_name)
    if not name:
        return False
    if name in user_skills:
        return True
    if len(name_norm) <= 2:
        return False
    for us in user_skills:
        if not us:
            continue
        us_norm = norm_skill(us)
        if name_norm == us_norm:
            return True
        if len(us_norm) > 2 and (name_norm in us_norm or us_norm in name_norm):
            return True
    return False


def skill_in_set(skill_name: str, skill_set: set[str]) -> bool:
    """Fuzzy-check whether skill_name appears in a given set."""
    if not skill_set:
        return False
    name_norm = norm_skill(skill_name)
    if not name_norm:
        return False
    for s in skill_set:
        s_norm = norm_skill(s)
        if name_norm == s_norm:
            return True
        if (
            len(name_norm) > 2
            and len(s_norm) > 2
            and (name_norm in s_norm or s_norm in name_norm)
        ):
            return True
    return False


def user_skill_set(profile_data: dict) -> set[str]:
    """Extract user skills as a lowercase set from profile data."""
    raw = profile_data.get("skills", [])
    if not raw:
        return set()
    if isinstance(raw[0], dict):
        return {s.get("name", "").lower().strip() for s in raw if s.get("name")}
    return {s.lower().strip() for s in raw if isinstance(s, str) and s.strip()}
