# -*- coding: utf-8 -*-
"""Narrative generation and profile diagnosis for career reports."""
from __future__ import annotations

import json
import logging
import re as _re_diag
from typing import Any

logger = logging.getLogger(__name__)


_HOLLOW_PATTERNS = [
    {
        "id": "no_numbers",
        "detect": lambda text: not _re_diag.search(r'\d', text),
        "label": "缺少量化数据",
    },
    {
        "id": "no_result",
        "detect": lambda text: not any(w in text for w in [
            '提升', '降低', '优化', '减少', '增加', '支撑', '处理',
            '完成', 'QPS', 'TPS', '延迟', '吞吐', '并发', '覆盖率',
            'improve', 'reduce', 'increase', 'optimize',
        ]),
        "label": "缺少成果描述",
    },
    {
        "id": "too_short",
        "detect": lambda text: len(text.strip()) < 30,
        "label": "描述过于简短",
    },
    {
        "id": "vague_participation",
        "detect": lambda text: '参与' in text and '负责' not in text and '实现' not in text and '开发' not in text,
        "label": "只说参与未说明职责",
    },
]


def _generate_narrative(
    target_label: str,
    match_score: int,
    four_dim: dict,
    gap_skills: list[str],
    market_info: dict | None,
    growth_delta: float,
    # Rich context for personalization
    education: dict | None = None,
    projects: list | None = None,
    claimed_skills: list[str] | None = None,
    applications: list | None = None,
    delta: dict | None = None,
) -> str:
    """Call LLM to generate personalized narrative using real student data."""
    try:
        from backend.skills import invoke_skill

        text = invoke_skill(
            "narrative",
            target_label=target_label,
            claimed_skills=", ".join(s for s in (claimed_skills or []) if s),
            projects_list="\n".join(_format_projects_for_prompt(projects or [])),
            education_line=_format_education(education),
            delta_line=_format_delta_line(delta),
            market_line=_format_market(market_info),
        )
        return text.strip()
    except Exception as e:
        logger.error("Narrative generation FAILED after retries: %s", e, exc_info=True)
        err_type = type(e).__name__
        err_msg = str(e)[:180] if str(e) else err_type
        return (
            f"⚠️ AI 综合评价暂时生成失败（{err_type}）。"
            f"这通常是大模型调用超时、配额或网络问题造成的——报告其他部分不受影响，"
            f"可稍后点击右上角「AI 润色」按钮重试综合评价。"
            f"\n\n[诊断信息：{err_msg}]"
        )


def _diagnose_profile(
    profile_data: dict,
    projects: list,
    node_label: str,
) -> list[dict]:
    """
    Scan profile projects/experience for hollow statements.
    Returns list of diagnosis items, each with:
      - source: project name or "简历"
      - status: "pass" | "needs_improvement"
      - highlight: what's good (亮点)
      - issues: list of detected problems
      - suggestion: specific text to add (from LLM)
    """
    # Collect all describable items: resume projects + growth log projects
    items_to_check: list[dict] = []

    # Smart project-name extraction (same logic as generate_report's _short_proj_name)
    def _smart_name(desc: str) -> str:
        before_punct = _re_diag.split(r'[，。,.、；]', desc)[0].strip()
        m = _re_diag.search(r'实现(?:了|的)?\s*(.{4,20}？)$', before_punct)
        if m:
            candidate = m.group(1).strip()
            candidate = _re_diag.sub(r'^[的了地一个款]{1,3}', '', candidate).strip()
            if len(candidate) >= 4:
                return candidate
        m2 = _re_diag.search(r'的\s*((?:[A-Za-z+#]+\s*)?[\u4e00-\u9fff]{2,}[\u4e00-\u9fff\w+# ]*)$', before_punct)
        if m2:
            candidate = m2.group(1).strip()
            if 4 <= len(candidate) <= 20:
                return candidate
        raw = before_punct[:30].strip() if len(before_punct) > 30 else before_punct
        return _re_diag.sub(r'^[的了地是]{1,2}\s*', '', raw).strip()

    # Resume-extracted projects
    raw_projects = profile_data.get("projects", [])
    for i, p in enumerate(raw_projects):
        if isinstance(p, str) and p.strip():
            items_to_check.append({"name": _smart_name(p), "text": p, "source_type": "resume", "source_id": i})
        elif isinstance(p, dict):
            name = p.get("name", "")
            desc = p.get("description", "") or name
            if desc:
                items_to_check.append({"name": name or _smart_name(desc), "text": desc, "source_type": "resume", "source_id": i})

    # Growth log projects
    for p in (projects or []):
        desc = getattr(p, "description", "") or ""
        name = getattr(p, "name", "") or ""
        text = desc if desc else name
        if text and not any(i["text"] == text for i in items_to_check):
            items_to_check.append({"name": name or _smart_name(text), "text": text, "source_type": "growth_log", "source_id": getattr(p, "id", 0)})

    if not items_to_check:
        return []

    # Step 1: Rule-based detection
    needs_fix: list[dict] = []
    passed: list[dict] = []

    for item in items_to_check:
        text = item["text"]
        issues = [p["label"] for p in _HOLLOW_PATTERNS if p["detect"](text)]
        if issues:
            needs_fix.append({**item, "issues": issues})
        else:
            passed.append(item)

    # Step 2: LLM generates specific suggestions for items with issues
    suggestions: dict[str, dict] = {}  # name -> {highlight, suggestion}
    if needs_fix:
        projects_for_llm = []
        for it in needs_fix:
            projects_for_llm.append({
                "name": it["name"],
                "text": it["text"],
                "source_type": it["source_type"],
                "source_id": it["source_id"],
                "issues": it["issues"],
            })

        try:
            from backend.skills import invoke_skill
            parsed = invoke_skill(
                "diagnosis",
                target_label=node_label,
                projects_json=json.dumps(projects_for_llm, ensure_ascii=False),
            )
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict):
                        key = item.get("source") or item.get("name")
                        if key:
                            suggestions[key] = {
                                "highlight": item.get("highlight", ""),
                                "suggestion": item.get("suggestion", ""),
                            }
        except Exception as e:
            logger.warning("Profile diagnosis LLM failed: %s", e)

    # Step 3: Assemble results
    results: list[dict] = []

    for item in needs_fix:
        s = suggestions.get(item["name"], {})
        results.append({
            "source": item["name"],
            "source_type": item["source_type"],
            "source_id": item["source_id"],
            "current_text": item["text"],
            "status": "needs_improvement",
            "highlight": s.get("highlight", ""),
            "issues": item["issues"],
            "suggestion": s.get("suggestion", ""),
        })

    for item in passed:
        results.append({
            "source": item["name"],
            "source_type": item["source_type"],
            "source_id": item["source_id"],
            "current_text": item["text"],
            "status": "pass",
            "highlight": "",
            "issues": [],
            "suggestion": "",
        })

    return results


def _format_projects_for_prompt(projects: list) -> list[str]:
    lines = []
    for p in projects[:4]:
        name = getattr(p, "name", "") or "未命名"
        desc = getattr(p, "description", "") or getattr(p, "_desc", "") or ""
        status = getattr(p, "status", "")
        status_tag = "[已完成]" if status == "completed" else "[进行中]" if status == "in_progress" else ""
        if desc:
            lines.append(f"- {status_tag}{name}：{desc[:180]}")
        else:
            lines.append(f"- {status_tag}{name}")
    return lines


def _format_education(education: dict | None) -> str:
    if not education or not isinstance(education, dict):
        return ""
    school = education.get("school", "")
    major = education.get("major", "")
    if school or major:
        return f"{school + ' ' if school else ''}{major + '专业' if major else ''}"
    return ""


def _format_delta_line(delta: dict | None) -> str:
    if not delta:
        return ""
    from datetime import datetime, timezone
    prev_date = delta.get("prev_date", "")
    gained = delta.get("gained_skills", [])
    days = 0
    if prev_date:
        try:
            prev_dt = datetime.fromisoformat(prev_date)
            days = (datetime.now(timezone.utc) - prev_dt).days
        except Exception:
            pass
    parts = []
    if days > 0:
        parts.append(f"距上次报告 {days} 天")
    if gained:
        parts.append(f"期间多掌握了 {', '.join(gained)}")
    if parts:
        return "，".join(parts) + "。"
    return ""


def _format_market(market_info: dict | None) -> str:
    if not market_info:
        return ""
    parts = []
    salary = market_info.get("salary_p50")
    if salary:
        parts.append(f"薪资 p50 ¥{salary}k")
    timing = market_info.get("timing_label", "")
    if timing:
        parts.append(f"入场时机{timing}")
    demand = market_info.get("demand_change_pct")
    if demand is not None:
        parts.append(f"需求变化 {demand:+.0f}%")
    if parts:
        return "；".join(parts) + "。"
    return ""
