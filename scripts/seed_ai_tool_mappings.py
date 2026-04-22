# -*- coding: utf-8 -*-
"""Seed ai_tool_mappings table with known AI tool alternatives for skills.

Run via:
    python -m scripts.seed_ai_tool_mappings
"""
from __future__ import annotations

from backend.db import SessionLocal
from backend.models import AiToolMapping

TOOL_MAPPINGS: list[tuple[str, list[str]]] = [
    # Programming languages — GitHub Copilot, Cursor, Claude
    ("Python", ["GitHub Copilot", "Cursor", "Claude"]),
    ("JavaScript", ["GitHub Copilot", "Cursor", "v0.dev"]),
    ("Java", ["GitHub Copilot", "Cursor", "Tabnine"]),
    ("Go", ["GitHub Copilot", "Cursor"]),
    ("C++", ["GitHub Copilot", "Cursor"]),
    ("Rust", ["GitHub Copilot", "Cursor"]),
    ("PHP", ["GitHub Copilot", "Cursor"]),
    ("TypeScript", ["GitHub Copilot", "Cursor", "v0.dev"]),
    ("SQL", ["GitHub Copilot", "ChatGPT", "Claude"]),
    # Frontend frameworks
    ("React", ["v0.dev", "GitHub Copilot", "Cursor"]),
    ("Vue", ["GitHub Copilot", "Cursor", "v0.dev"]),
    ("Angular", ["GitHub Copilot", "Cursor"]),
    # Testing — AI test generation tools
    ("功能测试", ["Testim", "Applitools", "GitHub Copilot"]),
    ("接口测试", ["GitHub Copilot", "Postman AI", "Claude"]),
    ("自动化测试", ["Testim", "GitHub Copilot", "Cursor"]),
    ("回归测试", ["Testim", "Applitools"]),
    ("测试用例设计", ["GitHub Copilot", "Claude"]),
    ("单元测试", ["GitHub Copilot", "Cursor", "Claude"]),
    ("Selenium", ["Testim", "GitHub Copilot"]),
    # Data
    ("数据分析", ["ChatGPT", "Claude", "Julius AI"]),
    ("数据清洗", ["ChatGPT", "Claude"]),
    ("报表", ["ChatGPT", "Claude", "Julius AI"]),
    # Docs / writing
    ("技术文档", ["Claude", "Notion AI", "GitHub Copilot"]),
    ("文档编写", ["Claude", "Notion AI"]),
    # DevOps
    ("Docker", ["GitHub Copilot", "Cursor"]),
    ("Kubernetes", ["GitHub Copilot", "Cursor"]),
    ("Linux", ["GitHub Copilot", "Claude"]),
    # AI/ML frameworks
    ("TensorFlow", ["GitHub Copilot", "Cursor"]),
    ("PyTorch", ["GitHub Copilot", "Cursor"]),
]


def main() -> None:
    session = SessionLocal()
    try:
        inserted = 0
        updated = 0

        for skill_name, tools in TOOL_MAPPINGS:
            existing = (
                session.query(AiToolMapping)
                .filter_by(skill_name=skill_name)
                .first()
            )
            if existing is None:
                session.add(AiToolMapping(skill_name=skill_name, tools=tools))
                inserted += 1
            else:
                existing.tools = tools
                updated += 1

        session.commit()
        print(f"seed_ai_tool_mappings: inserted={inserted}, updated={updated}, total={inserted + updated}")
    finally:
        session.close()

    from backend.scorer_service import run_rescore
    result = run_rescore("seed_fix")
    print(f"Rescore complete: {result}")


if __name__ == "__main__":
    main()
