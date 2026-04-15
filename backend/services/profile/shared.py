# -*- coding: utf-8 -*-
"""Shared constants and utilities for profile service sub-modules."""
from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
# Legacy data files — used for co-occurrence inference and scoring.
# These are optional; code gracefully handles missing files.
_PROFILES_PATH = _PROJECT_ROOT / "data" / "profiles.json"
_EVIDENCE_PATH = _PROJECT_ROOT / "data" / "evidence.jsonl"
_SKILL_EMBEDDINGS_PATH = _PROJECT_ROOT / "data" / "skill_embeddings.json"


# ═══════════════════════════════════════════════════════════════════════════════
# Constants — copied exactly from reference files
# ═══════════════════════════════════════════════════════════════════════════════

# ── Family keywords (from locate_on_graph.py) ────────────────────────────────

FAMILY_KEYWORDS: dict[str, list[str]] = {
    "quality_assurance": [
        "测试", "QA", "质量保证", "用例", "缺陷", "Bug", "自动化测试",
        "软件测试", "测试工程", "Selenium", "Pytest", "JMeter", "LoadRunner",
        "测试用例", "冒烟测试", "回归测试", "接口测试", "性能测试", "安全测试",
        "白盒", "黑盒", "ISTQB",
    ],
    "software_development": [
        "开发", "编程", "前端", "后端", "全栈", "程序员", "React", "Vue",
        "Angular", "Node.js", "Spring", "Django", "Flask", "Rails",
        "API开发", "组件开发", "页面开发", "APP开发", "游戏开发",
    ],
    "algorithm_ai": [
        "算法", "机器学习", "深度学习", "NLP", "CV", "人工智能", "大模型",
        "LLM", "推荐系统", "神经网络", "模型训练", "PyTorch", "TensorFlow",
        "强化学习", "自然语言处理", "图像识别", "目标检测", "自动驾驶",
    ],
    "data_engineering": [
        "数据工程", "ETL", "数据仓库", "大数据", "数据平台", "Spark", "Flink",
        "Hadoop", "Hive", "Kafka", "数据治理", "数据中台", "实时计算",
    ],
    "data_analysis": [
        "数据分析", "BI", "商业分析", "数据可视化", "Tableau", "Power BI",
        "数据挖掘", "运营分析",
    ],
    "devops_infra": [
        "运维", "DevOps", "SRE", "云原生", "容器", "Kubernetes", "Docker",
        "CI/CD", "网络工程", "系统管理", "DBA", "监控", "K8s",
    ],
    "embedded_hardware": [
        "嵌入式", "单片机", "FPGA", "硬件", "芯片", "固件", "PCB", "MCU",
        "ARM", "Verilog", "IoT", "物联网", "电路",
    ],
    "product_design": [
        "UI设计", "UX", "交互设计", "视觉设计", "用户研究", "Figma", "Sketch",
        "产品设计", "设计师",
    ],
    "product_management": [
        "产品经理", "产品运营", "需求管理", "产品规划", "用户增长", "竞品分析",
        "PRD",
    ],
    "delivery_and_support": [
        "实施工程", "技术支持", "售前", "售后", "客户成功", "IT支持", "系统管理",
    ],
}

# ── Degree rank mapping (from profile_scorer.py) ─────────────────────────────

_DEGREE_RANK: dict[str, int] = {
    "博士": 5, "硕士": 4, "本科": 3,
    "大专": 2, "专科": 2,
    "高中": 1, "中专": 1, "中技": 1,
    "初中": 0,
}

# ── Skill level → numeric weight (from profile_scorer.py) ────────────────────

_LEVEL_WEIGHT: dict[str, float] = {
    "beginner": 0.25, "了解": 0.25, "入门": 0.25,
    "intermediate": 0.50, "熟悉": 0.50, "一般": 0.50,
    "advanced": 0.75, "精通": 0.75, "熟练": 0.75, "熟练掌握": 0.75,
    "expert": 1.0, "专家": 1.0,
}

# ── JD proficiency → numeric weight (from profile_scorer.py) ─────────────────

_PROFICIENCY_WEIGHT: dict[str, float] = {
    "不限": 0.3, "了解": 0.25, "熟悉": 0.5,
    "精通": 0.85, "熟练": 0.7, "熟练掌握": 0.75,
    "较好": 0.6, "良好": 0.6, "较强": 0.7,
}

# ── AHP stage weights (from profile_scorer.py) ───────────────────────────────

_STAGE_WEIGHTS: dict[str, dict[str, float]] = {
    "entry":  {"basic": 0.20, "skills": 0.25, "qualities": 0.25, "potential": 0.30},
    "mid":    {"basic": 0.15, "skills": 0.40, "qualities": 0.25, "potential": 0.20},
    "senior": {"basic": 0.10, "skills": 0.35, "qualities": 0.35, "potential": 0.20},
}

# ── Default soft skill weights (from profile_scorer.py) ──────────────────────

_DEFAULT_SSW: dict[str, float] = {
    "communication": 0.35, "learning": 0.35, "collaboration": 0.30,
}

# ── Rank depth multiplier (from profile_scorer.py) ───────────────────────────

_RANK_DEPTH_MULTIPLIER: dict[int, float] = {0: 0.3, 1: 0.6, 2: 1.0}

# ── Direction ID → graph node ID mapping (from profile_scorer.py) ────────────

_DIRECTION_TO_GRAPH_NODE: dict[str, str] = {
    "15-1254.00": "前端开发",
    "15-1253.00": "测试工程师 / 软件测试",
    "15-1232.00": "实施工程师 / 技术支持工程师",
    "41-3091.00": "商务专员 / 广告销售 / 电话销售",
    "19-2099.00": "科研人员",
    "17-2072.00": "硬件测试",
    "13-1071.00": "招聘专员/助理",
    "23-1011.00": "法务专员/助理",
    "11-1021.00": "游戏运营 / 社区运营 / 运营助理/专员",
}


_SOFT_DIM_ZH = {
    "communication": "沟通能力",
    "learning": "学习能力",
    "resilience": "抗压能力",
    "innovation": "创新能力",
    "collaboration": "协作能力",
}


# ═══════════════════════════════════════════════════════════════════════════════
# Shared utilities
# ═══════════════════════════════════════════════════════════════════════════════


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


def _user_skill_map(profile: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Extract {skill_name_lower: {level, ...}} from user profile."""
    result: dict[str, dict[str, Any]] = {}
    for s in profile.get("skills", []):
        if isinstance(s, dict):
            name = (s.get("name") or "").strip()
            if name:
                result[name.lower()] = s
        elif isinstance(s, str) and s.strip():
            result[s.strip().lower()] = {"name": s.strip(), "level": "intermediate"}
    return result


def _user_cert_set(profile: dict[str, Any]) -> set[str]:
    """Extract user certificate name set (lowercased)."""
    certs: set[str] = set()
    for c in profile.get("certificates", []):
        name = c if isinstance(c, str) else (c.get("name") or "")
        if name.strip():
            certs.add(name.strip().lower())
    return certs


def _user_competency_names(profile: dict[str, Any]) -> set[str]:
    """Extract user competency name set."""
    names: set[str] = set()
    for c in profile.get("competencies", []):
        name = c.get("name", "") if isinstance(c, dict) else str(c)
        if name.strip():
            names.add(name.strip())
    # Also support 'competency' dict
    comp_dict = profile.get("competency", {})
    if isinstance(comp_dict, dict):
        for name in comp_dict:
            if name.strip():
                names.add(name.strip())
    return names


def _soft_skills_as_list(raw) -> list[str]:
    """Normalize soft_skills to a list of Chinese label strings.

    Handles both legacy list-of-str and new dict-of-scores formats.
    """
    if isinstance(raw, dict):
        return [_SOFT_DIM_ZH.get(k, k) for k, v in raw.items() if isinstance(v, (int, float)) and v >= 3]
    if isinstance(raw, list):
        return [s.strip() for s in raw if isinstance(s, str) and s.strip()]
    return []


def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Cosine similarity between two vectors."""
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
