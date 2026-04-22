#!/usr/bin/env python3
"""预生成面试题库 — 为每个方向批量生成高质量题目存入数据库。

用法:
    cd /path/to/project
    python scripts/generate_question_bank.py --directions all --per-direction 30
    python scripts/generate_question_bank.py --directions cpp-system-dev,java-backend --per-direction 20
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime

# Add parent to path so we can import backend
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.db import SessionLocal
from backend.models import InterviewQuestionBank
from backend.services.interview.skill_loader import build_prompt, load_skill_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ALL_DIRECTIONS = [
    "cpp-system-dev",
    "frontend-dev",
    "java-backend",
    "algorithm",
    "product-manager",
    "test-development",
]


def _generate_via_llm(skill_id: str, count: int = 5) -> list[dict]:
    """Call LLM to generate questions for a skill."""
    from backend.llm import get_llm_client, get_model

    system_prompt, user_prompt = build_prompt(
        skill_id=skill_id,
        resume_text="（未提供简历，请生成通用技术面试题）",
        difficulty="mid",
        question_count=count,
        follow_up_count=2,
    )

    resp = get_llm_client(timeout=120).chat.completions.create(
        model=get_model("strong"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.5,
        max_tokens=4000,
    )

    raw = resp.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    questions = json.loads(raw.strip())
    if not isinstance(questions, list):
        raise ValueError(f"Expected list, got {type(questions).__name__}")
    return questions


def _deduplicate(questions: list[dict], existing_topics: set[str]) -> list[dict]:
    """Filter out questions whose topic_summary already exists."""
    result = []
    for q in questions:
        topic = q.get("focus_area", "")
        if topic and topic in existing_topics:
            logger.info("Skipping duplicate topic: %s", topic[:60])
            continue
        existing_topics.add(topic)
        result.append(q)
    return result


def generate_for_direction(skill_id: str, per_direction: int, batch_size: int = 5) -> int:
    """Generate questions for one direction and save to DB."""
    db = SessionLocal()
    try:
        # Load existing topics for deduplication
        existing = (
            db.query(InterviewQuestionBank.topic_summary)
            .filter(InterviewQuestionBank.skill_id == skill_id)
            .all()
        )
        existing_topics = {row.topic_summary for row in existing}
        logger.info("[%s] Existing topics: %d", skill_id, len(existing_topics))

        generated = 0
        attempts = 0
        max_attempts = (per_direction // batch_size + 2) * 3  # generous retry budget

        while generated < per_direction and attempts < max_attempts:
            attempts += 1
            try:
                questions = _generate_via_llm(skill_id, batch_size)
                questions = _deduplicate(questions, existing_topics)

                for q in questions:
                    if generated >= per_direction:
                        break

                    row = InterviewQuestionBank(
                        skill_id=skill_id,
                        category=q.get("category", "GENERAL"),
                        difficulty=q.get("difficulty", "medium"),
                        question=q.get("question", ""),
                        focus_area=q.get("focus_area", ""),
                        follow_ups=json.dumps(q.get("follow_ups", []), ensure_ascii=False),
                        topic_summary=q.get("focus_area", ""),
                        generated_by="llm",
                    )
                    db.add(row)
                    generated += 1

                db.commit()
                logger.info("[%s] Batch %d: generated %d, total %d/%d", skill_id, attempts, len(questions), generated, per_direction)

            except Exception as exc:
                logger.error("[%s] Batch %d failed: %s", skill_id, attempts, exc)
                db.rollback()
                continue

        logger.info("[%s] Done. Generated %d new questions.", skill_id, generated)
        return generated

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Pre-generate interview question bank")
    parser.add_argument(
        "--directions",
        type=str,
        default="all",
        help="Comma-separated skill IDs, or 'all'",
    )
    parser.add_argument(
        "--per-direction",
        type=int,
        default=30,
        help="How many questions to generate per direction",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5,
        help="LLM calls generate this many questions at once",
    )
    args = parser.parse_args()

    directions = ALL_DIRECTIONS if args.directions == "all" else args.directions.split(",")

    total = 0
    for skill_id in directions:
        skill_id = skill_id.strip()
        if not skill_id:
            continue
        try:
            # Validate skill exists
            load_skill_config(skill_id)
        except FileNotFoundError:
            logger.warning("Skill not found: %s, skipping", skill_id)
            continue

        logger.info("=" * 50)
        logger.info("Generating for: %s", skill_id)
        count = generate_for_direction(skill_id, args.per_direction, args.batch_size)
        total += count

    logger.info("=" * 50)
    logger.info("All done. Total generated: %d", total)


if __name__ == "__main__":
    main()
