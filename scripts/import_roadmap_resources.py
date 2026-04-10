# -*- coding: utf-8 -*-
"""
从 developer-roadmap 仓库提取学习资源，重建 learning_resources.csv。

用法:
  python -m scripts.import_roadmap_resources --roadmap-dir ~/Desktop/developer-roadmap
  python -m scripts.import_roadmap_resources --roadmap-dir ~/Desktop/developer-roadmap --dry-run
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
from collections import defaultdict
from pathlib import Path

# ── 只导入 CS/IT 相关 roadmap ──────────────────────────────
CS_ROADMAPS = [
    "frontend", "backend", "devops", "qa",
    "ai-data-scientist", "ai-engineer", "ai-agents",
    "react", "vue", "angular", "nextjs", "nodejs",
    "python", "java", "golang", "rust", "cpp", "typescript", "javascript",
    "docker", "kubernetes", "linux", "aws", "terraform",
    "postgresql-dba", "mongodb", "redis", "sql", "elasticsearch",
    "system-design", "software-architect", "software-design-architecture",
    "cyber-security", "mlops", "machine-learning", "data-engineer", "data-analyst",
    "react-native", "flutter", "android", "ios",
    "git-github", "api-design", "graphql",
    "datastructures-and-algorithms", "computer-science",
    "spring-boot", "django", "laravel",
    "shell-bash", "devsecops",
]

# roadmap @tag@ → resource_type 映射
TAG_MAP = {
    "article": "article",
    "articles": "article",
    "Article": "article",
    "official": "course",    # 官方文档当课程
    "offical": "course",     # typo in source
    "course": "course",
    "video": "course",
    "youtube": "course",
    "book": "book",
    "opensource": "project",
    "opensources": "project",
    "roadmap": "roadmap",    # 交叉引用其他路线图
    "feed": None,            # daily.dev feed 链接，跳过
    "podcast": None,
}

# 资源链接正则
TAG_RE = re.compile(r"- \[@(\w+)@([^\]]+)\]\(([^)]+)\)")

# 难度推断
def _infer_difficulty(tag: str, name: str) -> str:
    name_lower = name.lower()
    if any(kw in name_lower for kw in ("beginner", "入门", "introduction", "getting started", "basics", "101", "tutorial")):
        return "入门"
    if any(kw in name_lower for kw in ("advanced", "进阶", "deep dive", "in-depth", "master", "expert")):
        return "进阶"
    if any(kw in name_lower for kw in ("project", "build", "实战", "hands-on", "practice")):
        return "实战"
    if tag in ("book",):
        return "进阶"
    if tag in ("opensource", "opensources"):
        return "实战"
    return "入门"

# 估算学时
def _estimate_hours(tag: str, name: str) -> int:
    if tag in ("book",):
        return 40
    if tag in ("course", "video", "youtube"):
        return 20
    if tag in ("opensource", "opensources"):
        return 15
    if tag in ("official", "offical"):
        return 10
    return 10

# 标准化技能名：去掉连字符，首字母大写
def _normalize_skill(raw: str) -> str:
    # 保留常见缩写
    KEEP_UPPER = {"html", "css", "sql", "api", "cdn", "dns", "http", "https",
                  "tcp", "udp", "ssh", "ssl", "tls", "jwt", "oauth", "cors",
                  "rest", "grpc", "graphql", "nosql", "orm", "ci", "cd",
                  "aws", "gcp", "ide", "cli", "gui", "mvc", "mvvm", "oop",
                  "solid", "acid", "cap", "cqrs", "ddd", "tdd", "bdd"}
    parts = raw.replace("-", " ").split()
    result = []
    for p in parts:
        if p.lower() in KEEP_UPPER:
            result.append(p.upper())
        elif p[0].isupper():
            result.append(p)
        else:
            result.append(p.capitalize())
    return " ".join(result)


def extract_resources(roadmap_dir: str) -> list[dict]:
    """从所有 CS roadmap 的 content/*.md 提取资源。"""
    base = Path(roadmap_dir) / "src" / "data" / "roadmaps"
    rows = []
    seen = set()  # (skill, url) 去重

    for rm in CS_ROADMAPS:
        content_dir = base / rm / "content"
        if not content_dir.is_dir():
            continue

        for fname in sorted(content_dir.iterdir()):
            if not fname.suffix == ".md":
                continue

            # 技能名从文件名提取
            raw_skill = fname.stem.split("@")[0]
            skill = _normalize_skill(raw_skill)
            if not skill or len(skill) < 2:
                continue

            text = fname.read_text(encoding="utf-8")
            matches = TAG_RE.findall(text)

            for tag, name, url in matches:
                resource_type = TAG_MAP.get(tag)
                if resource_type is None:
                    continue  # skip feed/podcast
                if resource_type == "roadmap":
                    continue  # skip cross-references

                # 去重
                dedup_key = (skill.lower(), url)
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)

                rows.append({
                    "skill": skill,
                    "resource_type": resource_type,
                    "name": name.strip(),
                    "provider": _extract_provider(url),
                    "url": url,
                    "difficulty": _infer_difficulty(tag, name),
                    "estimated_hours": _estimate_hours(tag, name),
                })

    return rows


def _extract_provider(url: str) -> str:
    """从 URL 提取 provider 名称。"""
    PROVIDER_MAP = {
        "youtube.com": "YouTube",
        "youtu.be": "YouTube",
        "github.com": "GitHub",
        "react.dev": "React",
        "angular.dev": "Angular",
        "vuejs.org": "Vue.js",
        "developer.mozilla.org": "MDN",
        "web.dev": "Google",
        "freecodecamp.org": "freeCodeCamp",
        "w3schools.com": "W3Schools",
        "digitalocean.com": "DigitalOcean",
        "medium.com": "Medium",
        "geeksforgeeks.org": "GeeksForGeeks",
        "docs.python.org": "Python",
        "go.dev": "Go",
        "rust-lang.org": "Rust",
        "typescriptlang.org": "TypeScript",
        "docker.com": "Docker",
        "kubernetes.io": "Kubernetes",
        "aws.amazon.com": "AWS",
        "cloud.google.com": "Google Cloud",
        "learn.microsoft.com": "Microsoft",
        "oracle.com": "Oracle",
        "postgresql.org": "PostgreSQL",
        "redis.io": "Redis",
        "mongodb.com": "MongoDB",
        "elastic.co": "Elastic",
        "udemy.com": "Udemy",
        "coursera.org": "Coursera",
        "codecademy.com": "Codecademy",
        "khanacademy.org": "Khan Academy",
        "roadmap.sh": "roadmap.sh",
    }
    try:
        from urllib.parse import urlparse
        host = urlparse(url).netloc.lower().lstrip("www.")
        for pattern, name in PROVIDER_MAP.items():
            if pattern in host:
                return name
        # Fallback: use domain
        parts = host.split(".")
        if len(parts) >= 2:
            return parts[-2].capitalize()
    except Exception:
        pass
    return ""


def extract_skill_trees(roadmap_dir: str) -> dict:
    """提取每个 roadmap 的技能树（节点+层级+学习顺序）。"""
    base = Path(roadmap_dir) / "src" / "data" / "roadmaps"
    trees = {}

    for rm in CS_ROADMAPS:
        json_path = base / rm / f"{rm}.json"
        if not json_path.exists():
            continue

        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)

        nodes = {n["id"]: n for n in data.get("nodes", [])}
        edges = [e for e in data.get("edges", []) if "source" in e and "target" in e]

        # 提取 topic 和 subtopic
        topics = []
        for n in data.get("nodes", []):
            if n.get("type") in ("topic", "subtopic"):
                topics.append({
                    "id": n["id"],
                    "label": n.get("data", {}).get("label", ""),
                    "type": n["type"],
                    "y": n.get("position", {}).get("y", 0),
                })

        # 边分类
        solid_edges = []  # 主路径
        dashed_edges = []  # 展开子技能
        for e in edges:
            style = e.get("data", {}).get("edgeStyle", "solid")
            src_node = nodes.get(e["source"])
            tgt_node = nodes.get(e["target"])
            if not src_node or not tgt_node:
                continue
            edge_info = {
                "source": e["source"],
                "target": e["target"],
                "source_label": src_node.get("data", {}).get("label", ""),
                "target_label": tgt_node.get("data", {}).get("label", ""),
            }
            if style == "dashed":
                dashed_edges.append(edge_info)
            else:
                solid_edges.append(edge_info)

        trees[rm] = {
            "topics": sorted(topics, key=lambda t: t["y"]),
            "solid_edges": solid_edges,
            "dashed_edges": dashed_edges,
        }

    return trees


def write_csv(rows: list[dict], output_path: str):
    """写入 CSV。"""
    fieldnames = ["skill", "resource_type", "name", "provider", "url", "difficulty", "estimated_hours"]
    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_skill_trees(trees: dict, output_path: str):
    """写入技能树 JSON。"""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(trees, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description="从 developer-roadmap 提取学习资源")
    parser.add_argument("--roadmap-dir", required=True, help="developer-roadmap 仓库路径")
    parser.add_argument("--output-csv", default="data/learning/learning_resources.csv", help="输出 CSV 路径")
    parser.add_argument("--output-trees", default="data/learning/roadmap_skill_trees.json", help="输出技能树 JSON")
    parser.add_argument("--dry-run", action="store_true", help="只统计不写文件")
    args = parser.parse_args()

    print(f"Scanning {args.roadmap_dir} ...")
    resources = extract_resources(args.roadmap_dir)
    trees = extract_skill_trees(args.roadmap_dir)

    # 统计
    skills = set(r["skill"] for r in resources)
    print(f"\nExtracted:")
    print(f"  Resources: {len(resources)} (from {len(CS_ROADMAPS)} roadmaps)")
    print(f"  Unique skills: {len(skills)}")
    print(f"  Skill trees: {len(trees)} roadmaps")
    print(f"  Total tree topics: {sum(len(t['topics']) for t in trees.values())}")

    if args.dry_run:
        print("\n[dry-run] No files written.")
        # 展示样本
        print("\nSample resources:")
        for r in resources[:5]:
            print(f"  {r['skill']:20s} | {r['resource_type']:8s} | {r['name'][:50]}")
        return

    write_csv(resources, args.output_csv)
    print(f"\nWritten: {args.output_csv} ({len(resources)} rows)")

    write_skill_trees(trees, args.output_trees)
    print(f"Written: {args.output_trees} ({len(trees)} roadmaps)")


if __name__ == "__main__":
    main()
