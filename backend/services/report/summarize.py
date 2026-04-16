# NOTE: coach_memo is intentionally NOT read anywhere in this module.
# It's a cross-session memo owned by the coach agent and may contain
# sensitive/personal content. It belongs to the coach-facing surface only.
"""Report summary builder — raw tables → intermediate JSON for skills."""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.db_models import (
    GrowthSnapshot,
    InterviewDebrief,
    InterviewRecord,
    JobApplication,
    Profile,
    ProjectLog,
    ProjectRecord,
    Report,
    SkillUpdate,
)

logger = logging.getLogger(__name__)

_WINDOW_DAYS = int(os.getenv("REPORT_SUMMARY_WINDOW_DAYS", "90"))


def build_report_summary(
    user_id: int,
    profile: Profile,
    db: Session,
    prev_report: Report | None = None,
    skill_gap_current: dict | None = None,
) -> dict:
    """构造报告的中间 JSON。纯 Python + 一次可选 LLM 调用（抽面试痛点）。

    Args:
        user_id: 用户 id
        profile: 已加载的 Profile ORM 对象
        db: SQLAlchemy Session
        prev_report: 上一份 Report（若有），用于算 delta / completed_since_last_report /
                     prev_report_recommendations
        skill_gap_current: 当前报告的 skill_gap 结果，用于计算 gained_since_last_report

    Returns:
        dict，严格遵守 §2 schema。永不返回 None。
    """
    # ── Cache: reuse prev report summary if no new activity ─────────────
    if prev_report is not None:
        latest_change = _latest_user_activity_time(user_id, db)
        if latest_change:
            prev_created = prev_report.created_at
            if prev_created:
                if prev_created.tzinfo:
                    prev_created = prev_created.replace(tzinfo=None)
                lc = latest_change.replace(tzinfo=None) if latest_change.tzinfo else latest_change
                if prev_created >= lc:
                    prev_data = json.loads(prev_report.data_json or "{}")
                    if prev_data.get("summary", {}).get("version") == "2.0":
                        logger.info("Reusing prev report summary (no new activity)")
                        return prev_data["summary"]

    now = datetime.now(timezone.utc)
    since = now - timedelta(days=_WINDOW_DAYS)

    # ── 1. milestones ──────────────────────────────────────────────────
    milestones = _build_milestones(user_id, profile.id, db, since)

    # ── 2. skill_deltas ────────────────────────────────────────────────
    skill_deltas = _build_skill_deltas(
        user_id, profile, db, since, prev_report, skill_gap_current
    )

    # ── 3. signals ─────────────────────────────────────────────────────
    signals = {
        "interview": _build_interview_signal(user_id, db, since),
        "application": _build_application_signal(user_id, db, since),
        "project_momentum": _build_project_momentum(user_id, db, since),
    }

    # ── 4. prev report delta ───────────────────────────────────────────
    completed_since_last, prev_recs = _build_prev_delta(
        prev_report, milestones, skill_deltas
    )

    return {
        "version": "2.0",
        "window": {
            "since_iso": since.isoformat(),
            "now_iso": now.isoformat(),
            "days": _WINDOW_DAYS,
        },
        "milestones": milestones,
        "skill_deltas": skill_deltas,
        "signals": signals,
        "completed_since_last_report": completed_since_last,
        "prev_report_recommendations": prev_recs,
    }


def _latest_user_activity_time(user_id: int, db: Session) -> datetime | None:
    """返回所有"活动表"里 max(created_at/updated_at)。"""
    queries = [
        db.query(func.max(ProjectLog.created_at)).join(ProjectRecord).filter(
            ProjectRecord.user_id == user_id
        ),
        db.query(func.max(ProjectRecord.updated_at)).filter(
            ProjectRecord.user_id == user_id
        ),
        db.query(func.max(InterviewRecord.updated_at)).filter(
            InterviewRecord.user_id == user_id
        ),
        db.query(func.max(JobApplication.updated_at)).filter(
            JobApplication.user_id == user_id
        ),
        db.query(func.max(SkillUpdate.created_at)).join(Profile).filter(
            Profile.user_id == user_id
        ),
    ]
    times: list[datetime] = []
    for q in queries:
        try:
            val = q.scalar()
            if val is not None:
                times.append(val)
        except Exception:
            pass
    return max(times) if times else None


def _build_milestones(
    user_id: int, profile_id: int, db: Session, since: datetime
) -> list[dict]:
    """合并 ProjectLog / ProjectRecord 完成 / InterviewRecord / JobApplication /
    SkillUpdate，按时间倒序取 20 条。每条带 source + category。
    """
    items: list[dict] = []
    counter = 0

    # ── ProjectLog ──
    try:
        logs = (
            db.query(ProjectLog, ProjectRecord)
            .join(ProjectRecord, ProjectLog.project_id == ProjectRecord.id)
            .filter(
                ProjectRecord.user_id == user_id,
                ProjectLog.created_at >= since,
            )
            .order_by(ProjectLog.created_at.desc())
            .limit(20)
            .all()
        )
        for log, proj in logs:
            counter += 1
            items.append({
                "id": f"M-{counter:03d}",
                "date_iso": _iso(log.created_at),
                "source": f"project_log:{log.id}",
                "category": "project_progress",
                "title": f"{proj.name}：{log.content[:40]}",
                "detail": (log.content or "")[:200],
                "skills_touched": list(proj.skills_used or []),
            })
    except Exception as e:
        logger.warning("_build_milestones ProjectLog failed: %s", e)

    # ── ProjectRecord completed in window ──
    try:
        completed_projs = (
            db.query(ProjectRecord)
            .filter(
                ProjectRecord.user_id == user_id,
                ProjectRecord.status == "completed",
                ProjectRecord.completed_at >= since,
            )
            .all()
        )
        for proj in completed_projs:
            counter += 1
            items.append({
                "id": f"M-{counter:03d}",
                "date_iso": _iso(proj.completed_at or proj.updated_at),
                "source": f"project_record:{proj.id}",
                "category": "project_complete",
                "title": f"完成项目 {proj.name}",
                "detail": (proj.reflection or proj.description or "")[:200],
                "skills_touched": list(proj.skills_used or []),
            })
    except Exception as e:
        logger.warning("_build_milestones ProjectRecord completed failed: %s", e)

    # ── ProjectRecord reflection updated in window ──
    try:
        reflected_projs = (
            db.query(ProjectRecord)
            .filter(
                ProjectRecord.user_id == user_id,
                ProjectRecord.reflection.isnot(None),
                ProjectRecord.updated_at >= since,
            )
            .all()
        )
        for proj in reflected_projs:
            # skip if we already added as completed
            if any(
                it["source"] == f"project_record:{proj.id}" and it["category"] == "project_complete"
                for it in items
            ):
                continue
            counter += 1
            items.append({
                "id": f"M-{counter:03d}",
                "date_iso": _iso(proj.updated_at),
                "source": f"project_record:{proj.id}",
                "category": "reflection",
                "title": f"{proj.name} 项目复盘",
                "detail": (proj.reflection or "")[:200],
                "skills_touched": list(proj.skills_used or []),
            })
    except Exception as e:
        logger.warning("_build_milestones reflection failed: %s", e)

    # ── InterviewRecord ──
    try:
        interviews = (
            db.query(InterviewRecord)
            .filter(
                InterviewRecord.user_id == user_id,
                InterviewRecord.created_at >= since,
            )
            .order_by(InterviewRecord.created_at.desc())
            .limit(10)
            .all()
        )
        for iv in interviews:
            counter += 1
            items.append({
                "id": f"M-{counter:03d}",
                "date_iso": _iso(iv.interview_at or iv.created_at),
                "source": f"interview_record:{iv.id}",
                "category": "interview",
                "title": f"{iv.company} {iv.round}",
                "detail": (iv.content_summary or "")[:200],
                "skills_touched": [],
            })
    except Exception as e:
        logger.warning("_build_milestones InterviewRecord failed: %s", e)

    # ── JobApplication ──
    try:
        apps = (
            db.query(JobApplication)
            .filter(
                JobApplication.user_id == user_id,
                JobApplication.created_at >= since,
            )
            .order_by(JobApplication.created_at.desc())
            .limit(10)
            .all()
        )
        for app in apps:
            counter += 1
            items.append({
                "id": f"M-{counter:03d}",
                "date_iso": _iso(app.created_at),
                "source": f"job_application:{app.id}",
                "category": "application",
                "title": f"投递 {app.company or '某公司'} {app.position or ''}".strip(),
                "detail": "",
                "skills_touched": [],
            })
    except Exception as e:
        logger.warning("_build_milestones JobApplication failed: %s", e)

    # ── SkillUpdate ──
    try:
        updates = (
            db.query(SkillUpdate)
            .filter(
                SkillUpdate.profile_id == profile_id,
                SkillUpdate.created_at >= since,
            )
            .order_by(SkillUpdate.created_at.desc())
            .limit(10)
            .all()
        )
        for su in updates:
            counter += 1
            content = su.content if isinstance(su.content, dict) else {}
            skill_name = content.get("name", "") or content.get("skill", "") or "技能更新"
            items.append({
                "id": f"M-{counter:03d}",
                "date_iso": _iso(su.created_at),
                "source": f"skill_update:{su.id}",
                "category": "skill_claim",
                "title": f"更新技能：{skill_name}",
                "detail": json.dumps(content, ensure_ascii=False)[:200],
                "skills_touched": [skill_name] if skill_name else [],
            })
    except Exception as e:
        logger.warning("_build_milestones SkillUpdate failed: %s", e)

    # sort by date desc, keep top 20
    items.sort(key=lambda x: x["date_iso"], reverse=True)
    return items[:20]


def _build_skill_deltas(
    user_id: int,
    profile: Profile,
    db: Session,
    since: datetime,
    prev_report: Report | None,
    skill_gap_current: dict | None,
) -> dict:
    """
    - practiced_in_window: 读 ProjectLog + ProjectRecord.skills_used（window 内）
    - gained_since_last_report: 对比上一份 Report.data_json 的 skill_gap.matched_skills
    - still_claimed_only: profile_json.skills 中，本期和历史都没在 practiced 里出现过的
    - four_dim_trend: 读 GrowthSnapshot.four_dim_detail 取最近 3 个快照
    """
    # ── practiced_in_window ──
    practiced_in_window: set[str] = set()
    try:
        # from ProjectRecord.skills_used where updated in window
        projs = (
            db.query(ProjectRecord)
            .filter(
                ProjectRecord.user_id == user_id,
                ProjectRecord.updated_at >= since,
            )
            .all()
        )
        for p in projs:
            for s in (p.skills_used or []):
                if isinstance(s, str) and s.strip():
                    practiced_in_window.add(s.strip())
    except Exception as e:
        logger.warning("_build_skill_deltas practiced_in_window ProjectRecord failed: %s", e)

    try:
        # from ProjectLog content heuristic: if log mentions skill name
        # simplistic: include any ProjectRecord skill that has a log in window
        log_skills = (
            db.query(ProjectRecord.skills_used)
            .join(ProjectLog, ProjectLog.project_id == ProjectRecord.id)
            .filter(
                ProjectRecord.user_id == user_id,
                ProjectLog.created_at >= since,
            )
            .all()
        )
        for (skills_used,) in log_skills:
            for s in (skills_used or []):
                if isinstance(s, str) and s.strip():
                    practiced_in_window.add(s.strip())
    except Exception as e:
        logger.warning("_build_skill_deltas practiced_in_window ProjectLog failed: %s", e)

    # ── all-time practiced (for still_claimed_only) ──
    all_practiced: set[str] = set()
    try:
        all_projs = db.query(ProjectRecord).filter(
            ProjectRecord.user_id == user_id
        ).all()
        for p in all_projs:
            for s in (p.skills_used or []):
                if isinstance(s, str) and s.strip():
                    all_practiced.add(s.strip())
    except Exception as e:
        logger.warning("_build_skill_deltas all_practiced failed: %s", e)

    # ── gained_since_last_report ──
    gained_since_last_report: set[str] = set()
    if prev_report is not None and skill_gap_current is not None:
        try:
            prev_data = json.loads(prev_report.data_json or "{}")
            prev_matched = {
                m.get("name", "").strip()
                for m in (prev_data.get("skill_gap", {}).get("matched_skills", []) or [])
                if m.get("name")
            }
            current_matched = {
                m.get("name", "").strip()
                for m in (skill_gap_current.get("matched_skills", []) or [])
                if m.get("name")
            }
            gained_since_last_report = current_matched - prev_matched
        except Exception as e:
            logger.warning("_build_skill_deltas gained failed: %s", e)

    # ── still_claimed_only ──
    still_claimed_only: list[str] = []
    try:
        profile_data = json.loads(profile.profile_json or "{}")
        claimed: list[str] = []
        for s in (profile_data.get("skills", []) or []):
            if isinstance(s, dict):
                name = s.get("name", "")
            elif isinstance(s, str):
                name = s
            else:
                name = ""
            if name:
                claimed.append(name.strip())
        still_claimed_only = [
            c for c in claimed
            if c.lower() not in {a.lower() for a in all_practiced}
        ]
    except Exception as e:
        logger.warning("_build_skill_deltas still_claimed_only failed: %s", e)

    # ── four_dim_trend ──
    four_dim_trend: dict[str, list] = {}
    try:
        snaps = (
            db.query(GrowthSnapshot)
            .filter(GrowthSnapshot.profile_id == profile.id)
            .order_by(GrowthSnapshot.created_at.asc())
            .limit(20)
            .all()
        )
        detail_snapshots = [s for s in snaps if s.four_dim_detail]
        last3 = detail_snapshots[-3:]
        dims = ["foundation", "skills", "qualities", "potential"]
        for dim in dims:
            four_dim_trend[dim] = []
        for s in last3:
            d = s.four_dim_detail if isinstance(s.four_dim_detail, dict) else {}
            for dim in dims:
                four_dim_trend[dim].append(d.get(dim))
    except Exception as e:
        logger.warning("_build_skill_deltas four_dim_trend failed: %s", e)
        four_dim_trend = {
            "foundation": [], "skills": [], "qualities": [], "potential": []
        }

    return {
        "practiced_in_window": sorted(practiced_in_window),
        "gained_since_last_report": sorted(gained_since_last_report),
        "still_claimed_only": still_claimed_only,
        "four_dim_trend": four_dim_trend,
    }


def _build_interview_signal(user_id: int, db: Session, since: datetime) -> dict:
    """读 InterviewRecord + InterviewDebrief。
    调用 invoke_skill('extract-interview-signals', ...) 从 content_summary / raw_input
    抽 pain_points（最多 5 条）。失败时 pain_points=[]。
    """
    result = {
        "count_in_window": 0,
        "total_ever": 0,
        "latest": None,
        "pain_points": [],
    }

    try:
        total = db.query(InterviewRecord).filter(
            InterviewRecord.user_id == user_id
        ).count()
        result["total_ever"] = total
    except Exception as e:
        logger.warning("_build_interview_signal total count failed: %s", e)

    try:
        in_window = (
            db.query(InterviewRecord)
            .filter(
                InterviewRecord.user_id == user_id,
                InterviewRecord.created_at >= since,
            )
            .order_by(InterviewRecord.created_at.desc())
            .all()
        )
        result["count_in_window"] = len(in_window)
    except Exception as e:
        logger.warning("_build_interview_signal window query failed: %s", e)
        in_window = []

    if in_window:
        latest = in_window[0]
        result["latest"] = {
            "company": latest.company or "",
            "position": latest.position or "",
            "round": latest.round or "",
            "self_rating": latest.self_rating or "medium",
            "result": latest.result or "pending",
            "date_iso": _iso(latest.interview_at or latest.created_at),
        }

    # Build LLM input for pain points extraction
    interviews_json: list[dict] = []
    try:
        for iv in in_window[:5]:
            reflection = iv.reflection or ""
            # try to get debrief raw_input
            debrief = (
                db.query(InterviewDebrief)
                .filter(InterviewDebrief.application_id == iv.application_id)
                .first()
            )
            if debrief and debrief.raw_input:
                try:
                    raw = json.loads(debrief.raw_input)
                    if isinstance(raw, list) and raw:
                        reflection = raw[0].get("answer", "")[:300]
                except Exception:
                    reflection = (debrief.raw_input or "")[:300]

            interviews_json.append({
                "company": iv.company or "",
                "round": iv.round or "",
                "self_rating": iv.self_rating or "medium",
                "result": iv.result or "pending",
                "summary": (iv.content_summary or "")[:400],
                "reflection": reflection[:200],
            })
    except Exception as e:
        logger.warning("_build_interview_signal interviews_json build failed: %s", e)

    if interviews_json:
        try:
            from backend.llm import get_llm_client, get_model
            from backend.skills import render_skill

            system, user, _ = render_skill(
                "extract-interview-signals",
                interviews_json=json.dumps(interviews_json, ensure_ascii=False),
            )
            resp = get_llm_client(timeout=15).chat.completions.create(
                model=get_model("fast"),
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.2,
                max_tokens=500,
            )
            raw = resp.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            parsed = json.loads(raw.strip())
            if isinstance(parsed, list):
                result["pain_points"] = [str(p) for p in parsed[:5]]
            elif isinstance(parsed, dict) and isinstance(parsed.get("pain_points"), list):
                result["pain_points"] = [str(p) for p in parsed["pain_points"][:5]]
        except Exception as e:
            logger.warning("extract-interview-signals failed: %s", e)
            result["pain_points"] = []

    return result


def _build_application_signal(user_id: int, db: Session, since: datetime) -> dict:
    """读 JobApplication，聚合 funnel + directions（按 position 字段聚类）。"""
    result = {
        "count_in_window": 0,
        "total_ever": 0,
        "funnel": {
            "applied": 0,
            "screening": 0,
            "interviewed": 0,
            "offer": 0,
            "rejected": 0,
            "withdrawn": 0,
        },
        "directions": [],
    }

    try:
        total = db.query(JobApplication).filter(
            JobApplication.user_id == user_id
        ).count()
        result["total_ever"] = total
    except Exception as e:
        logger.warning("_build_application_signal total count failed: %s", e)

    try:
        apps = (
            db.query(JobApplication)
            .filter(
                JobApplication.user_id == user_id,
                JobApplication.created_at >= since,
            )
            .all()
        )
        result["count_in_window"] = len(apps)
    except Exception as e:
        logger.warning("_build_application_signal window query failed: %s", e)
        apps = []

    status_map = {
        "applied": "applied",
        "screening": "screening",
        "interviewed": "interviewed",
        "offer": "offer",
        "rejected": "rejected",
        "withdrawn": "withdrawn",
    }
    directions: dict[str, int] = {}
    for app in apps:
        st = (app.status or "applied").lower()
        mapped = status_map.get(st, "applied")
        result["funnel"][mapped] = result["funnel"].get(mapped, 0) + 1
        pos = app.position or "未注明"
        directions[pos] = directions.get(pos, 0) + 1

    result["directions"] = [
        {"label": k, "count": v}
        for k, v in sorted(directions.items(), key=lambda x: -x[1])
    ][:5]

    return result


def _build_project_momentum(user_id: int, db: Session, since: datetime) -> dict:
    """
    - active_count: status='in_progress' 且最近 14 天有 ProjectLog 的项目
    - completed_in_window_count: completed_at 在 window 内的项目
    - stalled_ids: status='in_progress' 且 >30 天无 ProjectLog 的项目
    """
    result = {
        "active_count": 0,
        "completed_in_window_count": 0,
        "stalled_ids": [],
    }

    try:
        projs = (
            db.query(ProjectRecord)
            .filter(ProjectRecord.user_id == user_id)
            .all()
        )
    except Exception as e:
        logger.warning("_build_project_momentum query failed: %s", e)
        return result

    now = datetime.now(timezone.utc)
    naive_now = now.replace(tzinfo=None)
    active_14 = naive_now - timedelta(days=14)
    stalled_30 = naive_now - timedelta(days=30)

    def _normalize_dt(dt):
        if dt is None:
            return None
        return dt.replace(tzinfo=None) if dt.tzinfo else dt

    for proj in projs:
        comp_at = _normalize_dt(proj.completed_at)
        if proj.status == "completed" and comp_at and comp_at >= since.replace(tzinfo=None):
            result["completed_in_window_count"] += 1
            continue

        if proj.status != "in_progress":
            continue

        try:
            latest_log = (
                db.query(ProjectLog)
                .filter(ProjectLog.project_id == proj.id)
                .order_by(ProjectLog.created_at.desc())
                .first()
            )
        except Exception:
            latest_log = None

        log_dt = _normalize_dt(latest_log.created_at) if latest_log else None
        if log_dt and log_dt >= active_14:
            result["active_count"] += 1
        elif (not log_dt) or (log_dt and log_dt < stalled_30):
            result["stalled_ids"].append(proj.id)

    return result


def _build_prev_delta(
    prev_report: Report | None,
    milestones: list[dict],
    skill_deltas: dict,
) -> tuple[list[str], list[str]]:
    """从 prev_report.data_json 解出：
    - completed_since_last_report: 上次报告的 prev_report_recommendations 中，
      现在已经在 skill_deltas.practiced 或 milestones 中出现过的 → 标记完成
    - prev_report_recommendations: 上次报告 action_plan.stages[*].items[*].text 中
      type 为 skill / project 的条目
    若 prev_report 为 None，返回 ([], [])。
    """
    if prev_report is None:
        return [], []

    try:
        prev_data = json.loads(prev_report.data_json or "{}")
    except Exception:
        return [], []

    # prev_report_recommendations
    prev_recs: list[str] = []
    try:
        prev_action_plan = prev_data.get("action_plan", {})
        for stage in (prev_action_plan.get("stages", []) or []):
            for item in (stage.get("items", []) or []):
                if item.get("type") in ("skill", "project"):
                    text = item.get("text", "")
                    if text:
                        prev_recs.append(text)
    except Exception as e:
        logger.warning("_build_prev_delta prev_recs failed: %s", e)

    # completed_since_last_report: check if prev recs appear in current activity
    practiced = {s.lower() for s in (skill_deltas.get("practiced_in_window") or [])}
    milestone_texts = " ".join(
        f"{m.get('title', '')} {m.get('detail', '')}" for m in milestones
    ).lower()

    completed: list[str] = []
    for rec in prev_recs:
        rec_lower = rec.lower()
        # heuristic: if any practiced skill name appears in the rec text,
        # or if the rec text keywords appear in milestones
        matched = False
        for skill in practiced:
            if skill and skill in rec_lower:
                matched = True
                break
        if not matched:
            # simple keyword overlap: take first 3 significant words from rec
            words = [w for w in rec_lower.split() if len(w) >= 2][:5]
            for w in words:
                if w in milestone_texts:
                    matched = True
                    break
        if matched:
            completed.append(rec)

    return completed, prev_recs


def _iso(dt: datetime | None) -> str:
    if dt is None:
        return ""
    return dt.isoformat()
