"""Resume parsing pipeline — unified entry point.

Usage:
    from backend.services.profile.parser import parse_resume_pipeline
    profile_data = parse_resume_pipeline(file_content, filename)
"""
from __future__ import annotations

import logging

from backend.services.profile.parser.llm_adapter import adapt_resumesdk_to_profile
from backend.services.profile.parser.merger import merge_profiles
from backend.services.profile.parser.resumesdk_client import call_resumesdk
from backend.services.profile.parser.schema import ProfileData
from backend.services.profile.parser.skill_normalizer import apply_to_profile
from backend.services.profile.parser.text_extractor import extract_raw_text, is_scanned_pdf

logger = logging.getLogger(__name__)


def _extract_job_target_regex(raw_text: str) -> str:
    """Fast regex pre-extraction of job_target from raw resume text.

    Runs before LLM parsing so we have a deterministic fallback / hint.
    """
    import re as _re
    if not raw_text:
        return ""
    patterns = [
        r'(?:求职意向|期望职位|求职目标|意向岗位|期望岗位|目标职位|应聘职位)\s*[：:]\s*([^\n\r]{1,40})',
        r'(?:求职意向|期望职位|求职目标|意向岗位|期望岗位|目标职位|应聘职位)\s+([^\n\r]{1,40})',
        r'(?:期望从事|应聘|求职|目标)\s*[：:]\s*([^\n\r]{1,40})',
    ]
    for pat in patterns:
        m = _re.search(pat, raw_text, _re.IGNORECASE)
        if m:
            jt = m.group(1).strip()
            jt = _re.sub(r'[\s,，;.；。]+$', '', jt)
            if jt and jt not in {"面议", "不限", "待定", "无", "—", "-", "/"}:
                return jt
    return ""


def _is_insufficient(profile: ProfileData) -> bool:
    """Check if a parsed profile lacks critical semantic fields.

    Generic heuristics — no domain-specific keywords.
    """
    return (
        len(profile.projects) == 0
        or len(profile.skills) < 3
        or not profile.primary_domain
    )


def parse_resume_pipeline(file_content: bytes, filename: str, hint_job_target: str = "") -> ProfileData:
    """Full pipeline: extract text → call ResumeSDK → LLM adapt → merge → return.

    Falls back to LLM direct text extraction if ResumeSDK fails or returns
    insufficient data.
    """
    # 1. Extract raw text
    raw_text = extract_raw_text(file_content, filename)
    scanned = is_scanned_pdf(file_content, filename, raw_text)
    logger.info("Pipeline start: filename=%s scanned=%s text_len=%d", filename, scanned, len(raw_text))

    # 1b. Regex pre-extraction of job_target — deterministic fallback
    if hint_job_target:
        regex_job_target = hint_job_target
        logger.info("Using external hint_job_target: %r", hint_job_target)
    else:
        regex_job_target = _extract_job_target_regex(raw_text)
        if regex_job_target:
            logger.info("Regex job_target pre-extraction: %r", regex_job_target)

    if scanned:
        logger.info("Scanned PDF detected, using OCR+LLM pipeline")
        # Scanned PDF: skip ResumeSDK (unreliable), go straight to LLM
        # Note: OCR is handled upstream in profiles.py for scanned PDFs
        return ProfileData(raw_text=raw_text)

    # 2. Call ResumeSDK (raw API, no mapping)
    rs_json = call_resumesdk(file_content, filename)

    # 3. LLM adapt ResumeSDK raw JSON → standard profile
    sdk_profile: ProfileData | None = None
    if rs_json:
        sdk_profile = adapt_resumesdk_to_profile(rs_json, raw_text, regex_job_target)
        if sdk_profile:
            sdk_profile.raw_text = raw_text[:6000]
            if not sdk_profile.job_target and regex_job_target:
                sdk_profile.job_target = regex_job_target
                logger.info("Applied regex job_target to SDK profile: %r", regex_job_target)

    # 4. If SDK result is insufficient, also run LLM direct extraction
    llm_profile: ProfileData | None = None
    if not sdk_profile or _is_insufficient(sdk_profile):
        logger.info("SDK result insufficient, running LLM direct extraction")
        from backend.services.profile.parser.llm import _extract_profile_with_llm
        raw_profile = _extract_profile_with_llm(raw_text, hint_job_target=regex_job_target)
        if raw_profile:
            try:
                llm_profile = ProfileData.model_validate(raw_profile)
                llm_profile.raw_text = raw_text[:6000]
                if not llm_profile.job_target and regex_job_target:
                    llm_profile.job_target = regex_job_target
                    logger.info("Applied regex job_target to LLM profile: %r", regex_job_target)
            except Exception as e:
                logger.warning("LLM direct extraction schema validation failed: %s", e)

    # 5. Merge
    if sdk_profile and llm_profile:
        result = merge_profiles(sdk_profile, llm_profile)
    elif sdk_profile:
        result = sdk_profile
    elif llm_profile:
        result = llm_profile
    else:
        # Total failure — return empty profile with raw_text for manual review
        logger.error("All parsers failed for %s", filename)
        return ProfileData(raw_text=raw_text[:6000])

    # 5b. Final fallback: if merged profile still has no job_target, use regex result
    if not result.job_target and regex_job_target:
        result.job_target = regex_job_target
        logger.info("Applied regex job_target to merged profile: %r", regex_job_target)

    # 6. Normalize skill granularity (fold C++11→C++, Vector→STL, etc.)
    apply_to_profile(result)
    return result
