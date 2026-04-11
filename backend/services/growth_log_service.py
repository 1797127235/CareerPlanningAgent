"""成长档案服务 — 事件创建、readiness 估算、月度摘要。"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# readiness delta 估算（轻量规则，不调 matching_service）
_DELTA_ESTIMATE = {
    "project_completed": 3.0,
    "interview_done": 1.0,
    "learning_completed": 0.8,
    "skill_added": 1.5,
    "direction_set": 0.0,
    "profile_created": 0.0,
    "jd_diagnosis_done": 0.0,
    "skill_confirmed": 1.5,
}


# ── 自动成长事件触发器 ────────────────────────────────────────────────────────

def _auto_record(
    user_id: int,
    profile_id: int | None,
    event_type: str,
    summary: str,
    db: Session,
    skills_delta: dict | None = None,
    readiness_before: float | None = None,
    readiness_after: float | None = None,
    source_id: int = 0,
) -> None:
    """Create a GrowthEvent record for system-generated milestones. Silent on failure."""
    try:
        from backend.db_models import GrowthEvent
        event = GrowthEvent(
            user_id=user_id,
            profile_id=profile_id,
            event_type=event_type,
            source_table="system",
            source_id=source_id,
            summary=summary,
            skills_delta=skills_delta or {},
            readiness_before=readiness_before,
            readiness_after=readiness_after,
        )
        db.add(event)
        db.commit()
        logger.info("growth_event recorded: user=%d type=%s", user_id, event_type)
    except Exception as e:
        logger.debug("_auto_record failed: %s", e)


def record_profile_created(user_id: int, profile_id: int, skill_count: int, db: Session) -> None:
    """Record milestone: first resume uploaded and profile built."""
    _auto_record(
        user_id, profile_id, "profile_created",
        f"上传简历，识别到 {skill_count} 项技能，能力画像建立完成",
        db,
    )


def record_direction_set(
    user_id: int, profile_id: int, node_id: str, label: str, db: Session
) -> None:
    """Record milestone: student selected a career target direction."""
    readiness = _compute_readiness_live(profile_id, db)
    _auto_record(
        user_id, profile_id, "direction_set",
        f"选定目标方向：{label}",
        db,
        readiness_after=readiness,
    )


def record_jd_diagnosis(
    user_id: int,
    profile_id: int,
    jd_title: str,
    match_score: float,
    gap_skills: list[str],
    db: Session,
) -> None:
    """Record milestone: JD diagnosis completed with gap analysis."""
    gap_str = "、".join(gap_skills[:3]) if gap_skills else "无明显缺口"
    _auto_record(
        user_id, profile_id, "jd_diagnosis_done",
        f"JD诊断完成：{jd_title}，匹配度 {match_score:.0f}%，缺口技能：{gap_str}",
        db,
        readiness_after=match_score,
    )


def record_project_completed(
    user_id: int,
    profile_id: int,
    project_id: int,
    project_name: str,
    skills_used: list[str],
    db: Session,
) -> None:
    """Record milestone: project marked as completed."""
    readiness_before = _compute_readiness_live(profile_id, db)
    skills_str = "、".join(skills_used[:3]) if skills_used else ""
    summary = f"项目完成：{project_name}"
    if skills_str:
        summary += f"（技能：{skills_str}）"
    _auto_record(
        user_id, profile_id, "project_completed",
        summary, db,
        skills_delta={"added": skills_used},
        readiness_before=readiness_before,
        source_id=project_id,
    )


def record_skill_confirmed(
    user_id: int,
    profile_id: int,
    skill_name: str,
    db: Session,
) -> None:
    """Record milestone: Coach validated a skill via calibration question."""
    readiness_before = _compute_readiness_live(profile_id, db)
    _auto_record(
        user_id, profile_id, "skill_confirmed",
        f"Coach 校准确认掌握：{skill_name}",
        db,
        skills_delta={"confirmed": [skill_name]},
        readiness_before=readiness_before,
    )


def _skill_matches(skill_name: str, user_skills: set[str]) -> bool:
    """Case-insensitive substring match for a skill keyword against user skill set.

    Handles variants like "Spring Boot" vs "SpringBoot", "Redis缓存" vs "Redis".
    Normalization removes spaces/hyphens/underscores before comparison.
    Short keywords (≤2 chars) require exact match to avoid false positives.
    """
    def _norm(s: str) -> str:
        return s.lower().strip().replace(" ", "").replace("-", "").replace("_", "")

    name = skill_name.lower().strip()
    name_norm = _norm(skill_name)
    if not name:
        return False

    # Exact match (raw lowercase)
    if name in user_skills:
        return True

    # Short keyword: only exact match allowed
    if len(name_norm) <= 2:
        return False

    for us in user_skills:
        if not us:
            continue
        us_norm = _norm(us)
        # Normalized exact match (handles SpringBoot vs spring boot)
        if name_norm == us_norm:
            return True
        # Substring match (both directions, normalized)
        if len(us_norm) > 2 and (name_norm in us_norm or us_norm in name_norm):
            return True
    return False


def _compute_readiness_live(profile_id: int, db: Session) -> float | None:
    """Compute readiness from CareerGoal + current skills using real market skill weights.

    Uses skill_tiers (from 48万 JD ETL) with weighted scoring:
      core skills: weight 1.0 (≥50% JD mention rate)
      important:   weight 0.6 (20-49%)
      bonus:       weight 0.3 (5-19%)

    Falls back to flat must_skills matching if skill_tiers unavailable.
    Called after skill updates so the returned value reflects new skills immediately.
    """
    try:
        from backend.db_models import CareerGoal, Profile
        profile = db.query(Profile).filter(Profile.id == profile_id).first()
        if not profile:
            return None

        goal = (
            db.query(CareerGoal)
            .filter(CareerGoal.profile_id == profile_id, CareerGoal.is_active == True)
            .order_by(CareerGoal.is_primary.desc(), CareerGoal.set_at.desc())
            .first()
        )
        if not goal:
            return None

        from backend.services.graph_service import GraphService
        svc = GraphService()
        svc.load()
        node = svc.get_node(goal.target_node_id)
        if not node:
            return None

        # Build user skill set (lowercase, from both dict-format and string-format)
        profile_data = json.loads(profile.profile_json or "{}")
        raw_skills = profile_data.get("skills", [])
        if raw_skills and isinstance(raw_skills[0], dict):
            user_skills = {s.get("name", "").lower().strip() for s in raw_skills if s.get("name")}
        else:
            user_skills = {s.lower().strip() for s in raw_skills if isinstance(s, str) and s.strip()}

        # ── Tiered scoring (preferred) ──────────────────────────────────────
        tiers = node.get("skill_tiers", {})
        core_list = tiers.get("core", [])
        important_list = tiers.get("important", [])
        bonus_list = tiers.get("bonus", [])

        if core_list or important_list:
            # Weights: core=1.0, important=0.6, bonus=0.3
            total_w = len(core_list) * 1.0 + len(important_list) * 0.6 + len(bonus_list) * 0.3
            if total_w == 0:
                return 0.0
            matched_w = 0.0
            for entry in core_list:
                if _skill_matches(entry["name"], user_skills):
                    matched_w += 1.0
            for entry in important_list:
                if _skill_matches(entry["name"], user_skills):
                    matched_w += 0.6
            for entry in bonus_list:
                if _skill_matches(entry["name"], user_skills):
                    matched_w += 0.3
            return round(min(matched_w / total_w * 100, 100.0), 1)

        # ── Fallback: flat must_skills equal-weight matching ────────────────
        must_skills = [s.lower().strip() for s in node.get("must_skills", []) if s and s.strip()]
        if not must_skills:
            return 0.0
        matched = sum(1 for s in must_skills if _skill_matches(s, user_skills))
        return round(matched / len(must_skills) * 100, 1)

    except Exception as e:
        logger.debug("_compute_readiness_live failed: %s", e)
        return None


def get_current_readiness(profile_id: int, db: Session) -> float | None:
    """获取当前 readiness%。

    优先级：
    1. GrowthSnapshot（最精确，有就用）
    2. CareerGoal gap analysis（用户设定目标后，matched/must_skills 比值）
    3. 实时从图谱计算（兜底，用 profile skills 匹配 top 推荐，上限 80%）
    """
    try:
        from backend.db_models import GrowthSnapshot, Profile

        # 1. GrowthSnapshot
        snap = (
            db.query(GrowthSnapshot)
            .filter(GrowthSnapshot.profile_id == profile_id)
            .order_by(GrowthSnapshot.created_at.desc())
            .first()
        )
        if snap:
            return float(snap.readiness_score)

        profile = db.query(Profile).filter(Profile.id == profile_id).first()
        if not profile:
            return None

        # 2. CareerGoal gap analysis (most accurate — tied to user's actual target)
        from backend.db_models import CareerGoal
        goal = (
            db.query(CareerGoal)
            .filter(CareerGoal.profile_id == profile_id, CareerGoal.is_active == True)
            .order_by(CareerGoal.is_primary.desc(), CareerGoal.set_at.desc())
            .first()
        )
        if goal:
            from backend.services.graph_service import GraphService
            svc = GraphService()
            svc.load()
            node = svc.get_node(goal.target_node_id)
            if node:
                must_skills = [s.lower().strip() for s in node.get("must_skills", [])]
                profile_data = json.loads(profile.profile_json or "{}")
                raw_skills = profile_data.get("skills", [])
                if raw_skills and isinstance(raw_skills[0], dict):
                    user_skills = {s.get("name", "").lower().strip() for s in raw_skills}
                else:
                    user_skills = {s.lower().strip() for s in raw_skills if isinstance(s, str)}
                if must_skills:
                    matched = sum(1 for s in must_skills if s in user_skills)
                    return round(matched / len(must_skills) * 100, 1)
                else:
                    # Node has no must_skills — use 0% rather than falling through
                    # to tier 3 which would compute readiness against a different role
                    return 0.0

        # 3. Live compute from graph using real skill-gap ratio (NOT affinity_pct)
        profile_data = json.loads(profile.profile_json or "{}")
        raw_skills = profile_data.get("skills", [])
        if not raw_skills:
            return None

        if raw_skills and isinstance(raw_skills[0], dict):
            skill_names = [s.get("name", "") for s in raw_skills if s.get("name")]
        else:
            skill_names = [s for s in raw_skills if isinstance(s, str)]

        if not skill_names:
            return None

        from backend.services.graph_service import GraphService
        svc = GraphService()
        svc.load()
        results = svc.recommend_by_skills(skill_names, top_n=1)
        if results:
            top_result = results[0]
            matched_count = top_result.get("overlap_count", 0)
            missing = top_result.get("missing_skills", [])
            total = matched_count + len(missing)
            if total > 0:
                # Cap at 80% without real project/interview evidence
                raw_pct = round(matched_count / total * 100, 1)
                return min(raw_pct, 80.0)

    except Exception as e:
        logger.debug("Could not get readiness: %s", e)
    return None


def create_growth_event(
    *,
    user_id: int,
    profile_id: int | None,
    event_type: str,
    source_table: str,
    source_id: int,
    summary: str,
    skills_delta: dict | None = None,
    readiness_before_override: float | None = None,
    db: Session,
) -> "GrowthEvent":
    """创建成长事件，计算真实 readiness delta。

    If readiness_before_override is provided, use it (caller captured before skill update).
    Otherwise compute both before and after from current state.
    """
    from backend.db_models import GrowthEvent

    if readiness_before_override is not None:
        readiness_before = readiness_before_override
    else:
        readiness_before = get_current_readiness(profile_id, db) if profile_id else None

    readiness_after = get_current_readiness(profile_id, db) if profile_id else None

    # Fallback: if readiness didn't change (no skills change), use small estimate
    if readiness_before is not None and readiness_after is not None and readiness_after <= readiness_before:
        est = _DELTA_ESTIMATE.get(event_type, 0.0)
        if est > 0:
            readiness_after = round(readiness_before + est, 1)

    event = GrowthEvent(
        user_id=user_id,
        profile_id=profile_id,
        event_type=event_type,
        source_table=source_table,
        source_id=source_id,
        summary=summary,
        skills_delta=skills_delta or {},
        readiness_before=readiness_before,
        readiness_after=readiness_after,
    )
    db.add(event)
    db.flush()
    return event


def get_timeline(
    *,
    user_id: int,
    profile_id: int | None = None,
    event_type: str | None = None,
    limit: int = 30,
    offset: int = 0,
    db: Session,
) -> list[dict]:
    """获取成长事件时间线，返回序列化的事件列表。"""
    from backend.db_models import GrowthEvent

    q = db.query(GrowthEvent).filter(GrowthEvent.user_id == user_id)
    if profile_id:
        q = q.filter(GrowthEvent.profile_id == profile_id)
    if event_type:
        q = q.filter(GrowthEvent.event_type == event_type)
    q = q.order_by(GrowthEvent.created_at.desc()).offset(offset).limit(limit)

    events = q.all()
    return [_serialize_event(e) for e in events]


def _serialize_event(event: "GrowthEvent") -> dict:
    return {
        "id": event.id,
        "event_type": event.event_type,
        "source_table": event.source_table,
        "source_id": event.source_id,
        "summary": event.summary,
        "skills_delta": event.skills_delta or {},
        "readiness_before": event.readiness_before,
        "readiness_after": event.readiness_after,
        "created_at": event.created_at.isoformat(),
    }


def get_monthly_summary(
    *,
    user_id: int,
    profile_id: int | None = None,
    db: Session,
) -> dict:
    """生成本月成长摘要统计。"""
    from backend.db_models import GrowthEvent

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    events = (
        db.query(GrowthEvent)
        .filter(
            GrowthEvent.user_id == user_id,
            GrowthEvent.created_at >= month_start,
        )
        .all()
    )

    counts = {"project_completed": 0, "interview_done": 0, "learning_completed": 0, "skill_added": 0}
    readiness_start: float | None = None
    readiness_end: float | None = None

    for e in sorted(events, key=lambda x: x.created_at):
        counts[e.event_type] = counts.get(e.event_type, 0) + 1
        if e.readiness_before is not None and readiness_start is None:
            readiness_start = e.readiness_before
        if e.readiness_after is not None:
            readiness_end = e.readiness_after

    readiness_delta = None
    if readiness_start is not None and readiness_end is not None:
        readiness_delta = round(readiness_end - readiness_start, 1)

    current_readiness = get_current_readiness(profile_id, db) if profile_id else readiness_end

    return {
        "month": now.strftime("%Y年%m月"),
        "projects": counts["project_completed"],
        "interviews": counts["interview_done"],
        "learnings": counts["learning_completed"],
        "total_events": len(events),
        "readiness_start": readiness_start,
        "readiness_current": current_readiness,
        "readiness_delta": readiness_delta,
    }


def generate_interview_analysis(
    *,
    company: str,
    position: str,
    round_: str,
    content_summary: str,
    self_rating: str,
    profile_skills: list[str],
) -> str:
    """用 LLM 生成面试复盘分析，返回 JSON 字符串。"""
    try:
        from backend.llm import get_llm_client, get_model
        client = get_llm_client(timeout=30)
        model = get_model("fast")

        skill_str = ", ".join(profile_skills[:15]) if profile_skills else "未知"
        prompt = f"""你是职业规划教练，帮学生复盘真实面试经历。

面试信息：
- 公司：{company}
- 岗位：{position}
- 轮次：{round_}
- 面试内容：{content_summary}
- 自我评价：{self_rating}（good=发挥好/medium=一般/bad=发挥差）
- 用户技能：{skill_str}

请生成简洁的复盘分析，返回 JSON：
{{
  "strengths": ["做得好的地方（1-2条）"],
  "weaknesses": ["暴露的不足（1-2条）"],
  "action_items": ["下一步建议（1-2条）"],
  "overall": "一句话总结"
}}

直接返回 JSON，不要其他文字。"""

        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=400,
        )
        text = resp.choices[0].message.content.strip()
        # Validate it's parseable
        json.loads(text)
        return text
    except Exception as e:
        logger.warning("Interview analysis generation failed: %s", e)
        return json.dumps({
            "strengths": [],
            "weaknesses": [],
            "action_items": ["继续练习，下次会更好"],
            "overall": "面试经历已记录，保持积累。"
        })


def on_learning_completed(
    *,
    user_id: int,
    profile_id: int,
    subtopic_id: str,
    topic_title: str,
    role_id: str,
) -> None:
    """学习主题完成后的后台处理：技能匹配 → 更新画像 → 创建成长事件。

    此函数设计为在 BackgroundTask 中运行，不阻塞 HTTP 响应。
    所有异常都被捕获，不影响主流程。
    """
    try:
        from backend.db import SessionLocal
        from backend.db_models import Profile, LearningProgress
        from backend.services.graph_service import GraphService, find_skill_for_topic

        db = SessionLocal()
        try:
            profile = db.query(Profile).filter(Profile.id == profile_id).first()
            if not profile:
                return

            # Snapshot readiness BEFORE any skill update
            readiness_before = get_current_readiness(profile_id, db)

            # Load all graph skills for matching
            svc = GraphService()
            svc.load()
            all_graph_skills = list({
                s.lower().strip()
                for node in svc._nodes.values()
                for s in node.get("must_skills", [])
            })

            # Find best matching skill for this topic title
            matched_skill = find_skill_for_topic(topic_title, all_graph_skills, threshold=0.65)

            # Update profile skills if a match was found
            added_skills: list[str] = []
            if matched_skill:
                profile_data = json.loads(profile.profile_json or "{}")
                existing_skills = profile_data.get("skills", [])

                # Detect format: list of dicts vs list of strings
                is_dict_format = bool(existing_skills) and isinstance(existing_skills[0], dict)
                if is_dict_format:
                    existing_names = {s.get("name", "").lower() for s in existing_skills}
                    existing_list = existing_skills
                else:
                    existing_names = {s.lower() for s in existing_skills if isinstance(s, str)}
                    existing_list = list(existing_skills)

                # Add if not already present — preserve format (dict vs string)
                if matched_skill not in existing_names:
                    if is_dict_format:
                        existing_list.append({"name": matched_skill, "level": "familiar"})
                    else:
                        existing_list.append(matched_skill)
                    profile_data["skills"] = existing_list
                    profile.profile_json = json.dumps(profile_data, ensure_ascii=False)
                    # Invalidate cached recommendations so next visit recomputes
                    profile.cached_recs_json = "{}"
                    db.flush()
                    added_skills = [matched_skill]
                    logger.info(
                        "Learning '%s' → added skill '%s' to profile %d",
                        topic_title, matched_skill, profile_id,
                    )

            # Compute new readiness live (bypasses stale snapshot)
            readiness_after_live = _compute_readiness_live(profile_id, db)

            # Create new GrowthSnapshot on every learning completion (even without new skill).
            # This builds the readiness curve over time so students can see their progress.
            if readiness_after_live is not None:
                from backend.db_models import GrowthSnapshot, CareerGoal
                goal = (
                    db.query(CareerGoal)
                    .filter(CareerGoal.profile_id == profile_id, CareerGoal.is_active == True)
                    .order_by(CareerGoal.is_primary.desc(), CareerGoal.set_at.desc())
                    .first()
                )
                if goal:
                    db.add(GrowthSnapshot(
                        profile_id=profile_id,
                        target_node_id=goal.target_node_id,
                        trigger="skill_acquired",
                        stage_completed=0,
                        readiness_score=readiness_after_live,
                        base_score=readiness_after_live,
                        growth_bonus=0.0,
                        four_dim_detail=None,
                    ))
                    logger.info(
                        "GrowthSnapshot created: profile=%d readiness %.1f→%.1f (topic=%s)",
                        profile_id, readiness_before or 0, readiness_after_live, topic_title,
                    )

            # Create GrowthEvent (whether or not a skill was added)
            summary = f"完成学习「{topic_title}」"
            if added_skills:
                summary += f" · 掌握: {', '.join(added_skills)}"

            create_growth_event(
                user_id=user_id,
                profile_id=profile_id,
                event_type="learning_completed",
                source_table="learning_progress",
                source_id=0,
                summary=summary,
                skills_delta={"added": added_skills} if added_skills else {},
                readiness_before_override=readiness_before,
                db=db,
            )
            db.commit()
            logger.info("GrowthEvent created for learning '%s' (profile %d)", topic_title, profile_id)

        finally:
            db.close()

    except Exception as e:
        logger.exception("on_learning_completed failed for topic '%s': %s", topic_title, e)
