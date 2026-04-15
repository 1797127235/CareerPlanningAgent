# -*- coding: utf-8 -*-
"""SJT situational judgment test — question generation, scoring, and advice."""
from __future__ import annotations

import json
from typing import Any

from backend.services.profile.shared import _PROJECT_ROOT, _soft_skills_as_list


def direction_from_node(node: dict) -> dict:
    """Build a minimal direction dict from graph node when no profiles.json match."""
    must_skills = node.get("must_skills", [])
    soft_list = _soft_skills_as_list(node.get("soft_skills", []))
    return {
        "jd_count": 1,
        "skill_type_groups": {
            "hard_skill": [
                {"skill": s, "count": 1, "proficiency_dist": {}}
                for s in must_skills
            ],
            "soft_skill": [
                {"skill": s, "count": 1}
                for s in soft_list
            ],
            "knowledge": [],
        },
        "experience": {"years": {"p25": None, "p50": None, "p75": None}},
        "education_dist": {},
        "certificates": node.get("certificates", []),
    }


def _load_sjt_templates() -> list[dict]:
    """Load SJT scenario templates from data/sjt_templates.json."""
    path = _PROJECT_ROOT / "data" / "sjt_templates.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["templates"]


def generate_sjt_questions(profile_data: dict) -> list[dict]:
    """Fill SJT templates with personalized context based on user's resume.

    Returns list of questions with filled scenarios/options AND efficacy values
    (caller must strip efficacy before sending to client).
    """
    from backend.llm import llm_chat, parse_json_response, get_model

    templates = _load_sjt_templates()

    # Build resume summary for LLM context
    skills = [s.get("name", "") for s in profile_data.get("skills", [])[:10]]
    projects = profile_data.get("projects", [])[:3]
    education = profile_data.get("education", {})
    experience_years = profile_data.get("experience_years", 0)

    resume_summary = (
        f"技能: {', '.join(skills)}\n"
        f"项目经验: {'; '.join(p if isinstance(p, str) else p.get('description', str(p)) for p in projects)}\n"
        f"教育: {education.get('degree', '')} {education.get('major', '')} {education.get('school', '')}\n"
        f"工作年限: {experience_years}"
    )

    # Build slot fill request
    slot_request = []
    for t in templates:
        slot_request.append({
            "id": t["id"],
            "dimension": t["dimension"],
            "fill_slots": t["fill_slots"],
            "scenario_hint": t["scenario_template"][:60] + "...",
        })

    prompt = f"""你是一个 SJT（情境判断测验）情境个性化助手。

用户简历摘要：
{resume_summary}

请根据用户的行业背景和经历，为以下 {len(templates)} 道情境题的占位符填充具体内容。
填充要求：
- 内容必须贴合用户的行业/技术栈/项目经验
- 每个 slot 填 2-8 个字的短语
- 不要改变题目结构，只填空

请返回严格 JSON，格式为：
{{{{
  "fills": [
    {{{{"id": "t01", "slots": {{{{"stakeholder": "产品总监", "project_type": "电商推荐系统", ...}}}}}}}},
    ...
  ]
}}}}

需要填充的模板：
{json.dumps(slot_request, ensure_ascii=False, indent=2)}

只返回 JSON，不要有任何其他文字。"""

    result = llm_chat(
        [{"role": "user", "content": prompt}],
        model=get_model("default"),
        temperature=0.7,
        timeout=90,
    )
    fills_data = parse_json_response(result)
    fills_map = {f["id"]: f.get("slots", {}) for f in fills_data.get("fills", [])}
    if not fills_map:
        raise ValueError("LLM returned empty fills")

    # Apply fills to templates
    questions = []
    for t in templates:
        slots = fills_map.get(t["id"], {})
        # Fill scenario
        scenario = t["scenario_template"]
        for slot_name, slot_value in slots.items():
            scenario = scenario.replace("{" + slot_name + "}", str(slot_value))
        # Fill options
        options = []
        for o in t["options"]:
            text = o.get("text_template", o.get("text", ""))
            for slot_name, slot_value in slots.items():
                text = text.replace("{" + slot_name + "}", str(slot_value))
            options.append({
                "id": o["id"],
                "text": text,
                "efficacy": o["efficacy"],
            })
        questions.append({
            "id": t["id"],
            "dimension": t["dimension"],
            "scenario": scenario,
            "options": options,
        })

    return questions


_LEVEL_MAP = [
    (80, "优秀"),
    (60, "良好"),
    (40, "基础"),
    (0, "待发展"),
]


def score_to_level(score: float) -> str:
    """Map 0-100 score to 4-tier level."""
    for threshold, level in _LEVEL_MAP:
        if score >= threshold:
            return level
    return "待发展"


def score_sjt_v2(answers: list[dict], questions: list[dict]) -> dict:
    """Score SJT v2 answers using session questions (with efficacy).

    Args:
        answers: [{"question_id": "t01", "best": "b", "worst": "c"}, ...]
        questions: Full question list from SjtSession (with efficacy)

    Returns:
        {"dimensions": {"communication": {"score": 72, "level": "良好"}, ...}}
    """
    q_map = {q["id"]: q for q in questions}
    dim_scores: dict[str, list[float]] = {}

    for ans in answers:
        q = q_map.get(ans.get("question_id", ""))
        if not q:
            continue
        options = {o["id"]: o["efficacy"] for o in q["options"]}
        best_eff = options.get(ans.get("best", ""), 2)
        worst_eff = options.get(ans.get("worst", ""), 3)
        raw = best_eff + (4 - worst_eff)
        # Corrected normalization: actual range is 2-7
        normalized = max(0, min(100, round((raw - 2) / 5 * 100)))
        dim_scores.setdefault(q["dimension"], []).append(normalized)

    dimensions = {}
    for dim, vals in dim_scores.items():
        avg = round(sum(vals) / len(vals))
        dimensions[dim] = {
            "score": avg,
            "level": score_to_level(avg),
        }

    return {"dimensions": dimensions}


def generate_sjt_advice(
    dimensions: dict,
    answers: list[dict],
    questions: list[dict],
    profile_data: dict,
) -> dict[str, str]:
    """Generate per-dimension improvement advice based on answer patterns.

    Returns: {"communication": "advice text", "learning": "...", ...}
    """
    from backend.llm import llm_chat, parse_json_response, get_model

    # Build answer summary for LLM
    q_map = {q["id"]: q for q in questions}
    answer_details = []
    for ans in answers:
        q = q_map.get(ans.get("question_id", ""))
        if not q:
            continue
        opts = {o["id"]: o for o in q["options"]}
        best_opt = opts.get(ans.get("best", ""))
        worst_opt = opts.get(ans.get("worst", ""))
        answer_details.append({
            "dimension": q["dimension"],
            "scenario": q["scenario"][:80],
            "best_choice": best_opt["text"] if best_opt else "",
            "best_efficacy": best_opt["efficacy"] if best_opt else 0,
            "worst_choice": worst_opt["text"] if worst_opt else "",
            "worst_efficacy": worst_opt["efficacy"] if worst_opt else 0,
        })

    dim_summary = ", ".join(
        f"{dim}: {info['score']}分({info['level']})"
        for dim, info in dimensions.items()
    )

    skills = [s.get("name", "") for s in profile_data.get("skills", [])[:5]]

    prompt = f"""你是一个职业发展顾问。用户刚完成了一次软技能情境评估。

评估结果：{dim_summary}
用户技能背景：{', '.join(skills)}

作答详情：
{json.dumps(answer_details, ensure_ascii=False, indent=2)}

请为每个维度生成 50-100 字的改进建议。要求：
- 正向语气，指出具体行为模式（"你倾向于…"）
- 给出可操作建议（"可以尝试…"）
- 不要重复题目内容，总结行为模式
- 即使是"优秀"等级也给出进一步提升的方向

返回严格 JSON，包含所有评估过的维度：
{", ".join(f'"{dim}": "建议文字"' for dim in dimensions)}

只返回 JSON，不要有任何其他文字。"""

    try:
        result = llm_chat(
            [{"role": "user", "content": prompt}],
            model=get_model("default"),
            temperature=0.7,
            timeout=30,
        )
        advice = parse_json_response(result)
        if isinstance(advice, dict):
            return {k: str(v) for k, v in advice.items() if k in dimensions}
    except Exception:
        pass
    return {}
