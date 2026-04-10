# -*- coding: utf-8 -*-
"""
Mock interview module — three-stage design inspired by FoloUp.

Stage 1: generate_questions()  — LLM generates structured interview questions from JD + user gaps
Stage 2: (handled by chat.py)  — interviewer agent asks pre-generated questions
Stage 3: analyze_interview()   — LLM deeply analyzes the full transcript post-interview
"""
from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from backend.llm import get_llm_client, parse_json_response


# ── Stage 1: Question Generation ─────────────────────────────────

_QUESTION_GEN_SYSTEM = "你是一位资深技术面试官，擅长根据岗位要求设计有针对性的面试题目。"

_QUESTION_GEN_USER = """\
根据以下岗位信息和候选人情况，生成 {count} 道面试题。

【岗位信息】
目标岗位: {target_job}
JD 文本摘要:
{jd_text}

【候选人已匹配技能】
{matched_skills}

【候选人缺失技能（薄弱环节）】
{missing_skills}

【候选人档案摘要】
{profile_summary}

【出题要求】
1. 题目类型分配（按比例，不足则灵活调整）：
   - 基础技术题（约40%）：围绕岗位核心技能，由浅入深
   - 项目经验题（约20%）：如果候选人有相关项目，追问项目细节和技术决策
   - 场景设计题（约20%）：给出实际工作场景，考察分析和设计能力
   - 薄弱环节题（约20%）：围绕缺失技能出题，但以引导式提问为主，不刁难
2. 每道题 30 字以内，简洁精准，像真实面试官提问的风格
3. 每道题标注考察的核心技能点
4. 题目难度递进：前面的题简单，后面逐渐加深

【强制要求 — 违反则重新生成】
1. 至少 3 道题的考察点必须来自 JD 文本中明确出现的技术/框架/工具名称
2. 禁止出通用计算机基础题（链表、排序、操作系统原理等），除非 JD 明确提到算法
3. 项目经验题必须基于候选人档案中列出的真实项目，不可虚构项目名
4. 薄弱探测题：major缺口（严重缺失）出 easy 引导题，minor缺口（有差距）出 medium 题

严格输出 JSON，格式如下：
{{
  "questions": [
    {{
      "round": 1,
      "type": "基础技术",
      "question": "题目文本",
      "focus_skill": "考察的技能",
      "difficulty": "easy",
      "answer_key": "参考答案要点（30字以内）"
    }}
  ]
}}

difficulty 取值: easy / medium / hard
type 取值: 基础技术 / 项目经验 / 场景设计 / 薄弱探测"""


def generate_questions(
    jd_context: dict[str, Any],
    profile: dict[str, Any] | None = None,
    count: int = 5,
) -> list[dict[str, Any]]:
    """Stage 1 — Generate structured interview questions from JD + user gaps.

    Returns a list of question dicts with keys:
    round, type, question, focus_skill, difficulty
    """
    target_job = jd_context.get("target_job", "未知岗位")
    jd_text = (jd_context.get("jd_text", "") or "")[:2500]

    matched = jd_context.get("matched_skills", [])
    matched_str = "、".join(matched[:10]) if matched else "暂无"

    missing = jd_context.get("missing_skills", [])
    _level_map = {"major": "严重缺失", "minor": "有差距", "nice_to_have": "加分项"}
    missing_names = []
    for m in missing[:8]:
        if isinstance(m, dict):
            line = m.get("skill", str(m))
            if m.get("gap_level"):
                line += f"（{_level_map.get(m['gap_level'], '')}）"
            missing_names.append(line)
        else:
            missing_names.append(str(m))
    missing_str = "、".join(missing_names) if missing_names else "暂无"

    # Build profile summary
    profile_parts = []
    if profile:
        basic = profile.get("basic_info", {})
        if basic.get("major"):
            profile_parts.append(f"专业: {basic['major']}")
        skills = profile.get("skills", [])
        if skills:
            top = [s.get("name", "") if isinstance(s, dict) else str(s) for s in skills[:8]]
            profile_parts.append(f"技能: {'、'.join(top)}")
        projects = profile.get("projects", [])
        if projects:
            names = [
                (p.get("name", "") if isinstance(p, dict) else str(p))
                for p in projects[:3]
                if (p.get("name") if isinstance(p, dict) else p)
            ]
            if names:
                profile_parts.append(f"项目: {'、'.join(names)}")
    profile_summary = "\n".join(profile_parts) if profile_parts else "暂无档案信息"

    prompt = _QUESTION_GEN_USER.format(
        count=count,
        target_job=target_job,
        jd_text=jd_text or "（未提供JD文本）",
        matched_skills=matched_str,
        missing_skills=missing_str,
        profile_summary=profile_summary,
    )

    model = os.getenv("INTERVIEW_GEN_MODEL") or os.getenv("LLM_MODEL") or "qwen-plus"
    client = get_llm_client(timeout=120)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _QUESTION_GEN_SYSTEM},
            {"role": "user", "content": prompt},
        ],
    )

    raw = resp.choices[0].message.content or ""
    parsed = parse_json_response(raw)
    questions = parsed.get("questions", []) if isinstance(parsed, dict) else []

    # Ensure round numbers
    for i, q in enumerate(questions):
        q.setdefault("round", i + 1)
        q.setdefault("type", "基础技术")
        q.setdefault("difficulty", "medium")

    return questions


async def generate_questions_async(
    jd_context: dict[str, Any],
    profile: dict[str, Any] | None = None,
    count: int = 5,
) -> list[dict[str, Any]]:
    """Async wrapper — avoids blocking the FastAPI event loop."""
    return await asyncio.to_thread(generate_questions, jd_context, profile, count)


# ── Stage 3: Post-Interview Analysis ─────────────────────────────

_ANALYZE_SYSTEM = "你是一位资深面试评估专家，擅长从面试对话中提取深层洞察，给出结构化、有建设性的反馈。"

_ANALYZE_USER = """\
请分析以下模拟面试的完整对话记录，给出结构化评估。

【面试岗位】
{target_job}

【预设面试题目】
{questions_text}

【完整对话记录】
{transcript}

【面试官内部笔记】
{interviewer_notes}
（以上是面试官在对话中记录的内部观察，包含候选人的错误陈述、技术误解、明显遗漏和回答含糊处。评估时请参考这些笔记，基于笔记中的具体证据作出判断，不要凭空推断。）

【评估要求】
请从以下维度评分和分析：

1. 总分（0-100）和总体反馈（80字以内）
   评分时综合考虑以下因素：
   - 技术知识深度和准确性
   - 回答的条理性和结构（是否用 STAR 等框架）
   - 结合自身经历举例的能力
   - 面对不熟悉问题时的应变
   - 表达的自信度和流畅度
   - 回答与问题的相关性

2. 分维度评分（每个维度 0-100 + 20字反馈）：
   - technical_depth: 技术深度
   - expression: 表达清晰度
   - project_experience: 项目经验展示
   - adaptability: 应变能力
   - answer_structure: 回答结构性（STAR法则等）
   - example_ability: 举例说明能力

3. 每道题的回答摘要：
   - 如果某题没问到，summary 写 "未提问"
   - 如果问了但候选人没答上来，summary 写 "未作答"
   - 正常回答则写候选人的核心观点摘要（40字以内）

4. 引言反馈（从对话中提取候选人原话）：
   - 2-3 条回答亮点（标记为 strength）
   - 2-3 条可改进之处（标记为 improvement，附改进建议）

5. 技能差距映射：基于面试表现，列出候选人最需要提升的 2-3 个具体技能点

严格输出 JSON：
{{
  "overall_score": 72,
  "overall_feedback": "总体反馈文本",
  "dimensions": [
    {{ "key": "technical_depth", "label": "技术深度", "score": 70, "feedback": "..." }},
    {{ "key": "expression", "label": "表达清晰度", "score": 65, "feedback": "..." }},
    {{ "key": "project_experience", "label": "项目经验", "score": 75, "feedback": "..." }},
    {{ "key": "adaptability", "label": "应变能力", "score": 60, "feedback": "..." }},
    {{ "key": "answer_structure", "label": "回答结构性", "score": 55, "feedback": "..." }},
    {{ "key": "example_ability", "label": "举例能力", "score": 68, "feedback": "..." }}
  ],
  "question_summaries": [
    {{ "round": 1, "question": "原题", "summary": "回答摘要" }}
  ],
  "supporting_quotes": [
    {{ "quote": "候选人原话", "analysis": "分析", "type": "strength" }},
    {{ "quote": "候选人原话", "analysis": "这里可以改进...", "type": "improvement", "suggestion": "改进建议" }}
  ],
  "skill_gaps": ["技能1", "技能2"]
}}"""


def analyze_interview(
    messages: list[dict[str, str]],
    questions: list[dict[str, Any]],
    jd_context: dict[str, Any],
) -> dict[str, Any]:
    """Stage 3 — Post-interview deep analysis of the full transcript.

    Args:
        messages: Full conversation [{role, content}, ...]
        questions: Pre-generated questions from Stage 1
        jd_context: JD context with target_job etc.

    Returns structured analysis dict.
    """
    target_job = jd_context.get("target_job", "未知岗位")

    # Format questions
    q_lines = []
    for q in questions:
        r = q.get("round", "?")
        qtype = q.get("type", "")
        text = q.get("question", "")
        skill = q.get("focus_skill", "")
        q_lines.append(f"第{r}题 [{qtype}] {text}（考察: {skill}）")
    questions_text = "\n".join(q_lines) if q_lines else "（无预设题目）"

    # Format transcript
    transcript_lines = []
    for msg in messages:
        role = "面试官" if msg.get("role") == "assistant" else "候选人"
        content = msg.get("content", "").strip()
        if content:
            transcript_lines.append(f"{role}: {content}")
    transcript = "\n\n".join(transcript_lines)

    notes_list = jd_context.get("interviewer_notes", [])
    interviewer_notes = "\n---\n".join(n for n in notes_list if n and n.strip()) or "（无笔记）"

    prompt = _ANALYZE_USER.format(
        target_job=target_job,
        questions_text=questions_text,
        transcript=transcript,
        interviewer_notes=interviewer_notes,
    )

    model = os.getenv("CHAT_LLM_MODEL") or os.getenv("LLM_MODEL") or "qwen3.5-flash"
    client = get_llm_client(timeout=60)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _ANALYZE_SYSTEM},
            {"role": "user", "content": prompt},
        ],
    )

    raw = resp.choices[0].message.content or ""
    result = parse_json_response(raw)

    # Ensure required fields exist
    if isinstance(result, dict):
        result.setdefault("overall_score", 0)
        result.setdefault("overall_feedback", "")
        result.setdefault("dimensions", [])
        result.setdefault("question_summaries", [])
        result.setdefault("supporting_quotes", [])
        result.setdefault("skill_gaps", [])

    return result


async def analyze_interview_async(
    messages: list[dict[str, str]],
    questions: list[dict[str, Any]],
    jd_context: dict[str, Any],
) -> dict[str, Any]:
    """Async wrapper — avoids blocking the FastAPI event loop."""
    return await asyncio.to_thread(analyze_interview, messages, questions, jd_context)
