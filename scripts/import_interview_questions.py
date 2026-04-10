# -*- coding: utf-8 -*-
"""
从 CSV 导入管理员维护的面试题到题库。
source 标记为 'imported'（优先级高于 generated）。

用法: python scripts/import_interview_questions.py data/interview_bank.csv
"""
import csv
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db import SessionLocal, engine, Base
from backend.db_models import InterviewQuestion

Base.metadata.create_all(engine)


def import_csv(path: str):
    db = SessionLocal()
    count = 0
    try:
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                q = InterviewQuestion(
                    node_id=row.get("node_id") or None,
                    skill_tag=row.get("skill_tag", "").strip(),
                    question=row.get("question", "").strip(),
                    question_type=row.get("question_type", "technical").strip(),
                    difficulty=row.get("difficulty", "medium").strip(),
                    source="imported",
                    answer_key=row.get("answer_key") or None,
                    resource_url=row.get("resource_url") or None,
                    practice_task=row.get("practice_task") or None,
                )
                if q.question and q.skill_tag:
                    db.add(q)
                    count += 1
        db.commit()
        print(f"Imported {count} questions from {path}")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/import_interview_questions.py <csv_path>")
        sys.exit(1)
    import_csv(sys.argv[1])
