#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为 10 个缺少学习路径的图谱节点生成 learning_paths.json 条目。

策略：精选核心主题
  - 每个角色从 1-3 个 source roadmap 中抽取与 must_skills 最相关的 5-8 个 topic
  - 每个 topic 保留所有 subtopic，读取 content markdown 获取 description + resources
  - 输出追加到 data/learning_paths.json

用法:
  python -m scripts.gen_missing_learning_paths [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ROADMAP_BASE = PROJECT_ROOT / "developer-roadmap" / "src" / "data" / "roadmaps"
PATHS_FILE = PROJECT_ROOT / "data" / "learning_paths.json"

# ── 每个缺失角色的配置 ─────────────────────────────────────────────────────
# source_roadmaps: 按优先级排列，依次搜索 topic
# topic_keywords: 匹配 topic label 的关键词（任一匹配即选入），大小写不敏感
# max_topics: 最多选几个 topic

ROLE_CONFIG: dict[str, dict] = {
    "algorithm-engineer": {
        "label": "算法工程师",
        "source_roadmaps": ["datastructures-and-algorithms", "machine-learning", "python"],
        "topic_keywords": [
            "array", "tree", "graph", "dynamic", "sorting", "search", "hash",
            "linear algebra", "statistics", "probability", "neural network",
            "gradient", "loss", "regularization", "scikit", "pytorch", "numpy",
            "data structure", "algorithm", "complexity", "recursion",
        ],
        "max_topics": 8,
    },
    "cloud-architect": {
        "label": "云架构师",
        "source_roadmaps": ["aws", "kubernetes", "terraform"],
        "topic_keywords": [
            "iam", "ec2", "s3", "vpc", "rds", "storage", "cloudwatch",
            "introduction", "container", "running", "service", "networking",
            "security", "monitoring", "autoscal", "deployment",
            "provider", "resource", "variable", "module", "state", "workspace",
        ],
        "max_topics": 8,
    },
    "cto": {
        "label": "首席技术官/CTO",
        "source_roadmaps": ["engineering-manager", "software-architect"],
        "topic_keywords": [
            "management", "engineer", "understand", "responsib", "skill",
            "technical", "pattern", "design", "architecture", "tool",
            "security", "language", "principle",
        ],
        "max_topics": 8,
    },
    "data-architect": {
        "label": "数据架构师",
        "source_roadmaps": ["data-engineer", "sql"],
        "topic_keywords": [
            "data model", "schema", "warehouse", "lake", "etl", "pipeline",
            "spark", "hadoop", "kafka", "airflow", "batch", "streaming",
            "sql", "query", "index", "join", "normali", "partition",
            "governance", "quality", "lineage", "catalog", "metadata",
        ],
        "max_topics": 7,
    },
    "infrastructure-engineer": {
        "label": "基础架构工程师",
        "source_roadmaps": ["linux", "devops"],
        "topic_keywords": [
            "filesystem", "process", "network", "shell", "permission",
            "systemd", "kernel", "memory", "cpu", "disk", "package",
            "ci/cd", "docker", "kubernetes", "monitor", "logging",
            "infrastructure", "deployment", "container", "git", "secret",
            "observab", "tracing", "alert", "incident",
        ],
        "max_topics": 8,
    },
    "ml-architect": {
        "label": "AI/ML 架构师",
        "source_roadmaps": ["mlops", "machine-learning"],
        "topic_keywords": [
            "programming", "version control", "cloud", "container",
            "machine learning", "data engineer", "mlops", "infrastructure",
            "neural", "gradient", "training", "supervised", "deep learning",
            "pytorch", "scikit", "feature",
        ],
        "max_topics": 7,
    },
    "qa-lead": {
        "label": "质量架构师",
        "source_roadmaps": ["qa"],
        "topic_keywords": [
            "fundamental", "sdlc", "manual", "frontend", "backend", "mobile",
            "accessib", "load", "performance", "security", "email", "automati",
        ],
        "max_topics": 8,
    },
    "search-engine-engineer": {
        "label": "搜索引擎工程师",
        "source_roadmaps": ["system-design", "datastructures-and-algorithms", "cpp"],
        "topic_keywords": [
            "index", "inverted", "ranking", "relevance", "crawl",
            "distributed", "cache", "hash", "tree", "graph",
            "concurren", "memory", "template", "stl", "pointer",
            "network", "load balanc", "replication", "partition",
            "consistency", "availability", "latency", "throughput",
        ],
        "max_topics": 7,
    },
    "security-architect": {
        "label": "安全架构师",
        "source_roadmaps": ["cyber-security"],
        "topic_keywords": [
            "fundamental", "operating", "networking", "security", "cloud", "programming",
            "skill", "knowledge",
        ],
        "max_topics": 6,
    },
    "storage-database-kernel": {
        "label": "存储与数据库内核工程师",
        "source_roadmaps": ["postgresql-dba", "datastructures-and-algorithms", "system-design"],
        "topic_keywords": [
            "introduction", "basic", "relational", "object", "sql", "learn",
            "schema", "index", "query", "high level", "infrastructure",
            "tree", "hash", "graph", "algorithm", "sorting", "search",
            "consistency", "availability", "latency", "replication", "cache",
        ],
        "max_topics": 8,
    },
}

# ── Resource type normalization ────────────────────────────────────────────
_TAG_MAP = {
    "article": "article", "articles": "article",
    "official": "official", "offical": "official",
    "course": "course", "video": "video", "youtube": "video",
    "book": "book",
    "opensource": "article", "opensources": "article",
}

_RESOURCE_RE = re.compile(r"^-\s+\[@(\w+)@(.+?)\]\((.+?)\)\s*$", re.MULTILINE)


# ── Core parsing functions ─────────────────────────────────────────────────

def parse_content_file(md_path: Path) -> tuple[str, list[dict]]:
    """Return (description, resources) from a content markdown file."""
    try:
        text = md_path.read_text(encoding="utf-8")
    except Exception:
        return "", []

    lines = text.strip().split("\n")
    desc_lines: list[str] = []
    title_done = False

    for line in lines:
        stripped = line.strip()
        if not title_done:
            if stripped.startswith("# "):
                title_done = True
            continue
        if "visit the following resources" in stripped.lower():
            break
        if stripped:
            desc_lines.append(stripped)

    description = " ".join(desc_lines)[:300]

    resources = []
    for match in _RESOURCE_RE.finditer(text):
        tag, title, url = match.group(1), match.group(2).strip(), match.group(3).strip()
        rtype = _TAG_MAP.get(tag.lower())
        if rtype and url.startswith("http"):
            resources.append({"type": rtype, "title": title, "url": url})

    return description, resources[:5]  # cap at 5 resources per subtopic


def load_roadmap(roadmap_id: str) -> tuple[list[dict], list[dict], Path]:
    """Load nodes, edges, and content_dir from a roadmap."""
    rm_dir = ROADMAP_BASE / roadmap_id
    json_path = rm_dir / f"{roadmap_id}.json"
    if not json_path.exists():
        return [], [], rm_dir / "content"
    data = json.loads(json_path.read_text(encoding="utf-8"))
    return data.get("nodes", []), data.get("edges", []), rm_dir / "content"


def build_topic_subtopic_map(
    nodes: list[dict], edges: list[dict]
) -> dict[str, list[str]]:
    """Return {topic_id: [subtopic_id, ...]} from nodes/edges."""
    topic_ids = {n["id"] for n in nodes if n.get("type") == "topic"}
    subtopic_ids = {n["id"] for n in nodes if n.get("type") == "subtopic"}

    # edges: source → target (parent → child or reverse, try both)
    result: dict[str, list[str]] = {tid: [] for tid in topic_ids}
    for edge in edges:
        src, tgt = edge.get("source", ""), edge.get("target", "")
        if src in topic_ids and tgt in subtopic_ids:
            result[src].append(tgt)
        elif tgt in topic_ids and src in subtopic_ids:
            result[tgt].append(src)

    return result


def keyword_matches(label: str, keywords: list[str]) -> bool:
    label_lower = label.lower()
    return any(kw.lower() in label_lower for kw in keywords)


def build_path_for_role(role_id: str, config: dict, dry_run: bool = False) -> dict | None:
    """Build a learning path entry for a single role."""
    label = config["label"]
    source_roadmaps = config["source_roadmaps"]
    keywords = config["topic_keywords"]
    max_topics = config["max_topics"]

    print(f"\n{'[DRY-RUN] ' if dry_run else ''}Processing: {role_id} ({label})")

    selected_topics: list[dict] = []
    seen_labels: set[str] = set()

    for rm_id in source_roadmaps:
        if len(selected_topics) >= max_topics:
            break

        nodes, edges, content_dir = load_roadmap(rm_id)
        if not nodes:
            print(f"  ⚠️  Roadmap not found: {rm_id}")
            continue

        topic_nodes = {n["id"]: n for n in nodes if n.get("type") == "topic"}
        subtopic_nodes = {n["id"]: n for n in nodes if n.get("type") == "subtopic"}
        topic_subtopics = build_topic_subtopic_map(nodes, edges)

        print(f"  Source [{rm_id}]: {len(topic_nodes)} topics, {len(subtopic_nodes)} subtopics")

        for tid, tnode in topic_nodes.items():
            if len(selected_topics) >= max_topics:
                break

            topic_label = tnode["data"].get("label", "")
            if not topic_label:
                continue
            # Skip already-selected topics (dedup across roadmaps)
            if topic_label.lower() in seen_labels:
                continue
            # Keyword filter
            if not keyword_matches(topic_label, keywords):
                continue

            seen_labels.add(topic_label.lower())

            # Build subtopics
            sub_ids = topic_subtopics.get(tid, [])
            subtopics_out: list[dict] = []

            for sid in sub_ids:
                snode = subtopic_nodes.get(sid)
                if not snode:
                    continue
                sub_label = snode["data"].get("label", "")
                if not sub_label:
                    continue

                # Find content file
                if content_dir.exists():
                    matches = list(content_dir.glob(f"*@{sid}.md"))
                    desc, resources = ("", [])
                    if matches:
                        desc, resources = parse_content_file(matches[0])
                else:
                    desc, resources = "", []

                subtopics_out.append({
                    "id": sid,
                    "title": sub_label,
                    "description": desc,
                    "resources": resources,
                })

            # If topic has no subtopics, treat topic itself as a subtopic entry
            if not subtopics_out:
                if content_dir.exists():
                    matches = list(content_dir.glob(f"*@{tid}.md"))
                    desc, resources = ("", [])
                    if matches:
                        desc, resources = parse_content_file(matches[0])
                else:
                    desc, resources = "", []

                subtopics_out.append({
                    "id": tid,
                    "title": topic_label,
                    "description": desc,
                    "resources": resources,
                })

            # Topic-level description (from first content file matching topic id)
            topic_desc = ""
            if content_dir.exists():
                tm = list(content_dir.glob(f"*@{tid}.md"))
                if tm:
                    topic_desc, _ = parse_content_file(tm[0])

            selected_topics.append({
                "id": tid,
                "title": topic_label,
                "title_zh": _TRANSLATE.get(topic_label.lower(), ""),
                "description": topic_desc,
                "subtopics": subtopics_out,
            })

            sub_count = len(subtopics_out)
            res_count = sum(len(s["resources"]) for s in subtopics_out)
            print(f"  OK {topic_label} ({sub_count} subtopics, {res_count} resources)")

    if not selected_topics:
        print(f"  EMPTY No topics selected for {role_id}")
        return None

    print(f"  → Total: {len(selected_topics)} topics for {role_id}")

    return {
        "role_id": role_id,
        "topics": selected_topics,
    }


# ── Common Chinese translations for topic titles ───────────────────────────
_TRANSLATE: dict[str, str] = {
    "arrays and linked lists": "数组与链表",
    "trees": "树结构",
    "graphs": "图算法",
    "dynamic programming": "动态规划",
    "sorting algorithms": "排序算法",
    "searching algorithms": "搜索算法",
    "hash tables": "哈希表",
    "linear algebra": "线性代数",
    "statistics": "统计学",
    "probability": "概率论",
    "neural network basics": "神经网络基础",
    "gradient descent": "梯度下降",
    "iam": "身份与访问管理",
    "ec2": "EC2 云服务器",
    "s3": "S3 对象存储",
    "vpc": "VPC 网络",
    "kubernetes basics": "Kubernetes 基础",
    "pod": "Pod 管理",
    "deployment": "部署管理",
    "terraform basics": "Terraform 基础",
    "ci/cd": "持续集成/持续部署",
    "docker": "Docker 容器",
    "monitoring": "监控告警",
    "logging": "日志管理",
    "networking": "网络基础",
    "linux file system": "Linux 文件系统",
    "linux processes": "Linux 进程管理",
    "model serving": "模型服务化",
    "experiment tracking": "实验追踪",
    "feature store": "特征工程与存储",
    "data pipeline": "数据管道",
    "unit testing": "单元测试",
    "integration testing": "集成测试",
    "e2e testing": "端到端测试",
    "test automation": "自动化测试",
    "performance testing": "性能测试",
    "indexing": "索引设计",
    "transactions": "事务管理",
    "replication": "数据复制",
    "caching": "缓存系统",
    "load balancing": "负载均衡",
    "consensus algorithms": "共识算法",
    "threat modeling": "威胁建模",
    "penetration testing": "渗透测试",
    "cryptography": "密码学",
    "network security": "网络安全",
    "incident response": "安全事件响应",
    "compliance": "合规治理",
    "data modeling": "数据建模",
    "etl pipelines": "ETL 管道",
    "data warehouse": "数据仓库",
    "stream processing": "流处理",
    "data governance": "数据治理",
    "hiring": "招聘与人才",
    "team management": "团队管理",
    "agile": "敏捷开发",
    "technical roadmap": "技术规划",
    "architecture patterns": "架构模式",
}


# ── Main ───────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate learning paths for 10 missing roles")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be done without writing")
    parser.add_argument("--roles", nargs="+", help="Only process specific role IDs")
    args = parser.parse_args()

    # Load existing paths
    existing = {}
    if PATHS_FILE.exists():
        existing = json.loads(PATHS_FILE.read_text(encoding="utf-8"))
        print(f"Loaded existing learning_paths.json: {len(existing)} roles")

    roles_to_process = args.roles or list(ROLE_CONFIG.keys())
    added = 0
    skipped = 0

    for role_id in roles_to_process:
        if role_id not in ROLE_CONFIG:
            print(f"Unknown role: {role_id}")
            continue

        if role_id in existing:
            print(f"Skipping {role_id} (already exists)")
            skipped += 1
            continue

        config = ROLE_CONFIG[role_id]
        entry = build_path_for_role(role_id, config, dry_run=args.dry_run)

        if entry and not args.dry_run:
            existing[role_id] = entry
            added += 1
        elif entry:
            topic_count = len(entry["topics"])
            sub_count = sum(len(t["subtopics"]) for t in entry["topics"])
            print(f"  [DRY-RUN] Would add {topic_count} topics, {sub_count} subtopics")

    if not args.dry_run and added > 0:
        PATHS_FILE.write_text(
            json.dumps(existing, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\n✅ Written {added} new roles to {PATHS_FILE}")
        print(f"   Total roles in file: {len(existing)}")
    elif args.dry_run:
        print(f"\n[DRY-RUN] Would add {added if added else len(roles_to_process) - skipped} roles")
    else:
        print(f"\nNo new roles added (skipped {skipped})")


if __name__ == "__main__":
    main()
