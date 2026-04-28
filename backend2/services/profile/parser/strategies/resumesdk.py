"""
ResumeSDK 解析策略。
调用 ResumeSDK 第三方 API，再通过 LLM adapter 将原始 ResumeSDK JSON
转换为标准 ProfileData。支持阿里云市场和 SaaS 两种接入方式。
"""
from __future__ import annotations

import base64
import json
import logging

from backend2.core.config import (
    RESUMESDK_APPCODE,
    RESUMESDK_ENABLED,
    RESUMESDK_PWD,
    RESUMESDK_UID,
    RESUMESDK_BASE_URL,
)
from backend2.llm import llm_chat, parse_json_response
from backend2.schemas.profile import ParseCandidate, ProfileData, ResumeDocument
from backend2.services.profile.parser.base import ParseStrategy
from backend2.services.profile.parser.prompts import _RESUMESDK_ADAPT_PROMPT

logger = logging.getLogger(__name__)
_TIMEOUT = 60
_ADAPT_MODEL = "qwen-plus"
_ADAPT_TIMEOUT = 45


class ResumeSDKStrategy(ParseStrategy):
    """通过 ResumeSDK API + LLM adapter 解析简历。"""

    name = "resumesdk"

    def parse(self, document: ResumeDocument) -> ParseCandidate | None:
        if not document.file_bytes:
            logger.warning("ResumeSDK 策略需要 file_bytes，但文档中没有")
            return None

        # 1. 调 ResumeSDK
        rs_json = _call_resumesdk(document.file_bytes, document.filename)
        if not rs_json:
            return None

        # 2. LLM adapter 转为标准 ProfileData
        profile = _adapt_resumesdk_to_profile(
            rs_json, document.raw_text, _extract_job_target_hint(document.raw_text)
        )
        if not profile:
            return None

        return ParseCandidate(
            source="resumesdk_llm_adapter",
            profile=profile,
            confidence=0.7,
            raw_output=rs_json,
        )


def _extract_job_target_hint(raw_text: str) -> str:
    """从简历原文中快速正则提取求职意向，作为 LLM 的辅助线索。"""
    import re

    if not raw_text:
        return ""
    patterns = [
        r"(?:求职意向|期望职位|求职目标|意向岗位|期望岗位|目标职位|应聘职位)\s*[：:]\s*([^\n\r]{1,40})",
        r"(?:求职意向|期望职位|求职目标|意向岗位|期望岗位|目标职位|应聘职位)\s+([^\n\r]{1,40})",
        r"(?:期望从事|应聘|求职|目标)\s*[：:]\s*([^\n\r]{1,40})",
    ]
    for pat in patterns:
        m = re.search(pat, raw_text, re.IGNORECASE)
        if m:
            jt = m.group(1).strip()
            jt = re.sub(r"[\s,，;.；。]+$", "", jt)
            if jt and jt not in {"面议", "不限", "待定", "无", "—", "-", "/"}:
                return jt
    return ""


def _call_resumesdk(file_content: bytes, filename: str) -> dict | None:
    """调用 ResumeSDK API，返回原始 'result' 字典。"""
    logger.info("ResumeSDK 调用: enabled=%s", RESUMESDK_ENABLED)
    if not RESUMESDK_ENABLED:
        return None
    if not RESUMESDK_APPCODE and not (RESUMESDK_UID and RESUMESDK_PWD):
        logger.warning("ResumeSDK 已启用但未配置凭证")
        return None

    b64_cont = base64.b64encode(file_content).decode("ascii")

    if _is_aliyun_market():
        return _call_aliyun(b64_cont, filename)
    return _call_saas(b64_cont, filename)


def _is_aliyun_market() -> bool:
    """是否为阿里云市场版本。"""
    return "alicloudapi.com" in RESUMESDK_BASE_URL or "apigw" in RESUMESDK_BASE_URL


def _call_aliyun(b64_cont: str, filename: str) -> dict | None:
    """阿里云市场版 ResumeSDK 调用。"""
    if not RESUMESDK_APPCODE:
        logger.warning("阿里云市场需要 APPCODE")
        return None

    import requests

    headers = {
        "Authorization": f"APPCODE {RESUMESDK_APPCODE}",
        "Content-Type": "application/json; charset=UTF-8",
    }
    payload = {
        "file_name": filename,
        "file_cont": b64_cont,
        "need_avatar": 0,
        "ocr_type": 1,
    }
    try:
        resp = requests.post(
            RESUMESDK_BASE_URL, headers=headers, json=payload, timeout=_TIMEOUT
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning("ResumeSDK（阿里云）请求失败: %s", e)
        return None

    return _extract_result(data)


def _call_saas(b64_cont: str, filename: str) -> dict | None:
    """SaaS 版 ResumeSDK 调用。"""
    import requests

    headers = {"Content-Type": "application/json"}
    if RESUMESDK_UID and RESUMESDK_PWD:
        headers["uid"] = RESUMESDK_UID
        headers["pwd"] = RESUMESDK_PWD
    elif RESUMESDK_APPCODE:
        headers["Authorization"] = f"APPCODE {RESUMESDK_APPCODE}"

    payload = {"file_name": filename, "file_cont": b64_cont, "need_avatar": 0}
    try:
        resp = requests.post(
            RESUMESDK_BASE_URL, headers=headers, json=payload, timeout=_TIMEOUT
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning("ResumeSDK（SaaS）请求失败: %s", e)
        return None

    return _extract_result(data)


def _extract_result(data: dict) -> dict | None:
    """从 ResumeSDK 响应中提取解析结果。"""
    status = data.get("status", {})
    code = status.get("code")
    if code != 200:
        logger.warning("ResumeSDK 错误: code=%s message=%s", code, status.get("message"))
        return None
    result = data.get("result")
    return result if isinstance(result, dict) else None


def _adapt_resumesdk_to_profile(
    rs_raw_json: dict, raw_text: str, hint_job_target: str = ""
) -> ProfileData | None:
    """用 LLM 将 ResumeSDK 原始 JSON + 简历原文转为标准 ProfileData。"""
    if not rs_raw_json:
        return None

    rs_json_str = json.dumps(rs_raw_json, ensure_ascii=False, default=str)[:8000]
    raw_text_truncated = raw_text[:4000]

    hint_line = ""
    if hint_job_target:
        hint_line = (
            f"- 预处理已从原始文本中提取到疑似求职意向：「{hint_job_target}」。"
            "请以此为主要参考，同时核对 ResumeSDK 的 expect_job 字段。"
            "如果两者冲突，以原始文本中的板块内容为准。"
        )

    prompt = _RESUMESDK_ADAPT_PROMPT.format(
        rs_json=rs_json_str,
        raw_text=raw_text_truncated,
        hint_job_target_line=hint_line,
    )

    try:
        result = llm_chat(
            messages=[{"role": "user", "content": prompt}],
            model=_ADAPT_MODEL,
            temperature=0,
            timeout=_ADAPT_TIMEOUT,
        )
        parsed = parse_json_response(result)
        if not parsed or not isinstance(parsed, dict):
            logger.warning("LLM adapter 返回非字典类型: %s", type(parsed).__name__)
            return None

        profile = ProfileData.model_validate(parsed)
        logger.info(
            "LLM adapter 成功: %d skills, %d projects, domain=%r",
            len(profile.skills),
            len(profile.projects),
            profile.primary_domain,
        )
        return profile
    except Exception as e:
        logger.warning("LLM adapter 失败: %s", e)
        return None
