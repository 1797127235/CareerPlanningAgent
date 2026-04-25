#!/usr/bin/env python3
"""
Import learning topics from developer-roadmap content/ directories.

Parses markdown files for each of our 34 graph roles, extracting:
  - topic title
  - description paragraph
  - typed resource links (@article@, @video@, @book@, @course@, @official@)

Output: data/learning_topics.json
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ROADMAP_BASE = Path("C:/Users/liu/Desktop/developer-roadmap/src/data/roadmaps")
GRAPH_PATH = PROJECT_ROOT / "data" / "graph.json"
OUTPUT_PATH = PROJECT_ROOT / "data" / "learning_topics.json"

# Resource link pattern: - [@type@Title](url)
_RESOURCE_RE = re.compile(
    r"^-\s+\[@(\w+)@(.+?)\]\((.+?)\)\s*$", re.MULTILINE
)

# Valid resource types we care about
_VALID_TYPES = {"article", "video", "book", "course", "official", "opensource", "podcast", "feed"}


def parse_content_md(filepath: Path) -> dict | None:
    """Parse a single content markdown file."""
    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception:
        return None

    lines = text.strip().split("\n")
    if not lines:
        return None

    # Extract title from first # heading
    title = ""
    desc_lines: list[str] = []
    resource_section = False

    for line in lines:
        stripped = line.strip()
        if not title and stripped.startswith("# "):
            title = stripped[2:].strip()
            continue
        if "visit the following resources" in stripped.lower():
            resource_section = True
            continue
        if resource_section:
            continue  # resources handled by regex
        if stripped and title:
            desc_lines.append(stripped)

    if not title:
        return None

    description = " ".join(desc_lines).strip()

    # Extract resources
    resources = []
    for match in _RESOURCE_RE.finditer(text):
        rtype, rtitle, url = match.group(1), match.group(2), match.group(3)
        if rtype in _VALID_TYPES:
            resources.append({
                "type": rtype,
                "title": rtitle.strip(),
                "url": url.strip(),
            })

    # Extract topic_id from filename: "topic-name@unique-id.md" -> "topic-name"
    fname = filepath.stem  # e.g. "acid@qSAdfaGUfn8mtmDjHJi3z"
    topic_id = fname.split("@")[0] if "@" in fname else fname

    return {
        "topic_id": topic_id,
        "title": title,
        "description": description[:500] if description else "",
        "resources": resources,
    }


def main():
    # Load graph to get our 34 role IDs
    graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    role_ids = [n["node_id"] for n in graph["nodes"]]

    result: dict[str, dict] = {}
    total_topics = 0
    total_resources = 0

    for role_id in sorted(role_ids):
        content_dir = ROADMAP_BASE / role_id / "content"
        if not content_dir.is_dir():
            print(f"  SKIP {role_id}: no content/ dir")
            continue

        topics = []
        for md_file in sorted(content_dir.glob("*.md")):
            topic = parse_content_md(md_file)
            if topic and topic["resources"]:  # only include topics with resources
                topics.append(topic)

        # Deduplicate by topic_id (some files share the same topic_id with different unique IDs)
        seen_ids: set[str] = set()
        deduped: list[dict] = []
        for t in topics:
            if t["topic_id"] not in seen_ids:
                seen_ids.add(t["topic_id"])
                deduped.append(t)

        resource_count = sum(len(t["resources"]) for t in deduped)
        result[role_id] = {
            "topic_count": len(deduped),
            "resource_count": resource_count,
            "topics": deduped,
        }
        total_topics += len(deduped)
        total_resources += resource_count
        print(f"  {role_id:25s} {len(deduped):3d} topics, {resource_count:4d} resources")

    # Write output
    OUTPUT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"\nDone: {len(result)} roles, {total_topics} topics, {total_resources} resources")
    print(f"Output: {OUTPUT_PATH} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
