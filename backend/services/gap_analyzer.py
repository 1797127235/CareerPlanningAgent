# -*- coding: utf-8 -*-
"""
GapAnalyzer — LLM-based learning gap analysis.

Given a user profile and a target role's learning roadmap,
uses LLM to determine which modules are mastered vs gaps.
Results are cached per (profile_id, role_id) to avoid repeated calls.

Uses constrained classification (closed-set) to minimize hallucination:
the LLM picks from a FIXED list of roadmap modules, not open-ended generation.
"""
from __future__ import annotations

import json
import hashlib
import logging
from typing import Any

from backend.llm import get_llm_client, get_model

logger = logging.getLogger(__name__)

# ── Prompt template ────────────────────────────────────────────────────────

_ANALYSIS_PROMPT = """\
根据用户画像判断目标岗位各模块的掌握情况。

用户画像：技能={skills}；项目={projects}；经验={experience}

目标岗位：{role_label}
模块列表：{modules}

返回JSON，仅从上方模块选择，不编造：
{{"mastered":[{{"module":"名","reason":"依据(几个字)"}}],"gaps":[{{"module":"名","reason":"原因(几个字)","priority":"high/medium/low"}}]}}
规则：无证据的归gaps；priority:high=核心,medium=补充,low=加分；仅JSON无其他文字。"""


def _build_profile_text(profile_data: dict) -> dict[str, str]:
    """Extract relevant text from profile for the prompt."""
    skills = [
        s.get("name", "") if isinstance(s, dict) else str(s)
        for s in profile_data.get("skills", [])
        if (s.get("name") if isinstance(s, dict) else s)
    ]

    projects = []
    for p in profile_data.get("projects", []):
        if isinstance(p, str):
            if p.strip():
                projects.append(p.strip())
            continue
        name = p.get("name", "")
        desc = p.get("description", "")
        if name or desc:
            projects.append(f"{name}：{desc}" if name and desc else name or desc)

    experience = []
    raw_exp = profile_data.get("internships", []) + profile_data.get("experience", [])
    for e in raw_exp:
        if isinstance(e, str):
            if e.strip():
                experience.append(e.strip())
            continue
        company = e.get("company", "")
        role = e.get("role", e.get("position", ""))
        desc = e.get("description", "")
        if company or role:
            experience.append(f"{company} {role}：{desc}".strip())

    return {
        "skills": "、".join(skills) if skills else "未提供",
        "projects": "\n".join(projects) if projects else "未提供",
        "experience": "\n".join(experience) if experience else "未提供",
    }


def analyze_gaps(
    profile_data: dict,
    role_id: str,
    role_label: str,
    topics: list[str],
) -> dict[str, Any]:
    """Analyze learning gaps using LLM constrained classification.

    Args:
        profile_data: parsed profile JSON (skills, projects, etc.)
        role_id: target role identifier
        role_label: Chinese role name for display
        topics: list of learning module names from the roadmap

    Returns:
        {
            "role_id": str,
            "mastered": [{"module": str, "reason": str}],
            "gaps": [{"module": str, "reason": str, "priority": str}],
            "mastered_count": int,
            "gap_count": int,
            "coverage_pct": int,
        }
    """
    if not topics:
        return {"role_id": role_id, "mastered": [], "gaps": [],
                "mastered_count": 0, "gap_count": 0, "coverage_pct": 0}

    profile_text = _build_profile_text(profile_data)
    modules_text = "、".join(topics)

    prompt = _ANALYSIS_PROMPT.format(
        skills=profile_text["skills"],
        projects=profile_text["projects"],
        experience=profile_text["experience"],
        role_label=role_label,
        modules=modules_text,
    )

    max_retries = 2
    result = None
    last_err = None
    for attempt in range(max_retries):
        try:
            client = get_llm_client(timeout=90)
            resp = client.chat.completions.create(
                model=get_model("fast"),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1200,
                temperature=0.1,
            )
            text = (resp.choices[0].message.content or "").strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            result = json.loads(text)
            break
        except Exception as e:
            last_err = e
            logger.warning("GapAnalyzer attempt %d/%d failed for %s: %s", attempt + 1, max_retries, role_id, e)

    if result is None:
        logger.error("GapAnalyzer all %d retries failed for %s: %s", max_retries, role_id, last_err)
        return {
            "role_id": role_id,
            "mastered": [],
            "gaps": [{"module": t, "reason": "无法分析", "priority": "medium"} for t in topics],
            "mastered_count": 0,
            "gap_count": len(topics),
            "coverage_pct": 0,
            "failed": True,
        }

    mastered = result.get("mastered", [])
    gaps = result.get("gaps", [])

    # Sort gaps: high > medium > low
    priority_order = {"high": 0, "medium": 1, "low": 2}
    gaps.sort(key=lambda g: priority_order.get(g.get("priority", "medium"), 1))

    mastered_count = len(mastered)
    total = mastered_count + len(gaps)
    coverage = round(mastered_count / max(total, 1) * 100)

    return {
        "role_id": role_id,
        "mastered": mastered,
        "gaps": gaps,
        "mastered_count": mastered_count,
        "gap_count": len(gaps),
        "coverage_pct": coverage,
    }


def profile_hash(profile_data: dict) -> str:
    """Generate a stable hash of profile data for cache invalidation."""
    key_data = json.dumps({
        "skills": sorted(s.get("name", "") if isinstance(s, dict) else str(s) for s in profile_data.get("skills", [])),
        "projects": [p.get("name", "") if isinstance(p, dict) else str(p) for p in profile_data.get("projects", [])],
    }, ensure_ascii=False)
    return hashlib.md5(key_data.encode()).hexdigest()[:12]
