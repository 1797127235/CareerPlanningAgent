"""用户决策模式分析器 — 基于行为数据的规则推理。

不用 LLM，避免长尾阻塞和 token 成本。规则简单可解释可测试。
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def analyze_user(db: Session, user_id: int) -> list[str]:
    """分析单个用户，返回决策模式标签列表。

    标签词汇表（固定，便于 coach prompt 对齐）：
    - "搜索型决策" / "锚定型决策"
    - "项目驱动" / "信息驱动"
    - "快速决策" / "反复纠结"
    - "数据不足"（冷启动用户）
    """
    from backend.models import JDDiagnosis, JobApplication, ProjectRecord
    from sqlalchemy import func

    patterns: list[str] = []

    # 数据量检查
    diag_count = db.query(func.count(JDDiagnosis.id)).filter_by(user_id=user_id).scalar() or 0
    app_count = db.query(func.count(JobApplication.id)).filter_by(user_id=user_id).scalar() or 0
    project_count = db.query(func.count(ProjectRecord.id)).filter_by(user_id=user_id).scalar() or 0

    if diag_count < 3 and app_count < 2 and project_count < 1:
        return ["数据不足"]

    # 规则 1：搜索型 vs 锚定型
    # 搜索型：诊断过 5+ 不同岗位
    distinct_titles = (
        db.query(func.count(func.distinct(JDDiagnosis.jd_title)))
        .filter_by(user_id=user_id)
        .scalar() or 0
    )
    if distinct_titles >= 5:
        patterns.append("搜索型决策")
    elif diag_count >= 3 and distinct_titles <= 2:
        patterns.append("锚定型决策")

    # 规则 2：项目驱动 vs 信息驱动
    # 项目驱动：project_count / diag_count >= 0.5
    if diag_count > 0:
        ratio = project_count / diag_count
        if ratio >= 0.5 and project_count >= 2:
            patterns.append("项目驱动")
        elif diag_count >= 5 and project_count <= 1:
            patterns.append("信息驱动")

    # 规则 3：快速决策 vs 反复纠结
    # 反复纠结：同一岗位 title 诊断过 3+ 次
    max_repeat_row = (
        db.query(func.count(JDDiagnosis.id))
        .filter_by(user_id=user_id)
        .group_by(JDDiagnosis.jd_title)
        .order_by(func.count(JDDiagnosis.id).desc())
        .limit(1)
        .first()
    )
    max_repeat = max_repeat_row[0] if max_repeat_row else 0
    if max_repeat >= 3:
        patterns.append("反复纠结")
    elif distinct_titles >= 3 and max_repeat == 1:
        patterns.append("快速决策")

    return patterns


def run_pattern_analysis_all() -> int:
    """扫所有用户，把 pattern 作为结构化记忆写入 Mem0。"""
    from backend.db import SessionLocal
    from backend.models import User
    from backend.services.coach.memory import get_memory

    db = SessionLocal()
    count = 0
    try:
        mem = get_memory()
        users = db.query(User).all()
        for u in users:
            patterns = analyze_user(db, u.id)
            if not patterns or patterns == ["数据不足"]:
                continue

            pattern_summary = f"[行为模式分析] 该用户的决策特征：{', '.join(patterns)}"
            try:
                mem.add(pattern_summary, user_id=str(u.id), metadata={"kind": "pattern_analysis"})
                count += 1
            except Exception:
                logger.exception("Failed to write pattern for user %d", u.id)
        logger.info("Pattern analysis updated %d users via Mem0", count)
        return count
    except Exception:
        logger.exception("Pattern analysis failed")
        return 0
    finally:
        db.close()
