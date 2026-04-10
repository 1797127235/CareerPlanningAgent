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
}


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

                # Normalize to list of strings
                if existing_skills and isinstance(existing_skills[0], dict):
                    existing_names = {s.get("name", "").lower() for s in existing_skills}
                    existing_list = existing_skills
                else:
                    existing_names = {s.lower() for s in existing_skills if isinstance(s, str)}
                    existing_list = list(existing_skills)

                # Add if not already present
                if matched_skill not in existing_names:
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

            # Create GrowthEvent (whether or not a skill was added)
            summary = f"完成学习「{topic_title}」"
            if added_skills:
                summary += f" · 掌握: {', '.join(added_skills)}"

            create_growth_event(
                user_id=user_id,
                profile_id=profile_id,
                event_type="learning_completed",
                source_table="learning_progress",
                source_id=0,  # subtopic_id is a string, use 0 as placeholder
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
