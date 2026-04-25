"""Project editing routes for profiles.

PATCH /me/projects/refine  — content-match update (preferred)
PATCH /me/projects/{index} — index-based update (legacy)
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.db import get_db
from backend.models import Profile, User
from backend.routers._profiles_helpers import _load_profile_json
from backend.utils import ok

logger = logging.getLogger(__name__)

router = APIRouter()


def _update_project_description(projects: list, idx: int, description: str) -> None:
    current = projects[idx]
    if isinstance(current, str):
        projects[idx] = description
    elif isinstance(current, dict):
        projects[idx] = {**current, "description": description}


class RefineProjectBody(BaseModel):
    """基于 original_text 内容匹配来定位项目，避免数组下标漂移。"""
    original_text: str = Field(..., max_length=10000)
    new_description: str = Field(..., max_length=10000)

    @field_validator("original_text")
    @classmethod
    def _strip_original(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("original_text 不能为空")
        return v

    @field_validator("new_description")
    @classmethod
    def _strip_new(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("new_description 不能为空")
        return v


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
    profile = (
        db.query(Profile)
        .filter(Profile.user_id == user.id)
        .with_for_update()
        .first()
    )
    if not profile:
        raise HTTPException(404, "未找到画像")

    data = _load_profile_json(profile)
    projects = data.get("projects", [])
    target = body.original_text
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

    _update_project_description(projects, matched_idx, body.new_description)
    data["projects"] = projects
    profile.profile_json = json.dumps(data, ensure_ascii=False, default=str)
    db.commit()
    return ok(message="项目已更新")


# Legacy index-based PATCH removed — use PATCH /me/projects/refine instead.
