"""ResumeSDK 证据提供者。

ResumeSDK 未配置或调用失败时不中断主流程，仅返回 None。
返回值作为证据进入 LLM prompt，不直接成为最终 ProfileData。
"""
from __future__ import annotations

import base64
import logging

from backend2.core.config import (
    RESUMESDK_APPCODE,
    RESUMESDK_BASE_URL,
    RESUMESDK_ENABLED,
    RESUMESDK_PWD,
    RESUMESDK_UID,
)
from backend2.schemas.profile import ResumeFile

logger = logging.getLogger(__name__)
_TIMEOUT = 60


def collect(file: ResumeFile) -> dict | None:
    """调用 ResumeSDK API，返回原始解析结果作为证据字典。

    失败时返回 None，不抛异常，不中断主流程。
    """
    if not RESUMESDK_ENABLED:
        return None
    if not RESUMESDK_APPCODE and not (RESUMESDK_UID and RESUMESDK_PWD):
        logger.warning("ResumeSDK 已启用但未配置凭证")
        return None

    b64_cont = base64.b64encode(file.file_bytes).decode("ascii")

    try:
        if _is_aliyun_market():
            result = _call_aliyun(b64_cont, file.filename)
        else:
            result = _call_saas(b64_cont, file.filename)
        if result:
            logger.info("ResumeSDK 证据收集成功: %s", file.filename)
        return result
    except Exception as e:
        logger.warning("ResumeSDK 证据收集失败: %s", e)
        return None


def _is_aliyun_market() -> bool:
    return "alicloudapi.com" in RESUMESDK_BASE_URL or "apigw" in RESUMESDK_BASE_URL


def _call_aliyun(b64_cont: str, filename: str) -> dict | None:
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
    status = data.get("status", {})
    code = status.get("code")
    if code != 200:
        logger.warning("ResumeSDK 错误: code=%s message=%s", code, status.get("message"))
        return None
    result = data.get("result")
    return result if isinstance(result, dict) else None
