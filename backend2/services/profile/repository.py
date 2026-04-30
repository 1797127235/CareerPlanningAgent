"""backend2/services/profile/repository.py — profiles + profile_parses 表 CRUD。

职责：封装所有数据库操作，对外提供纯函数接口。
服务层通过本模块访问 DB，不直接使用 db.query()。
"""
from __future__ import annotations
import json
import logging
from sqlalchemy.orm import Session
from backend.models.profile import Profile, ProfileParse

logger = logging.getLogger(__name__)


# ── Profile 主表 ────────────────────────────────────────────────────────

def get_profile(db: Session, user_id: int) -> Profile | None:
    """按 user_id 查询 Profile 行（不含 parses）。"""
    return db.query(Profile).filter(Profile.user_id == user_id).first()


def get_profile_for_update(db: Session, user_id: int) -> Profile | None:
    """按 user_id 查询 Profile 行，加行锁防止并发写覆盖。"""
    return (
        db.query(Profile)
        .filter(Profile.user_id == user_id)
        .with_for_update()
        .first()
    )


def create_profile(
    db: Session,
    *,
    user_id: int,
    name: str = "",
    profile_json: str = "{}",
    quality_json: str = "{}",
    source: str = "manual",
) -> Profile:
    """创建 Profile 行并 flush（获取 id）。"""
    profile = Profile(
        user_id=user_id,
        name=name,
        profile_json=profile_json,
        quality_json=quality_json,
        source=source,
    )
    db.add(profile)
    db.flush()
    logger.info("Profile 创建: user_id=%d, profile_id=%d", user_id, profile.id)
    return profile


def update_profile_fields(
    db: Session,
    profile: Profile,
    *,
    name: str | None = None,
    profile_json: str | None = None,
    quality_json: str | None = None,
    source: str | None = None,
    active_parse_id: int | None = None,
    is_edited: bool | None = None,
) -> None:
    """原地更新 Profile 行字段，不 commit（由调用方控制事务）。"""
    if name is not None:
        profile.name = name
    if profile_json is not None:
        profile.profile_json = profile_json
    if quality_json is not None:
        profile.quality_json = quality_json
    if source is not None:
        profile.source = source
    if active_parse_id is not None:
        profile.active_parse_id = active_parse_id
    if is_edited is not None:
        profile.is_edited = is_edited
    db.flush()


def reset_profile_fields(db: Session, profile: Profile) -> None:
    """将 Profile 行重置为空状态（保留行本身）。"""
    profile.active_parse_id = None
    profile.profile_json = "{}"
    profile.quality_json = "{}"
    profile.name = ""
    profile.source = "manual"
    profile.cached_recs_json = "{}"
    profile.cached_gaps_json = "{}"
    profile.is_edited = False
    db.flush()


# ── ProfileParse 快照表 ─────────────────────────────────────────────────

def create_parse(
    db: Session,
    *,
    profile_id: int,
    file_hash: str = "",
    raw_profile_json: str,
    confirmed_profile_json: str,
    document_json: str,
    meta_json: str,
) -> ProfileParse:
    """插入一条 ProfileParse 快照并 flush（获取 id）。"""
    snapshot = ProfileParse(
        profile_id=profile_id,
        file_hash=file_hash,
        raw_profile_json=raw_profile_json,
        confirmed_profile_json=confirmed_profile_json,
        document_json=document_json,
        meta_json=meta_json,
    )
    db.add(snapshot)
    db.flush()
    logger.info("ProfileParse 创建: parse_id=%d, profile_id=%d", snapshot.id, profile_id)
    return snapshot


def get_parse(db: Session, parse_id: int) -> ProfileParse | None:
    """按 id 查询单条 ProfileParse。"""
    return db.query(ProfileParse).filter(ProfileParse.id == parse_id).first()


def update_parse_confirmed_json(db: Session, parse_id: int, confirmed_json: str) -> None:
    """更新指定快照的 confirmed_profile_json 字段。"""
    snapshot = get_parse(db, parse_id)
    if snapshot:
        snapshot.confirmed_profile_json = confirmed_json
        db.flush()


def delete_parses_for_profile(db: Session, profile_id: int) -> None:
    """删除指定 profile 的所有 ProfileParse 记录。"""
    db.query(ProfileParse).filter(
        ProfileParse.profile_id == profile_id
    ).delete(synchronize_session=False)
    logger.info("ProfileParse 批量删除: profile_id=%d", profile_id)
