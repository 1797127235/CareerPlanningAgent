"""backend2/services/profile/resolver.py — 画像解析公共逻辑。

从 user_id 获取 ProfileData + profile_id + parse_id，供多个模块共用。
避免在 profile/service.py 和 opportunity/service.py 中重复相同的查询逻辑。
"""
from __future__ import annotations

import json
import logging

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend2.schemas.profile import ProfileData

logger = logging.getLogger(__name__)


def resolve_profile_context(
    db: Session, user_id: int
) -> tuple[ProfileData, int, int | None]:
    """Return ProfileData, profile_id, and parse_id in one query session.

    查询顺序：
    1. 从 profiles 表获取 profile_id 和 active_parse_id
    2. 优先从 profile_parses.confirmed_profile_json 获取 v2 格式画像
    3. 降级从 profiles.profile_json 获取画像

    Raises:
        HTTPException 404: 用户未创建画像
        HTTPException 500: 画像数据损坏
    """
    from backend.models import Profile, ProfileParse

    profile_row = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile_row:
        raise HTTPException(status_code=404, detail="用户未创建画像")

    profile_id = profile_row.id
    parse_id = profile_row.active_parse_id

    # 优先取 active_parse 的 confirmed_profile_json（v2 格式）
    if parse_id:
        parse_record = db.query(ProfileParse).filter(
            ProfileParse.id == parse_id
        ).first()
        if parse_record and parse_record.confirmed_profile_json:
            try:
                data = json.loads(parse_record.confirmed_profile_json)
                return ProfileData.model_validate(data), profile_id, parse_id
            except Exception:
                logger.warning(
                    "confirmed_profile_json 解析失败，降级到 profile_json: parse_id=%d",
                    parse_id,
                )

    # 降级：从 profiles.profile_json 读取
    try:
        data = json.loads(profile_row.profile_json or "{}")
        return ProfileData.model_validate(data), profile_id, parse_id
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"画像数据损坏: {e}")
