"""简历解析与画像路由 — 只负责 HTTP 边界。

- 接收上传文件
- 校验文件大小和类型
- 调用 ProfileService
- 返回 response schema

不做：OCR 判断、ResumeSDK 调用、prompt 拼接、职业方向计算。
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.models import User
from backend2.core.security import get_current_user
from backend2.db.session import get_db
from backend2.schemas.profile import (
    ParseResumePreviewResponse,
    ProfileData,
    SaveProfileRequest,
    SaveProfileResponse,
)
from backend2.services.profile.service import (
    get_my_profile as _get_my_profile,
    parse_resume_preview,
    save_profile,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profiles", tags=["profiles"])

_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
_ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}
_ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


@router.post("/parse-preview", response_model=ParseResumePreviewResponse)
async def parse_preview(file: UploadFile = File(...)) -> ParseResumePreviewResponse:
    """上传简历文件，返回解析预览。"""
    # 文件大小校验
    content = await file.read()
    if len(content) > _MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="文件超过 10MB 限制")

    # 文件类型校验
    filename = file.filename or ""
    ext = filename.lower()[filename.rfind("."):]
    if ext not in _ALLOWED_EXTENSIONS and file.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"不支持的文件类型: {file.content_type or ext}。仅支持 PDF、DOCX、TXT、MD",
        )

    # 重置文件指针供 service 读取
    await file.seek(0)

    try:
        result = await parse_resume_preview(file)
        logger.info(
            "解析完成: %s, score=%d, skills=%d",
            filename,
            result.meta.quality_score,
            len(result.profile.skills),
        )
        return result
    except HTTPException:
        raise
    except Exception:
        logger.exception("解析简历失败: %s", filename)
        raise HTTPException(status_code=500, detail="解析失败，请稍后重试")


@router.post("", response_model=SaveProfileResponse)
def create_profile(
    request: SaveProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SaveProfileResponse:
    """保存用户确认后的画像。

    前端展示 parse-preview 结果后，用户可编辑或直接确认保存。
    本端点接收 raw_profile（原始解析）+ confirmed_profile（用户确认后）
    + document + parse_meta，写入数据库。
    """
    try:
        return save_profile(
            db=db,
            user_id=current_user.id,
            request=request,
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("保存画像失败: user_id=%d", current_user.id)
        raise HTTPException(status_code=500, detail="保存失败，请稍后重试")


@router.get("/me", response_model=ProfileData)
def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileData:
    """获取当前用户最新确认后的画像（v2 格式）。"""
    try:
        return _get_my_profile(db=db, user_id=current_user.id)
    except HTTPException:
        raise
    except Exception:
        logger.exception("读取画像失败: user_id=%d", current_user.id)
        raise HTTPException(status_code=500, detail="读取画像失败")
