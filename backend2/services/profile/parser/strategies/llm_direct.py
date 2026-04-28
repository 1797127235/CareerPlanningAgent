"""LLM 直接解析策略。

直接从简历文本中通过单次 LLM 调用提取结构化画像。
包含技能重试兜底：当主解析未提取到技能时，单独发起一次技能提取请求。
"""
from __future__ import annotations

import logging

from backend2.llm import llm_chat, parse_json_response
from backend2.schemas.profile import ParseCandidate, ProfileData, ResumeDocument
from backend2.services.profile.parser.base import ParseStrategy
from backend2.services.profile.parser.prompts import (
    _RESUME_PARSE_PROMPT,
    _SKILLS_RETRY_PROMPT,
)

logger = logging.getLogger(__name__)


class LLMDirectStrategy(ParseStrategy):
    """通过 LLM 结构化提取直接解析简历文本。"""

    name = "llm_direct"

    def parse(self, document: ResumeDocument) -> ParseCandidate | None:
        profile = _extract_with_llm(document.raw_text)
        if not profile:
            return None

        # 向后兼容：保留原始文本引用
        profile.raw_text = document.raw_text

        return ParseCandidate(
            source="llm_direct",
            profile=profile,
            confidence=0.6,
        )


def _extract_with_llm(raw_text: str) -> ProfileData | None:
    """执行主 LLM 提取，失败时尝试技能重试。"""
    try:
        truncated = _smart_truncate(raw_text, max_chars=4000)
        hint_line = _build_hint_line(raw_text)
        skill_vocab = _build_skill_vocab()

        prompt = _RESUME_PARSE_PROMPT.format(
            resume_text=truncated,
            skill_vocab=skill_vocab,
            hint_job_target_line=hint_line,
        )
        result = llm_chat([{"role": "user", "content": prompt}], temperature=0)
        parsed = parse_json_response(result)

        # 重试：主解析未返回技能时，做一次技能专项提取
        if not parsed or not parsed.get("skills"):
            logger.warning("LLM 主解析无技能，执行重试")
            retry_prompt = _SKILLS_RETRY_PROMPT.format(
                skill_vocab=skill_vocab,
                resume_text=raw_text[:2500],
            )
            retry_result = llm_chat(
                [{"role": "user", "content": retry_prompt}], temperature=0
            )
            retry_parsed = parse_json_response(retry_result)
            if retry_parsed and retry_parsed.get("skills"):
                if not parsed:
                    parsed = {}
                parsed["skills"] = retry_parsed["skills"]

        if not parsed:
            parsed = {}

        # 确保所有可选字段都有默认值
        parsed.setdefault("knowledge_areas", [])
        parsed.setdefault("experience_years", 0)
        parsed.setdefault("projects", [])
        parsed.setdefault("awards", [])
        parsed.setdefault("internships", [])
        parsed.setdefault("certificates", [])
        parsed.setdefault("career_signals", {})
        parsed.setdefault("soft_skills", {
            "_version": 2,
            "communication": None,
            "learning": None,
            "collaboration": None,
            "innovation": None,
            "resilience": None,
        })

        return ProfileData.model_validate(parsed)
    except Exception as e:
        logger.exception("LLM 直接提取失败: %s", e)
        return None


def _smart_truncate(text: str, max_chars: int = 4000) -> str:
    """保留原文头部，超出部分从末尾截断。"""
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


def _build_hint_line(raw_text: str) -> str:
    """从原文中预售求职意向线索，辅助 LLM 判断。"""
    import re

    patterns = [
        r"(?:求职意向|期望职位|求职目标|意向岗位|期望岗位|目标职位|应聘职位)\s*[：:]\s*([^\n\r]{1,40})",
        r"(?:求职意向|期望职位|求职目标|意向岗位|期望岗位|目标职位|应聘职位)\s+([^\n\r]{1,40})",
    ]
    for pat in patterns:
        m = re.search(pat, raw_text, re.IGNORECASE)
        if m:
            jt = m.group(1).strip()
            jt = re.sub(r"[\s,，;.；。]+$", "", jt)
            if jt and jt not in {"面议", "不限", "待定", "无", "—", "-", "/"}:
                return (
                    f"预处理提示：原始文本中疑似包含求职意向「{jt}」，"
                    "请重点核对，但不要盲从——如果该词出现在项目经历/实习经历中而非'求职意向'板块，则不要采信。"
                )
    return ""


def _build_skill_vocab() -> str:
    """返回技能词表字符串，用于 prompt 中的参考列表。"""
    # TODO: 后续从 backend2 图谱技能模块加载完整词表
    skills = [
        "Python", "C++", "Java", "JavaScript", "TypeScript", "Go", "Rust",
        "React", "Vue.js", "Next.js", "Node.js",
        "Spring Boot", "MyBatis",
        "PyTorch", "TensorFlow", "OpenCV", "CUDA",
        "PostgreSQL", "MySQL", "Redis", "MongoDB",
        "Docker", "Kubernetes", "Linux", "Git",
        "OpenAI API", "LangChain", "Vector DB",
        "Unity", "Unreal",
    ]
    return "、".join(skills)
