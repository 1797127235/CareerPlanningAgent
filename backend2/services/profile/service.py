"""ProfileService — 简历解析与画像保存业务入口。"""
from __future__ import annotations

import hashlib
import json
import logging

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session
from backend.models.profile import Profile, ProfileParse
from backend2.schemas.profile import (
    ParseResumePreviewResponse,
    ProfileData,
    ProfileDataPatch,
    ResumeFile,
    SaveProfileRequest,
    SaveProfileResponse,
)
from backend2.services.profile.parser.evidence import resumesdk
from backend2.services.profile.parser.pipeline import ParserPipeline


logger = logging.getLogger(__name__)

# 单例管线，可复用
_pipeline = ParserPipeline(evidence_collector=resumesdk.collect)

async def parse_resume_preview(file: UploadFile) -> ParseResumePreviewResponse:
    """解析上传的简历文件，返回预览响应。"""
    content = await file.read()
    resume_file = ResumeFile(
        filename=file.filename or "unknown",
        content_type=file.content_type,
        file_bytes=content,
        file_hash=hashlib.sha256(content).hexdigest(),
    )
    logger.info("解析简历: %s (%d bytes)", resume_file.filename, len(content))
    return _pipeline.parse(resume_file)

def save_profile(
    db: Session,
    user_id: int,
    request: SaveProfileRequest,
) -> SaveProfileResponse:
    """保存用户确认后的画像。

    事务流程：
    1. 插入或更新 profiles（按 user_id）
    2. 插入一条 profile_parses 快照（区分 raw / confirmed）
    3. 回填 profiles.active_parse_id
    4. 自动计算 is_edited（raw != confirmed）
    """
    raw_profile = request.raw_profile
    confirmed_profile = request.confirmed_profile
    document = request.document
    parse_meta = request.parse_meta

    # 序列化各层 JSON
    raw_json = raw_profile.model_dump(mode="json")
    confirmed_json = confirmed_profile.model_dump(mode="json")
    document_json = document.model_dump(mode="json")
    meta_json = parse_meta.model_dump(mode="json")

    # 自动判断用户是否做过编辑
    is_edited = raw_json != confirmed_json

    # 用 confirmed_profile 重新计算 quality（覆盖 meta 里的 score）
    from backend2.services.profile.parser.quality import score_profile

    quality_meta = score_profile(confirmed_profile)
    meta_json["quality_score"] = quality_meta.quality_score
    meta_json["quality_checks"] = quality_meta.quality_checks

    # 事务开始
    try:
        # 1. 插入或更新 profiles
        profile = db.query(Profile).filter(
            Profile.user_id == user_id
        ).first()

        if profile is None:
            profile = Profile(
                user_id=user_id,
                name=confirmed_profile.name or "",
                profile_json=json.dumps(confirmed_json, ensure_ascii=False),
                quality_json=json.dumps(meta_json, ensure_ascii=False),
                source="resume",
            )
            db.add(profile)
            db.flush()  # 拿到 profile.id
        else:
            profile.name = confirmed_profile.name or profile.name
            profile.profile_json = json.dumps(confirmed_json, ensure_ascii=False)
            profile.quality_json = json.dumps(meta_json, ensure_ascii=False)
            profile.source = "resume"
            db.flush()

        # 2. 插入 profile_parses（保留原始解析快照）
        parse_snapshot = ProfileParse(
            profile_id=profile.id,
            file_hash=document.file_hash or "",
            raw_profile_json=json.dumps(raw_json, ensure_ascii=False),
            confirmed_profile_json=json.dumps(confirmed_json, ensure_ascii=False),
            document_json=json.dumps(document_json, ensure_ascii=False),
            meta_json=json.dumps(meta_json, ensure_ascii=False),
        )
        db.add(parse_snapshot)
        db.flush()

        # 3. 回填 active_parse_id + is_edited
        profile.active_parse_id = parse_snapshot.id
        profile.is_edited = is_edited

        db.commit()
        db.refresh(profile)
        db.refresh(parse_snapshot)

        # Demo: trigger v1 recommendation generation in background
        # so profile page can show directions immediately after upload.
        try:
            import threading
            from backend.db import SessionLocal
            from backend.services.graph.locator import _auto_locate_on_graph

            profile_data_for_v1 = json.loads(profile.profile_json or "{}")
            if "job_target_text" in profile_data_for_v1 and "job_target" not in profile_data_for_v1:
                profile_data_for_v1["job_target"] = profile_data_for_v1.pop("job_target_text")

            def _bg_locate():
                db_bg = SessionLocal()
                try:
                    _auto_locate_on_graph(profile.id, user_id, profile_data_for_v1, db_bg)
                except Exception:
                    logger.exception("后台推荐生成失败")
                finally:
                    db_bg.close()

            threading.Thread(target=_bg_locate, daemon=True).start()
        except Exception:
            logger.exception("启动后台推荐生成失败")

        logger.info(
            "画像保存成功: user_id=%d, profile_id=%d, parse_id=%d, edited=%s",
            user_id, profile.id, parse_snapshot.id, is_edited,
        )

        return SaveProfileResponse(
            profile_id=profile.id,
            parse_id=parse_snapshot.id,
        )

    except Exception:
        db.rollback()
        logger.exception("画像保存失败: user_id=%d", user_id)
        raise

def get_my_profile(db: Session, user_id: int) -> ProfileData:
    """读取用户最新确认后的画像。

    优先从 active_parse 取 confirmed_profile_json（v2 原始格式），
    无快照时从 profiles.profile_json 降级返回。
    """
    from backend2.services.profile.resolver import resolve_profile_context

    profile_data, _profile_id, _parse_id = resolve_profile_context(db, user_id)
    return profile_data


def patch_profile_data(
    db: Session,
    user_id: int,
    patch: ProfileDataPatch,
) -> ProfileData:
    """局部更新用户画像，不生成新的 parse 快照。

    同时更新 profiles.profile_json 和当前 active_parse 的 confirmed_profile_json，
    因为 get_my_profile() 优先从 active_parse 读取。
    """
    from backend2.services.profile.resolver import resolve_profile_context
    from backend.models.profile import Profile, ProfileParse

    profile_data, profile_id, _parse_id = resolve_profile_context(db, user_id)
    if profile_id is None:
        raise HTTPException(status_code=404, detail="画像不存在")

    # 读取当前 JSON
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    current_json = json.loads(profile.profile_json or "{}")

    # 只覆盖请求中提供的字段
    patch_dict = patch.model_dump(exclude_unset=True, mode="json")
    current_json.update(patch_dict)

    updated_json = json.dumps(current_json, ensure_ascii=False)

    # 写回 profiles 主表
    profile.profile_json = updated_json

    # 同步更新当前 active_parse 的 confirmed_profile_json
    if profile.active_parse_id:
        parse_snapshot = db.query(ProfileParse).filter(
            ProfileParse.id == profile.active_parse_id
        ).first()
        if parse_snapshot:
            parse_snapshot.confirmed_profile_json = updated_json

    db.commit()
    db.refresh(profile)

    logger.info("画像局部更新: user_id=%d, fields=%s", user_id, list(patch_dict.keys()))
    return ProfileData.model_validate(current_json)
