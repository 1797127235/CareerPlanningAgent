# -*- coding: utf-8 -*-
"""
面试复盘分析模块 — 单题 Q+A 深度评估。

analyze_single_qa() — 分析单道面试题的回答质量
"""
from __future__ import annotations

import logging
import os
from typing import Any

from backend.llm import get_llm_client, parse_json_response

logger = logging.getLogger(__name__)

_SYSTEM = (
    "你是一位资深技术面试评估专家。评价风格：直接、具体、有建设性，不用官腔。\n"
    "亮点和不足均基于回答的实际内容——若回答严重不足，可跳过亮点，直接给出改进建议。\n"
    "评分必须使用完整区间：优秀 70+，普通 50-70，较差 30-50，严重不足 30 以下。"
)

_USER = """\
请分析以下面试题的回答质量。

【目标岗位】
{target_job}

【面试题】
{question}

【候选人回答】
{answer}

【候选人背景】
{profile_summary}

【评估要求】
1. 找出回答中的亮点（如有实质亮点才列举，无明显亮点可留空数组）
2. 找出回答中的不足（至少1条），每条附具体改进建议
3. 给出整体反馈（2-3句话，口语化，直接指出问题）
4. 给出评分（0-100，必须诚实使用完整区间，不得集中在60-80）
5. 按以下维度分别打分（每个维度 0-100 分，附 1-2 句点评）：
   - 技术深度：技术概念是否准确、有深度
   - 表达结构：逻辑是否清晰、有条理
   - STAR完整度：是否包含情境/任务/行动/结果（仅适用于行为类/项目类问题；
     纯技术概念题此项 score 设为 -1，comment 填"N/A - 纯技术题不适用"）
{jd_dimension}

严格输出 JSON：
{{
  "strengths": [
    {{"point": "亮点概括", "detail": "为什么这是亮点"}}
  ],
  "weaknesses": [
    {{"point": "不足概括", "suggestion": "具体改进建议"}}
  ],
  "overall_feedback": "整体反馈，2-3句大白话",
  "score": 72,
  "dimensions": [
    {{"name": "技术深度", "score": 75, "comment": "1-2句点评"}},
    {{"name": "表达结构", "score": 80, "comment": "1-2句点评"}},
    {{"name": "STAR完整度", "score": 60, "comment": "1-2句点评（纯技术题score=-1）"}}
  ]
}}"""

_JD_DIMENSION = "   - JD相关度：回答内容与目标岗位要求的契合程度"


def analyze_single_qa(
    question: str,
    answer: str,
    target_job: str = "",
    profile_summary: str = "",
    has_jd: bool = False,
) -> dict[str, Any]:
    """分析单道面试题的回答质量。

    Returns:
        {strengths: [{point, detail}], weaknesses: [{point, suggestion}],
         overall_feedback: str, score: int, dimensions: [{name, score, comment}]}
    """
    prompt = _USER.format(
        target_job=target_job or "未指定",
        question=question,
        answer=answer,
        profile_summary=profile_summary or "暂无背景信息",
        jd_dimension=_JD_DIMENSION if has_jd else "",
    )

    model = os.getenv("CHAT_LLM_MODEL") or os.getenv("LLM_MODEL") or "qwen3.5-flash"
    client = get_llm_client(timeout=60)

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": prompt},
            ],
        )
        raw = resp.choices[0].message.content or ""
        result = parse_json_response(raw)

        if isinstance(result, dict):
            result.setdefault("strengths", [])
            result.setdefault("weaknesses", [])
            result.setdefault("overall_feedback", "")
            result.setdefault("score", 0)
            result.setdefault("dimensions", [])
            return result
    except Exception as e:
        logger.warning("Interview review analysis failed: %s", e)

    return {
        "strengths": [],
        "weaknesses": [],
        "overall_feedback": "分析失败，请重试",
        "score": 0,
        "dimensions": [],
    }


