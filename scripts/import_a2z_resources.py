# -*- coding: utf-8 -*-
"""
从 dipakkr/A-to-Z-Resources-for-Students 解析学习资源，
追加到 data/learning/learning_resources.csv（按 URL 去重）。

用法:
  python scripts/import_a2z_resources.py
  python scripts/import_a2z_resources.py --dry-run

说明:
  - 只导入与 IT 学习相关的章节（编程/AI/Web/DevOps/面试准备等）
  - 跳过：Hackathon、实习机会、奖学金、会议活动等非学习内容
  - 按 URL 去重，不会与已有资源冲突
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import urllib.request
from pathlib import Path

README_URL = (
    "https://raw.githubusercontent.com/"
    "dipakkr/A-to-Z-Resources-for-Students/master/README.md"
)

CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "learning" / "learning_resources.csv"
CSV_FIELDS = ["skill", "resource_type", "name", "provider", "url", "difficulty", "estimated_hours"]

# ── 只处理这些章节（小写匹配） ──────────────────────────────────────────────────
INCLUDE_SECTIONS = {
    "programming languages",
    "frameworks",
    "web development",
    "backend development",
    "modern frontend",
    "mobile development",
    "ai & machine learning",
    "ai tools",
    "data science",
    "cloud computing",
    "devops",
    "cybersecurity",
    "ethical hacking",
    "interview preparation",
    "interview prep",
    "learning resources",
    "free resources",
    "beginner-friendly",
    "computer science",
    "open source",
    "web3",
    "blockchain",
    "database",
    "system design",
    "algorithms",
    "data structures",
    "git",
    "linux",
    "python",
    "javascript",
    "java",
    "golang",
    "rust",
    "c++",
    "cpp",
    "typescript",
    "react",
    "vue",
    "angular",
    "node",
    "docker",
    "kubernetes",
    "aws",
    "gcp",
    "azure",
}

# ── 跳过这些章节 ───────────────────────────────────────────────────────────────
SKIP_SECTIONS = {
    "hackathon",
    "competition",
    "scholarship",
    "fellowship",
    "conference",
    "event",
    "student program",
    "student benefit",
    "student pack",
    "internship",
    "community",
    "networking",
    "opportunity",
    "opportunities",
    "meetup",
    "social",
    "campus ambassador",
    "people to follow",
    "websites to follow",
    "top people",
    "top websites",
    "newsletter",
    "youtube channel",
    "podcast",
    "quick start",
    "table of contents",
    "fyi",
    "quick access",
    "quick start",
    "top 10",
    "top 5",
    "finance",
    "best github repositories",
    "github repositories to follow",
}

# ── URL → Provider 映射 ───────────────────────────────────────────────────────
PROVIDER_MAP = {
    "youtube.com": "YouTube",
    "youtu.be": "YouTube",
    "github.com": "GitHub",
    "freecodecamp.org": "freeCodeCamp",
    "w3schools.com": "W3Schools",
    "developer.mozilla.org": "MDN",
    "coursera.org": "Coursera",
    "udemy.com": "Udemy",
    "edx.org": "edX",
    "codecademy.com": "Codecademy",
    "khanacademy.org": "Khan Academy",
    "udacity.com": "Udacity",
    "pluralsight.com": "Pluralsight",
    "linkedin.com/learning": "LinkedIn Learning",
    "medium.com": "Medium",
    "dev.to": "Dev.to",
    "geeksforgeeks.org": "GeeksForGeeks",
    "towardsdatascience.com": "Towards Data Science",
    "kaggle.com": "Kaggle",
    "leetcode.com": "LeetCode",
    "hackerrank.com": "HackerRank",
    "hackerearth.com": "HackerEarth",
    "codeforces.com": "Codeforces",
    "docs.python.org": "Python",
    "huggingface.co": "Hugging Face",
    "tensorflow.org": "TensorFlow",
    "pytorch.org": "PyTorch",
    "scikit-learn.org": "Scikit-Learn",
    "fast.ai": "fast.ai",
    "roadmap.sh": "roadmap.sh",
    "cloud.google.com": "Google Cloud",
    "aws.amazon.com": "AWS",
    "learn.microsoft.com": "Microsoft",
    "docker.com": "Docker",
    "kubernetes.io": "Kubernetes",
    "git-scm.com": "Git",
    "digitalocean.com": "DigitalOcean",
    "realpython.com": "Real Python",
}

# ── Regex ─────────────────────────────────────────────────────────────────────
LINK_RE = re.compile(r'\[([^\]]+)\]\((https?://[^)]+)\)')
H2_RE = re.compile(r'^##\s+(.*)')
H3_RE = re.compile(r'^###\s+(.*)')
BOLD_RE = re.compile(r'^\s*[-*]\s+\*\*([^*]+)\*\*')


def _extract_provider(url: str) -> str:
    try:
        from urllib.parse import urlparse
        host = urlparse(url).netloc.lower().lstrip("www.")
        for pattern, name in PROVIDER_MAP.items():
            if pattern in host:
                return name
        parts = host.split(".")
        return parts[-2].capitalize() if len(parts) >= 2 else ""
    except Exception:
        return ""


def _infer_type(name: str, url: str) -> str:
    name_l = name.lower()
    url_l = url.lower()
    if any(k in name_l for k in ("course", "tutorial", "learn", "bootcamp", "mooc",
                                  "class", "crash", "masterclass", "specialization")):
        return "course"
    if any(k in name_l for k in ("book", "guide", "handbook", "manual", "textbook")):
        return "book"
    if any(k in name_l for k in ("project", "build", "implement", "practice", "hands-on")):
        return "project"
    if "youtube.com" in url_l or "youtu.be" in url_l:
        return "course"
    if "github.com" in url_l:
        return "project"
    if any(k in url_l for k in ("coursera", "udemy", "edx", "codecademy", "pluralsight",
                                  "udacity", "khanacademy")):
        return "course"
    if any(k in url_l for k in ("leetcode", "hackerrank", "codeforces", "hackerearth")):
        return "project"
    return "article"


def _infer_difficulty(name: str, desc: str) -> str:
    text = (name + " " + desc).lower()
    if any(k in text for k in ("beginner", "introduction", "intro", "basics", "101",
                                "getting started", "starter", "baby", "scratch")):
        return "入门"
    if any(k in text for k in ("advanced", "expert", "mastering", "in-depth", "deep dive",
                                "architecture", "production")):
        return "进阶"
    return "入门"


def _infer_hours(rtype: str) -> int:
    return {"course": 20, "book": 40, "project": 15, "article": 2}.get(rtype, 5)


def _section_relevant(section: str) -> bool | None:
    """Returns True=include, False=skip, None=unknown(include by default)."""
    s = section.lower()
    for skip in SKIP_SECTIONS:
        if skip in s:
            return False
    for include in INCLUDE_SECTIONS:
        if include in s:
            return True
    return None  # ambiguous — include


_GENERIC_NAMES = {
    "tutorials", "tutorial", "courses", "course", "resources", "resource",
    "best online courses", "online platforms", "platforms", "learning resources",
    "free resources", "tools", "books", "articles", "videos", "links",
    "references", "documentation", "docs", "examples", "projects",
    "research papers", "papers", "beginner-friendly resources",
    "popular ai tools", "ai tool directories",
}


def _clean_section(raw: str) -> str:
    """Strip leading numbering, emojis, and normalize."""
    # Strip leading numbers like "1.22 " or "## 1. "
    clean = re.sub(r'^[\d\s\.]+', '', raw).strip()
    # Strip emojis and special chars but keep alphanumeric, spaces, + # . - &
    clean = re.sub(r'[^\w\s\-\+\#\.\&/]', '', clean).strip()
    clean = re.sub(r'\s+', ' ', clean)
    return clean


def _skill_from_context(h2: str, h3: str, bold: str) -> str:
    """Derive skill name from most specific non-generic context."""
    for ctx in [bold, h3, h2]:
        if not ctx:
            continue
        clean = _clean_section(ctx)
        if not clean or len(clean) < 3:
            continue
        if clean.lower() in _GENERIC_NAMES:
            continue
        return clean[:60]
    return "General"


def fetch_readme(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def parse_resources(text: str) -> list[dict]:
    rows: list[dict] = []
    seen_urls: set[str] = set()

    h2 = ""
    h3 = ""
    bold = ""
    active = True  # include by default

    for line in text.splitlines():
        # Track section headings
        m2 = H2_RE.match(line)
        if m2:
            h2 = m2.group(1).strip()
            h3 = ""
            bold = ""
            rel = _section_relevant(h2)
            active = rel is not False  # include if True or None
            continue

        m3 = H3_RE.match(line)
        if m3:
            h3 = m3.group(1).strip()
            bold = ""
            rel = _section_relevant(h3)
            if rel is not None:
                active = rel is not False
            continue

        mb = BOLD_RE.match(line)
        if mb:
            bold = mb.group(1).strip()
            rel = _section_relevant(bold)
            if rel is not None:
                active = rel is not False
            continue

        if not active:
            continue

        # Extract links from this line
        for name, url in LINK_RE.findall(line):
            if url in seen_urls:
                continue
            # Skip non-resource links (social profiles, repo links, images)
            if any(skip in url for skip in (
                "linkedin.com/in/", "twitter.com/", "instagram.com/",
                "facebook.com/", "t.me/", "/blob/", "/tree/master",
                "shields.io", "badge", "github.com/dipakkr",
            )):
                continue
            if not name.strip() or len(name) < 3:
                continue

            seen_urls.add(url)
            skill = _skill_from_context(h2, h3, bold)
            # Extract description from rest of line after the link
            after = line[line.find(url) + len(url):]
            desc = re.sub(r'[^\w\s]', ' ', after).strip()[:100]
            rtype = _infer_type(name, url)
            difficulty = _infer_difficulty(name, desc)

            rows.append({
                "skill": skill,
                "resource_type": rtype,
                "name": name.strip()[:120],
                "provider": _extract_provider(url),
                "url": url,
                "difficulty": difficulty,
                "estimated_hours": _infer_hours(rtype),
            })

    return rows


def load_existing_urls(csv_path: Path) -> set[str]:
    if not csv_path.exists():
        return set()
    urls: set[str] = set()
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("url"):
                urls.add(row["url"].strip())
    return urls


def append_to_csv(new_rows: list[dict], csv_path: Path) -> int:
    """Append rows to CSV; return count written."""
    write_header = not csv_path.exists()
    with open(csv_path, "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerows(new_rows)
    return len(new_rows)


def main():
    parser = argparse.ArgumentParser(description="从 A-to-Z-Resources-for-Students 导入学习资源")
    parser.add_argument("--dry-run", action="store_true", help="只统计不写文件")
    parser.add_argument("--csv", default=str(CSV_PATH), help="输出 CSV 路径")
    args = parser.parse_args()

    csv_path = Path(args.csv)

    print("Fetching README from GitHub...")
    try:
        text = fetch_readme(README_URL)
    except Exception as exc:
        print(f"Error fetching README: {exc}")
        sys.exit(1)
    print(f"  README size: {len(text):,} chars")

    print("Parsing resources...")
    all_rows = parse_resources(text)
    print(f"  Total parsed: {len(all_rows)} resources")

    # Deduplicate against existing CSV
    existing_urls = load_existing_urls(csv_path)
    print(f"  Existing CSV URLs: {len(existing_urls)}")

    new_rows = [r for r in all_rows if r["url"] not in existing_urls]
    print(f"  New (not in CSV): {len(new_rows)} resources")

    # Stats by section
    from collections import Counter
    skill_counts = Counter(r["skill"] for r in new_rows)
    print("\nTop 15 skills:")
    for skill, count in skill_counts.most_common(15):
        print(f"  {skill:40s} {count:4d}")

    type_counts = Counter(r["resource_type"] for r in new_rows)
    print("\nResource types:")
    for rtype, count in type_counts.most_common():
        print(f"  {rtype:15s} {count:4d}")

    if args.dry_run:
        print("\n[dry-run] No files written.")
        print("\nSample new rows:")
        for r in new_rows[:8]:
            print(f"  [{r['skill'][:25]}] {r['name'][:50]} ({r['resource_type']})")
        return

    written = append_to_csv(new_rows, csv_path)
    print(f"\nAppended {written} rows to {csv_path}")
    print(f"CSV now has ~{len(existing_urls) + written} rows total")


if __name__ == "__main__":
    main()
