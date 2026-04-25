"""成长档案服务 — readiness 估算、面试分析。"""
from __future__ import annotations

import json
import logging


logger = logging.getLogger(__name__)


def _skill_matches(skill_name: str, user_skills: set[str]) -> bool:
    """Case-insensitive substring match for a skill keyword against user skill set.

    Handles variants like "Spring Boot" vs "SpringBoot", "Redis缓存" vs "Redis".
    Normalization removes spaces/hyphens/underscores before comparison.
    Short keywords (≤2 chars) require exact match to avoid false positives.
    """
    def _norm(s: str) -> str:
        return s.lower().strip().replace(" ", "").replace("-", "").replace("_", "")

    name = skill_name.lower().strip()
    name_norm = _norm(skill_name)
    if not name:
        return False

    # Exact match (raw lowercase)
    if name in user_skills:
        return True

    # Short keyword: only exact match allowed
    if len(name_norm) <= 2:
        return False

    for us in user_skills:
        if not us:
            continue
        us_norm = _norm(us)
        # Normalized exact match (handles SpringBoot vs spring boot)
        if name_norm == us_norm:
            return True
        # Substring match (both directions, normalized)
        if len(us_norm) > 2 and (name_norm in us_norm or us_norm in name_norm):
            return True
    return False


def generate_interview_analysis(
    *,
    company: str,
    position: str,
    round_: str,
    content_summary: str,
    self_rating: str,
    profile_skills: list[str],
) -> str:
    """用 LLM 生成面试复盘分析，返回 JSON 字符串。"""
    try:
        from backend.llm import get_llm_client, get_model
        client = get_llm_client(timeout=30)
        model = get_model("fast")

        skill_str = ", ".join(profile_skills[:15]) if profile_skills else "未知"
        prompt = f"""你是职业规划教练，帮学生复盘真实面试经历。

面试信息：
- 公司：{company}
- 岗位：{position}
- 轮次：{round_}
- 面试内容：{content_summary}
- 自我评价：{self_rating}（good=发挥好/medium=一般/bad=发挥差）
- 用户技能：{skill_str}

请生成简洁的复盘分析，返回 JSON：
{{
  "strengths": ["做得好的地方（1-2条）"],
  "weaknesses": ["暴露的不足（1-2条）"],
  "action_items": ["下一步建议（1-2条）"],
  "overall": "一句话总结"
}}

直接返回 JSON，不要其他文字。"""

        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=400,
        )
        text = resp.choices[0].message.content.strip()
        # Validate it's parseable
        json.loads(text)
        return text
    except Exception as e:
        logger.warning("Interview analysis generation failed: %s", e)
        return json.dumps({
            "strengths": [],
            "weaknesses": [],
            "action_items": ["继续练习，下次会更好"],
            "overall": "面试经历已记录，保持积累。"
        })



