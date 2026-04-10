# backend/plan_adapter.py
"""Unified adapter for reading plan data from new or old report format."""
from __future__ import annotations


def get_plan_data(report_data: dict) -> dict:
    """Return standard plan structure regardless of report format.

    New reports: structured_data.action_plan
    Old reports: structured_data.training_plan
    """
    sd = report_data.get("structured_data", {})

    if "action_plan" in sd:
        ap = sd["action_plan"]
        return {
            "stages": ap.get("stages", []),
            "time_budget": ap.get("time_budget", {"hours_per_week": 10}),
            "selected_skills": ap.get("selected_skills", []),
            "source": "action_plan",
        }

    tp = sd.get("training_plan", {})
    return {
        "stages": tp.get("stages", []),
        "time_budget": {"hours_per_week": 10, "total_weeks": 12},
        "selected_skills": [],
        "source": "training_plan",
    }


def action_plan_to_training_plan(action_plan: dict) -> dict:
    """Derive old training_plan format from new action_plan for backward compat."""
    return {
        "estimated_months": action_plan.get("time_budget", {}).get("total_weeks", 12) // 4,
        "stages": [
            {
                "stage": s["stage"],
                "label": s.get("label", ""),
                "items": s.get("items", []),
            }
            for s in action_plan.get("stages", [])
        ],
    }


def quick_gaps_logic(
    user_skills: set[str],
    required: list[str],
    *,
    target_job: str = "",
    profile_summary: str = "",
    use_llm: bool = True,
) -> dict:
    """Compute skill gaps: set diff first, then LLM supplement.

    Args:
        user_skills: lowercase set of user's skill names
        required: list of required skill names from job node
        target_job: job label (for LLM context)
        profile_summary: brief text about student's background (for LLM context)
        use_llm: whether to call LLM for supplementary gap analysis
    """
    def estimate_hours(skill: str) -> int:
        """Rough estimate of learning hours for a skill."""
        return 20  # default estimate; was in deleted agent/learning_resources.py

    if not required and not use_llm:
        return {"match_score": 0, "matched_skills": [], "skill_gaps": []}

    # ── Step 1: Set diff ──
    n = len(required) or 1
    weights = {s.lower(): n - i for i, s in enumerate(required)}
    total_weight = sum(weights.values()) or 1

    matched = [s for s in required if s.lower() in user_skills]
    missing = [s for s in required if s.lower() not in user_skills]

    matched_weight = sum(weights.get(s.lower(), 1) for s in matched)
    match_score = round(matched_weight / total_weight * 100) if required else 0

    gaps = []
    for skill in missing:
        w = weights.get(skill.lower(), 1)
        score_if_learned = round((matched_weight + w) / total_weight * 100)
        gaps.append({
            "skill": skill,
            "priority": "high",
            "estimated_hours": estimate_hours(skill),
            "match_delta": score_if_learned - match_score,
            "match_if_learned": score_if_learned,
            "source": "data",
        })

    # ── Step 2: LLM supplement ──
    if use_llm and target_job:
        llm_gaps = _llm_gap_supplement(
            target_job=target_job,
            user_skills_list=sorted(user_skills),
            existing_gaps=[g["skill"] for g in gaps],
            profile_summary=profile_summary,
        )
        for skill in llm_gaps:
            gaps.append({
                "skill": skill,
                "priority": "medium",
                "estimated_hours": estimate_hours(skill),
                "match_delta": 0,  # LLM gaps don't have weighted delta
                "match_if_learned": 0,
                "source": "llm",
            })

    # Sort: data gaps (with delta) first, then LLM gaps
    gaps.sort(key=lambda g: (-1 if g.get("source") == "data" else 0, -g["match_delta"]))

    # Top 5 = high, rest = medium
    for i, g in enumerate(gaps):
        g["priority"] = "high" if i < 5 else "medium"

    return {
        "match_score": match_score,
        "matched_skills": matched,
        "skill_gaps": gaps,
    }


def _llm_gap_supplement(
    *,
    target_job: str,
    user_skills_list: list[str],
    existing_gaps: list[str],
    profile_summary: str,
) -> list[str]:
    """Call LLM to identify additional missing skills not caught by set diff.

    Returns a list of skill names (max 5) that the student should learn.
    """
    import json
    import logging

    logger = logging.getLogger(__name__)

    try:
        from backend.llm import get_llm_client, get_env_str

        client = get_llm_client(timeout=15)
        model = get_env_str("CHAT_LLM_MODEL", "qwen3.5-flash")

        user_skills_str = "、".join(user_skills_list[:20]) if user_skills_list else "无"
        existing_gaps_str = "、".join(existing_gaps[:10]) if existing_gaps else "无"
        profile_str = profile_summary[:200] if profile_summary else "计算机类大学生"

        prompt = (
            f"目标岗位：{target_job}\n"
            f"学生背景：{profile_str}\n"
            f"学生已有技能：{user_skills_str}\n"
            f"系统已识别的技能缺口：{existing_gaps_str}\n\n"
            f"请判断：对于「{target_job}」这个岗位，除了上面已识别的缺口，"
            "这个学生还缺少哪些关键技能？只列出系统漏掉的重要技能。\n\n"
            "要求：\n"
            "1. 只输出 JSON 数组，如 [\"技能1\", \"技能2\"]\n"
            "2. 最多5个技能\n"
            "3. 不要重复已有技能和已识别缺口\n"
            "4. 只列真正重要的，不要凑数"
        )

        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是一位资深 IT 招聘顾问。只输出 JSON 数组，不要其他内容。"},
                {"role": "user", "content": prompt},
            ],
            timeout=15,
            extra_body={"enable_thinking": False},
        )

        raw = (resp.choices[0].message.content or "").strip()
        # Extract JSON array
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start >= 0 and end > start:
            skills = json.loads(raw[start:end])
            if isinstance(skills, list):
                # Filter: no duplicates with existing
                existing_lower = {s.lower() for s in user_skills_list} | {s.lower() for s in existing_gaps}
                result = [s for s in skills if isinstance(s, str) and s.strip() and s.lower() not in existing_lower]
                return result[:5]

    except Exception as exc:
        logger.warning("LLM gap supplement failed: %s", exc)

    return []
