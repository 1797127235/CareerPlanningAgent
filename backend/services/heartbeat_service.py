"""Heartbeat service — 生成主动 check-in 消息。

规则驱动（非 LLM），限频：同一 (user_id, kind) 7 天内只发 1 条。

由 scheduler 每天 09:00 调用一次。
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# ── 限频规则 ────────────────────────────────────────────────────────────────
# 同一 user + kind 在这个时间窗内不能重复推
_DEDUP_WINDOW_DAYS = 7


def _recently_sent(db: Session, user_id: int, kind: str) -> bool:
    """检查该 user+kind 是否在去重窗口内已发过。"""
    from backend.models import UserNotification
    cutoff = datetime.now(timezone.utc) - timedelta(days=_DEDUP_WINDOW_DAYS)
    exists = (
        db.query(UserNotification.id)
        .filter(
            UserNotification.user_id == user_id,
            UserNotification.kind == kind,
            UserNotification.created_at >= cutoff,
        )
        .first()
    )
    return exists is not None


def _emit(db: Session, user_id: int, kind: str, title: str, body: str,
          cta_label: str | None = None, cta_route: str | None = None) -> None:
    """写一条 UserNotification，带限频检查。"""
    from backend.models import UserNotification
    if _recently_sent(db, user_id, kind):
        return
    db.add(UserNotification(
        user_id=user_id,
        kind=kind,
        title=title,
        body=body,
        cta_label=cta_label,
        cta_route=cta_route,
    ))


# ── 规则 1：JD 诊断后 3 天没有对应投递 ─────────────────────────────────────
def _rule_jd_followup(db: Session) -> int:
    """诊断过 JD 但 3 天没建 JobApplication → 提醒。"""
    from backend.models import JDDiagnosis, JobApplication
    cutoff_min = datetime.now(timezone.utc) - timedelta(days=7)
    cutoff_max = datetime.now(timezone.utc) - timedelta(days=3)

    candidates = (
        db.query(JDDiagnosis)
        .filter(
            JDDiagnosis.created_at >= cutoff_min,
            JDDiagnosis.created_at <= cutoff_max,
        )
        .all()
    )
    count = 0
    for diag in candidates:
        # 检查这条诊断有没有关联的 JobApplication
        has_app = (
            db.query(JobApplication.id)
            .filter(JobApplication.user_id == diag.user_id)
            .filter(JobApplication.position.ilike(f"%{(diag.jd_title or '')[:20]}%"))
            .first()
        )
        if has_app:
            continue
        _emit(
            db, diag.user_id,
            kind="jd_followup",
            title="那份 JD 还在看吗",
            body=f"你 3 天前诊断了「{diag.jd_title[:30]}」，{diag.match_score}% 匹配。什么让你还没投？",
            cta_label="去追踪",
            cta_route="/growth-log",
        )
        count += 1
    return count


# ── 规则 2：一周未活跃 ─────────────────────────────────────────────────────
def _rule_inactive_nudge(db: Session) -> int:
    """7 天没任何活动（chat/诊断/档案更新）→ 推"你在追踪的公司有新动态"。"""
    from backend.models import User, ChatMessage, ChatSession, JDDiagnosis, JobApplication
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    users = db.query(User).all()
    count = 0
    for u in users:
        last_chat = (
            db.query(ChatMessage.created_at)
            .join(ChatSession, ChatMessage.session_id == ChatSession.id)
            .filter(ChatSession.user_id == u.id)
            .order_by(ChatMessage.created_at.desc())
            .first()
        )
        last_diag = (
            db.query(JDDiagnosis.created_at)
            .filter(JDDiagnosis.user_id == u.id)
            .order_by(JDDiagnosis.created_at.desc())
            .first()
        )
        def _as_utc(dt):
            return dt.replace(tzinfo=timezone.utc) if dt and dt.tzinfo is None else dt

        last_active = max(
            (_as_utc(last_chat[0]) if last_chat else datetime.min.replace(tzinfo=timezone.utc)),
            (_as_utc(last_diag[0]) if last_diag else datetime.min.replace(tzinfo=timezone.utc)),
        )
        if last_active >= cutoff:
            continue

        # 有追踪公司的才推
        tracked = (
            db.query(JobApplication)
            .filter(
                JobApplication.user_id == u.id,
                ~JobApplication.status.in_(["withdrawn", "rejected"]),
            )
            .count()
        )
        if tracked == 0:
            continue
        _emit(
            db, u.id,
            kind="inactive_nudge",
            title="好久没来了",
            body=f"你追踪的 {tracked} 家公司里，哪一家你最想先推进？",
            cta_label="查看追踪",
            cta_route="/growth-log",
        )
        count += 1
    return count


# ── 规则 3：项目里程碑到期 ─────────────────────────────────────────────────
def _rule_milestone_due(db: Session) -> int:
    """ProjectRecord 有 deadline 字段的 → 临近 3 天提醒。

    注意：当前 ProjectRecord 没有 deadline 字段。此规则暂留占位，
    等 ProjectRecord 加 deadline 字段后再启用。
    """
    return 0


# ── 主入口 ───────────────────────────────────────────────────────────────
def run_heartbeat() -> dict:
    """扫所有规则，写 UserNotification。返回 {rule_name: emitted_count}."""
    from backend.db import SessionLocal
    db = SessionLocal()
    try:
        stats = {
            "jd_followup": _rule_jd_followup(db),
            "inactive_nudge": _rule_inactive_nudge(db),
            "milestone_due": _rule_milestone_due(db),
        }
        db.commit()
        logger.info("Heartbeat done: %s", stats)
        return stats
    except Exception:
        db.rollback()
        logger.exception("Heartbeat failed")
        return {}
    finally:
        db.close()
