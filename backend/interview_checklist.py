# -*- coding: utf-8 -*-
"""
面试通关清单构建与管理。

build_checklist()  — 从 JD 诊断结果构建清单
update_item()      — 更新单题状态
checklist_stats()  — 计算进度统计
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from backend.db_models import InterviewQuestion, InterviewChecklist, JobNode

logger = logging.getLogger(__name__)

MAX_ITEMS = 15
MIN_ITEMS = 5


def _template_question(skill: str, job_label: str) -> dict:
    """为没有题库覆盖的技能生成模板题目。"""
    return {
        "question_id": None,
        "question": f"请解释{skill}的核心概念，以及它在{job_label}岗位中的典型应用场景。",
        "skill": skill,
        "type": "technical",
        "difficulty": "medium",
        "status": "not_assessed",
        "source": "template",
        "answer_key": None,
        "resource_url": None,
        "practice_task": None,
    }


def _question_to_item(q: InterviewQuestion) -> dict:
    return {
        "question_id": q.id,
        "question": q.question,
        "skill": q.skill_tag,
        "type": q.question_type,
        "difficulty": q.difficulty,
        "status": "not_assessed",
        "source": q.source,
        "answer_key": q.answer_key,
        "resource_url": q.resource_url,
        "practice_task": q.practice_task,
    }


def build_checklist(
    profile_id: int,
    target_node_id: str,
    jd_title: str,
    missing_skills: list[dict | str],
    diagnosis_id: int | None,
    db: Session,
) -> InterviewChecklist:
    """从 JD 诊断结果构建面试通关清单。"""
    # 获取目标岗位信息
    node = db.query(JobNode).filter_by(node_id=target_node_id).first()
    job_label = node.label if node else target_node_id

    # 提取缺失技能名
    missing_names: list[str] = []
    for s in missing_skills:
        name = s.get("skill", s) if isinstance(s, dict) else str(s)
        if name and name.strip():
            missing_names.append(name.strip())

    items: list[dict] = []
    covered_skills: set[str] = set()

    # Step 1: 从题库中查询目标岗位的题目（优先 imported > generated）
    bank = (
        db.query(InterviewQuestion)
        .filter(InterviewQuestion.node_id == target_node_id)
        .order_by(
            # imported 排前面
            InterviewQuestion.source.asc(),
            InterviewQuestion.difficulty.asc(),
        )
        .all()
    )

    # 优先取 missing_skills 相关的题
    for q in bank:
        if q.skill_tag.lower() in {s.lower() for s in missing_names}:
            items.append(_question_to_item(q))
            covered_skills.add(q.skill_tag.lower())
            if len(items) >= MAX_ITEMS:
                break

    # 补充其他题库题目
    if len(items) < MAX_ITEMS:
        for q in bank:
            if q.skill_tag.lower() not in covered_skills:
                items.append(_question_to_item(q))
                covered_skills.add(q.skill_tag.lower())
                if len(items) >= MAX_ITEMS:
                    break

    # Step 2: 对没有题库覆盖的 missing_skills 用模板补充
    if len(items) < MAX_ITEMS:
        for skill in missing_names:
            if skill.lower() not in covered_skills:
                items.append(_template_question(skill, job_label))
                covered_skills.add(skill.lower())
                if len(items) >= MAX_ITEMS:
                    break

    # 按难度排序: easy → medium → hard
    diff_order = {"easy": 0, "medium": 1, "hard": 2}
    items.sort(key=lambda x: diff_order.get(x.get("difficulty", "medium"), 1))

    # 给每个 item 分配序号
    for i, item in enumerate(items):
        item["index"] = i

    checklist = InterviewChecklist(
        profile_id=profile_id,
        diagnosis_id=diagnosis_id,
        target_node_id=target_node_id,
        jd_title=jd_title,
        items=items,
    )
    db.add(checklist)
    db.commit()
    db.refresh(checklist)
    return checklist


def update_item_status(
    checklist_id: int,
    item_index: int,
    new_status: str,
    db: Session,
) -> InterviewChecklist | None:
    """更新清单中某题的状态。"""
    valid = {"not_assessed", "can_answer", "unsure", "cannot", "learned"}
    if new_status not in valid:
        return None

    cl = db.query(InterviewChecklist).filter_by(id=checklist_id).first()
    if not cl:
        return None

    items = list(cl.items)  # 拷贝 JSON
    if item_index < 0 or item_index >= len(items):
        return None

    items[item_index]["status"] = new_status
    if new_status == "learned":
        items[item_index]["learned_at"] = datetime.now(timezone.utc).isoformat()
    if new_status in ("can_answer", "unsure", "cannot"):
        items[item_index]["assessed_at"] = datetime.now(timezone.utc).isoformat()

    cl.items = items
    # Force SQLAlchemy to detect JSON change
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(cl, "items")
    db.commit()
    db.refresh(cl)
    return cl


def checklist_stats(checklist: InterviewChecklist) -> dict:
    """计算清单进度统计。"""
    items = checklist.items or []
    total = len(items)
    counts = {"not_assessed": 0, "can_answer": 0, "unsure": 0, "cannot": 0, "learned": 0}
    for item in items:
        s = item.get("status", "not_assessed")
        counts[s] = counts.get(s, 0) + 1

    passed = counts["can_answer"] + counts["learned"]
    progress = round(passed / total * 100) if total else 0

    return {
        "total": total,
        "passed": passed,
        "progress": progress,
        **counts,
    }
