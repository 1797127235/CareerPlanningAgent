"""Profile post-processing after LLM/VLM extraction."""
from __future__ import annotations

import json
import logging

from sqlalchemy.orm import Session

from backend.models import Profile
from backend.services.profile.parser.internship import _is_valid_internship, _internship_to_project_str
from backend.services.profile.parser.text import _supplement_skills_from_projects

logger = logging.getLogger(__name__)

_AWARD_KEYWORDS = (
    "大赛", "竞赛", "比赛", "获奖", "奖学金", "省一", "省二", "省三",
    "国一", "国二", "国三", "一等奖", "二等奖", "三等奖", "特等奖",
    "金奖", "银奖", "铜奖", "优秀奖", "荣誉", "证书", "认证",
)


def _postprocess_profile(parsed: dict) -> dict:
    projects: list = parsed.get("projects", [])
    awards: list = parsed.get("awards", [])

    # Move award-like items from projects → awards
    clean_projects = []
    for item in projects:
        text = str(item)
        if any(kw in text for kw in _AWARD_KEYWORDS):
            if text not in awards:
                awards.append(text)
        else:
            clean_projects.append(item)
    parsed["projects"] = clean_projects
    parsed["awards"] = awards

    # Validate internships — move misclassified entries back to projects
    raw_internships = parsed.get("internships", [])
    valid_internships = []
    for entry in raw_internships:
        if not isinstance(entry, dict):
            continue
        if _is_valid_internship(entry):
            valid_internships.append(entry)
        else:
            proj_str = _internship_to_project_str(entry)
            if proj_str and proj_str not in parsed["projects"]:
                parsed["projects"].append(proj_str)
            logger.info("Demoted internship→project: company=%s role=%s",
                        entry.get("company"), entry.get("role"))
    parsed["internships"] = valid_internships

    # Supplement skills from project descriptions when LLM/VLM misses tech terms
    parsed = _supplement_skills_from_projects(parsed)

    return parsed


def _lazy_fix_misclassified_internships(profile: Profile, db: Session) -> bool:
    """Retroactively demote misclassified internships on existing profiles.

    Runs as a background fix when profile data is loaded.
    Returns True if any changes were made.
    """
    try:
        data = json.loads(profile.profile_json or "{}")
    except (json.JSONDecodeError, TypeError):
        return False

    raw_internships = data.get("internships", [])
    if not raw_internships:
        return False

    valid = []
    demoted = []
    changed = False
    for entry in raw_internships:
        if not isinstance(entry, dict):
            continue
        if _is_valid_internship(entry):
            valid.append(entry)
        else:
            proj_str = _internship_to_project_str(entry)
            if proj_str:
                demoted.append(proj_str)
            changed = True

    if changed:
        data["internships"] = valid
        projects = list(data.get("projects", []))
        for p in demoted:
            if p not in projects:
                projects.append(p)
        data["projects"] = projects
        profile.profile_json = json.dumps(data, ensure_ascii=False)
        db.commit()
        logger.info("Lazy-fixed misclassified internships for profile %s", profile.id)

    return changed
