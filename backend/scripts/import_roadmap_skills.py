"""
Import skill trees from developer-roadmap into a role→skills JSON.

Handles two roadmap formats:
  1. JSON-based: topics/subtopics extracted from react-flow node data
  2. Content-based: skills extracted from content/ directory filenames
     (for roadmaps like golang, docker, kotlin that use a simpler format)

Usage:
    python -m backend.scripts.import_roadmap_skills

Output: data/roadmap_skills.json
"""

import json
import os
import re
from pathlib import Path

ROADMAP_BASE = Path(os.environ.get(
    "ROADMAP_PATH",
    "C:/Users/liu/Desktop/developer-roadmap/src/data/roadmaps",
))

# ── 33 CS career directions ────────────────────────────────────────────────
PRIMARY_ROLES = [
    # Core engineering
    "backend", "frontend", "full-stack", "devops",
    # Mobile
    "android", "ios", "flutter", "react-native",
    # AI / Data
    "ai-engineer", "machine-learning", "mlops", "data-engineer", "data-analyst",
    # Architecture & Management
    "software-architect", "engineering-manager",
    # Specialized engineering
    "game-developer", "qa", "cyber-security", "devsecops",
    # Language-specific
    "cpp", "rust", "python", "java", "golang", "kotlin", "php",
    # Framework-specific
    "react", "vue", "angular", "nodejs",
    # Infrastructure
    "kubernetes", "linux", "docker", "postgresql-dba",
]

# Chinese labels — tailored for Chinese tech market
ROLE_LABELS = {
    "backend": "后端工程师",
    "frontend": "前端工程师",
    "full-stack": "全栈工程师",
    "devops": "DevOps 工程师",
    "android": "Android 工程师",
    "ios": "iOS 工程师",
    "flutter": "Flutter 工程师",
    "react-native": "React Native 工程师",
    "ai-engineer": "AI 工程师",
    "machine-learning": "机器学习工程师",
    "mlops": "MLOps 工程师",
    "data-engineer": "数据工程师",
    "data-analyst": "数据分析师",
    "software-architect": "软件架构师",
    "engineering-manager": "工程经理",
    "game-developer": "游戏开发工程师",
    "qa": "测试工程师",
    "cyber-security": "网络安全工程师",
    "devsecops": "DevSecOps 工程师",
    "cpp": "C++ 工程师",
    "rust": "Rust 工程师",
    "python": "Python 工程师",
    "java": "Java 工程师",
    "golang": "Go 工程师",
    "kotlin": "Kotlin 工程师",
    "php": "PHP 工程师",
    "react": "React 工程师",
    "vue": "Vue 工程师",
    "angular": "Angular 工程师",
    "nodejs": "Node.js 工程师",
    "kubernetes": "Kubernetes 工程师",
    "linux": "Linux 工程师",
    "docker": "Docker 工程师",
    "postgresql-dba": "数据库工程师",
}


def _extract_skills_from_json(json_path: Path) -> dict:
    """Extract topic + subtopic labels from a roadmap JSON (react-flow format)."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    nodes = data.get("nodes", [])
    topics = []
    subtopics = []

    for n in nodes:
        label = (n.get("data") or {}).get("label", "").strip()
        if not label:
            continue
        ntype = n.get("type", "")
        if ntype == "topic":
            topics.append(label)
        elif ntype == "subtopic":
            subtopics.append(label)

    return {"topics": topics, "subtopics": subtopics}


def _extract_skills_from_content(content_dir: Path) -> dict:
    """Extract skills from content/ directory filenames.

    Filename format: topic-name@unique-id.md
    Falls back to this when JSON has no topic/subtopic nodes.
    """
    if not content_dir.exists():
        return {"topics": [], "subtopics": []}

    skills = []
    seen = set()
    for f in sorted(content_dir.iterdir()):
        if f.suffix != ".md":
            continue
        name = f.stem.split("@")[0]
        readable = name.replace("-", " ").strip()
        # De-duplicate (some content files share topic prefix)
        if readable.lower() in seen:
            continue
        seen.add(readable.lower())
        if readable and len(readable) >= 2:
            skills.append(readable)

    # Content-based extraction doesn't distinguish topics vs subtopics
    # Treat all as subtopics (skills)
    return {"topics": [], "subtopics": skills}


def _extract_skills(role_id: str) -> dict:
    """Extract skills using JSON first, falling back to content/ directory."""
    json_path = ROADMAP_BASE / role_id / f"{role_id}.json"
    content_dir = ROADMAP_BASE / role_id / "content"

    result = {"topics": [], "subtopics": []}

    # Try JSON extraction first
    if json_path.exists():
        result = _extract_skills_from_json(json_path)

    # If JSON yielded nothing useful, try content/ directory
    if not result["subtopics"] and not result["topics"]:
        result = _extract_skills_from_content(content_dir)

    return result


def _extract_related(md_path: Path) -> list[str]:
    """Extract relatedRoadmaps from frontmatter."""
    if not md_path.exists():
        return []
    content = md_path.read_text(encoding="utf-8")
    m = re.search(r"relatedRoadmaps:\s*\n((?:\s+-\s+.+\n)*)", content)
    if not m:
        return []
    return [
        line.strip().lstrip("- ").strip("\"'")
        for line in m.group(1).strip().split("\n")
        if line.strip()
    ]


# ── Noise filter ───────────────────────────────────────────────────────────
_NOISE_PATTERNS = [
    "?",           # questions
    "Checkpoint",
    "Pick a ",
    "Learn a ",
    "What ",
    "How ",
    "Why ",
    "When ",
    "Which ",
    "Where ",
    "Who ",
    "NOTE",
    "TODO",
    "IMPORTANT",
]


def _is_noise(skill: str) -> bool:
    """Filter out question-like, instructional, or UI label strings."""
    if len(skill) < 2:
        return True
    for pattern in _NOISE_PATTERNS:
        if skill.startswith(pattern):
            return True
    return False


def build_role_skills() -> dict:
    """Build the complete role → skills mapping."""
    roles = {}

    for role_id in PRIMARY_ROLES:
        role_dir = ROADMAP_BASE / role_id
        md_path = role_dir / f"{role_id}.md"

        if not role_dir.exists():
            print(f"  SKIP {role_id}: directory not found")
            continue

        skills_data = _extract_skills(role_id)
        related = _extract_related(md_path)

        # Use subtopics as primary skills; topics as categories
        all_skills = list(dict.fromkeys(
            skills_data["subtopics"] + skills_data["topics"]
        ))

        # Filter out noise
        clean_skills = [s for s in all_skills if not _is_noise(s)]

        # Only keep related roles that are in our PRIMARY_ROLES set
        valid_related = [r for r in related if r in PRIMARY_ROLES]

        roles[role_id] = {
            "label": ROLE_LABELS.get(role_id, role_id),
            "skills": clean_skills,
            "skill_count": len(clean_skills),
            "related_roles": valid_related,
            "topics": skills_data["topics"],
        }

        print(f"  {role_id:22s} → {len(clean_skills):3d} skills, "
              f"{len(valid_related):2d} related, "
              f"{'json' if skills_data['topics'] else 'content'}")

    return roles


def main():
    print("Importing roadmap skill trees...")
    print(f"Source: {ROADMAP_BASE}")
    print(f"Target roles: {len(PRIMARY_ROLES)}\n")

    roles = build_role_skills()

    out_path = Path("data/roadmap_skills.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(roles, f, ensure_ascii=False, indent=2)

    total_skills = sum(r["skill_count"] for r in roles.values())
    print(f"\nDone: {len(roles)} roles → {out_path}")
    print(f"Total skills: {total_skills}")
    print(f"Avg skills/role: {total_skills // len(roles)}")


if __name__ == "__main__":
    main()
