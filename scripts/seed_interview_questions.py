# -*- coding: utf-8 -*-
"""
从图谱节点的 must_skills + core_tasks 生成面试题库。
模板驱动，不调 LLM。管理员可后续通过 CSV 覆盖/补充。

用法: python scripts/seed_interview_questions.py [--dry-run]
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db import SessionLocal, engine, Base
from backend.db_models import JobNode, InterviewQuestion, Base as _B

# 确保表存在
Base.metadata.create_all(engine)

SKILL_TEMPLATES = [
    ("technical", "easy", "请解释{skill}的核心概念，以及它在{job}岗位中的典型应用场景。"),
    ("technical", "medium", "在实际项目中使用{skill}时，常见的坑有哪些？你是怎么避免的？"),
    ("scenario", "medium", "{job}日常工作中会用到{skill}，请描述一个你用{skill}解决实际问题的案例。"),
]

TASK_TEMPLATES = [
    ("scenario", "medium", "作为{job}，你需要{task}。请描述你的思路和关键步骤。"),
    ("scenario", "hard", "在{task}过程中遇到异常情况（如性能瓶颈/需求变更），你会怎么处理？"),
]


def seed(dry_run=False):
    db = SessionLocal()
    try:
        # 清空已有 generated 题目
        if not dry_run:
            db.query(InterviewQuestion).filter_by(source="generated").delete()
            db.commit()

        nodes = db.query(JobNode).all()
        count = 0
        for node in nodes:
            job_label = node.label
            skills = node.must_skills or []
            tasks = node.core_tasks or []

            # 每个 must_skill 生成模板题
            for skill in skills[:8]:  # 取前8个核心技能
                if not skill or not skill.strip():
                    continue
                for qtype, diff, tmpl in SKILL_TEMPLATES:
                    q = InterviewQuestion(
                        node_id=node.node_id,
                        skill_tag=skill.strip(),
                        question=tmpl.format(skill=skill.strip(), job=job_label),
                        question_type=qtype,
                        difficulty=diff,
                        source="generated",
                    )
                    if not dry_run:
                        db.add(q)
                    count += 1

            # 每个 core_task 生成场景题
            for task in tasks[:5]:
                if not task or not task.strip():
                    continue
                for qtype, diff, tmpl in TASK_TEMPLATES:
                    q = InterviewQuestion(
                        node_id=node.node_id,
                        skill_tag="综合",
                        question=tmpl.format(task=task.strip(), job=job_label),
                        question_type=qtype,
                        difficulty=diff,
                        source="generated",
                    )
                    if not dry_run:
                        db.add(q)
                    count += 1

        if not dry_run:
            db.commit()
        print(f"{'[DRY RUN] ' if dry_run else ''}Generated {count} questions for {len(nodes)} nodes")
    finally:
        db.close()


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    seed(dry_run=dry_run)
