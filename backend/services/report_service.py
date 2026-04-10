# -*- coding: utf-8 -*-
"""
ReportService — five-chapter data-driven report generation.

Migrated from _reference/report_v2_service.py.

Chapter structure:
  Ch1: Ability Profile      <- Profile
  Ch2: Job Match            <- Latest JD diagnosis
  Ch3: Career Path          <- Graph + escape routes
  Ch4: Action Plan          <- JD gaps + interview review improvements
  Ch5: Interview Records    <- Review history
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from backend.llm import get_model, llm_chat, parse_json_response

logger = logging.getLogger(__name__)


class ReportService:
    """Generates a 5-chapter data-driven career report."""

    def generate_report(self, profile_id: int, db: Session) -> dict[str, Any]:
        """Aggregate data and build a 5-chapter report dict.

        Fetches Profile, JDDiagnosis, InterviewReview, InterviewChecklist,
        CareerGoal, and builds structured chapter data.

        Returns {report_key, data: {chapters, summary, ...}}.
        """
        from backend.db_models import (
            Profile as ProfileModel,
            Report,
            JDDiagnosis,
            InterviewReview,
            InterviewChecklist,
            CareerGoal,
            MockInterviewSession,
        )

        # 1. Fetch profile
        profile = db.query(ProfileModel).filter_by(id=profile_id).first()
        if not profile:
            raise ValueError("未找到简历画像")

        profile_data = json.loads(profile.profile_json or "{}")
        student_name = (
            profile_data.get("name")
            or profile_data.get("basic_info", {}).get("name")
            or profile.name
            or "同学"
        )

        # 2. Fetch JD diagnoses (latest 5)
        jd_rows = (
            db.query(JDDiagnosis)
            .filter_by(profile_id=profile_id)
            .order_by(JDDiagnosis.created_at.desc())
            .limit(5)
            .all()
        )

        # 3. Fetch interview reviews (latest 20)
        review_rows = (
            db.query(InterviewReview)
            .filter_by(profile_id=profile_id)
            .order_by(InterviewReview.created_at.desc())
            .limit(20)
            .all()
        )

        # 4. Fetch latest checklist
        checklist = (
            db.query(InterviewChecklist)
            .filter_by(profile_id=profile_id)
            .order_by(InterviewChecklist.created_at.desc())
            .first()
        )

        # 5. Fetch career goal (scoped to this user)
        career_goal = (
            db.query(CareerGoal)
            .filter_by(profile_id=profile_id, user_id=profile.user_id, is_active=True)
            .order_by(CareerGoal.set_at.desc())
            .first()
        )

        # 6. Fetch finished mock interview sessions (latest 5)
        mock_rows = (
            db.query(MockInterviewSession)
            .filter_by(profile_id=profile_id, status="finished")
            .order_by(MockInterviewSession.created_at.desc())
            .limit(5)
            .all()
        )

        # 7. Compute escape routes dynamically from graph
        escape_routes = self._load_escape_routes(profile_id, profile.user_id, db)

        # Build chapters
        ch1 = self._build_ability_chapter(profile_data)
        ch2 = self._build_job_match_chapter(jd_rows)
        ch3 = self._build_career_path_chapter(escape_routes, career_goal)
        ch4 = self._build_action_plan_chapter(jd_rows, review_rows, checklist, career_goal, mock_rows)
        ch5 = self._build_interview_chapter(review_rows, mock_rows)

        chapters = [ch1, ch2, ch3, ch4, ch5]

        # Compute summary stats
        latest_jd = jd_rows[0] if jd_rows else None
        target_job = "未设定"
        match_score = 0
        if career_goal:
            target_job = career_goal.target_label or "未设定"
        if latest_jd:
            if target_job == "未设定":
                target_job = latest_jd.jd_title or "未设定"
            match_score = latest_jd.match_score or 0

        # Version & previous report
        prev_report = self._get_previous_report(profile.user_id, db)
        report_version = (prev_report.get("report_version", 0) + 1) if prev_report else 1

        # LLM narrative (structured per-chapter analysis)
        narrative = self._generate_narrative(
            chapters, student_name, target_job, prev_report,
        )
        markdown = self._narrative_to_markdown(narrative) if narrative else None

        # Build report payload
        report_key = f"v2_{profile_id}_{int(datetime.now(timezone.utc).timestamp())}"
        report_payload = {
            "id": report_key,
            "version": "v2",
            "report_version": report_version,
            "title": f"{student_name}的职业发展报告",
            "summary": self._build_summary(student_name, target_job, match_score, len(review_rows)),
            "student_name": student_name,
            "target_job": target_job,
            "match_score": match_score,
            "profile_id": profile_id,
            "chapters": chapters,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "report_source": "v2",
        }
        if narrative:
            report_payload["narrative"] = narrative
        if markdown:
            report_payload["markdown"] = markdown

        # Persist
        row = Report(
            report_key=report_key,
            user_id=profile.user_id,
            title=report_payload["title"],
            summary=report_payload["summary"],
            data_json=json.dumps(report_payload, ensure_ascii=False, default=str),
        )
        db.add(row)
        db.commit()

        return {"report_key": report_key, "data": report_payload}

    # ── Public data-gathering (used by agent tools) ──────────────────────

    def gather_report_data(self, profile_id: int, db: Session) -> str:
        """Collect report material and return structured text for LLM consumption.

        This is the single source of truth for data aggregation.
        Agent tools should call this instead of reimplementing queries.
        """
        from backend.db_models import (
            Profile as ProfileModel,
            JDDiagnosis,
            InterviewReview,
            CareerGoal,
        )
        from backend.services.dashboard_service import get_dashboard_stats

        profile = db.query(ProfileModel).filter_by(id=profile_id).first()
        if not profile:
            return f"未找到画像 #{profile_id}。"

        profile_data = json.loads(profile.profile_json or "{}")
        quality_data = json.loads(profile.quality_json or "{}")

        jd_rows = (
            db.query(JDDiagnosis)
            .filter_by(profile_id=profile_id)
            .order_by(JDDiagnosis.created_at.desc())
            .limit(5)
            .all()
        )

        review_rows = (
            db.query(InterviewReview)
            .filter_by(profile_id=profile_id)
            .order_by(InterviewReview.created_at.desc())
            .limit(10)
            .all()
        )

        goal = (
            db.query(CareerGoal)
            .filter_by(user_id=profile.user_id, is_active=True)
            .order_by(CareerGoal.set_at.desc())
            .first()
        )

        stats = get_dashboard_stats(profile_id, db)

        return self._format_report_text(
            profile, profile_data, quality_data,
            jd_rows, review_rows, goal, stats,
        )

    # ── Internal text formatter ────────────────────────────────────────

    @staticmethod
    def _format_report_text(
        profile: Any,
        profile_data: dict,
        quality_data: dict,
        jd_rows: list,
        review_rows: list,
        goal: Any,
        stats: dict,
    ) -> str:
        """Format gathered data into structured text sections for LLM."""
        sections: list[str] = []

        # ── Section 1: 能力画像 ──
        sections.append("【第一章：能力画像】")
        sections.append(f"姓名: {profile.name}")
        sections.append(f"来源: {'简历解析' if profile.source == 'resume' else '手动填写'}")

        skills = profile_data.get("skills", [])
        if skills:
            skill_lines = []
            for s in skills:
                if isinstance(s, dict):
                    skill_lines.append(f"{s.get('name', '')}({s.get('level', '')})")
                else:
                    skill_lines.append(str(s))
            sections.append(f"技能({len(skills)}项): {', '.join(skill_lines)}")

        knowledge = profile_data.get("knowledge_areas", [])
        if knowledge:
            sections.append(f"知识领域: {', '.join(knowledge)}")

        edu = profile_data.get("education", {})
        if isinstance(edu, dict) and edu:
            sections.append(f"教育: {edu.get('degree', '')} {edu.get('major', '')} {edu.get('school', '')}")

        projects = profile_data.get("projects", [])
        if projects:
            sections.append(f"项目经历({len(projects)}个):")
            for p in projects[:5]:
                if isinstance(p, dict):
                    sections.append(f"  · {p.get('name', '')} — {p.get('description', '')[:80]}")
                else:
                    sections.append(f"  · {str(p)[:80]}")

        awards = profile_data.get("awards", [])
        if awards:
            sections.append(f"竞赛/荣誉({len(awards)}项): {', '.join(str(a) for a in awards[:8])}")

        completeness = quality_data.get("completeness", 0)
        competitiveness = quality_data.get("competitiveness", 0)
        if completeness <= 1:
            completeness = round(completeness * 100)
        if competitiveness <= 1:
            competitiveness = round(competitiveness * 100)
        sections.append(f"画像完整度: {completeness}%，竞争力: {competitiveness}")

        # ── Section 2: JD诊断 ──
        sections.append("\n【第二章：岗位匹配】")
        if jd_rows:
            for jd in jd_rows:
                result = json.loads(jd.result_json or "{}")
                sections.append(f"  JD「{jd.jd_title or '未命名'}」 匹配度: {jd.match_score}%")
                dims = result.get("dimensions", {})
                if dims:
                    for key in ["basic", "skills", "qualities", "potential"]:
                        d = dims.get(key, {})
                        if d:
                            sections.append(f"    {d.get('label', key)}: {d.get('score', 0)}分 — {d.get('detail', '')}")
                matched = result.get("matched_skills", [])
                gap = result.get("gap_skills", [])
                if matched:
                    sections.append(f"    已匹配: {', '.join(matched[:10])}")
                if gap:
                    gap_names = [g.get("skill", str(g)) if isinstance(g, dict) else str(g) for g in gap[:8]]
                    sections.append(f"    缺口: {', '.join(gap_names)}")
                tips = result.get("resume_tips", [])
                if tips:
                    sections.append(f"    简历建议: {'; '.join(tips[:3])}")
        else:
            sections.append("  尚无JD诊断记录。")

        # ── Section 3: 发展路径 ──
        sections.append("\n【第三章：发展路径】")
        if goal:
            sections.append(f"  目标岗位: {goal.target_label}")
            sections.append(f"  目标区域: {goal.target_zone}")
            if goal.gap_skills:
                gap_s = goal.gap_skills if isinstance(goal.gap_skills, list) else []
                sections.append(f"  差距技能: {', '.join(str(g.get('name', g)) if isinstance(g, dict) else str(g) for g in gap_s[:8])}")
            if goal.total_hours:
                sections.append(f"  预计学习时长: {goal.total_hours} 小时")
            if goal.salary_p50:
                sections.append(f"  目标薪资中位数: ¥{goal.salary_p50}")
        else:
            sections.append("  尚未设定职业目标。建议先在岗位图谱中探索方向。")

        # ── Section 4: 面试记录 ──
        sections.append("\n【第四章：面试训练】")
        if review_rows:
            total_score = 0
            for r in review_rows:
                analysis = json.loads(r.analysis_json or "{}")
                score = analysis.get("score", 0)
                total_score += score
                strengths = analysis.get("strengths", [])
                weaknesses = analysis.get("weaknesses", [])
                s_text = "; ".join(str(s.get("point", s)) if isinstance(s, dict) else str(s) for s in strengths[:2])
                w_text = "; ".join(str(w.get("point", w)) if isinstance(w, dict) else str(w) for w in weaknesses[:2])
                sections.append(f"  题目: {r.question_text[:60]}  得分: {score}")
                if s_text:
                    sections.append(f"    亮点: {s_text}")
                if w_text:
                    sections.append(f"    不足: {w_text}")
            avg = round(total_score / len(review_rows)) if review_rows else 0
            sections.append(f"  平均分: {avg}，共 {len(review_rows)} 次练习")
        else:
            sections.append("  尚无面试练习记录。")

        # ── Section 5: 成长数据 ──
        sections.append("\n【第五章：行动计划与成长】")
        sections.append(f"  JD诊断次数: {stats.get('jd_diagnosis_count', 0)}")
        sections.append(f"  面试练习次数: {stats.get('review_count', 0)}")
        sections.append(f"  连续活跃天数: {stats.get('streak_days', 0)}")

        checklist = stats.get("checklist_progress")
        if checklist:
            sections.append(f"  备战清单进度: {checklist.get('passed', 0)}/{checklist.get('total', 0)} ({checklist.get('progress', 0)}%)")

        curve = stats.get("progress_curve", [])
        if curve:
            recent = curve[-5:]
            pts = [f"{p.get('type','?')}:{p.get('score',0)}" for p in recent]
            sections.append(f"  最近得分趋势: {' → '.join(pts)}")

        return "\n".join(sections)

    # ── Chapter builders ────────────────────────────────────────────────

    def _build_ability_chapter(self, profile_data: dict) -> dict:
        """Chapter 1: Ability Profile."""
        skills = profile_data.get("skills", [])
        basic = profile_data.get("basic_info", {})
        education = profile_data.get("education", [])
        experience = profile_data.get("experience", [])

        normalized_skills = []
        for s in skills:
            if isinstance(s, str):
                normalized_skills.append({"name": s, "level": "intermediate"})
            elif isinstance(s, dict):
                normalized_skills.append({
                    "name": s.get("name") or s.get("skill", ""),
                    "level": s.get("level", "intermediate"),
                })

        level_counts = {"advanced": 0, "intermediate": 0, "beginner": 0}
        for s in normalized_skills:
            lv = s.get("level", "intermediate")
            if lv in level_counts:
                level_counts[lv] += 1

        knowledge_areas = profile_data.get("knowledge_areas", [])
        awards = profile_data.get("awards", [])
        has_data = bool(normalized_skills or basic or education)

        return {
            "key": "ability",
            "title": "能力画像",
            "subtitle": "技能分布与职业背景",
            "has_data": has_data,
            "locked_hint": "上传简历建立画像后解锁本章",
            "data": {
                "name": basic.get("name", ""),
                "current_title": basic.get("current_title", ""),
                "degree": basic.get("degree", ""),
                "major": basic.get("major", ""),
                "education": education[:3] if isinstance(education, list) else [],
                "experience": experience[:5] if isinstance(experience, list) else [],
                "skills": normalized_skills,
                "level_counts": level_counts,
                "total_skills": len(normalized_skills),
                "knowledge_areas": knowledge_areas,
                "awards": awards,
            },
        }

    def _build_job_match_chapter(self, jd_rows: list) -> dict:
        """Chapter 2: Job Match."""
        if not jd_rows:
            return {
                "key": "job_match",
                "title": "岗位匹配",
                "subtitle": "JD 诊断结果与技能缺口",
                "has_data": False,
                "locked_hint": "完成 JD 诊断后解锁本章",
                "data": {},
            }

        latest = jd_rows[0]
        result = json.loads(latest.result_json or "{}")

        trend = []
        for jd in reversed(jd_rows):
            trend.append({
                "date": jd.created_at.isoformat() if jd.created_at else "",
                "score": jd.match_score or 0,
                "title": jd.jd_title or "",
            })

        return {
            "key": "job_match",
            "title": "岗位匹配",
            "subtitle": "人岗匹配分析",
            "has_data": True,
            "data": {
                "jd_title": latest.jd_title or "未命名 JD",
                "match_score": latest.match_score or 0,
                "matched_skills": result.get("matched_skills", []),
                "missing_skills": result.get("missing_skills", []),
                "verdict": result.get("verdict", ""),
                "resume_tips": result.get("resume_tips", []),
                "trend": trend,
            },
        }

    _TREND_MAP: dict = {
        "safe":       {"label": "AI 安全区", "insight": "该岗位对人类判断力需求较高，社会用人需求稳定，AI 短期内难以全面替代，就业前景相对可期。"},
        "leverage":   {"label": "AI 杠杆区", "insight": "该岗位可借助 AI 工具大幅提升产出效率，人机协作是核心竞争力，掌握 AI 工具者具备显著优势。"},
        "transition": {"label": "AI 过渡区", "insight": "该岗位处于技术迭代活跃期，部分工作内容已被 AI 辅助替代，需持续更新技能以保持市场竞争力。"},
        "danger":     {"label": "AI 高风险区", "insight": "该岗位面临较高 AI 自动化压力，行业需求可能趋于收缩，差异化能力与跨方向逃逸路线是关键应对策略。"},
    }

    def _build_career_path_chapter(
        self, escape_routes: list, career_goal: Any = None
    ) -> dict:
        """Chapter 3: Career Path."""
        goal_data = None
        if career_goal:
            goal_data = {
                "target_label": career_goal.target_label,
                "target_zone": career_goal.target_zone,
                "gap_skills": career_goal.gap_skills or [],
                "total_hours": career_goal.total_hours,
                "safety_gain": career_goal.safety_gain,
                "salary_p50": career_goal.salary_p50,
                "tag": career_goal.tag,
                "transition_probability": career_goal.transition_probability,
            }

        # Derive industry trend insight from zone
        trend_zone = (
            (career_goal.target_zone if career_goal and career_goal.target_zone else None)
            or (escape_routes[0].get("target_zone") if escape_routes else None)
            or "transition"
        )
        trend_insight = self._TREND_MAP.get(trend_zone, self._TREND_MAP["transition"])

        has_data = bool(escape_routes) or goal_data is not None

        return {
            "key": "career_path",
            "title": "发展路径",
            "subtitle": "目标方向与行业趋势分析",
            "has_data": has_data,
            "locked_hint": "上传简历建立画像后自动解锁本章",
            "data": {
                "goal": goal_data,
                "escape_routes": escape_routes[:5] if escape_routes else [],
                "trend_insight": trend_insight,
            },
        }

    def _build_action_plan_chapter(
        self, jd_rows: list, review_rows: list,
        checklist: Any, career_goal: Any = None, mock_rows: list | None = None,
    ) -> dict:
        """Chapter 4: Action Plan."""
        action_items: list[dict] = []

        # From career goal gap skills
        if career_goal and career_goal.gap_skills:
            for gs in career_goal.gap_skills:
                skill_name = gs.get("name", "") if isinstance(gs, dict) else str(gs)
                if skill_name:
                    action_items.append({
                        "source": "goal_gap",
                        "skill": skill_name,
                        "detail": f"目标方向「{career_goal.target_label}」所需技能",
                        "priority": "high",
                    })

        # From JD skill gaps
        if jd_rows:
            latest_result = json.loads(jd_rows[0].result_json or "{}")
            for ms in latest_result.get("missing_skills", []):
                skill_name = ms.get("skill", "") if isinstance(ms, dict) else str(ms)
                action_items.append({
                    "source": "jd_gap",
                    "skill": skill_name,
                    "detail": ms.get("reason", "") if isinstance(ms, dict) else "",
                    "priority": "high",
                })

        # From mock interview skill gaps (highest confidence gaps)
        seen_skills = {a["skill"].lower() for a in action_items}
        if mock_rows:
            latest_mock_analysis = json.loads(mock_rows[0].analysis_json or "{}")
            mock_target_job = mock_rows[0].target_job or "模拟面试"
            for gap in latest_mock_analysis.get("skill_gaps", []):
                gap_str = gap if isinstance(gap, str) else str(gap)
                if gap_str.lower() not in seen_skills:
                    action_items.append({
                        "source": "mock_gap",
                        "skill": gap_str,
                        "detail": f"模拟面试「{mock_target_job}」中真实暴露的技能缺口",
                        "priority": "high",
                    })
                    seen_skills.add(gap_str.lower())

        # From interview review weaknesses
        for r in review_rows[:10]:
            analysis = json.loads(r.analysis_json or "{}")
            for w in analysis.get("weaknesses", []):
                point = w.get("point", "") if isinstance(w, dict) else str(w)
                suggestion = w.get("suggestion", "") if isinstance(w, dict) else ""
                if point.lower() not in seen_skills:
                    action_items.append({
                        "source": "review",
                        "skill": point,
                        "detail": suggestion,
                        "priority": "medium",
                    })
                    seen_skills.add(point.lower())

        # Checklist progress
        checklist_data = None
        if checklist:
            items = checklist.items or []
            total = len(items)
            passed = sum(1 for i in items if i.get("status") in ("can_answer", "learned"))
            checklist_data = {
                "total": total,
                "passed": passed,
                "progress": round(passed / total * 100) if total else 0,
                "jd_title": checklist.jd_title or "",
            }

        has_data = bool(action_items) or checklist_data is not None

        short_term = [a for a in action_items if a["priority"] == "high"][:10]
        mid_term = [a for a in action_items if a["priority"] == "medium"][:10]

        return {
            "key": "action_plan",
            "title": "行动计划",
            "subtitle": "分阶段成长规划与评估周期",
            "has_data": has_data,
            "locked_hint": "完成 JD 诊断或面试复盘后解锁本章",
            "data": {
                "items": action_items[:20],
                "short_term": short_term,
                "mid_term": mid_term,
                "checklist": checklist_data,
                "evaluation_schedule": {
                    "short_term_label": "4 周",
                    "mid_term_label": "3 个月",
                    "review_hint": "建议 4 周后重新进行 JD 诊断，评估短期技能提升成效；3 个月后重新生成完整报告，进行阶段性职业规划复盘。",
                },
            },
        }

    def _build_interview_chapter(self, review_rows: list, mock_rows: list | None = None) -> dict:
        """Chapter 5: Interview Records — includes both single-Q reviews and full mock sessions."""
        mock_sessions = []
        for m in (mock_rows or [])[:3]:
            analysis = json.loads(m.analysis_json or "{}")
            mock_sessions.append({
                "id": m.id,
                "target_job": m.target_job,
                "overall_score": analysis.get("overall_score", 0),
                "overall_feedback": analysis.get("overall_feedback", ""),
                "dimensions": analysis.get("dimensions", []),
                "skill_gaps": analysis.get("skill_gaps", []),
                "date": m.created_at.isoformat() if m.created_at else "",
            })

        if not review_rows and not mock_sessions:
            return {
                "key": "interview",
                "title": "面试记录",
                "subtitle": "模拟面试与复盘历史",
                "has_data": False,
                "locked_hint": "完成模拟面试或单题复盘后解锁本章",
                "data": {},
            }

        records = []
        total_score = 0
        for r in review_rows:
            analysis = json.loads(r.analysis_json or "{}")
            score = analysis.get("score", 0)
            total_score += score
            records.append({
                "id": r.id,
                "question": r.question_text[:100],
                "target_job": r.target_job or "",
                "score": score,
                "strengths": analysis.get("strengths", [])[:3],
                "weaknesses": analysis.get("weaknesses", [])[:3],
                "date": r.created_at.isoformat() if r.created_at else "",
            })

        avg_score = round(total_score / len(records)) if records else 0

        return {
            "key": "interview",
            "title": "面试记录",
            "subtitle": "模拟面试与复盘历史",
            "has_data": True,
            "data": {
                "records": records,
                "avg_score": avg_score,
                "total_count": len(records),
                "mock_sessions": mock_sessions,
            },
        }

    # ── LLM narrative ───────────────────────────────────────────────────

    def _get_previous_report(self, user_id: int, db: Session) -> dict | None:
        """Return key metrics from the user's most recent report."""
        from backend.db_models import Report

        prev = (
            db.query(Report)
            .filter(Report.user_id == user_id)
            .order_by(Report.created_at.desc())
            .first()
        )
        if not prev:
            return None
        data = json.loads(prev.data_json or "{}")
        return {
            "summary": prev.summary,
            "match_score": data.get("match_score", 0),
            "report_version": data.get("report_version", 1),
            "created_at": str(prev.created_at),
        }

    def _generate_narrative(
        self,
        chapters: list[dict],
        student_name: str,
        target_job: str,
        prev_report: dict | None,
    ) -> dict | None:
        """Call LLM to produce structured per-chapter narrative analysis.

        Returns a dict like:
          {"summary": "...", "comparison": "...|null",
           "chapters": {"ability": "...", ...}, "actions": ["...", ...]}
        or None on failure.
        """
        system_prompt = (
            "你是一位资深职业发展顾问，擅长为大学生撰写专业的职业发展报告。\n"
            "文风简洁专业、有洞察力，避免空话和鸡汤。\n"
            "像经验丰富的学长/导师，直说问题不回避短板，建议具体到「去做什么」。\n\n"
            "技能等级参考（须结合证据校准，不得直接接受自述）：\n"
            "advanced≈高级(须有开源/竞赛/工作经验等硬性证据), intermediate≈中级(须有实质项目), familiar≈了解, beginner≈入门\n"
            "注意：简历解析的技能等级来自自述，可能偏高。分析时须结合 experience_years 和项目深度校准；\n"
            "对于 experience_years=0 的在校生，'advanced' 级别极少合理，应审慎使用'精通'等强词，\n"
            "改用'简历标注较高，需项目实践验证'等表述，并指出需要补充的证据。\n\n"
            "【严格禁止】：\n"
            "- 若 target_job 为空或'未设定'，禁止自行推测或编造任何职业方向（如'自动驾驶算法工程师'等），\n"
            "  应在 summary 中提示用户先在图谱页设定目标岗位，career_path 章节设为 null。\n"
            "- 分析建议必须基于简历中实际存在的项目/技能/经历，不得引入简历未提及的能力方向。\n\n"
            "返回 JSON，严格遵循以下结构：\n"
            "{\n"
            '  "summary": "3-4句总结（准备度评估+核心优势+最大缺口）",\n'
            '  "comparison": "与上次对比分析（无上一版数据则设为null）",\n'
            '  "chapters": {\n'
            '    "ability": "能力分析200-300字（无数据则null）",\n'
            '    "job_match": "匹配分析200-300字（无数据则null）",\n'
            '    "career_path": "路径分析200-300字，需结合行业社会需求与AI时代趋势（基于zone数据），分析该职业的发展前景（target_job为空则null）",\n'
            '    "action_plan": "行动计划分析200-300字，需明确短期（4周）和中期（3个月）的评估节点与成功指标，给出可量化的阶段性目标（无数据则null）",\n'
            '    "interview": "面试分析200-300字，需综合模拟面试（mock_sessions）和单题复盘（records）两类数据，重点分析模拟面试的综合得分、维度表现与技能缺口（无数据则null）"\n'
            "  },\n"
            '  "actions": ["具体行动建议1（带优先级）", "建议2", "建议3"]\n'
            "}\n\n"
            "规则：\n"
            "1. 无数据的章节值设为 null，不要编造\n"
            "2. 分析数据背后的含义，不要简单复述数据\n"
            "3. 建议要具体到「去做什么」，且必须基于简历中真实存在的背景\n"
            "4. 全文不超过1500字"
        )

        user_content = json.dumps(
            {
                "student_name": student_name,
                "target_job": target_job,
                "chapters": [
                    {
                        "key": ch["key"],
                        "title": ch["title"],
                        "has_data": ch["has_data"],
                        "data": ch["data"] if ch["has_data"] else None,
                    }
                    for ch in chapters
                ],
                "previous_report": prev_report,
            },
            ensure_ascii=False,
            default=str,
        )

        try:
            result = llm_chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                model=get_model("strong"),
                temperature=0.5,
                timeout=120,
            )
        except Exception as exc:
            logger.warning("LLM narrative call failed: %s", exc)
            return None

        if not result:
            return None

        parsed = parse_json_response(result)
        if not isinstance(parsed, dict) or "summary" not in parsed:
            logger.warning("LLM narrative returned invalid JSON (len=%d)", len(result))
            return None

        return parsed

    @staticmethod
    def _narrative_to_markdown(narrative: dict) -> str:
        """Convert structured narrative dict to a markdown string (for export)."""
        lines: list[str] = []

        if narrative.get("summary"):
            lines.append(narrative["summary"])
            lines.append("")

        if narrative.get("comparison"):
            lines.append("## 与上次相比")
            lines.append(narrative["comparison"])
            lines.append("")

        chapter_titles = {
            "ability": "能力画像",
            "job_match": "岗位匹配",
            "career_path": "发展路径",
            "action_plan": "行动计划",
            "interview": "面试记录",
        }
        for key, title in chapter_titles.items():
            text = narrative.get("chapters", {}).get(key)
            if text:
                lines.append(f"## {title}")
                lines.append(text)
                lines.append("")

        actions = narrative.get("actions", [])
        if actions:
            lines.append("## 下一步行动")
            for i, action in enumerate(actions, 1):
                lines.append(f"{i}. {action}")
            lines.append("")

        return "\n".join(lines)

    # ── Helpers ──────────────────────────────────────────────────────────

    def _load_escape_routes(self, profile_id: int, user_id: int, db: Session) -> list[dict]:
        """Compute escape routes dynamically from CareerGoal + graph service."""
        from backend.db_models import CareerGoal
        from backend.services.graph_service import get_graph_service

        # Find user's active career goal to get from_node_id
        goal = (
            db.query(CareerGoal)
            .filter_by(user_id=user_id, profile_id=profile_id, is_active=True)
            .first()
        )
        if not goal or not goal.from_node_id:
            return []

        try:
            graph = get_graph_service(db)
            raw_routes = graph.find_escape_routes(goal.from_node_id, db_session=db)
            return [
                {
                    "target_node_id": r.get("target", ""),
                    "target_label": r.get("target_label", ""),
                    "target_zone": r.get("target_zone", "transition"),
                    "gap_skills": [g["name"] if isinstance(g, dict) else str(g) for g in r.get("gap_skills", [])],
                    "estimated_hours": r.get("total_hours", 0),
                    "safety_gain": r.get("safety_gain", 0),
                    "salary_p50": r.get("salary_p50", 0),
                    "tag": r.get("tag", ""),
                }
                for r in raw_routes
            ]
        except Exception as exc:
            logger.warning("Failed to compute escape routes: %s", exc)
            return []

    @staticmethod
    def _build_summary(
        name: str, target_job: str, score: int, review_count: int
    ) -> str:
        """Generate report summary text."""
        parts = [f"{name}的职业发展报告"]
        if target_job:
            parts.append(f"目标岗位「{target_job}」")
        if score > 0:
            parts.append(f"匹配度 {score}%")
        if review_count > 0:
            parts.append(f"已复盘 {review_count} 道面试题")
        return "，".join(parts) + "。"
