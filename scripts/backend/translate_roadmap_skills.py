"""
Batch-translate roadmap skills from English to Chinese using LLM.

Reads:  data/roadmap_skills.json
Writes: data/roadmap_skills.json (adds 'skills_zh' field to each role)

Usage:
    python -m backend.scripts.translate_roadmap_skills
"""

import json
import time
from pathlib import Path

from backend.llm import get_llm_client, get_model

SKILLS_PATH = Path("data/roadmap_skills.json")
BATCH_SIZE = 15  # skills per LLM call


def _translate_batch(client, model: str, skills: list[str]) -> dict[str, str]:
    """Translate a batch of English tech skill names to Chinese."""
    skill_list = "\n".join(f"{i+1}. {s}" for i, s in enumerate(skills))

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "你是技术术语翻译专家。将以下英文技术技能名翻译为中文。"
                    "规则：\n"
                    "1. 专有名词保留英文（如 Docker, Redis, MySQL, Git, REST, OAuth）\n"
                    "2. 通用概念翻译（如 Data Structures→数据结构, Multithreading→多线程）\n"
                    "3. 混合词用中文+英文（如 Smart Pointers→智能指针, Lambda Expressions→Lambda 表达式）\n"
                    "4. 返回纯 JSON 对象 {\"英文原文\": \"中文翻译\", ...}，不要加 markdown 标记"
                ),
            },
            {"role": "user", "content": skill_list},
        ],
        temperature=0.1,
        max_tokens=4000,
    )

    text = resp.choices[0].message.content.strip()
    # Strip markdown code fence if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        print(f"  WARNING: Failed to parse LLM response, returning raw skills")
        return {s: s for s in skills}


def main():
    with open(SKILLS_PATH, "r", encoding="utf-8") as f:
        roles = json.load(f)

    client = get_llm_client(timeout=120)
    model = get_model("default")
    print(f"Using model: {model}")

    # Collect all unique skills across all roles
    all_skills: set[str] = set()
    for role_data in roles.values():
        all_skills.update(role_data["skills"])

    unique_skills = sorted(all_skills)
    print(f"Total unique skills to translate: {len(unique_skills)}")

    # Translate in batches
    translation_map: dict[str, str] = {}
    for i in range(0, len(unique_skills), BATCH_SIZE):
        batch = unique_skills[i : i + BATCH_SIZE]
        print(f"  Translating batch {i // BATCH_SIZE + 1}/{(len(unique_skills) + BATCH_SIZE - 1) // BATCH_SIZE} ({len(batch)} skills)...")

        result = _translate_batch(client, model, batch)
        translation_map.update(result)

        # Rate limit
        if i + BATCH_SIZE < len(unique_skills):
            time.sleep(1)

    print(f"Translated: {len(translation_map)} skills")

    # Apply translations to each role
    for role_id, role_data in roles.items():
        role_data["skills_zh"] = [
            translation_map.get(s, s) for s in role_data["skills"]
        ]
        # Build a combined set for matching (both en + zh)
        role_data["match_tokens"] = list(set(
            [s.lower() for s in role_data["skills"]]
            + [s.lower() for s in role_data["skills_zh"]]
        ))

    # Save back
    with open(SKILLS_PATH, "w", encoding="utf-8") as f:
        json.dump(roles, f, ensure_ascii=False, indent=2)

    print(f"Done. Updated {SKILLS_PATH}")

    # Quick verification
    cpp = roles.get("cpp", {})
    print(f"\nC++ sample translations:")
    for en, zh in zip(cpp.get("skills", [])[:10], cpp.get("skills_zh", [])[:10]):
        print(f"  {en:30s} -> {zh}")


if __name__ == "__main__":
    main()
