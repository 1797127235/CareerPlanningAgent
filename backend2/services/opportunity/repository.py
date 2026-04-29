"""backend2/services/opportunity/repository.py — jd_diagnoses_v2 表 CRUD。"""
from __future__ import annotations

import json
import logging

from sqlalchemy.orm import Session

from backend2.models.opportunity import JDDiagnosisV2
from backend2.schemas.opportunity import JDExtract, JDDiagnosisResult

logger = logging.getLogger(__name__)


def create_diagnosis(
    db: Session,
    *,
    user_id: int,
    profile_id: int,
    profile_parse_id: int | None,
    jd_text: str,
    jd_title: str,
    company: str,
    profile_snapshot: dict,
    jd_extract: JDExtract,
    result: JDDiagnosisResult,
) -> JDDiagnosisV2:
    """创建一条诊断记录。"""
    record = JDDiagnosisV2(
        user_id=user_id,
        profile_id=profile_id,
        profile_parse_id=profile_parse_id,
        jd_text=jd_text,
        jd_title=jd_title or jd_extract.title or "",
        company=company or jd_extract.company or "",
        profile_snapshot_json=json.dumps(profile_snapshot, ensure_ascii=False),
        jd_extract_json=json.dumps(jd_extract.model_dump(mode="json"), ensure_ascii=False),
        result_json=json.dumps(result.model_dump(mode="json"), ensure_ascii=False),
        match_score=result.match_score,
    )
    db.add(record)
    db.flush()
    db.refresh(record)
    logger.info(
        "诊断记录创建: id=%d, user_id=%d, score=%d",
        record.id, user_id, result.match_score,
    )
    return record


def get_history(db: Session, user_id: int, limit: int = 50) -> list[JDDiagnosisV2]:
    """获取用户诊断历史，按 created_at desc。"""
    return (
        db.query(JDDiagnosisV2)
        .filter(JDDiagnosisV2.user_id == user_id)
        .order_by(JDDiagnosisV2.created_at.desc())
        .limit(limit)
        .all()
    )


def get_by_id(db: Session, diagnosis_id: int, user_id: int) -> JDDiagnosisV2 | None:
    """获取单条诊断详情（校验 user_id 权限）。"""
    return (
        db.query(JDDiagnosisV2)
        .filter(JDDiagnosisV2.id == diagnosis_id, JDDiagnosisV2.user_id == user_id)
        .first()
    )
