"""ResumeSDK API client — raw HTTP only, zero business logic."""
from __future__ import annotations

import base64
import json
import logging

import requests

from backend.config import (
    RESUMESDK_APPCODE,
    RESUMESDK_ENABLED,
    RESUMESDK_PWD,
    RESUMESDK_UID,
    RESUMESDK_BASE_URL,
)

logger = logging.getLogger(__name__)
_TIMEOUT = 60


def _is_aliyun_market() -> bool:
    return "alicloudapi.com" in RESUMESDK_BASE_URL or "apigw" in RESUMESDK_BASE_URL


def call_resumesdk(file_content: bytes, filename: str) -> dict | None:
    """Call ResumeSDK API and return the raw 'result' dict.

    No field mapping, no quality gate, no filtering — just HTTP.
    Returns None if the API is disabled, unconfigured, or errors out.
    """
    logger.info("ResumeSDK call: enabled=%s base_url=%s", RESUMESDK_ENABLED, RESUMESDK_BASE_URL)
    if not RESUMESDK_ENABLED:
        logger.info("ResumeSDK disabled via config")
        return None

    if not RESUMESDK_APPCODE and not (RESUMESDK_UID and RESUMESDK_PWD):
        logger.warning("ResumeSDK enabled but no credentials configured")
        return None

    b64_cont = base64.b64encode(file_content).decode("ascii")

    if _is_aliyun_market():
        return _call_aliyun(b64_cont, filename)
    return _call_saas(b64_cont, filename)


def _call_aliyun(b64_cont: str, filename: str) -> dict | None:
    if not RESUMESDK_APPCODE:
        logger.warning("Alibaba Cloud Market requires APPCODE")
        return None

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
    logger.info("ResumeSDK (Aliyun) request: file_name=%s file_cont_len=%d", filename, len(b64_cont))

    try:
        resp = requests.post(RESUMESDK_BASE_URL, headers=headers, json=payload, timeout=_TIMEOUT)
        logger.info("ResumeSDK (Aliyun) HTTP status=%s", resp.status_code)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.Timeout:
        logger.warning("ResumeSDK (Aliyun) timed out after %ds", _TIMEOUT)
        return None
    except requests.exceptions.RequestException as e:
        resp_text = getattr(e.response, "text", "")[:500] if hasattr(e, "response") and e.response else ""
        logger.warning("ResumeSDK (Aliyun) request failed: %s | resp=%s", e, resp_text)
        return None
    except json.JSONDecodeError as e:
        logger.warning("ResumeSDK (Aliyun) invalid JSON: %s", e)
        return None

    return _extract_result(data)


def _call_saas(b64_cont: str, filename: str) -> dict | None:
    headers = {"Content-Type": "application/json"}
    if RESUMESDK_UID and RESUMESDK_PWD:
        headers["uid"] = RESUMESDK_UID
        headers["pwd"] = RESUMESDK_PWD
    elif RESUMESDK_APPCODE:
        headers["Authorization"] = f"APPCODE {RESUMESDK_APPCODE}"

    payload = {"file_name": filename, "file_cont": b64_cont, "need_avatar": 0}

    try:
        resp = requests.post(RESUMESDK_BASE_URL, headers=headers, json=payload, timeout=_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.Timeout:
        logger.warning("ResumeSDK (SaaS) timed out after %ds", _TIMEOUT)
        return None
    except requests.exceptions.RequestException as e:
        logger.warning("ResumeSDK (SaaS) request failed: %s", e)
        return None
    except json.JSONDecodeError as e:
        logger.warning("ResumeSDK (SaaS) invalid JSON: %s", e)
        return None

    return _extract_result(data)


def _extract_result(data: dict) -> dict | None:
    """Extract 'result' from ResumeSDK response, logging status."""
    status = data.get("status", {})
    code = status.get("code")
    logger.info("ResumeSDK status code=%s message=%s", code, status.get("message"))

    if code != 200:
        logger.warning("ResumeSDK error: code=%s message=%s", code, status.get("message"))
        return None

    result = data.get("result")
    if result and isinstance(result, dict):
        logger.info("ResumeSDK result keys=%s has_skills=%s",
                    list(result.keys()), bool(result.get("skills")))
    return result if isinstance(result, dict) else None
