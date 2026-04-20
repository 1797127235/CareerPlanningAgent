"""Smart merger: combine ResumeSDK base fields + LLM semantic fields into one ProfileData."""
from __future__ import annotations

import logging

from backend.services.profile.parser.schema import ProfileData, Skill

logger = logging.getLogger(__name__)

_LEVEL_ORDER = {"beginner": 0, "familiar": 1, "intermediate": 2, "advanced": 3}


def merge_profiles(sdk: ProfileData | None, llm: ProfileData | None) -> ProfileData:
    """Merge SDK base fields + LLM semantic fields.

    Strategy:
    - SDK is better at: name, education (structured data)
    - LLM is better at: skills, projects, primary_domain, knowledge_areas, career_signals
    - Union for: internships, awards, certificates, knowledge_areas
    - Max for: experience_years
    """
    if not sdk and not llm:
        logger.warning("merge_profiles called with both sources None")
        return ProfileData()

    if not sdk:
        return llm or ProfileData()
    if not llm:
        return sdk

    # Start with SDK as base, overlay LLM where it's stronger
    merged = ProfileData()

    # SDK-priority fields: structured data extraction is more reliable
    merged.name = _pick_non_empty(sdk.name, llm.name)
    merged.education = sdk.education if sdk.education.school else llm.education
    merged.experience_years = max(sdk.experience_years, llm.experience_years)
    merged.raw_text = sdk.raw_text or llm.raw_text
    merged.preferences = sdk.preferences or llm.preferences

    # LLM-priority fields: semantic understanding is better
    merged.job_target = _pick_non_empty(llm.job_target, sdk.job_target)
    merged.primary_domain = _pick_non_empty(llm.primary_domain, sdk.primary_domain)
    merged.career_signals = llm.career_signals if llm.career_signals.domain_specialization else sdk.career_signals
    merged.projects = llm.projects if llm.projects else sdk.projects
    merged.soft_skills = llm.soft_skills if llm.soft_skills.get("_version") else sdk.soft_skills

    # Union + conflict resolution for skills
    merged.skills = _merge_skills(sdk.skills, llm.skills)

    # Union for arrays (deduplicated by schema validator)
    merged.knowledge_areas = _union_strings(sdk.knowledge_areas, llm.knowledge_areas)
    merged.awards = _union_strings(sdk.awards, llm.awards)
    merged.certificates = _union_strings(sdk.certificates, llm.certificates)
    merged.internships = _union_internships(sdk.internships, llm.internships)

    logger.info(
        "Merged profile: SDK(skills=%d projects=%d) + LLM(skills=%d projects=%d) → "
        "merged(skills=%d projects=%d domain=%r)",
        len(sdk.skills), len(sdk.projects),
        len(llm.skills), len(llm.projects),
        len(merged.skills), len(merged.projects), merged.primary_domain,
    )
    return merged


def _pick_non_empty(a: str, b: str) -> str:
    return a.strip() if a.strip() else b.strip()


def _merge_skills(sdk_skills: list[Skill], llm_skills: list[Skill]) -> list[Skill]:
    """Union skills: higher level wins; same level → prefer LLM (more granular/context-aware)."""
    skill_map: dict[str, Skill] = {}

    # SDK base layer
    for s in sdk_skills:
        key = s.name.lower()
        skill_map[key] = s

    # LLM overlay
    for s in llm_skills:
        key = s.name.lower()
        llm_lvl = _LEVEL_ORDER.get(s.level, 0)

        if key not in skill_map:
            skill_map[key] = s
        else:
            existing_lvl = _LEVEL_ORDER.get(skill_map[key].level, 0)
            if llm_lvl > existing_lvl:
                skill_map[key] = s
            elif llm_lvl == existing_lvl:
                # Same level: prefer LLM's context-aware assessment
                skill_map[key] = s

    return list(skill_map.values())


def _union_strings(a: list[str], b: list[str]) -> list[str]:
    """Union two string lists, case-insensitive dedup, preserving order."""
    seen: set[str] = set()
    out: list[str] = []
    for item in a + b:
        key = item.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(item.strip())
    return out


def _union_internships(sdk: list, llm: list) -> list:
    """Union internships by (company + role), prefer LLM on conflict."""
    interns: dict[str, dict] = {}
    for entry in sdk + llm:
        if not isinstance(entry, dict):
            continue
        key = (entry.get("company", "") + "|" + entry.get("role", "")).lower()
        if key:
            interns[key] = entry
    return list(interns.values())
