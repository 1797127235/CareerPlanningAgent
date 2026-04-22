# -*- coding: utf-8 -*-
"""
DebriefService — LLM-powered interview debrief analysis.
Input: list of {question, answer} + JD context + profile skills
Output: structured report JSON
"""
from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_DEBRIEF_PROMPT = """你是一位严格但有建设性的面试复盘教练。请对以下面试进行深度分析。

## 目标岗位 JD
{jd_text}

## 候选人技能画像
{profile_skills}

## 面试题目与回答记录
{qa_list}

## 分析要求

对每道题目：
- 给出 0-100 的回答质量分
- 列出 1-3 个明确亮点（要具体，不能说"表达清晰"这种空话）
- 列出 1-3 个明确不足（直接指出）
- 给出参考回答思路（2-3 句话的骨架）
- 标注涉及的技能标签

综合评估：
- 加权平均综合分
- 一句话总结整体表现（客观，不要夸大）
- 识别高优先级待补短板技能（与 JD 对比）
- 给出 2-4 条具体改进建议

## 评分原则
- 诚实优于奉承，准确的低分比虚假高分更有价值
- 亮点必须有具体依据，不得使用"表达流畅"、"思路清晰"等空洞词
- 不足必须直接点名，不得模糊处理
- 若回答为空或"不知道"，直接给 0-20 分

## 输出格式（严格 JSON，不加注释）
{{
  "overall_score": 综合分整数(0-100),
  "summary": "一句话总结",
  "question_reviews": [
    {{
      "question": "题目原文",
      "your_answer": "回答原文（截断至100字）",
      "score": 0-100整数,
      "strengths": ["亮点1"],
      "weaknesses": ["不足1"],
      "suggested_answer": "参考思路2-3句",
      "skill_tags": ["技能1", "技能2"]
    }}
  ],
  "gap_skills": [
    {{"skill": "技能名", "priority": "high或medium", "advice": "具体改进建议"}}
  ],
  "overall_tips": ["改进建议1", "改进建议2"]
}}

只返回 JSON，不要有任何其他文字。"""


class DebriefService:
    """Interview debrief: QA list + context → structured LLM analysis."""

    def analyze(
        self,
        qa_list: list[dict],
        jd_text: str = "",
        profile_data: dict | None = None,
    ) -> dict:
        if not qa_list:
            return self._empty_report()

        # Build profile context
        profile = profile_data or {}
        skills = profile.get("skills", [])
        skill_names = []
        for s in skills:
            if isinstance(s, dict):
                name = s.get("name", "")
                level = s.get("level", "")
                skill_names.append(f"{name}({level})" if level else name)
            else:
                skill_names.append(str(s))

        # Format QA list
        qa_text_parts = []
        for i, item in enumerate(qa_list, 1):
            q = item.get("question", "").strip()
            a = item.get("answer", "").strip()
            qa_text_parts.append(f"**题目 {i}：** {q}\n**我的回答：** {a or '（未作答）'}")
        qa_text = "\n\n".join(qa_text_parts)

        prompt = _DEBRIEF_PROMPT.format(
            jd_text=jd_text[:2000] if jd_text else "（无 JD 信息）",
            profile_skills="、".join(skill_names) if skill_names else "（无画像数据）",
            qa_list=qa_text,
        )

        try:
            from backend.llm import llm_chat, parse_json_response
            result_text = llm_chat(
                [{"role": "user", "content": prompt}],
                temperature=0,
                timeout=120,
            )
            result = parse_json_response(result_text)
        except Exception as e:
            logger.error("LLM debrief failed: %s", e)
            return {**self._empty_report(), "overall_tips": [f"AI 分析暂时不可用：{e}"]}

        # Normalize
        result.setdefault("overall_score", 0)
        result.setdefault("summary", "")
        result.setdefault("question_reviews", [])
        result.setdefault("gap_skills", [])
        result.setdefault("overall_tips", [])

        try:
            result["overall_score"] = max(0, min(100, int(result["overall_score"])))
        except (ValueError, TypeError):
            result["overall_score"] = 0

        for qr in result["question_reviews"]:
            try:
                qr["score"] = max(0, min(100, int(qr.get("score", 0))))
            except (ValueError, TypeError):
                qr["score"] = 0
            qr.setdefault("strengths", [])
            qr.setdefault("weaknesses", [])
            qr.setdefault("suggested_answer", "")
            qr.setdefault("skill_tags", [])

        return result

    def _empty_report(self) -> dict:
        return {
            "overall_score": 0,
            "summary": "",
            "question_reviews": [],
            "gap_skills": [],
            "overall_tips": [],
        }
