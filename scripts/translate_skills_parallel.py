#!/usr/bin/env python3
"""Parallel batch translation of skill names using concurrent LLM calls."""
from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.llm import get_llm_client, get_model

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "roadmap_skills.json"
BATCH_SIZE = 40
MAX_WORKERS = 5

PROMPT = """将以下英文技术技能名翻译为中文。规则：
- 专有名词保留：React, Docker, gRPC, CMake, Redis, vcpkg
- 描述性术语翻译：Memory Leakage→内存泄漏, Virtual Methods→虚函数
- 混合保留专有名词：Partial Template Specialization→模板偏特化
- 缩写加说明：RAII→RAII (资源获取即初始化)
返回JSON对象 {原文:翻译}，仅JSON。

"""


def translate_batch(batch: list[str], batch_id: int) -> dict[str, str]:
    client = get_llm_client(timeout=120)
    prompt = PROMPT + json.dumps(batch, ensure_ascii=False)
    try:
        resp = client.chat.completions.create(
            model=get_model("fast"),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
            temperature=0.1,
        )
        text = (resp.choices[0].message.content or "").strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        result = json.loads(text)
        print(f"  Batch {batch_id}: {len(result)}/{len(batch)} translated", flush=True)
        return result
    except Exception as e:
        print(f"  Batch {batch_id}: ERROR {e}", flush=True)
        return {}


def main():
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    # Collect untranslated
    untranslated: set[str] = set()
    for role_data in data.values():
        en = role_data.get("skills", [])
        zh = role_data.get("skills_zh", en)
        for e, z in zip(en, zh):
            if e == z and len(e) > 2:
                untranslated.add(e)

    skills_list = sorted(untranslated)
    print(f"Untranslated: {len(skills_list)} skills, {MAX_WORKERS} parallel workers")

    # Create batches
    batches = []
    for i in range(0, len(skills_list), BATCH_SIZE):
        batches.append(skills_list[i:i + BATCH_SIZE])
    print(f"Batches: {len(batches)}")

    # Parallel translation
    translation_map: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(translate_batch, batch, i + 1): i
            for i, batch in enumerate(batches)
        }
        for future in as_completed(futures):
            result = future.result()
            translation_map.update(result)

    print(f"\nTotal translations: {len(translation_map)}/{len(skills_list)}")

    # Apply
    updated = 0
    for role_data in data.values():
        en = role_data.get("skills", [])
        zh = list(role_data.get("skills_zh", en))
        for idx, (e, z) in enumerate(zip(en, zh)):
            if e == z and e in translation_map:
                zh[idx] = translation_map[e]
                updated += 1
        role_data["skills_zh"] = zh

    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Updated {updated} entries. Saved to {DATA_PATH}")


if __name__ == "__main__":
    main()
