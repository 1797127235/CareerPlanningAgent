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
from backend.services.profile.parser.text_extractor import extract_raw_text, is_scanned_pdf

logger = logging.getLogger(__name__)


def _is_insufficient(profile: ProfileData) -> bool:
    """Check if a parsed profile lacks critical semantic fields.

    Generic heuristics — no domain-specific keywords.
    """
    return (
        len(profile.projects) == 0
        or len(profile.skills) < 3
        or not profile.primary_domain
    )


def parse_resume_pipeline(file_content: bytes, filename: str) -> ProfileData:
    """Full pipeline: extract text → call ResumeSDK → LLM adapt → merge → return.

    Falls back to LLM direct text extraction if ResumeSDK fails or returns
    insufficient data.
    """
    # 1. Extract raw text
    raw_text = extract_raw_text(file_content, filename)
    scanned = is_scanned_pdf(file_content, filename, raw_text)
    logger.info("Pipeline start: filename=%s scanned=%s text_len=%d", filename, scanned, len(raw_text))

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
        sdk_profile = adapt_resumesdk_to_profile(rs_json, raw_text)
        if sdk_profile:
            sdk_profile.raw_text = raw_text[:6000]

    # 4. If SDK result is insufficient, also run LLM direct extraction
    llm_profile: ProfileData | None = None
    if not sdk_profile or _is_insufficient(sdk_profile):
        logger.info("SDK result insufficient, running LLM direct extraction")
        from backend.routers._profiles_parsing import _extract_profile_with_llm
        raw_profile = _extract_profile_with_llm(raw_text)
        if raw_profile:
            try:
                llm_profile = ProfileData.model_validate(raw_profile)
                llm_profile.raw_text = raw_text[:6000]
            except Exception as e:
                logger.warning("LLM direct extraction schema validation failed: %s", e)

    # 5. Merge
    if sdk_profile and llm_profile:
        return merge_profiles(sdk_profile, llm_profile)
    if sdk_profile:
        return sdk_profile
    if llm_profile:
        return llm_profile

    # Total failure — return empty profile with raw_text for manual review
    logger.error("All parsers failed for %s", filename)
    return ProfileData(raw_text=raw_text[:6000])
