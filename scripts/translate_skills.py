#!/usr/bin/env python3
"""
Batch translate untranslated skill names in roadmap_skills.json.
Uses LLM to translate English descriptive terms → Chinese,
while keeping proper nouns (React, Docker, gRPC) as-is.

Output: updates data/roadmap_skills.json in-place with skills_zh.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.llm import get_llm_client, get_model

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "roadmap_skills.json"
BATCH_SIZE = 30

TRANSLATE_PROMPT = """你是技术术语翻译专家。将以下英文技能名翻译为中文。

规则：
1. 专有名词/库名/框架名保持原样：React, Docker, gRPC, CMake, Redis, Kubernetes
2. 描述性短语翻译为简洁中文：Memory Leakage → 内存泄漏, Virtual Methods → 虚函数
3. 混合情况保留专有名词+翻译描述：Partial Template Specialization → 模板偏特化
4. 缩写保留括号说明：RAII → RAII (资源获取即初始化)
5. 单个通用词如果是技术概念也翻译：Scope → 作用域, Containers → 容器

返回 JSON 对象，key 是原文，value 是翻译。仅返回 JSON，不要其他文字。

技能列表：
"""


def translate_batch(client, skills: list[str]) -> dict[str, str]:
    """Translate a batch of skills via LLM."""
    prompt = TRANSLATE_PROMPT + json.dumps(skills, ensure_ascii=False)
    try:
        resp = client.chat.completions.create(
            model=get_model("fast"),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
            temperature=0.1,
        )
        text = (resp.choices[0].message.content or "").strip()
        # Extract JSON from response (handle ```json blocks)
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        return json.loads(text)
    except Exception as e:
        print(f"  ERROR: {e}")
        return {}


def main():
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    # Collect all unique untranslated skills
    untranslated: set[str] = set()
    for role_data in data.values():
        en = role_data.get("skills", [])
        zh = role_data.get("skills_zh", en)
        for e, z in zip(en, zh):
            if e == z and len(e) > 2:
                untranslated.add(e)

    print(f"Untranslated skills: {len(untranslated)}")
    if not untranslated:
        print("All skills already translated!")
        return

    # Batch translate
    skills_list = sorted(untranslated)
    translation_map: dict[str, str] = {}
    client = get_llm_client(timeout=120)

    for i in range(0, len(skills_list), BATCH_SIZE):
        batch = skills_list[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(skills_list) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"  Batch {batch_num}/{total_batches} ({len(batch)} skills)...", end=" ", flush=True)

        result = translate_batch(client, batch)
        translation_map.update(result)
        print(f"got {len(result)} translations")
        time.sleep(0.5)  # rate limit courtesy

    print(f"\nTotal translations: {len(translation_map)}")

    # Apply translations to roadmap_skills.json
    updated_count = 0
    for role_id, role_data in data.items():
        en = role_data.get("skills", [])
        zh = list(role_data.get("skills_zh", en))
        changed = False
        for idx, (e, z) in enumerate(zip(en, zh)):
            if e == z and e in translation_map:
                zh[idx] = translation_map[e]
                changed = True
                updated_count += 1
        if changed:
            role_data["skills_zh"] = zh

    # Write back
    DATA_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Updated {updated_count} skill entries across {len(data)} roles")
    print(f"Saved to {DATA_PATH}")


if __name__ == "__main__":
    main()
