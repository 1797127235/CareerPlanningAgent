# -*- coding: utf-8 -*-
"""Narrative generation and profile diagnosis for career reports."""
from __future__ import annotations

import json
import logging
import re as _re_diag
from typing import Any

logger = logging.getLogger(__name__)


_NARRATIVE_SYSTEM = """你是一位兼具数据敏感度和教练视角的职业规划顾问，正在为一名IT学生撰写职业发展报告的核心评估段落。
要求：
- 语言亲切专业，直接称呼"你"，200-300字
- 结合具体数据说话（技能匹配、分数、差距）
- 指出最大亮点和最需改进的1-2个方向
- 适当体现"职业阶段感"：如果是初级方向强调基础与完整度，如果是中高级方向强调系统深度与可量化影响
- 如果项目描述缺少"动词+动作+数字"的 impact-first 结构，要把它作为简历层面的关键观察点提出来
- 结尾给出一句鼓励性总结，并传递一种温和的"计划性偶发"（Planned Happenstance）态度：职业路径往往是非线性的，保持好奇心和小步尝试比追求完美规划更重要
- 直接输出段落文字，不要标题或标签"""


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
) -> str:
    """Call LLM to generate personalized 200-300 char narrative using real student data."""
    try:
        from backend.llm import get_llm_client, get_model

        dim_labels = {"foundation": "基础要求", "skills": "职业技能",
                      "qualities": "职业素养", "potential": "发展潜力"}
        dim_text = []
        for k, label in dim_labels.items():
            v = four_dim.get(k)
            dim_text.append(f"- {label}: {v if v is not None else '暂无（需完成模拟面试）'}")

        # Education context
        edu_text = ""
        if education and isinstance(education, dict):
            school = education.get("school", "")
            major = education.get("major", "")
            if school or major:
                edu_text = f"学生背景：{school + ' ' if school else ''}{major + '专业' if major else ''}"

        # Projects context（含描述，让 LLM 能基于真实项目推理而不是空谈）
        proj_text = ""
        if projects:
            proj_lines = []
            for p in projects[:4]:
                name = getattr(p, "name", "") or "未命名"
                desc = getattr(p, "description", "") or getattr(p, "_desc", "") or ""
                status = getattr(p, "status", "")
                status_tag = "[已完成]" if status == "completed" else "[进行中]" if status == "in_progress" else ""
                if desc:
                    proj_lines.append(f"{status_tag}{name}：{desc[:180]}")
                else:
                    proj_lines.append(f"{status_tag}{name}")
            proj_text = "\n".join(proj_lines)

        # Claimed-but-unverified skills (risk signal)
        # 注：经 6b embedding + 6c LLM 隐式推断之后仍未匹配到项目的，才算真 claimed
        claimed_text = ""
        if claimed_skills:
            claimed_text = (
                f"简历声称但无项目可对应的技能：{', '.join(claimed_skills[:3])}。"
                "⚠️ 仅当该技能确实无法从现有项目推理出使用场景时，才当作面试风险点；"
                "如果学生的项目隐式使用了这些技能（例如 C++ 后端项目必然用 STL），不要当成风险。"
            )

        # Application status
        apply_text = ""
        if applications:
            total = len(applications)
            active = [a for a in applications if getattr(a, "status", "") in ("applied", "screening", "scheduled", "interviewed")]
            apply_text = f"已投递 {total} 家公司，{len(active)} 个进行中"

        market_text = ""
        if market_info:
            market_text = (
                f"市场：该方向需求变化 {market_info.get('demand_change_pct', 0):+.0f}%，"
                f"入场时机{market_info.get('timing_label', '良好')}"
            )

        gap_text = "、".join(gap_skills[:4]) if gap_skills else "暂无明显差距"

        context_parts = [p for p in [edu_text, proj_text, claimed_text, apply_text] if p]
        context_block = "\n".join(context_parts) if context_parts else ""

        # Resume impact-first observation
        resume_impact_text = ""
        if projects:
            has_metrics = any(
                any(d in (getattr(p, "description", "") + getattr(p, "_desc", "")).lower() for d in ["qps", "latency", "用户", "日活", "准确率", "提升", "%", "倍", "ms", "tps"])
                for p in projects[:4]
            )
            if not has_metrics:
                resume_impact_text = "注意：该学生项目描述中缺少可量化的结果数字（如 QPS、用户数、准确率等），这意味着简历可能还停留在'做了什么'而不是'做成了什么'的层面。"

        prompt = f"""为以下学生撰写职业发展报告的综合评价段落（200-300字）：

目标岗位：{target_label}
综合匹配分：{match_score}/100
近期成长趋势：{growth_delta:+.1f}分

四维评分：
{chr(10).join(dim_text)}

核心技能差距：{gap_text}
{market_text}

【学生真实档案】
{context_block if context_block else '（学生尚未完善档案）'}
{resume_impact_text}

要求：
- 语言亲切专业，直接称呼"你"
- **不要罗列分数**（例如"职业技能维度得分 47，发展潜力 50"这类 X 分 Y 分的堆砌）。分数已经在页面其他地方展示，你的文字要讲**故事**，不要复读数据
- 必须引用学生项目里的具体细节（项目名 + 做法或数字）作为推理依据，**严禁泛泛而谈**
- 点名最大优势和最需改进的 1-2 个方向时，每条结论都要能回指上面的项目或数字
- 对"简历声称但无项目可对应的技能"要先判断：该技能是否已经**隐式用在学生现有项目里**？
  • 如果是（例如做 C++ 网络库必然用到 STL+Linux socket），**不要**列为面试风险
  • 只有确实找不到任何项目能证明的技能，才能提风险
- 如果项目缺少量化数字，要把"缺少 impact-first 叙事"当作一个独立的简历观察点提出来
- 严禁输出"建议聚焦实战项目填补技能缺口"、"保持当前成长势头"、"持续积累实战项目经验"、"相信你一定行"这类万能套话
- 结尾一句鼓励，要具体（例如"把下一个 demo 的 QPS 数据写进档案就能封堵这个缺口"这种），并传递职业路径可以是非线性的、小步尝试同样有价值的温和态度
- 直接输出段落，不要标题"""

        # 带重试：首次 60s 超时，失败再试一次 90s；max_tokens 收敛到 400 降低耗时
        client = get_llm_client(timeout=60)
        last_err: Exception | None = None
        for attempt in range(2):
            try:
                resp = client.chat.completions.create(
                    model=get_model("fast"),
                    messages=[
                        {"role": "system", "content": _NARRATIVE_SYSTEM},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.5,
                    max_tokens=400,
                )
                return resp.choices[0].message.content.strip()
            except Exception as inner:
                last_err = inner
                logger.warning("Narrative attempt %d failed: %s", attempt + 1, inner)
                if attempt == 0:
                    # 第二次用更长超时 + 更短 max_tokens
                    client = get_llm_client(timeout=90)
        if last_err:
            raise last_err

    except Exception as e:
        # 重试两次都失败——诚实告知，不伪装 AI 输出
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
        try:
            from backend.llm import get_llm_client, get_model

            items_text = "\n".join(
                f"- 项目「{it['name']}」: {it['text'][:100]}\n  问题: {', '.join(it['issues'])}"
                for it in needs_fix
            )

            prompt = f"""你是简历优化专家。学生目标岗位是「{node_label}」。

以下项目/经历存在描述问题，请为每个项目输出：
1. highlight: 一句话总结亮点（肯定学生做了什么）
2. suggestion: 具体建议补充的文字（包含具体数字占位符如 XX，让学生填入真实数据）

{items_text}

输出 JSON 数组，每项包含 name、highlight、suggestion。只输出 JSON。"""

            resp = get_llm_client(timeout=20).chat.completions.create(
                model=get_model("fast"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=800,
            )
            raw = resp.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            parsed = json.loads(raw.strip())
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and item.get("name"):
                        suggestions[item["name"]] = {
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
