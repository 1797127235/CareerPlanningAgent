"""Profiles router — single-profile system.

Each user has exactly one Profile. Multiple resume uploads are incremental
additions that merge into the same profile (union skills, take higher level).
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.db import get_db
from backend.db_models import Profile, User
from backend.routers._profiles_graph import _auto_locate_on_graph
from backend.routers._profiles_helpers import (
    _get_or_create_profile,
    _profile_to_dict,
    _merge_profiles,
    _execute_profile_reset,
)
from backend.routers._profiles_parsing import (
    _extract_profile_with_llm,
    _extract_profile_multimodal_vl,
    _ocr_pdf_with_vl,
    _lazy_fix_misclassified_internships,
)
from backend.routers._profiles_resumesdk import parse_with_resumesdk
from backend.routers._profiles_sjt import router as sjt_router
from backend.services.profile import ProfileService
from backend.utils import ok

logger = logging.getLogger(__name__)

router = APIRouter()
router.include_router(sjt_router)


class UpdateProjectDescBody(BaseModel):
    description: str


class RefineProjectBody(BaseModel):
    """基于 original_text 内容匹配来定位项目，避免数组下标漂移。"""
    original_text: str
    new_description: str


@router.patch("/me/projects/refine")
def refine_profile_project(
    body: RefineProjectBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """按原文内容匹配更新 profile_json.projects 中的某一条。

    相比下标定位，内容匹配不受学生增删/重排项目的影响；
    若匹配失败（例如学生已经手动改过），返回 409，让前端提示"档案已变动，请刷新"。
    """
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        raise HTTPException(404, "未找到画像")

    data = json.loads(profile.profile_json or "{}")
    projects = data.get("projects", [])
    target = body.original_text.strip()
    if not target:
        raise HTTPException(400, "original_text 不能为空")

    matched_idx = -1
    for i, p in enumerate(projects):
        if isinstance(p, str) and p.strip() == target:
            matched_idx = i
            break
        if isinstance(p, dict):
            desc = (p.get("description") or p.get("name") or "").strip()
            if desc == target:
                matched_idx = i
                break

    if matched_idx < 0:
        raise HTTPException(409, "档案已变动，未找到对应项目原文。请刷新后重试。")

    current = projects[matched_idx]
    if isinstance(current, str):
        projects[matched_idx] = body.new_description
    else:
        projects[matched_idx] = {**current, "description": body.new_description}

    data["projects"] = projects
    profile.profile_json = json.dumps(data, ensure_ascii=False)
    db.commit()
    return {"ok": True}


@router.patch("/me/projects/{proj_index}")
def update_profile_project(
    proj_index: int,
    body: UpdateProjectDescBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """[遗留] 按下标更新；新代码请用 PATCH /me/projects/refine（按内容匹配）。"""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        raise HTTPException(404, "未找到画像")

    data = json.loads(profile.profile_json or "{}")
    projects = data.get("projects", [])

    if proj_index < 0 or proj_index >= len(projects):
        raise HTTPException(400, "项目索引越界")

    current = projects[proj_index]
    if isinstance(current, str):
        projects[proj_index] = body.description
    elif isinstance(current, dict):
        projects[proj_index] = {**current, "description": body.description}

    data["projects"] = projects
    profile.profile_json = json.dumps(data, ensure_ascii=False)
    db.commit()

    return {"ok": True}


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

    # ── Extract text for self-hosted fallback ──────────────────────────────
    raw_text = ""
    if filename.lower().endswith(".pdf"):
        try:
            import pdfplumber
            import io
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                raw_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        except ImportError:
            raw_text = content.decode("utf-8", errors="ignore")
    elif filename.lower().endswith(".docx"):
        try:
            import docx
            import io
            doc = docx.Document(io.BytesIO(content))
            raw_text = "\n".join(p.text for p in doc.paragraphs if p.text)
        except ImportError:
            raw_text = content.decode("utf-8", errors="ignore")
    elif filename.lower().endswith(".doc"):
        # .doc is a binary format; third-party APIs handle the raw bytes.
        # Skip text extraction so the LLM fallback gets a clean signal.
        raw_text = ""
    else:
        raw_text = content.decode("utf-8", errors="ignore")

    is_scanned_pdf = not raw_text.strip() and filename.lower().endswith(".pdf")
    logger.info("Resume parser strategy: filename=%s is_scanned=%s raw_text_len=%d", filename, is_scanned_pdf, len(raw_text))

    # ── Strategy ──────────────────────────────────────────────────────────
    # 文字版PDF: ResumeSDK → 自研LLM (fallback)
    # 扫描版PDF: 直接 OCR → 自研LLM (第三方API对扫描版效果差且耗时长，跳过)
    profile_data: dict | None = None

    if is_scanned_pdf:
        logger.info("Scanned PDF detected, using OCR+LLM pipeline")
        raw_text = _ocr_pdf_with_vl(content)
        if not raw_text.strip():
            raise HTTPException(400, "无法提取简历文本，请使用文字版 PDF 或直接粘贴简历文本")
        profile_data = _extract_profile_with_llm(raw_text)
    else:
        # Text-based PDF / Word / TXT
        # 1. Try ResumeSDK (commercial parser)
        logger.info("Trying ResumeSDK first for text-based file")
        profile_data = parse_with_resumesdk(content, filename)

        # 2. Fallback: self-hosted LLM parsing
        if not profile_data:
            logger.info("ResumeSDK unavailable/failed, falling back to self-hosted parser")
            if not raw_text.strip():
                raise HTTPException(400, "无法提取简历文本，请使用文字版 PDF 或直接粘贴简历文本")
            profile_data = _extract_profile_with_llm(raw_text)

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
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create-or-update the user's single profile.

    If merge=True (default), incoming skills/knowledge_areas/projects/awards
    are merged with existing data. If merge=False, existing data is replaced.
    """
    profile = _get_or_create_profile(user.id, db)

    if req.profile is not None:
        if req.merge:
            existing = json.loads(profile.profile_json or "{}")
            merged = _merge_profiles(existing, req.profile)
        else:
            merged = req.profile

        profile.profile_json = json.dumps(merged, ensure_ascii=False, default=str)
        # Sync name to DB column only when source is NOT 'resume' (user confirmed)
        # During resume upload, name goes into profile_json but DB column stays null
        source = (req.profile or {}).get("source", "")
        if source != "resume" and merged.get("name") and not profile.name:
            profile.name = str(merged["name"]).strip()
        quality_data = ProfileService.compute_quality(merged)
        profile.quality_json = json.dumps(quality_data, ensure_ascii=False, default=str)

    if req.quality is not None:
        profile.quality_json = json.dumps(req.quality, ensure_ascii=False, default=str)

    db.commit()
    db.refresh(profile)

    # Graph location + growth event run in background threads — don't block the response
    if req.profile is not None:
        import threading as _threading
        from backend.db import SessionLocal as _SL
        _final = json.loads(profile.profile_json)
        _pid, _uid = profile.id, user.id
        _skill_count = len(_final.get("skills", []))
        _source = (_final or {}).get("source", "")

        def _locate_bg():
            _bg_db = _SL()
            try:
                _auto_locate_on_graph(_pid, _uid, _final, _bg_db)
            except Exception:
                logger.exception("Background graph location failed (profile %s)", _pid)
            finally:
                _bg_db.close()

        _threading.Thread(target=_locate_bg, daemon=True).start()

    return ok(_profile_to_dict(profile, db, user.id), message="画像已更新")


# ── POST /profiles/reparse — re-run LLM on stored raw_text ──────────────────

@router.post("/reparse")
def reparse_profile(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Re-run LLM extraction on stored raw_text and update the profile."""
    profile = _get_or_create_profile(user.id, db)
    existing = json.loads(profile.profile_json or "{}")
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
    profile.name = req.name.strip()
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

    profile_data = json.loads(profile.profile_json or "{}")
    profile_data["preferences"] = req.model_dump(exclude_none=True)
    profile.profile_json = json.dumps(profile_data, ensure_ascii=False)
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
