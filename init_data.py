"""Initialize data directory from data-deploy templates.

Run once after fresh clone:
    python init_data.py

This copies required JSON files from data-deploy/ to data/ 
(which is gitignored, so runtime data doesn't pollute the repo).
"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "data-deploy"
TARGET = ROOT / "data"

# Files to copy from data-deploy → data
FILES = [
    "graph.json",
    "market_signals.json",
    "role_intros.json",
    "industry_signals.json",
    "sjt_templates.json",
    "learning_paths.json",
    "node_embeddings.json",
    "skill_embeddings.json",
    "skill_fill_path_tags.json",
    "skill_frequencies.json",
]


def main() -> None:
    TARGET.mkdir(parents=True, exist_ok=True)

    copied = 0
    skipped = 0

    for name in FILES:
        src = SOURCE / name
        dst = TARGET / name

        if not src.exists():
            logger.warning("  SKIP %s (not found in data-deploy)", name)
            skipped += 1
            continue

        shutil.copy2(src, dst)
        copied += 1

    print(f"Done: {copied} files copied to data/, {skipped} skipped.")
    print("Run the app: python -m uvicorn backend.app:app --reload")


if __name__ == "__main__":
    main()
