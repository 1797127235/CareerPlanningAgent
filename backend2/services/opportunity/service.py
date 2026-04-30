"""backend2/services/opportunity/service.py — JD 诊断业务编排。"""
from __future__ import annotations
import json
import logging
from fastapi import HTTPException
from sqlalchemy.orm import Session
from backend2.schemas.opportunity import (
    JDExtract,
    JDDiagnoseRequest,
    JDDiagnosisListItem,
    JDDiagnosisResponse,
    JDDiagnosisResult,
)
from backend2.schemas.profile import ProfileData
from backend2.services.opportunity.evaluator import evaluate
from backend2.services.opportunity.parser import parse_jd
from backend2.services.opportunity.repository import create_diagnosis, get_by_id, get_history
from backend2.services.profile.resolver import resolve_profile_context
logger = logging.getLogger(__name__)

def _format_dt(dt) -> str:
    """将 datetime 格式化为 ISO 字符串。"""
    if dt is None:
        return ""
    return dt.isoformat()

def _to_response(record, warnings: list[str] | None = None) -> JDDiagnosisResponse:
    """将 ORM 记录转换为 API 响应。"""
    jd_extract = JDExtract.model_validate_json(record.jd_extract_json or "{}")
    result = JDDiagnosisResult.model_validate_json(record.result_json or "{}")

    return JDDiagnosisResponse(
        id=record.id,
        match_score=record.match_score,
        jd_title=record.jd_title,
        company=record.company,
        jd_text=record.jd_text or "",
        jd_extract=jd_extract,
        result=result,
        created_at=_format_dt(record.created_at),
        warnings=warnings or [],
    )

def diagnose(
    db: Session,
    user_id: int,
    request: JDDiagnoseRequest,
) -> JDDiagnosisResponse:
    """执行 JD 诊断完整流程。
    1. 读取用户最新画像
    2. 解析 JD 文本
    3. 评估匹配度
    4. 保存诊断快照
    5. 返回响应
    """
    try:
        warnings: list[str] = []

        # 1. 读取画像（单次查询拿到 ProfileData + IDs）
        profile, profile_id, parse_id = resolve_profile_context(db, user_id)

        # 2. 解析 JD
        jd_extract = parse_jd(request.jd_text)
        if request.jd_title:
            jd_extract.title = request.jd_title
        if not jd_extract.required_skills and not jd_extract.preferred_skills:
            warnings.append("JD 解析未提取到技能要求，匹配结果可能不准确")

        # 3. 评估
        result = evaluate(profile, jd_extract)
        if result.match_score == 0 and not result.matched_skills and not result.gap_skills:
            warnings.append("LLM 评估返回空结果，可能调用失败")

        # 4. 保存
        record = create_diagnosis(
            db=db,
            user_id=user_id,
            profile_id=profile_id,
            profile_parse_id=parse_id,
            jd_text=request.jd_text,
            jd_title=request.jd_title,
            company="",
            profile_snapshot=profile.model_dump(mode="json"),
            jd_extract=jd_extract,
            result=result,
        )
        db.commit()

        return _to_response(record, warnings=warnings)
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("JD 诊断流程失败: user_id=%d", user_id)
        raise HTTPException(status_code=500, detail="诊断失败，请稍后重试")

def get_diagnosis_history(
    db: Session,
    user_id: int,
) -> list[JDDiagnosisListItem]:
    """获取用户诊断历史列表。"""
    records = get_history(db, user_id, limit=50)
    return [
        JDDiagnosisListItem(
            id=r.id,
            jd_title=r.jd_title,
            company=r.company,
            match_score=r.match_score,
            created_at=_format_dt(r.created_at),
        )
        for r in records
    ]


def get_diagnosis_detail(
    db: Session,
    user_id: int,
    diagnosis_id: int,
) -> JDDiagnosisResponse:
    """获取单条诊断详情。"""
    record = get_by_id(db, diagnosis_id, user_id)
    if not record:
        raise HTTPException(status_code=404, detail="诊断记录不存在")
    return _to_response(record)

