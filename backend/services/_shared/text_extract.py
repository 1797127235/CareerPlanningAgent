"""Shared text extraction utilities for profile data."""

from __future__ import annotations


def build_user_text(profile_data: dict) -> str:
    """Build combined lowercase text from raw_text, projects, and internships.

    Used by embedding prefilter, backfill scoring, and skill extraction.
    """
    parts: list[str] = []

    raw_text = (profile_data.get("raw_text") or "").lower()
    if raw_text:
        parts.append(raw_text)

    for p in profile_data.get("projects", []):
        if isinstance(p, dict):
            parts.append(str(p.get("name", "")).lower())
            parts.append(
                str(p.get("description", "") or p.get("highlights", "")).lower()
            )
        elif isinstance(p, str):
            parts.append(p.lower())

    for i in profile_data.get("internships", []):
        if isinstance(i, dict):
            parts.append(str(i.get("role", "")).lower())
            parts.append(
                str(i.get("description", "") or i.get("highlights", "")).lower()
            )
        elif isinstance(i, str):
            parts.append(i.lower())

    for w in profile_data.get("work_experiences", []):
        if isinstance(w, dict):
            parts.append(str(w.get("description", "")).lower())
        elif isinstance(w, str):
            parts.append(w.lower())

    return " ".join(parts)
