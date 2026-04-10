# -*- coding: utf-8 -*-
"""
PracticeService — unified wrapper for interview, review, and checklist modules.

Delegates to existing backend/interview.py, backend/interview_review.py,
backend/interview_checklist.py. No logic rewrite — just a service facade.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class PracticeService:
    """Unified service for interview practice: questions, review, checklist."""

    def analyze_answer(
        self,
        question: str,
        answer: str,
        target_job: str,
        profile_summary: str = "",
        has_jd: bool = False,
    ) -> dict[str, Any]:
        """Analyze a single Q+A pair for interview review.

        Delegates to interview_review.analyze_single_qa().
        Returns {score, strengths, weaknesses, overall_feedback, dimensions}.
        """
        from backend.interview_review import analyze_single_qa

        return analyze_single_qa(question, answer, target_job, profile_summary, has_jd=has_jd)

    def generate_questions(
        self,
        jd_context: dict[str, Any],
        profile: dict[str, Any] | None = None,
        count: int = 5,
    ) -> list[dict[str, Any]]:
        """Generate structured interview questions from JD context + profile.

        Delegates to interview.generate_questions().
        Returns list of question dicts with round, type, question, etc.
        """
        from backend.interview import generate_questions

        return generate_questions(jd_context, profile, count)

    def build_checklist(
        self,
        profile_id: int,
        target_node_id: str,
        jd_title: str,
        missing_skills: list[dict | str],
        diagnosis_id: int | None,
        db: Any,
    ) -> Any:
        """Build an interview checklist from JD diagnosis results.

        Delegates to interview_checklist.build_checklist().
        Returns InterviewChecklist ORM instance.
        """
        from backend.interview_checklist import build_checklist

        return build_checklist(
            profile_id, target_node_id, jd_title,
            missing_skills, diagnosis_id, db,
        )

    def update_checklist_item(
        self,
        checklist_id: int,
        item_index: int,
        status: str,
        db: Any,
    ) -> Any:
        """Update a single checklist item's status.

        Delegates to interview_checklist.update_item_status().
        Returns updated InterviewChecklist or None.
        """
        from backend.interview_checklist import update_item_status

        return update_item_status(checklist_id, item_index, status, db)

    def pick_questions(
        self,
        db: Any,
        skill_tags: list[str] | None = None,
        count: int = 3,
    ) -> list[dict[str, Any]]:
        """Sample questions from the question bank with balanced difficulty."""
        from backend.db_models import InterviewQuestion

        query = db.query(InterviewQuestion)
        if skill_tags:
            query = query.filter(InterviewQuestion.skill_tag.in_(skill_tags))
        questions = query.all()

        import random
        sampled = random.sample(questions, min(count, len(questions)))
        return [
            {
                "round": i + 1,
                "type": q.question_type or "technical",
                "question": q.question_text,
                "focus_skill": q.skill_tag,
                "difficulty": q.difficulty or "medium",
                "answer_key": q.answer_key,
            }
            for i, q in enumerate(sampled)
        ]

    def list_question_tags(self, db: Any) -> list[dict[str, Any]]:
        """List available skill tags with question counts from the question bank.

        Returns [{"tag": str, "count": int}, ...]
        """
        from sqlalchemy import func
        from backend.db_models import InterviewQuestion

        rows = (
            db.query(InterviewQuestion.skill_tag, func.count(InterviewQuestion.id))
            .group_by(InterviewQuestion.skill_tag)
            .order_by(func.count(InterviewQuestion.id).desc())
            .all()
        )
        return [{"tag": tag, "count": cnt} for tag, cnt in rows]

    def checklist_stats(self, checklist: Any) -> dict:
        """Compute progress statistics for a checklist.

        Delegates to interview_checklist.checklist_stats().
        Returns {total, passed, progress, ...status counts}.
        """
        from backend.interview_checklist import checklist_stats

        return checklist_stats(checklist)
