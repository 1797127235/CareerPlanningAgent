# -*- coding: utf-8 -*-
"""
LearningService — serves developer-roadmap learning topics per role.

Loads data/learning_topics.json once (singleton), provides:
  get_role_summary(role_id) → {topic_count, resource_count, type_breakdown}
  get_role_topics(role_id)  → full topic list with resources
  search_topics(query)      → cross-role keyword search
"""
from __future__ import annotations

import json
import logging
from collections import Counter
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_PATH = _PROJECT_ROOT / "data" / "learning_topics.json"
_PATHS_PATH = _PROJECT_ROOT / "data" / "learning_paths.json"


class LearningService:
    def __init__(self, data_path: Path | None = None, paths_path: Path | None = None):
        self._path = data_path or _DEFAULT_PATH
        self._paths_path = paths_path or _PATHS_PATH
        self._data: dict[str, Any] | None = None
        self._paths: dict[str, Any] | None = None

    def _load(self) -> None:
        if self._data is not None:
            return
        try:
            self._data = json.loads(self._path.read_text(encoding="utf-8"))
            total = sum(r.get("topic_count", 0) for r in self._data.values())
            logger.info("LearningService loaded: %d roles, %d topics", len(self._data), total)
        except Exception as e:
            logger.error("Failed to load learning topics: %s", e)
            self._data = {}

    def _load_paths(self) -> None:
        if self._paths is not None:
            return
        try:
            self._paths = json.loads(self._paths_path.read_text(encoding="utf-8"))
            logger.info("LearningService paths loaded: %d roles", len(self._paths))
        except Exception as e:
            logger.error("Failed to load learning paths: %s", e)
            self._paths = {}

    @property
    def role_ids(self) -> list[str]:
        self._load()
        return list(self._data.keys())

    def get_role_summary(self, role_id: str) -> dict[str, Any] | None:
        """Return topic/resource counts and type breakdown for a role."""
        self._load()
        role = self._data.get(role_id)
        if not role:
            return None
        # Count resource types
        type_counts: Counter[str] = Counter()
        for t in role.get("topics", []):
            for r in t.get("resources", []):
                type_counts[r.get("type", "other")] += 1
        return {
            "role_id": role_id,
            "topic_count": role.get("topic_count", 0),
            "resource_count": role.get("resource_count", 0),
            "type_breakdown": dict(type_counts),
        }

    def get_role_topics(
        self,
        role_id: str,
        resource_type: str | None = None,
        limit: int = 0,
        offset: int = 0,
    ) -> dict[str, Any] | None:
        """Return topics with resources for a role, with optional type filter."""
        self._load()
        role = self._data.get(role_id)
        if not role:
            return None

        topics = role.get("topics", [])

        # Filter by resource type if requested
        if resource_type:
            filtered = []
            for t in topics:
                matching = [r for r in t.get("resources", []) if r.get("type") == resource_type]
                if matching:
                    filtered.append({**t, "resources": matching})
            topics = filtered

        total = len(topics)

        # Pagination
        if offset:
            topics = topics[offset:]
        if limit > 0:
            topics = topics[:limit]

        return {
            "role_id": role_id,
            "total": total,
            "offset": offset,
            "topics": topics,
        }

    def get_learning_path(
        self,
        role_id: str,
        gap_topics: list[str] | None = None,
        completed_ids: set[str] | None = None,
    ) -> dict[str, Any] | None:
        """Return structured learning path for a role, optionally filtered to gap topics.

        Args:
            role_id: target role (e.g. 'cpp')
            gap_topics: if provided, only include topics whose title is in this list
            completed_ids: set of subtopic IDs already completed (from DB)

        Returns:
            { role_id, topics: [{ id, title, description, subtopics: [...], completed, total }], progress }
        """
        self._load_paths()
        role = self._paths.get(role_id)
        if not role:
            return None

        completed_ids = completed_ids or set()
        topics_out = []
        total_subs = 0
        total_done = 0

        for topic in role.get("topics", []):
            title = topic.get("title", "")
            # Filter to gap topics if specified
            if gap_topics is not None and title not in gap_topics:
                continue

            subs = topic.get("subtopics", [])
            subs_out = []
            for s in subs:
                done = s.get("id", "") in completed_ids
                subs_out.append({
                    "id": s.get("id", ""),
                    "title": s.get("title", ""),
                    "description": s.get("description", ""),
                    "resources": s.get("resources", []),
                    "completed": done,
                })
                total_subs += 1
                if done:
                    total_done += 1

            topics_out.append({
                "id": topic.get("id", ""),
                "title": title,
                "description": topic.get("description", ""),
                "subtopics": subs_out,
                "completed": sum(1 for s in subs_out if s["completed"]),
                "total": len(subs_out),
            })

        return {
            "role_id": role_id,
            "topics": topics_out,
            "progress": {
                "completed": total_done,
                "total": total_subs,
                "pct": round(total_done / total_subs * 100) if total_subs else 0,
            },
        }



# ── Singleton ──────────────────────────────────────────────────────────────

_instance: LearningService | None = None


def get_learning_service() -> LearningService:
    global _instance
    if _instance is None:
        _instance = LearningService()
    return _instance
