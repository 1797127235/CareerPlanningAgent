# -*- coding: utf-8 -*-
"""
ProfileService — unified profile analysis service.

Consolidates five algorithm modules into one Service class:
  - locate_on_graph (IDF-weighted graph positioning)
  - profile_scorer (seven-dimension + four-dimension scoring)
  - sjt_scorer (SJT situational judgment scoring)
  - skill_cooccurrence (co-occurrence based skill inference)
  - skill_inferrer (ESCO DAG-based skill inference)

Public methods:
  locate_on_graph()            — IDF-weighted positioning on career graph
  score_four_dimensions()      — Four-dimension scoring (basic/skills/qualities/potential)
  score_sjt_v2()               — SJT v2 scoring from scenario-based answers
  infer_skills_cooccurrence()  — Co-occurrence based skill inference
  infer_skills_esco()          — ESCO DAG-based skill inference
"""
from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
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


# ═══════════════════════════════════════════════════════════════════════════════
# Helper functions — positioning (from locate_on_graph.py)
# ═══════════════════════════════════════════════════════════════════════════════


def _collect_profile_text(profile: dict[str, Any]) -> list[tuple[str, float]]:
    """Collect resume text fields with signal weights.

    Returns [(text, weight), ...] — stronger signals get higher weight.
    """
    texts: list[tuple[str, float]] = []
    # current_title (strongest signal)
    title = profile.get("current_title", "")
    if title and title.strip():
        texts.append((title, 3.0))
    # internships
    for intern in profile.get("internships", []):
        if isinstance(intern, dict):
            role = intern.get("role", "")
            desc = intern.get("description", "")
            if role:
                texts.append((role, 2.0))
            if desc:
                texts.append((desc, 1.5))
    # work experience
    for work in profile.get("work_experiences", []):
        if isinstance(work, dict):
            role = work.get("role", "")
            desc = work.get("description", "")
            if role:
                texts.append((role, 2.0))
            if desc:
                texts.append((desc, 1.5))
    # Also support 'experience' key (from sample_profile)
    for work in profile.get("experience", []):
        if isinstance(work, dict):
            title_val = work.get("title", "")
            desc = work.get("description", "")
            if title_val:
                texts.append((title_val, 2.0))
            if desc:
                texts.append((desc, 1.5))
    # projects
    for proj in profile.get("projects", []):
        if isinstance(proj, dict):
            name = proj.get("name", "")
            desc = proj.get("description", "")
            if name:
                texts.append((name, 1.5))
            if desc:
                texts.append((desc, 1.5))
    # knowledge areas
    for ka in profile.get("knowledge_areas", []):
        if ka and ka.strip():
            texts.append((ka, 1.0))
    # Also support 'knowledge' key
    for ka in profile.get("knowledge", []):
        if ka and ka.strip():
            texts.append((ka, 1.0))
    # certificates
    for cert in profile.get("certificates", []):
        cert_name = cert.get("name", "") if isinstance(cert, dict) else str(cert)
        if cert_name and cert_name.strip():
            texts.append((cert_name, 0.5))
    return texts


def _build_family_task_vocab(
    graph_nodes: dict[str, Any],
) -> dict[str, set[str]]:
    """Build family task vocabulary from graph node core_tasks.

    Only keeps phrases with length >= 3 to avoid false matches.
    """
    vocab: dict[str, set[str]] = defaultdict(set)
    for node in graph_nodes.values():
        fam = node.get("role_family", "")
        if not fam:
            continue
        for task in node.get("core_tasks", []):
            task = task.strip()
            if len(task) >= 3:
                vocab[fam].add(task)
    return dict(vocab)


def _infer_family_prior(
    profile: dict[str, Any],
    family_keywords: dict[str, list[str]],
    family_task_vocab: dict[str, set[str]],
) -> dict[str, float]:
    """Infer family prior distribution from resume text.

    Scans family_keywords and family_task_vocab, accumulates by signal weight,
    normalizes to [0, 1].
    """
    texts = _collect_profile_text(profile)
    if not texts:
        return {}

    family_score: dict[str, float] = defaultdict(float)

    for text, weight in texts:
        text_lower = text.lower()
        # keyword matching
        for fam, keywords in family_keywords.items():
            for kw in keywords:
                if kw.lower() in text_lower:
                    family_score[fam] += weight
        # core_tasks matching (stronger signal)
        for fam, tasks in family_task_vocab.items():
            for task in tasks:
                if task in text:
                    family_score[fam] += weight * 1.5

    if not family_score:
        return {}

    max_score = max(family_score.values())
    if max_score <= 0:
        return {}
    return {fam: score / max_score for fam, score in family_score.items()}


def _task_match(profile: dict[str, Any], node: dict[str, Any]) -> float:
    """Substring match of user project/internship descriptions against node core_tasks."""
    core_tasks = [
        t.strip() for t in node.get("core_tasks", []) if t and len(t.strip()) >= 3
    ]
    if not core_tasks:
        return 0.0

    user_text_parts: list[str] = []
    for proj in profile.get("projects", []):
        if isinstance(proj, dict):
            user_text_parts.append(proj.get("name", ""))
            user_text_parts.append(proj.get("description", ""))
    for intern in profile.get("internships", []):
        if isinstance(intern, dict):
            user_text_parts.append(intern.get("role", ""))
            user_text_parts.append(intern.get("description", ""))
    for work in profile.get("work_experiences", []):
        if isinstance(work, dict):
            user_text_parts.append(work.get("description", ""))
    # Also support 'experience' key
    for work in profile.get("experience", []):
        if isinstance(work, dict):
            user_text_parts.append(work.get("description", ""))
    user_text = " ".join(user_text_parts).strip()
    if not user_text:
        return 0.0

    hits = sum(1 for task in core_tasks if task in user_text)
    return hits / len(core_tasks)


def _skill_names_from_profile(
    profile: dict[str, Any],
    graph_skill_vocab: set[str] | None = None,
) -> set[str]:
    """Extract skill name set from user profile (lowercased for matching).

    Includes ESCO canonical name, raw_name, knowledge_areas, and
    scans project/internship descriptions for graph skill vocab matches.
    """
    names: set[str] = set()
    for s in profile.get("skills", []):
        if isinstance(s, dict):
            name = s.get("name", "")
            if name.strip():
                names.add(name.strip().lower())
            raw = s.get("raw_name", "")
            if raw.strip():
                names.add(raw.strip().lower())
        else:
            name = str(s)
            if name.strip():
                names.add(name.strip().lower())
    # knowledge_areas as weak skill signals
    for ka in profile.get("knowledge_areas", []):
        if ka and ka.strip():
            names.add(ka.strip().lower())
    # Also support 'knowledge' key
    for ka in profile.get("knowledge", []):
        if ka and ka.strip():
            names.add(ka.strip().lower())
    # Scan descriptions for graph skill vocab matches
    if graph_skill_vocab:
        desc_texts: list[str] = []
        for proj in profile.get("projects", []):
            if isinstance(proj, dict):
                desc_texts.append(proj.get("name", ""))
                desc_texts.append(proj.get("description", ""))
                for su in proj.get("skills_used", []):
                    if su and su.strip():
                        names.add(su.strip().lower())
                # Also support 'tech_stack' key
                for su in proj.get("tech_stack", []):
                    if su and su.strip():
                        names.add(su.strip().lower())
        for intern in profile.get("internships", []):
            if isinstance(intern, dict):
                desc_texts.append(intern.get("role", ""))
                desc_texts.append(intern.get("description", ""))
        for work in profile.get("work_experiences", []):
            if isinstance(work, dict):
                desc_texts.append(work.get("description", ""))
        for work in profile.get("experience", []):
            if isinstance(work, dict):
                desc_texts.append(work.get("description", ""))
        combined = " ".join(desc_texts).lower()
        if combined.strip():
            for skill in graph_skill_vocab:
                if len(skill) >= 2 and skill in combined:
                    names.add(skill)
    return names


def _node_skill_set(node: dict[str, Any]) -> set[str]:
    """Extract must_skills set from graph node (lowercased)."""
    return {s.strip().lower() for s in node.get("must_skills", []) if s and s.strip()}


def _build_skill_idf(graph_nodes: dict[str, Any]) -> dict[str, float]:
    """Compute IDF weight for each skill across all graph nodes.

    IDF = log((N+1) / (1 + doc_count))
    """
    skill_doc_count: dict[str, int] = {}
    total = len(graph_nodes)
    for node in graph_nodes.values():
        seen: set[str] = set()
        for s in node.get("must_skills", []):
            sl = s.strip().lower()
            if sl and sl not in seen:
                skill_doc_count[sl] = skill_doc_count.get(sl, 0) + 1
                seen.add(sl)
    return {
        skill: math.log((total + 1) / (1 + cnt))
        for skill, cnt in skill_doc_count.items()
    }


def _weighted_skill_match(
    user_skills: set[str],
    node_skills: set[str],
    idf: dict[str, float],
) -> float:
    """IDF-weighted skill match score.

    Numerator: sum of IDF for skills in both user and node.
    Denominator: sum of IDF for all node must_skills.
    Result range [0, 1].
    """
    if not node_skills:
        return 0.0
    total_w = sum(idf.get(s, 1.0) for s in node_skills)
    if total_w == 0:
        return 0.0
    match_w = sum(idf.get(s, 1.0) for s in (user_skills & node_skills))
    return match_w / total_w


def _extract_terms(text: str) -> set[str]:
    """Extract matching terms from mixed Chinese/English text.

    English: split by separators; Chinese: contiguous sequences + bigrams.
    """
    parts: set[str] = set()
    for token in text.replace("/", " ").replace("-", " ").replace("_", " ").split():
        if token:
            parts.add(token)
    for match in re.finditer(r"[\u4e00-\u9fff]{2,}", text):
        seq = match.group()
        parts.add(seq)
        for i in range(len(seq) - 1):
            parts.add(seq[i: i + 2])
    return parts


def _title_bonus(user_title: str, node_label: str) -> float:
    """Title match score, returns 0-1.

    1.0 = full substring hit
    0.5 = partial term overlap (including Chinese bigrams)
    0.0 = unrelated
    """
    if not user_title or not node_label:
        return 0.0
    ut = user_title.strip().lower()
    nl = node_label.strip().lower()
    if ut in nl or nl in ut:
        return 1.0
    ut_terms = _extract_terms(ut)
    nl_terms = _extract_terms(nl)
    if not ut_terms or not nl_terms:
        return 0.0
    overlap = ut_terms & nl_terms
    if overlap and len(overlap) >= max(1, min(len(ut_terms), len(nl_terms)) // 2):
        return 0.5
    return 0.0


def _soft_match_lite(required: str, user_comps: set[str]) -> bool:
    """Lightweight competency matching for positioning stage.

    - Exact match → True
    - Short word (<=2 chars) only matches as prefix
    - Long words: bigram Jaccard >= 0.2
    """
    req = required.strip()
    if not req:
        return False
    for comp in user_comps:
        comp = comp.strip()
        if not comp:
            continue
        if req == comp:
            return True
        shorter, longer = (req, comp) if len(req) <= len(comp) else (comp, req)
        if len(shorter) <= 2:
            if longer.startswith(shorter):
                return True
            continue
        req_bg = (
            {req[i: i + 2] for i in range(len(req) - 1)} if len(req) >= 2 else {req}
        )
        comp_bg = (
            {comp[i: i + 2] for i in range(len(comp) - 1)}
            if len(comp) >= 2
            else {comp}
        )
        union = req_bg | comp_bg
        if union and len(req_bg & comp_bg) / len(union) >= 0.2:
            return True
    return False


_SOFT_DIM_ZH = {
    "communication": "沟通能力",
    "learning": "学习能力",
    "resilience": "抗压能力",
    "innovation": "创新能力",
    "collaboration": "协作能力",
}


def _soft_skills_as_list(raw) -> list[str]:
    """Normalize soft_skills to a list of Chinese label strings.

    Handles both legacy list-of-str and new dict-of-scores formats.
    """
    if isinstance(raw, dict):
        return [_SOFT_DIM_ZH.get(k, k) for k, v in raw.items() if isinstance(v, (int, float)) and v >= 3]
    if isinstance(raw, list):
        return [s.strip() for s in raw if isinstance(s, str) and s.strip()]
    return []


def _competency_match(profile: dict[str, Any], node: dict[str, Any]) -> float:
    """Match user competencies against node soft_skills, returns 0-1."""
    node_soft = {s for s in _soft_skills_as_list(node.get("soft_skills", []))}
    if not node_soft:
        return 0.0
    user_comp_names: set[str] = set()
    # Support 'competencies' list
    for c in profile.get("competencies", []):
        name = c.get("name", "") if isinstance(c, dict) else str(c)
        if name.strip():
            user_comp_names.add(name.strip())
    # Support 'competency' dict (from sample_profile)
    comp_dict = profile.get("competency", {})
    if isinstance(comp_dict, dict):
        for name in comp_dict:
            if name.strip():
                user_comp_names.add(name.strip())
    # Support 'soft_skills' dict
    ss_dict = profile.get("soft_skills", {})
    if isinstance(ss_dict, dict):
        for name in ss_dict:
            if name.strip():
                user_comp_names.add(name.strip())
    if not user_comp_names:
        return 0.0
    hit = sum(1 for s in node_soft if _soft_match_lite(s, user_comp_names))
    return hit / len(node_soft)


# ═══════════════════════════════════════════════════════════════════════════════
# Helper functions — scoring (from profile_scorer.py)
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


# ═══════════════════════════════════════════════════════════════════════════════
# Seven-dimension scoring functions (from profile_scorer.py)
# ═══════════════════════════════════════════════════════════════════════════════


def _compute_idf_cross_direction(profiles: dict[str, Any]) -> dict[str, float]:
    """Compute cross-direction IDF for each skill.

    IDF(skill) = log(N / (1 + df))
    """
    n_directions = len(profiles)
    doc_freq: dict[str, int] = {}
    for direction in profiles.values():
        stg = direction.get("skill_type_groups", {})
        seen_skills: set[str] = set()
        for group in (
            (stg.get("hard_skill") or [])
            + (stg.get("knowledge") or [])
            + (stg.get("soft_skill") or [])
        ):
            if isinstance(group, dict):
                name = (group.get("skill") or group.get("name") or "").strip().lower()
                if name and name not in seen_skills:
                    seen_skills.add(name)
                    doc_freq[name] = doc_freq.get(name, 0) + 1

    return {
        skill: math.log(n_directions / (1 + df))
        for skill, df in doc_freq.items()
    }


def _score_skill_coverage(
    user_skills: dict[str, dict],
    direction: dict[str, Any],
    idf: dict[str, float],
) -> tuple[float, dict]:
    """Dimension 1: Skill coverage — TF-IDF weighted coverage ratio."""
    stg = direction.get("skill_type_groups", {})
    required_skills = (stg.get("hard_skill") or []) + (stg.get("knowledge") or [])
    if not required_skills:
        required_skills = direction.get("top_skills", [])

    if not required_skills:
        return 0.5, {"detail": "该方向无技能数据", "matched": [], "missing": []}

    jd_count = max(direction.get("jd_count", 1), 1)
    total_weight = 0.0
    matched_weight = 0.0
    matched_list: list[str] = []
    missing_list: list[dict] = []

    for skill_entry in required_skills[:15]:
        if not isinstance(skill_entry, dict):
            continue
        skill_name = (skill_entry.get("skill") or skill_entry.get("name") or "").strip()
        if not skill_name:
            continue
        count = skill_entry.get("count", 0) or 0
        tf = count / jd_count
        skill_idf = idf.get(skill_name.lower(), 1.0)
        tfidf = tf * skill_idf
        total_weight += tfidf

        if skill_name.lower() in user_skills:
            matched_weight += tfidf
            matched_list.append(skill_name)
        else:
            missing_list.append({
                "name": skill_name,
                "frequency": round(tf, 3),
                "idf": round(skill_idf, 2),
                "tfidf": round(tfidf, 3),
            })

    score = matched_weight / total_weight if total_weight > 0 else 0.0
    return round(min(score, 1.0), 3), {
        "matched": matched_list,
        "missing": missing_list[:8],
    }


def _score_skill_depth(
    user_skills: dict[str, dict],
    direction: dict[str, Any],
) -> tuple[float, dict]:
    """Dimension 2: Skill depth — user level vs JD proficiency requirements."""
    stg = direction.get("skill_type_groups", {})
    required_skills = (stg.get("hard_skill") or []) + (stg.get("knowledge") or [])
    if not required_skills:
        return 0.5, {"detail": "无技能数据"}

    depth_scores: list[float] = []
    rank_weights: list[float] = []
    details: list[dict] = []

    for skill_entry in required_skills[:15]:
        if not isinstance(skill_entry, dict):
            continue
        skill_name = (skill_entry.get("skill") or skill_entry.get("name") or "").strip()
        if not skill_name or skill_name.lower() not in user_skills:
            continue

        user_info = user_skills[skill_name.lower()]
        user_level_w = _LEVEL_WEIGHT.get(user_info.get("level", "intermediate"), 0.5)

        # JD required average proficiency
        prof_dist = skill_entry.get("proficiency_dist", {})
        unspecified_ratio = 0.0
        if prof_dist:
            total_cnt = sum(prof_dist.values())
            if total_cnt > 0:
                unspecified_cnt = prof_dist.get("不限", 0)
                unspecified_ratio = unspecified_cnt / total_cnt
                required_w = sum(
                    _PROFICIENCY_WEIGHT.get(level, 0.3) * cnt
                    for level, cnt in prof_dist.items()
                ) / total_cnt
            else:
                required_w = 0.3
        else:
            required_w = 0.3

        if unspecified_ratio > 0.8:
            raw_score = user_level_w
        else:
            ratio = min(user_level_w / max(required_w, 0.1), 1.5)
            raw_score = min(ratio, 1.0)

        # Default rank=1 (no ESCO dependency in service layer)
        rank = 1
        weight = _RANK_DEPTH_MULTIPLIER.get(rank, 0.6)

        depth_scores.append(raw_score * weight)
        rank_weights.append(weight)
        details.append({
            "skill": skill_name,
            "user_level": user_info.get("level", "?"),
            "required_avg": round(required_w, 2),
            "rank": rank,
        })

    if not depth_scores:
        return 0.0, {"skills_compared": 0, "details": []}

    total_weight = sum(rank_weights)
    score = sum(depth_scores) / total_weight if total_weight > 0 else 0.0
    return round(score, 3), {"skills_compared": len(depth_scores), "details": details[:5]}


def _score_experience(
    profile: dict[str, Any],
    direction: dict[str, Any],
) -> tuple[float, dict]:
    """Dimension 3: Experience match — user years vs JD percentiles."""
    exp_data = direction.get("experience", {}).get("years", {})
    p25 = exp_data.get("p25")
    p50 = exp_data.get("p50")
    p75 = exp_data.get("p75")

    # Calculate user experience years
    user_years = 0.0
    for intern in profile.get("internships", []):
        dur = intern.get("duration", "")
        if isinstance(dur, (int, float)):
            user_years += dur / 12.0
        elif isinstance(dur, str) and dur:
            m = re.search(r"(\d+)", dur)
            if m:
                num = int(m.group(1))
                if "年" in dur:
                    user_years += num
                else:
                    user_years += num / 12.0
    for we in profile.get("work_experiences", []):
        dur = we.get("duration", "")
        if isinstance(dur, (int, float)):
            user_years += dur / 12.0
        elif isinstance(dur, str) and dur:
            m = re.search(r"(\d+)", dur)
            if m:
                num = int(m.group(1))
                if "年" in dur:
                    user_years += num
                else:
                    user_years += num / 12.0
    # Support 'experience' key with duration_months
    for we in profile.get("experience", []):
        if isinstance(we, dict):
            dur = we.get("duration_months", 0)
            if isinstance(dur, (int, float)):
                user_years += dur / 12.0

    if p50 is None:
        return 0.5, {"detail": "该方向无经验数据", "user_years": round(user_years, 1)}

    p50 = float(p50)
    if p50 <= 0:
        level_dist = direction.get("experience", {}).get("level_dist", {})
        total_levels = sum(level_dist.values()) if level_dist else 0
        if total_levels > 0:
            senior = level_dist.get("senior", 0)
            mid = level_dist.get("mid", 0)
            experienced_ratio = (mid + senior) / total_levels
            if user_years >= 2:
                score = 1.0
            elif user_years >= 1:
                score = 0.7 + 0.3 * (1 - experienced_ratio)
            else:
                score = 0.5 + 0.3 * (1 - experienced_ratio)
        else:
            score = 0.8
    elif user_years >= p50:
        score = min(1.0, 0.8 + 0.2 * min(user_years / max(p50, 0.1), 2.0))
    else:
        score = max(0.1, user_years / max(p50, 0.1)) * 0.8

    return round(score, 3), {
        "user_years": round(user_years, 1),
        "required_p50": p50,
        "required_p25": p25,
    }


def _score_education(
    profile: dict[str, Any],
    direction: dict[str, Any],
) -> tuple[float, dict]:
    """Dimension 4: Education match — user degree vs JD distribution."""
    edu_dist = direction.get("education_dist", {})
    if not edu_dist:
        return 0.5, {"detail": "该方向无学历数据"}

    user_degree = (
        profile.get("basic_info", {}).get("degree", "")
        or profile.get("basic_info", {}).get("education", "")
        or profile.get("degree", "")
    ).strip()
    user_rank = _DEGREE_RANK.get(user_degree, 2)

    total = sum(edu_dist.values())
    if total <= 0:
        return 0.5, {"detail": "学历数据为空"}

    required_avg_rank = sum(
        _DEGREE_RANK.get(deg, 2) * cnt for deg, cnt in edu_dist.items()
    ) / total

    if user_rank >= required_avg_rank:
        score = 1.0
    else:
        score = max(0.2, user_rank / max(required_avg_rank, 1))

    return round(score, 3), {
        "user_degree": user_degree or "未填写",
        "user_rank": user_rank,
        "required_avg_rank": round(required_avg_rank, 1),
        "distribution": edu_dist,
    }


def _score_practice(
    profile: dict[str, Any],
    direction: dict[str, Any],
) -> tuple[float, dict]:
    """Dimension 5: Practice depth — project + internship count."""
    project_count = len(profile.get("projects", []))
    intern_count = len(profile.get("internships", []))
    work_count = len(profile.get("work_experiences", []))
    exp_count = len(profile.get("experience", []))
    total_practice = project_count + intern_count + work_count + exp_count

    level_dist = direction.get("experience", {}).get("level_dist", {})
    senior_ratio = level_dist.get("senior", 0)
    mid_ratio = level_dist.get("mid", 0)
    total_levels = senior_ratio + mid_ratio + level_dist.get("junior", 0)

    if total_levels > 0:
        expected_practice = 2 + (senior_ratio + mid_ratio) / total_levels * 4
    else:
        expected_practice = 3

    score = min(1.0, total_practice / max(expected_practice, 1))
    return round(score, 3), {
        "projects": project_count,
        "internships": intern_count,
        "work_experiences": work_count + exp_count,
        "expected": round(expected_practice, 1),
    }


def _score_certificates(
    user_certs: set[str],
    direction: dict[str, Any],
) -> tuple[float, dict]:
    """Dimension 6: Certificate match."""
    dir_certs = direction.get("certificates", [])
    if not dir_certs:
        return 1.0, {"detail": "该方向无证书要求", "matched": [], "missing": []}

    dir_cert_names: list[str] = []
    for c in dir_certs:
        name = c.get("name", "") if isinstance(c, dict) else str(c)
        if name.strip():
            dir_cert_names.append(name.strip())

    if not dir_cert_names:
        return 1.0, {"detail": "该方向无证书要求", "matched": [], "missing": []}

    matched = [c for c in dir_cert_names if c.lower() in user_certs]
    missing = [c for c in dir_cert_names if c.lower() not in user_certs]

    score = len(matched) / len(dir_cert_names)
    return round(score, 3), {"matched": matched, "missing": missing}


def _score_competency(
    user_competencies: set[str],
    direction: dict[str, Any],
    graph_node: dict[str, Any] | None = None,
) -> tuple[float, dict]:
    """Dimension 7: Competency match — user competencies vs soft_skills."""
    soft_skills: list[str] = []
    if graph_node:
        soft_skills = graph_node.get("soft_skills", [])
    if not soft_skills:
        stg = direction.get("skill_type_groups", {})
        for s in (stg.get("soft_skill") or [])[:5]:
            name = s.get("skill") or s.get("name") or ""
            if name.strip():
                soft_skills.append(name.strip())

    if not soft_skills:
        return 0.5, {"detail": "该方向无素质要求"}

    matched: list[str] = []
    missing: list[str] = []
    for soft in soft_skills:
        if any(soft in comp or comp in soft for comp in user_competencies):
            matched.append(soft)
        else:
            missing.append(soft)

    score = len(matched) / len(soft_skills) if soft_skills else 0.5
    return round(score, 3), {"matched": matched, "missing": missing}


def _compute_weights(direction: dict[str, Any]) -> dict[str, float]:
    """Auto-derive dimension weights from JD data distribution."""
    stg = direction.get("skill_type_groups", {})
    hard_mentions = sum(s.get("count", 0) for s in (stg.get("hard_skill") or []))
    soft_mentions = sum(s.get("count", 0) for s in (stg.get("soft_skill") or []))
    knowledge_mentions = sum(s.get("count", 0) for s in (stg.get("knowledge") or []))
    total_mentions = hard_mentions + soft_mentions + knowledge_mentions

    if total_mentions <= 0:
        return {
            "skill_coverage": 0.25, "skill_depth": 0.15,
            "experience": 0.15, "education": 0.10,
            "practice": 0.15, "certificates": 0.05,
            "competency": 0.15,
        }

    hard_ratio = hard_mentions / total_mentions
    soft_ratio = soft_mentions / total_mentions

    exp_p50 = (direction.get("experience", {}).get("years", {}).get("p50") or 0)
    exp_boost = min(0.10, float(exp_p50) * 0.03)

    cert_count = len(direction.get("certificates", []))
    cert_boost = min(0.08, cert_count * 0.03)

    raw = {
        "skill_coverage": 0.15 + hard_ratio * 0.20,
        "skill_depth": 0.10 + hard_ratio * 0.10,
        "experience": 0.10 + exp_boost,
        "education": 0.08,
        "practice": 0.12,
        "certificates": 0.03 + cert_boost,
        "competency": 0.08 + soft_ratio * 0.10,
    }

    total = sum(raw.values())
    return {k: round(v / total, 3) for k, v in raw.items()}


# ═══════════════════════════════════════════════════════════════════════════════
# Four-dimension aggregation helpers (from profile_scorer.py)
# ═══════════════════════════════════════════════════════════════════════════════


def _infer_career_stage(profile: dict[str, Any], dims: dict) -> str:
    """Infer career stage from 7-dim results."""
    user_years = dims.get("experience", {}).get("detail", {}).get("user_years", 0)
    if user_years <= 2:
        return "entry"
    elif user_years <= 7:
        return "mid"
    return "senior"


def _score_basic(dims: dict) -> tuple[float, dict]:
    """Basic requirements = education(0.30) + certificates(0.20) + experience(0.50)."""
    s_edu = dims["education"]["score"] / 100.0
    s_cert = dims["certificates"]["score"] / 100.0
    s_exp = dims["experience"]["score"] / 100.0
    score = 0.30 * s_edu + 0.20 * s_cert + 0.50 * s_exp
    return score, {
        "education": round(s_edu * 100, 1),
        "certificates": round(s_cert * 100, 1),
        "experience": round(s_exp * 100, 1),
    }


def _score_skills_agg(dims: dict) -> tuple[float, dict]:
    """Professional skills = coverage(0.40) + depth(0.35) + practice(0.25)."""
    s_cov = dims["skill_coverage"]["score"] / 100.0
    s_dep = dims["skill_depth"]["score"] / 100.0
    s_pra = dims["practice"]["score"] / 100.0
    score = 0.40 * s_cov + 0.35 * s_dep + 0.25 * s_pra
    return score, {
        "coverage": round(s_cov * 100, 1),
        "depth": round(s_dep * 100, 1),
        "practice": round(s_pra * 100, 1),
    }


def _score_qualities(
    user_profile: dict[str, Any],
    graph_node: dict[str, Any] | None,
    sjt_scores: dict[str, float] | None,
) -> tuple[float, dict]:
    """Professional qualities — 3 sub-dimensions weighted by job soft_skill_weights."""
    ssw = (graph_node or {}).get("soft_skill_weights") or {}
    # Fallback: if old 5-dim weights or empty, use default 3-dim
    dims_v2 = ["communication", "learning", "collaboration"]
    if not all(d in ssw for d in dims_v2):
        ssw = _DEFAULT_SSW.copy()

    user_soft = user_profile.get("soft_skills", {})

    sub_scores: dict[str, float] = {}
    for dim in dims_v2:
        job_weight = ssw.get(dim, 0.33)

        # User score from soft_skills dict (v2 format)
        user_val = user_soft.get(dim)
        if isinstance(user_val, dict):
            user_score = user_val.get("score", 0) / 100.0
        elif isinstance(user_val, (int, float)):
            user_score = user_val / 100.0
        else:
            user_score = 0  # Not assessed yet

        # Match: user / job_requirement, capped at 1.0
        if job_weight > 0.05:
            match = _clamp01(user_score / job_weight)
        else:
            match = _clamp01(user_score)

        sub_scores[dim] = round(match * 100, 1)

    # Weighted average by job weights
    total_w = sum(ssw.get(d, 0.33) for d in dims_v2)
    if total_w > 0:
        score = sum(sub_scores[d] / 100.0 * ssw.get(d, 0.33) for d in dims_v2) / total_w
    else:
        score = sum(sub_scores[d] for d in dims_v2) / (100.0 * len(dims_v2))

    return score, {d: sub_scores[d] for d in dims_v2}


def _score_potential(
    direction: dict[str, Any],
    role_family: str,
) -> tuple[float, dict]:
    """Development potential — salary_growth + skill_growth + promotion + outlook.

    Returns neutral scores (0.5) since market signal DB queries are deferred.
    """
    s_salary = 0.5
    s_skill = 0.5

    # Promotion space from level distribution
    level_dist = direction.get("experience", {}).get("level_dist", {})
    total_levels = sum(level_dist.values()) or 1
    senior_ratio = level_dist.get("senior", 0) / total_levels
    exp_years = direction.get("experience", {}).get("years", {})
    p25 = exp_years.get("p25", 1) or 1
    p75 = exp_years.get("p75", 3) or 3
    spread = p75 / max(p25, 0.5)
    s_promotion = _clamp01(0.5 * min(1.0, senior_ratio * 3) + 0.5 * min(1.0, spread / 5))

    s_outlook = 0.5

    score = 0.30 * s_salary + 0.25 * s_skill + 0.20 * s_promotion + 0.25 * s_outlook

    return score, {
        "salary_growth": round(s_salary * 100, 1),
        "skill_growth": round(s_skill * 100, 1),
        "promotion_space": round(s_promotion * 100, 1),
        "industry_outlook": round(s_outlook * 100, 1),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Co-occurrence helper (from skill_cooccurrence.py)
# ═══════════════════════════════════════════════════════════════════════════════


def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Cosine similarity between two vectors."""
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ═══════════════════════════════════════════════════════════════════════════════
# ProfileService
# ═══════════════════════════════════════════════════════════════════════════════


class ProfileService:
    """Unified profile analysis service.

    Replaces 5 separate algorithm files with one Service class:
    - locate_on_graph.py → locate_on_graph()
    - profile_scorer.py → score_four_dimensions()
    - sjt_scorer.py → score_sjt_v2()
    - skill_cooccurrence.py → infer_skills_cooccurrence()
    - skill_inferrer.py → infer_skills_esco()
    """

    def __init__(self, graph_service: Any):
        from backend.services.graph_service import GraphService
        self._graph: GraphService = graph_service
        self._profiles_cache: dict[str, Any] | None = None
        self._idf_cache: dict[str, float] | None = None
        self._cooccurrence_loaded = False
        self._cooccurrence_conditional: dict[str, list[tuple[str, float]]] = {}
        self._skill_count: dict[str, int] = {}
        self._total_jds: int = 0
        self._skill_embeddings: dict[str, list[float]] | None = None

    # ------------------------------------------------------------------
    # Data loading helpers
    # ------------------------------------------------------------------

    def _load_profiles(self) -> dict[str, Any]:
        """Lazy-load profiles.json."""
        if self._profiles_cache is None:
            if _PROFILES_PATH.exists():
                self._profiles_cache = json.loads(
                    _PROFILES_PATH.read_text(encoding="utf-8")
                )
            else:
                self._profiles_cache = {}
        return self._profiles_cache

    def _get_cross_direction_idf(self) -> dict[str, float]:
        """Lazy-compute cross-direction IDF."""
        if self._idf_cache is None:
            profiles = self._load_profiles()
            self._idf_cache = _compute_idf_cross_direction(profiles)
        return self._idf_cache

    def _load_cooccurrence(self) -> None:
        """Lazy-load co-occurrence graph from evidence.jsonl."""
        if self._cooccurrence_loaded:
            return
        self._cooccurrence_loaded = True

        if not _EVIDENCE_PATH.exists():
            return

        from itertools import combinations

        pair_count: dict[tuple[str, str], int] = defaultdict(int)
        skill_count: dict[str, int] = defaultdict(int)
        total_jds = 0

        with open(_EVIDENCE_PATH, encoding="utf-8") as f:
            for line in f:
                try:
                    jd = json.loads(line)
                except json.JSONDecodeError:
                    continue

                skills_raw = jd.get("skills", [])
                if not isinstance(skills_raw, list):
                    continue

                skill_names: set[str] = set()
                for s in skills_raw:
                    if not isinstance(s, dict):
                        continue
                    cat = (s.get("category") or "").lower()
                    if cat == "soft_skill":
                        continue
                    name = (s.get("name") or "").strip()
                    if name:
                        skill_names.add(name)

                if len(skill_names) < 2:
                    continue

                total_jds += 1
                for name in skill_names:
                    skill_count[name] += 1

                for a, b in combinations(sorted(skill_names), 2):
                    pair_count[(a, b)] += 1

        self._skill_count = dict(skill_count)
        self._total_jds = total_jds

        # Build conditional probability index: P(B|A) = count(A,B) / count(A)
        conditional: dict[str, list[tuple[str, float]]] = defaultdict(list)
        for (a, b), count in pair_count.items():
            prob_b_given_a = count / skill_count[a] if skill_count[a] > 0 else 0
            prob_a_given_b = count / skill_count[b] if skill_count[b] > 0 else 0

            if prob_b_given_a >= 0.3:
                conditional[a].append((b, prob_b_given_a))
            if prob_a_given_b >= 0.3:
                conditional[b].append((a, prob_a_given_b))

        for skill in conditional:
            conditional[skill].sort(key=lambda x: -x[1])

        self._cooccurrence_conditional = dict(conditional)

    def _load_skill_embeddings(self) -> dict[str, list[float]]:
        """Lazy-load skill embeddings cache."""
        if self._skill_embeddings is not None:
            return self._skill_embeddings

        if not _SKILL_EMBEDDINGS_PATH.exists():
            self._skill_embeddings = {}
            return self._skill_embeddings

        try:
            data = json.loads(_SKILL_EMBEDDINGS_PATH.read_text(encoding="utf-8"))
            self._skill_embeddings = data.get("skills", {})
        except Exception:
            self._skill_embeddings = {}

        return self._skill_embeddings

    # ------------------------------------------------------------------
    # compute_quality — deterministic profile quality scoring
    # ------------------------------------------------------------------

    @staticmethod
    def compute_quality(profile_data: dict) -> dict:
        """Deterministic quality scoring from profile data.

        Returns dict with ``completeness``, ``competitiveness``, and
        ``dimensions`` (soft-skill entries if present).
        """
        _QUALITY_LEVEL_WEIGHT = {
            "expert": 1.0, "advanced": 1.0,
            "proficient": 0.7, "intermediate": 0.7,
            "familiar": 0.3, "beginner": 0.1,
        }

        skills = profile_data.get("skills", [])
        knowledge_areas = profile_data.get("knowledge_areas", [])
        projects = profile_data.get("projects", [])
        has_education = bool(profile_data.get("education"))
        has_experience = profile_data.get("experience_years", 0) > 0

        # Completeness: are the sections filled?
        completeness = min(1.0, (
            (0.3 if skills else 0)
            + (0.2 if knowledge_areas else 0)
            + (0.2 if has_experience else 0)
            + (0.2 if has_education else 0)
            + (0.1 if projects else 0)
        ))

        # Competitiveness: weighted skill depth + breadth + experience
        skill_score = sum(
            _QUALITY_LEVEL_WEIGHT.get(s.get("level", "beginner"), 0.1)
            for s in skills
        )
        skill_component = min(0.4, skill_score * 0.04)
        breadth_component = min(0.2, len(knowledge_areas) * 0.03)
        project_component = min(0.15, len(projects) * 0.05)
        experience_component = min(
            0.15, profile_data.get("experience_years", 0) * 0.05
        )
        education_component = 0.1 if has_education else 0

        raw_competitiveness = (
            skill_component + breadth_component + project_component
            + experience_component + education_component
        )
        # Ensure minimum baseline for non-empty profiles, cap at 1.0
        competitiveness = min(1.0, max(raw_competitiveness, 0.05 if skills else 0))

        # Extract soft skill dimensions if present
        soft = profile_data.get("soft_skills", {})
        dimensions: list[dict] = []
        if soft.get("_version") == 2:
            dim_labels = {
                "communication": "沟通能力",
                "learning": "学习能力",
                "collaboration": "协作能力",
            }
        else:
            dim_labels = {
                "innovation": "创新能力",
                "learning": "学习能力",
                "resilience": "抗压能力",
                "communication": "沟通能力",
                "internship": "实习能力",
            }
        for key, label in dim_labels.items():
            val = soft.get(key)
            if isinstance(val, dict):
                score = val.get("score", 50)
            elif isinstance(val, (int, float)):
                score = val
            else:
                continue
            dimensions.append({"key": key, "label": label, "score": int(score)})

        return {
            "completeness": round(completeness, 2),
            "competitiveness": round(competitiveness, 2),
            "dimensions": dimensions,
        }

    # ------------------------------------------------------------------
    # locate_on_graph
    # ------------------------------------------------------------------

    def locate_on_graph(
        self,
        profile: dict,
        nodes: list[dict] | None = None,
    ) -> dict:
        """IDF-weighted positioning on career graph.

        Two-stage scoring:
          Stage 1 — Infer family prior from resume text
          Stage 2 — Multi-factor scoring + family prior multiplicative boost

        Returns:
            {node_id, label, score, family_confidence, candidates: top-5}
        """
        graph_nodes = self._graph._nodes
        user_title = profile.get("current_title", "")
        has_title = bool(user_title and user_title.strip())

        idf = _build_skill_idf(graph_nodes)

        # Build global skill vocab for description scanning
        graph_skill_vocab: set[str] = set()
        for node in graph_nodes.values():
            for s in node.get("must_skills", []):
                if s and s.strip() and len(s.strip()) >= 2:
                    graph_skill_vocab.add(s.strip().lower())

        user_skills = _skill_names_from_profile(profile, graph_skill_vocab)

        # Stage 1: Family prior
        family_task_vocab = _build_family_task_vocab(graph_nodes)
        family_prior = _infer_family_prior(profile, FAMILY_KEYWORDS, family_task_vocab)

        # Build candidate nodes list
        if nodes is not None:
            candidate_nodes = {
                n.get("node_id", ""): n for n in nodes if not n.get("is_milestone", False)
            }
        else:
            candidate_nodes = {
                nid: n for nid, n in graph_nodes.items() if not n.get("is_milestone", False)
            }

        # Stage 2: Multi-factor scoring
        scores: list[tuple[str, float]] = []

        for nid, node in candidate_nodes.items():
            node_skills = _node_skill_set(node)
            skill_score = _weighted_skill_match(user_skills, node_skills, idf)
            title_score = _title_bonus(user_title, node.get("label", ""))
            comp_score = _competency_match(profile, node)
            task_score = _task_match(profile, node)

            # Weight blend: with-title vs student/no-title
            if has_title:
                base = (
                    skill_score * 0.45
                    + task_score * 0.10
                    + title_score * 0.25
                    + comp_score * 0.20
                )
            else:
                base = skill_score * 0.55 + task_score * 0.20 + comp_score * 0.25

            # Family prior multiplicative boost (max +35%)
            node_family = node.get("role_family", "")
            family_conf = family_prior.get(node_family, 0.0)
            combined = base * (1.0 + 0.35 * family_conf)

            scores.append((nid, combined))

        scores.sort(key=lambda x: -x[1])

        if not scores:
            return {
                "node_id": None,
                "label": "",
                "score": 0.0,
                "family_confidence": 0.0,
                "candidates": [],
            }

        best_id, best_score = scores[0]
        best_node = candidate_nodes.get(best_id, {})
        best_family = best_node.get("role_family", "")
        best_family_conf = family_prior.get(best_family, 0.0)

        candidates = [
            {
                "node_id": nid,
                "label": candidate_nodes.get(nid, {}).get("label", nid),
                "score": round(s, 4),
            }
            for nid, s in scores[:5]
        ]

        return {
            "node_id": best_id,
            "label": best_node.get("label", best_id),
            "score": round(best_score, 4),
            "family_confidence": round(best_family_conf, 4),
            "candidates": candidates,
        }

    # ------------------------------------------------------------------
    # score_four_dimensions
    # ------------------------------------------------------------------

    def score_four_dimensions(
        self,
        profile: dict,
        target_node: dict,
        db_session: Any = None,
        sjt_scores: dict[str, float] | None = None,
    ) -> dict:
        """Four-dimension scoring.

        Builds on seven-dimension scoring, then aggregates:
          basic = edu(0.30) + cert(0.20) + exp(0.50)
          skills = coverage(0.40) + depth(0.35) + practice(0.25)
          qualities = 3 sub-dimensions (communication/learning/collaboration) weighted by soft_skill_weights
          potential = salary + skill_growth + promotion + outlook

        AHP stage weights: entry/mid/senior (from _STAGE_WEIGHTS)
        Basic score threshold penalty: if s_basic < 0.4, penalty = 0.7 + 0.3 * (s_basic / 0.4)

        Returns:
            {total_score, career_stage, four_dimensions: {basic, skills, qualities, potential}}
        """
        # Find matching direction in profiles.json
        profiles = self._load_profiles()
        node_id = target_node.get("node_id", "")

        # Try direct match, then label match, then mapping
        direction = profiles.get(node_id)
        if not direction:
            label = target_node.get("label", "")
            direction = profiles.get(label)
        if not direction:
            # Try reverse mapping
            for onet_id, graph_id in _DIRECTION_TO_GRAPH_NODE.items():
                if graph_id == node_id or graph_id == target_node.get("label", ""):
                    direction = profiles.get(onet_id)
                    if direction:
                        break

        # If no profiles data, create a minimal one from graph node
        if not direction:
            direction = self._direction_from_node(target_node)

        cross_idf = self._get_cross_direction_idf()
        user_skills = _user_skill_map(profile)
        user_certs = _user_cert_set(profile)
        user_comps = _user_competency_names(profile)
        weights = _compute_weights(direction)

        # Compute seven dimensions
        dim_results: dict[str, dict] = {}
        scorers = [
            ("skill_coverage", lambda: _score_skill_coverage(user_skills, direction, cross_idf)),
            ("skill_depth", lambda: _score_skill_depth(user_skills, direction)),
            ("experience", lambda: _score_experience(profile, direction)),
            ("education", lambda: _score_education(profile, direction)),
            ("practice", lambda: _score_practice(profile, direction)),
            ("certificates", lambda: _score_certificates(user_certs, direction)),
            ("competency", lambda: _score_competency(user_comps, direction, target_node)),
        ]

        for dim_name, scorer_fn in scorers:
            score, detail = scorer_fn()
            weight = weights[dim_name]
            dim_results[dim_name] = {
                "score": round(score * 100, 1),
                "weight": weight,
                "weighted_score": round(score * weight * 100, 1),
                "detail": detail,
            }

        # Infer career stage
        stage = _infer_career_stage(profile, dim_results)
        stage_weights = _STAGE_WEIGHTS[stage]

        # Compute 4 dimensions
        s_basic, sub_basic = _score_basic(dim_results)
        s_skills, sub_skills = _score_skills_agg(dim_results)
        s_qualities, sub_qualities = _score_qualities(profile, target_node, sjt_scores)

        role_family = target_node.get("role_family", "")
        s_potential, sub_potential = _score_potential(direction, role_family)

        # Basic threshold penalty
        if s_basic < 0.4:
            penalty = 0.7 + 0.3 * (s_basic / 0.4)
        else:
            penalty = 1.0

        # Weighted total
        total = penalty * (
            stage_weights["basic"] * s_basic
            + stage_weights["skills"] * s_skills
            + stage_weights["qualities"] * s_qualities
            + stage_weights["potential"] * s_potential
        )

        return {
            "total_score": round(total * 100, 1),
            "career_stage": stage,
            "stage_weights": stage_weights,
            "basic_penalty_applied": penalty < 1.0,
            "four_dimensions": {
                "basic": {
                    "score": round(s_basic * 100, 1),
                    "weight": stage_weights["basic"],
                    "sub": sub_basic,
                },
                "skills": {
                    "score": round(s_skills * 100, 1),
                    "weight": stage_weights["skills"],
                    "sub": sub_skills,
                },
                "qualities": {
                    "score": round(s_qualities * 100, 1),
                    "weight": stage_weights["qualities"],
                    "sub": sub_qualities,
                },
                "potential": {
                    "score": round(s_potential * 100, 1),
                    "weight": stage_weights["potential"],
                    "sub": sub_potential,
                },
            },
        }

    def _direction_from_node(self, node: dict) -> dict:
        """Build a minimal direction dict from graph node when no profiles.json match."""
        must_skills = node.get("must_skills", [])
        soft_list = _soft_skills_as_list(node.get("soft_skills", []))
        return {
            "jd_count": 1,
            "skill_type_groups": {
                "hard_skill": [
                    {"skill": s, "count": 1, "proficiency_dist": {}}
                    for s in must_skills
                ],
                "soft_skill": [
                    {"skill": s, "count": 1}
                    for s in soft_list
                ],
                "knowledge": [],
            },
            "experience": {"years": {"p25": None, "p50": None, "p75": None}},
            "education_dist": {},
            "certificates": node.get("certificates", []),
        }

    # ------------------------------------------------------------------
    # score_sjt
    # ------------------------------------------------------------------

    @staticmethod
    def _load_sjt_templates() -> list[dict]:
        """Load SJT scenario templates from data/sjt_templates.json."""
        path = _PROJECT_ROOT / "data" / "sjt_templates.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        return data["templates"]

    @staticmethod
    def generate_sjt_questions(profile_data: dict) -> list[dict]:
        """Fill SJT templates with personalized context based on user's resume.

        Returns list of questions with filled scenarios/options AND efficacy values
        (caller must strip efficacy before sending to client).
        """
        from backend.llm import llm_chat, parse_json_response, get_model

        templates = ProfileService._load_sjt_templates()

        # Build resume summary for LLM context
        skills = [s.get("name", "") for s in profile_data.get("skills", [])[:10]]
        projects = profile_data.get("projects", [])[:3]
        education = profile_data.get("education", {})
        experience_years = profile_data.get("experience_years", 0)

        resume_summary = (
            f"技能: {', '.join(skills)}\n"
            f"项目经验: {'; '.join(p if isinstance(p, str) else p.get('description', str(p)) for p in projects)}\n"
            f"教育: {education.get('degree', '')} {education.get('major', '')} {education.get('school', '')}\n"
            f"工作年限: {experience_years}"
        )

        # Build slot fill request
        slot_request = []
        for t in templates:
            slot_request.append({
                "id": t["id"],
                "dimension": t["dimension"],
                "fill_slots": t["fill_slots"],
                "scenario_hint": t["scenario_template"][:60] + "...",
            })

        prompt = f"""你是一个 SJT（情境判断测验）情境个性化助手。

用户简历摘要：
{resume_summary}

请根据用户的行业背景和经历，为以下 {len(templates)} 道情境题的占位符填充具体内容。
填充要求：
- 内容必须贴合用户的行业/技术栈/项目经验
- 每个 slot 填 2-8 个字的短语
- 不要改变题目结构，只填空

请返回严格 JSON，格式为：
{{{{
  "fills": [
    {{{{"id": "t01", "slots": {{{{"stakeholder": "产品总监", "project_type": "电商推荐系统", ...}}}}}}}},
    ...
  ]
}}}}

需要填充的模板：
{json.dumps(slot_request, ensure_ascii=False, indent=2)}

只返回 JSON，不要有任何其他文字。"""

        result = llm_chat(
            [{"role": "user", "content": prompt}],
            model=get_model("default"),
            temperature=0.7,
            timeout=90,
        )
        fills_data = parse_json_response(result)
        fills_map = {f["id"]: f.get("slots", {}) for f in fills_data.get("fills", [])}
        if not fills_map:
            raise ValueError("LLM returned empty fills")

        # Apply fills to templates
        questions = []
        for t in templates:
            slots = fills_map.get(t["id"], {})
            # Fill scenario
            scenario = t["scenario_template"]
            for slot_name, slot_value in slots.items():
                scenario = scenario.replace("{" + slot_name + "}", str(slot_value))
            # Fill options
            options = []
            for o in t["options"]:
                text = o.get("text_template", o.get("text", ""))
                for slot_name, slot_value in slots.items():
                    text = text.replace("{" + slot_name + "}", str(slot_value))
                options.append({
                    "id": o["id"],
                    "text": text,
                    "efficacy": o["efficacy"],
                })
            questions.append({
                "id": t["id"],
                "dimension": t["dimension"],
                "scenario": scenario,
                "options": options,
            })

        return questions

    _LEVEL_MAP = [
        (80, "优秀"),
        (60, "良好"),
        (40, "基础"),
        (0, "待发展"),
    ]

    @staticmethod
    def score_to_level(score: float) -> str:
        """Map 0-100 score to 4-tier level."""
        for threshold, level in ProfileService._LEVEL_MAP:
            if score >= threshold:
                return level
        return "待发展"

    @staticmethod
    def score_sjt_v2(answers: list[dict], questions: list[dict]) -> dict:
        """Score SJT v2 answers using session questions (with efficacy).

        Args:
            answers: [{"question_id": "t01", "best": "b", "worst": "c"}, ...]
            questions: Full question list from SjtSession (with efficacy)

        Returns:
            {"dimensions": {"communication": {"score": 72, "level": "良好"}, ...}}
        """
        q_map = {q["id"]: q for q in questions}
        dim_scores: dict[str, list[float]] = {}

        for ans in answers:
            q = q_map.get(ans.get("question_id", ""))
            if not q:
                continue
            options = {o["id"]: o["efficacy"] for o in q["options"]}
            best_eff = options.get(ans.get("best", ""), 2)
            worst_eff = options.get(ans.get("worst", ""), 3)
            raw = best_eff + (4 - worst_eff)
            # Corrected normalization: actual range is 2-7
            normalized = max(0, min(100, round((raw - 2) / 5 * 100)))
            dim_scores.setdefault(q["dimension"], []).append(normalized)

        dimensions = {}
        for dim, vals in dim_scores.items():
            avg = round(sum(vals) / len(vals))
            dimensions[dim] = {
                "score": avg,
                "level": ProfileService.score_to_level(avg),
            }

        return {"dimensions": dimensions}

    @staticmethod
    def generate_sjt_advice(
        dimensions: dict,
        answers: list[dict],
        questions: list[dict],
        profile_data: dict,
    ) -> dict[str, str]:
        """Generate per-dimension improvement advice based on answer patterns.

        Returns: {"communication": "advice text", "learning": "...", ...}
        """
        from backend.llm import llm_chat, parse_json_response, get_model

        # Build answer summary for LLM
        q_map = {q["id"]: q for q in questions}
        answer_details = []
        for ans in answers:
            q = q_map.get(ans.get("question_id", ""))
            if not q:
                continue
            opts = {o["id"]: o for o in q["options"]}
            best_opt = opts.get(ans.get("best", ""))
            worst_opt = opts.get(ans.get("worst", ""))
            answer_details.append({
                "dimension": q["dimension"],
                "scenario": q["scenario"][:80],
                "best_choice": best_opt["text"] if best_opt else "",
                "best_efficacy": best_opt["efficacy"] if best_opt else 0,
                "worst_choice": worst_opt["text"] if worst_opt else "",
                "worst_efficacy": worst_opt["efficacy"] if worst_opt else 0,
            })

        dim_summary = ", ".join(
            f"{dim}: {info['score']}分({info['level']})"
            for dim, info in dimensions.items()
        )

        skills = [s.get("name", "") for s in profile_data.get("skills", [])[:5]]

        prompt = f"""你是一个职业发展顾问。用户刚完成了一次软技能情境评估。

评估结果：{dim_summary}
用户技能背景：{', '.join(skills)}

作答详情：
{json.dumps(answer_details, ensure_ascii=False, indent=2)}

请为每个维度生成 50-100 字的改进建议。要求：
- 正向语气，指出具体行为模式（"你倾向于…"）
- 给出可操作建议（"可以尝试…"）
- 不要重复题目内容，总结行为模式
- 即使是"优秀"等级也给出进一步提升的方向

返回严格 JSON，包含所有评估过的维度：
{{{", ".join(f'"{dim}": "建议文字"' for dim in dimensions)}}}

只返回 JSON，不要有任何其他文字。"""

        try:
            result = llm_chat(
                [{"role": "user", "content": prompt}],
                model=get_model("default"),
                temperature=0.7,
                timeout=30,
            )
            advice = parse_json_response(result)
            if isinstance(advice, dict):
                return {k: str(v) for k, v in advice.items() if k in dimensions}
        except Exception:
            pass
        return {}

    # ------------------------------------------------------------------
    # infer_skills_cooccurrence
    # ------------------------------------------------------------------

    def infer_skills_cooccurrence(
        self,
        skills: list[str],
        min_cooccurrence: float = 0.6,
        min_similarity: float = 0.85,
        max_inferred: int = 10,
    ) -> list[str]:
        """Co-occurrence based skill inference.

        Dual-filter: co-occurrence >= 0.6 AND embedding cosine >= 0.85
        Fallback: pure co-occurrence >= 0.80 when no embeddings

        Returns list of inferred skill names.
        """
        if not skills:
            return []

        self._load_cooccurrence()
        embeddings = self._load_skill_embeddings()
        use_embeddings = len(embeddings) > 0

        fallback_min_prob = 0.8 if not use_embeddings else min_cooccurrence

        user_lower = {s.lower() for s in skills if s}
        # name → (confidence, source, similarity)
        inferred: dict[str, tuple[float, str, float]] = {}

        for skill in skills:
            related = [
                (s, p)
                for s, p in self._cooccurrence_conditional.get(skill, [])
                if p >= fallback_min_prob
            ]
            for related_skill, prob in related:
                if related_skill.lower() in user_lower:
                    continue

                if use_embeddings:
                    vec_a = embeddings.get(skill)
                    vec_b = embeddings.get(related_skill)
                    if vec_a is not None and vec_b is not None:
                        sim = max(0.0, _cosine_similarity(vec_a, vec_b))
                        if prob < min_cooccurrence or sim < min_similarity:
                            continue
                    else:
                        # No embedding for one of them, use pure cooccurrence with higher threshold
                        if prob < 0.8:
                            continue
                        sim = 0.0
                else:
                    sim = 0.0

                if related_skill not in inferred or prob > inferred[related_skill][0]:
                    inferred[related_skill] = (prob, skill, sim)

        # Sort by confidence descending, return just names
        result = sorted(inferred.keys(), key=lambda n: -inferred[n][0])
        return result[:max_inferred]

