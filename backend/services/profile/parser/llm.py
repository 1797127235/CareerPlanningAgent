"""LLM-based structured profile extraction from resume text."""
from __future__ import annotations

import json
import logging

from backend.llm import get_model, llm_chat, parse_json_response
from backend.prompts.resume_parse import _RESUME_PARSE_PROMPT
from backend.services.profile.parser.normalize import _normalize_skills
from backend.services.profile.parser.postprocess import _postprocess_profile
from backend.services.profile.parser.text import _smart_truncate_resume, _supplement_missing_fields

logger = logging.getLogger(__name__)

_SKILLS_RETRY_PROMPT = """从以下简历文本中只提取技能列表，返回严格 JSON，不要其他文字：
{{"skills": [{{"name": "技能名（英文或通用短名）", "level": "familiar"}}]}}

词表仅供参考，不在词表中的技能也必须提取，使用行业通用名称：
{skill_vocab}

简历：{resume_text}"""

def _extract_profile_with_llm(raw_text: str, hint_job_target: str = "") -> dict:
    try:
        from backend.llm import llm_chat, parse_json_response
        from backend.services.graph.skills import _build_skill_vocab
        skill_vocab = _build_skill_vocab()

        # Smart truncation: preserve key sections, drop fluff
        truncated = _smart_truncate_resume(raw_text, max_chars=4000)

        hint_line = ""
        if hint_job_target:
            hint_line = f'预处理提示：原始文本中疑似包含求职意向「{hint_job_target}」，请重点核对，但不要盲从——如果简历中该词出现在项目经历/实习经历中而非"求职意向"板块，则不要采信。'

        prompt = _RESUME_PARSE_PROMPT.format(
            resume_text=truncated,
            skill_vocab=skill_vocab,
            hint_job_target_line=hint_line,
        )
        result = llm_chat([{"role": "user", "content": prompt}], temperature=0)
        parsed = parse_json_response(result)

        # Retry: if primary parse failed or returned no skills, do a focused skills-only call
        if not parsed or not parsed.get("skills"):
            logger.warning("_extract_profile_with_llm: primary parse returned no skills, retrying")
            retry_prompt = _SKILLS_RETRY_PROMPT.format(
                skill_vocab=skill_vocab,
                resume_text=raw_text[:2500],
            )
            retry_result = llm_chat([{"role": "user", "content": retry_prompt}], temperature=0)
            retry_parsed = parse_json_response(retry_result)
            if retry_parsed and retry_parsed.get("skills"):
                if not parsed:
                    parsed = {}
                parsed["skills"] = retry_parsed["skills"]

        if not parsed:
            parsed = {}
        # Normalize skill names using alias map
        parsed["skills"] = _normalize_skills(parsed.get("skills", []))
        parsed.setdefault("knowledge_areas", [])
        parsed.setdefault("experience_years", 0)
        parsed.setdefault("projects", [])
        parsed.setdefault("awards", [])
        parsed.setdefault("internships", [])
        parsed.setdefault("certificates", [])

        # Supplement missing fields with focused per-field extraction
        parsed = _supplement_missing_fields(parsed, raw_text)

        parsed = _postprocess_profile(parsed)
        parsed["raw_text"] = raw_text[:6000]
        parsed["soft_skills"] = {
            "_version": 2,
            "communication": None,
            "learning": None,
            "collaboration": None,
            "innovation": None,
            "resilience": None,
        }
        return parsed
    except Exception as e:
        logger.exception("_extract_profile_with_llm failed: %s", e)
        return {
            "skills": [],
            "knowledge_areas": [],
            "experience_years": 0,
            "raw_text": raw_text[:6000],
            "projects": [],
            "internships": [],
            "certificates": [],
            "awards": [],
            "education": {},
            "job_target": "",
            "soft_skills": {},
            "career_signals": {},
            "primary_domain": "",
        }