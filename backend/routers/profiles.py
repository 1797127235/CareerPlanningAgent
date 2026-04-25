"""Profiles router — single-profile system.

Each user has exactly one Profile. Multiple resume uploads are incremental
additions that merge into the same profile (union skills, take higher level).
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, UploadFile, File
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.db import get_db
from backend.models import Profile, User
from backend.services.graph.locator import _auto_locate_on_graph
from backend.routers._profiles_helpers import (
    _get_or_create_profile,
    _load_profile_json,
    _profile_to_dict,
    _merge_profiles,
    _execute_profile_reset,
)
from backend.services.profile.parser.llm import _extract_profile_with_llm
from backend.services.profile.parser.postprocess import _lazy_fix_misclassified_internships
from backend.services.profile.parser.vlm import _ocr_pdf_with_vl

from backend.services.profile import ProfileService
from backend.utils import ok

logger = logging.getLogger(__name__)


router = APIRouter()


# ── GET /profiles — return single profile ───────────────────────────────────

@router.get("")
@router.get("/")
def get_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return the current user's profile. Auto-creates an empty one if none exists."""
    profile = _get_or_create_profile(user.id, db)

    # Lazy migration: fix any internships that were misclassified in older extractions
    _lazy_fix_misclassified_internships(profile, db)

    return ok(_profile_to_dict(profile, db, user.id))


# ── POST /profiles/parse-resume — parse only, don't save ────────────────────

@router.post("/parse-resume")
async def parse_resume(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Parse resume file and return structured data for preview.

    Does NOT save to DB — call PUT /profiles to merge the result.
    """
    # ── File validation ───────────────────────────────────────────────
    _MAX_SIZE = 10 * 1024 * 1024  # 10 MB
    _ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt"}
    _ALLOWED_MIMES = {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
    }

    # Peek at first 10 MB, reject the rest
    content = await file.read(_MAX_SIZE + 1)
    if len(content) > _MAX_SIZE:
        raise HTTPException(413, "文件过大，请上传 10MB 以内的简历文件")

    filename = (file.filename or "resume.txt").strip()
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"不支持的文件格式 {ext!r}，请上传 PDF、Word 或 TXT 格式的简历")

    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type and content_type not in _ALLOWED_MIMES and content_type != "application/octet-stream":
        raise HTTPException(400, "文件类型不符，请上传简历文档")

    # ── Extract raw text ───────────────────────────────────────────────────
    from backend.services.profile.parser.text_extractor import extract_raw_text, is_scanned_pdf
    raw_text = extract_raw_text(content, filename)
    scanned = is_scanned_pdf(content, filename, raw_text)
    logger.info("Resume parser strategy: filename=%s scanned=%s text_len=%d", filename, scanned, len(raw_text))

    # Pre-extract job_target via regex — works for both scanned and text-based PDFs
    from backend.services.profile.parser import _extract_job_target_regex
    hint_jt = _extract_job_target_regex(raw_text)

    profile_data: dict | None = None

    if scanned:
        # Scanned PDF: OCR → LLM direct extraction
        logger.info("Scanned PDF detected, using OCR+LLM pipeline")
        raw_text = _ocr_pdf_with_vl(content)
        if not raw_text.strip():
            raise HTTPException(400, "无法提取简历文本，请使用文字版 PDF 或直接粘贴简历文本")
        # OCR text may have different extraction quality; try regex again
        ocr_jt = _extract_job_target_regex(raw_text)
        if ocr_jt and not hint_jt:
            hint_jt = ocr_jt
            logger.info("Regex job_target found in OCR text: %r", hint_jt)
        profile_data = _extract_profile_with_llm(raw_text, hint_job_target=hint_jt)
    else:
        # Text-based: use new parser pipeline (ResumeSDK + LLM adapter + merger)
        from backend.services.profile.parser import parse_resume_pipeline
        parsed = parse_resume_pipeline(content, filename, hint_job_target=hint_jt)
        profile_data = parsed.to_dict()

    logger.info(
        "[PARSE-RESUME] job_target=%r skills=%d projects=%d raw_text_len=%d",
        profile_data.get("job_target", ""),
        len(profile_data.get("skills", [])),
        len(profile_data.get("projects", [])),
        len(profile_data.get("raw_text", "")),
    )

    quality_data = ProfileService.compute_quality(profile_data)
    return ok({"profile": profile_data, "quality": quality_data})


# ── PUT /profiles — create-or-merge profile ──────────────────────────────────

class UpdateProfileRequest(BaseModel):
    profile: dict | None = None
    quality: dict | None = None
    # False (default) = replace existing profile_json with incoming.
    # True = union with existing (skills/projects/awards/certificates/internships).
    # Resume uploads must pass True explicitly and only after the user picked
    # "补充" in the frontend confirm dialog; default is replace so re-uploading
    # a different resume doesn't silently stack two careers' projects together.
    merge: bool = False

    model_config = {"extra": "ignore"}


@router.put("")
@router.put("/")
def update_profile(
    req: UpdateProfileRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create-or-update the user's single profile.

    If merge=True (default), incoming skills/knowledge_areas/projects/awards
    are merged with existing data. If merge=False, existing data is replaced.
    """
    profile = _get_or_create_profile(user.id, db)

    if req.profile is not None:
        existing = _load_profile_json(profile)
        if req.merge:
            merged = _merge_profiles(existing, req.profile)
        else:
            merged = req.profile

        # Defensive: always preserve raw_text — it's the only way to re-parse later.
        # If the incoming profile lacks it (frontend bug / old code), keep existing.
        if not merged.get("raw_text") and existing.get("raw_text"):
            merged["raw_text"] = existing["raw_text"]
            logger.info("Preserved existing raw_text (%d chars) during profile update", len(existing["raw_text"]))

        profile.profile_json = json.dumps(merged, ensure_ascii=False, default=str)
        # Sync name to DB column only when source is NOT 'resume' (user confirmed)
        # During resume upload, name goes into profile_json but DB column stays null
        source = (req.profile or {}).get("source", "")
        if source != "resume" and merged.get("name") and not profile.name:
            profile.name = str(merged["name"]).strip()
        quality_data = ProfileService.compute_quality(merged)
        profile.quality_json = json.dumps(quality_data, ensure_ascii=False, default=str)

        logger.info(
            "[UPDATE-PROFILE] job_target=%r source=%r merge=%s",
            merged.get("job_target", ""),
            (merged or {}).get("source", ""),
            req.merge,
        )

        # Graph location runs in background — don't block the response
        _final_snapshot = json.loads(json.dumps(merged, default=str))
        background_tasks.add_task(_auto_locate_bg, profile.id, user.id, _final_snapshot)

    if req.quality is not None:
        profile.quality_json = json.dumps(req.quality, ensure_ascii=False, default=str)

    db.commit()
    db.refresh(profile)

    return ok(_profile_to_dict(profile, db, user.id), message="画像已更新")


# ── POST /profiles/reparse — re-run LLM on stored raw_text ──────────────────

@router.post("/reparse")
def reparse_profile(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Re-run LLM extraction on stored raw_text and update the profile."""
    profile = _get_or_create_profile(user.id, db)
    existing = _load_profile_json(profile)
    raw_text = existing.get("raw_text") or existing.get("markdown", "")
    if not raw_text.strip():
        raise HTTPException(400, "没有原始简历文本，请重新上传简历")

    profile_data = _extract_profile_with_llm(raw_text)
    quality_data = ProfileService.compute_quality(profile_data)

    profile.profile_json = json.dumps(profile_data, ensure_ascii=False, default=str)
    profile.quality_json = json.dumps(quality_data, ensure_ascii=False, default=str)
    db.commit()
    db.refresh(profile)

    graph_position = _auto_locate_on_graph(profile.id, user.id, profile_data, db)
    result = _profile_to_dict(profile, db, user.id)
    if graph_position:
        result["graph_position"] = graph_position
    return ok(result, message="重新解析完成")


# ── PATCH /profiles/name — lightweight name update ────────────────────────────

class SetNameRequest(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def _strip_and_check(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("姓名不能为空")
        return v


@router.patch("/name")
def set_profile_name(
    req: SetNameRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Set the profile display name. Lightweight — no LLM calls."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        raise HTTPException(404, "画像不存在")
    profile.name = req.name
    db.commit()
    return ok(message="姓名已更新")


# ── PATCH /profiles/preferences — save career preferences ────────────────────

class PreferencesRequest(BaseModel):
    work_style: str = ""      # tech / product / data / management
    value_priority: str = ""  # growth / stability / balance / innovation
    work_intensity: str = ""  # high / moderate / low
    company_type: str = ""    # big_tech / growing / startup / state_owned
    ai_attitude: str = ""     # do_ai / avoid_ai / no_preference
    current_stage: str = ""   # lost / know_gap / ready / not_started


@router.patch("/preferences")
def set_preferences(
    req: PreferencesRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save career preferences into profile_json.preferences field."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        raise HTTPException(404, "画像不存在")

    profile_data = _load_profile_json(profile)
    dumped = req.model_dump(exclude_none=True)
    profile_data["preferences"] = {k: v for k, v in dumped.items() if v != ""}
    profile.profile_json = json.dumps(profile_data, ensure_ascii=False, default=str)
    db.commit()
    return ok(message="就业意愿已保存")


# ── DELETE /profiles — reset profile data ────────────────────────────────────

@router.delete("")
@router.delete("/")
def reset_profile(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reset the user's profile and wipe all profile-derived artifacts."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        return ok(message="画像已清空")
    _execute_profile_reset(user.id, profile, db)
    return ok(message="画像已重置")


