"""LLMParser — 唯一语义解析器。

负责：字段提取、技能标准化、重复内容合并、无意义内容过滤。
不负责：岗位图谱映射、职位推荐、公司 tier 判断、研究/工程倾向推断。

JSON 解析稳定性：
- 清理 markdown code block 和 thinking/reasoning tag
- 检测截断 JSON
- 有限次数重试
- 最终经过 ProfileData.model_validate()
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass

from backend2.llm import llm_chat
from backend2.schemas.profile import ParseMeta, ProfileData, ResumeDocument
from backend2.services.profile.parser.prompts import (
    _RESUME_PARSE_PROMPT,
    _SKILLS_RETRY_PROMPT,
)

logger = logging.getLogger(__name__)
_MAX_RETRIES = 2

# 匹配 <think>...</think>、<thinking>...</thinking>、<reasoning>...</reasoning>
_THINKING_RE = re.compile(r"<(think|thinking|reasoning)>.*?</\1>", re.DOTALL | re.IGNORECASE)
# 匹配 markdown code fence
_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


@dataclass
class LLMParseResult:
    """LLM 解析结果，包含画像和解析元信息。"""

    profile: ProfileData
    meta: ParseMeta


def parse(document: ResumeDocument, evidence: dict | None = None) -> LLMParseResult | None:
    """解析 ResumeDocument，可选结合 evidence，返回 LLMParseResult。

    主解析失败或 skills 为空时，自动执行一次轻量 skill_retry。
    """
    result = _parse_main(document, evidence)
    if result is None:
        return None

    profile = result.profile
    meta = result.meta

    # 技能重试兜底
    if not profile.skills:
        logger.warning("主解析无技能，执行技能重试")
        skills = _retry_skills(document.raw_text)
        if skills:
            profile.skills = skills

    return LLMParseResult(profile=profile, meta=meta)


def _parse_main(document: ResumeDocument, evidence: dict | None = None) -> LLMParseResult | None:
    raw_text = document.raw_text
    if not raw_text.strip():
        logger.warning("文档 raw_text 为空，跳过 LLM 解析")
        return None

    # 截断到合理长度，保留头部信息密度最高的部分
    truncated = _smart_truncate(raw_text, max_chars=6000)
    evidence_str = _format_evidence(evidence) if evidence else ""

    prompt = _RESUME_PARSE_PROMPT.format(
        resume_text=truncated,
        evidence_section=evidence_str,
    )

    llm_model = os.getenv("LLM_MODEL", "qwen-plus")
    json_repaired = False

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            result = llm_chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                timeout=90,
            )
            if not result:
                logger.warning("LLM 返回空内容 (attempt %d)", attempt)
                continue

            parsed, was_repaired = _robust_json_parse(result)
            if was_repaired:
                json_repaired = True
            if not parsed:
                logger.warning("JSON 解析失败 (attempt %d)", attempt)
                continue

            profile = ProfileData.model_validate(parsed)
            logger.info(
                "LLM 解析成功 (attempt %d): name=%r skills=%d projects=%d internships=%d",
                attempt,
                profile.name,
                len(profile.skills),
                len(profile.internships),
            )
            meta = ParseMeta(
                llm_model=llm_model,
                json_repaired=json_repaired,
                retry_count=attempt - 1,
            )
            return LLMParseResult(profile=profile, meta=meta)
        except Exception as e:
            logger.warning("LLM 解析异常 (attempt %d): %s", attempt, e)

    logger.error("LLM 解析在 %d 次尝试后均失败", _MAX_RETRIES)
    return None


def _retry_skills(raw_text: str) -> list:
    """轻量技能重试：只提取技能列表。"""
    truncated = _smart_truncate(raw_text, max_chars=3000)
    prompt = _SKILLS_RETRY_PROMPT.format(resume_text=truncated)

    try:
        result = llm_chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            timeout=60,
        )
        parsed, _ = _robust_json_parse(result)
        if parsed and isinstance(parsed, dict):
            skills = parsed.get("skills", [])
            if skills:
                logger.info("技能重试成功，提取 %d 个技能", len(skills))
            return skills
    except Exception as e:
        logger.warning("技能重试失败: %s", e)
    return []


def _robust_json_parse(text: str) -> tuple[dict | None, bool]:
    """从 LLM 响应中稳定提取 JSON 对象。

    处理：thinking tag、markdown fence、截断检测、首尾定位。

    Returns:
        (parsed_dict, json_repaired): 解析后的字典，以及是否通过截断修复成功。
    """
    if not text:
        return None, False

    # 1. 去除 thinking tag
    cleaned = _THINKING_RE.sub("", text)

    # 2. 尝试去除 markdown code block
    fence_match = _FENCE_RE.search(cleaned)
    candidate = fence_match.group(1).strip() if fence_match else cleaned.strip()

    # 3. 直接解析
    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed, False
    except json.JSONDecodeError:
        pass

    # 4. 定位首尾花括号再试
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            parsed = json.loads(candidate[start : end + 1])
            if isinstance(parsed, dict):
                return parsed, False
        except json.JSONDecodeError:
            pass

    # 5. 截断检测与修复：如果末尾明显被截断，尝试补全
    if _looks_truncated(candidate):
        logger.warning("JSON 疑似被截断，尝试修复")
        fixed = _try_fix_truncated_json(candidate)
        if fixed:
            try:
                parsed = json.loads(fixed)
                if isinstance(parsed, dict):
                    return parsed, True
            except json.JSONDecodeError:
                pass

    logger.warning("robust_json_parse: 无法提取有效 JSON（长度=%d）", len(text))
    return None, False


def _looks_truncated(text: str) -> bool:
    """启发式检测 JSON 是否被截断。"""
    text = text.strip()
    if not text:
        return False
    # 以未闭合的字符串、对象、数组结尾
    if text.endswith('"') or text.endswith(":") or text.endswith(","):
        return True
    open_braces = text.count("{") - text.count("}")
    open_brackets = text.count("[") - text.count("]")
    if open_braces > 0 or open_brackets > 0:
        return True
    return False


def _try_fix_truncated_json(text: str) -> str | None:
    """对截断 JSON 做极简修复尝试。"""
    text = text.strip()
    # 补全缺失的闭合括号
    open_braces = text.count("{") - text.count("}")
    open_brackets = text.count("[") - text.count("]")
    fixed = text
    if open_brackets > 0:
        fixed += "]" * open_brackets
    if open_braces > 0:
        fixed += "}" * open_braces
    # 如果最后一个值是未闭合字符串，尝试闭合
    if fixed.rstrip().endswith('"'):
        fixed = fixed.rstrip() + '"'
    return fixed


def _smart_truncate(text: str, max_chars: int) -> str:
    """保留头部，超出部分从末尾截断。"""
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


def _format_evidence(evidence: dict | None) -> str:
    """将证据字典格式化为 prompt 中的参考文本。"""
    if not evidence:
        return ""
    import json

    try:
        ev_json = json.dumps(evidence, ensure_ascii=False, default=str)[:4000]
    except Exception:
        return ""
    return (
        "\n\n【参考证据】以下是一家第三方简历解析服务（ResumeSDK）的原始输出，"
        "供你参考校对自己的提取结果。如果与简历原文冲突，以简历原文为准。\n"
        f"{ev_json}"
    )
