"""GapAnalyzer — minimal stub with profile_hash only."""
from __future__ import annotations

import hashlib
import json


def profile_hash(profile_data: dict) -> str:
    """Generate a stable hash of profile data for cache invalidation."""
    key_data = json.dumps({
        "skills": sorted(s.get("name", "") if isinstance(s, dict) else str(s) for s in profile_data.get("skills", [])),
        "projects": [p.get("name", "") if isinstance(p, dict) else str(p) for p in profile_data.get("projects", [])],
    }, ensure_ascii=False)
    return hashlib.md5(key_data.encode()).hexdigest()[:12]
