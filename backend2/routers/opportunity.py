"""backend2/routers/opportunity.py — 职位机会评估 v2 API 路由。"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.models import User
from backend2.core.security import get_current_user
from backend2.db.session import get_db
from backend2.schemas.opportunity import (
    JDDiagnoseRequest,
    JDDiagnosisListItem,
    JDDiagnosisResponse,
)
from backend2.services.opportunity.service import (
    diagnose,
    get_diagnosis_detail,
    get_diagnosis_history,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


@router.post("/evaluate", response_model=JDDiagnosisResponse)
def evaluate_opportunity(
    request: JDDiagnoseRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JDDiagnosisResponse:
    """评估职位机会。

    基于当前用户最新画像，对粘贴的 JD 文本进行匹配分析。
    """
    try:
        return diagnose(db=db, user_id=current_user.id, request=request)
    except HTTPException:
        raise
    except Exception:
        logger.exception("机会评估失败: user_id=%d", current_user.id)
        raise HTTPException(status_code=500, detail="评估失败，请稍后重试")


@router.get("/evaluations", response_model=list[JDDiagnosisListItem])
def list_evaluations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[JDDiagnosisListItem]:
    """获取当前用户的评估历史列表。"""
    try:
        return get_diagnosis_history(db=db, user_id=current_user.id)
    except Exception:
        logger.exception("获取评估历史失败: user_id=%d", current_user.id)
        raise HTTPException(status_code=500, detail="获取历史失败")


@router.get("/evaluations/{evaluation_id}", response_model=JDDiagnosisResponse)
def get_evaluation(
    evaluation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JDDiagnosisResponse:
    """获取单条评估详情。"""
    try:
        return get_diagnosis_detail(
            db=db, user_id=current_user.id, diagnosis_id=evaluation_id
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("获取评估详情失败: user_id=%d, id=%d", current_user.id, evaluation_id)
        raise HTTPException(status_code=500, detail="获取详情失败")
