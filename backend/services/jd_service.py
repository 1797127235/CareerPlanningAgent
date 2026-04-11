# -*- coding: utf-8 -*-
"""
JDService — LLM-powered JD diagnosis: skill extraction, matching, gap analysis.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_DIAGNOSE_PROMPT = """你是一个职业技能匹配分析师。请从4个维度分析 JD 与用户画像的匹配情况。

## JD 文本
{jd_text}

## 用户画像技能
{user_skills}

## 用户知识领域
{knowledge_areas}

## 用户项目经历
{projects}

## 用户教育背景
{education}

## 用户软技能 / 素质
{soft_skills}

## 四维度评分规则

### 1. 基础要求 (basic)
对比 JD 中的学历要求、工作年限要求、证书/资质要求 vs 用户的教育背景和经历。
- 学历达标 +30，专业对口 +20，证书匹配 +20
- 年限匹配规则（区分应届生JD vs 有经验JD）：
  · JD明确写"应届生/实习/校招/不限工作经验"：年限项满分 +30
  · JD要求经验"1年以下/1年以内"：0年经验候选人 +20
  · JD要求"1-3年"：0年经验 +0，有实习经历 +10
  · JD要求"3年以上"：0年经验 +0，<2年实习 +5
  · 禁止将应届生JD的年限项直接扣分

### 2. 职业技能 (skills)
对比 JD 中要求的技术栈/工具/硬技能 vs 用户掌握的技能。
- 逐一匹配，按覆盖率打分；核心技能（JD中靠前位置）权重更高
- 缺失核心技能必须如实反映在分数中，不得因其他维度良好而掩盖
- 匹配判定规则（严格执行）：
  · 完全匹配（同名或公认缩写，如k8s=Kubernetes）：算匹配
  · 同义词匹配（Redis=缓存数据库，MySQL=关系型数据库）：算匹配
  · 上位匹配（JD要求Python，用户有Django/Flask）：算匹配，权重×0.8
  · 相关但非匹配（"了解计算机网络"≠"掌握分布式系统"，"学过数据结构"≠"算法工程能力"）：不算匹配
  · 禁止：将学过某领域课程等同于掌握该领域工程技术

### 3. 职业素养 (qualities)
评估 JD 要求的软性能力（沟通、协作、抗压等）。

严格评分标准（基准分20，所有候选人起点相同）：
- 有具体行为证据（项目经历中的明确事件：如"主导X评审"、"带领Y人团队"）：+15/项，最多+45
- 仅有自述标签（如"沟通能力强"等无法核实的描述）：+3/项，此类累计不超过15分
- 完成SJT软技能测评且有得分：额外+10
- 无任何软技能数据时：detail必须注明"暂无行为数据支撑，建议完成软技能评估"（不额外加分）
- 上限85
- 禁止因"标签数量多"就给高分——标签是自述，不是证据

### 4. 发展潜力 (potential)
基于可观察事实评估成长空间。

严格评分标准：
- 基准分30（所有候选人起点相同，避免空白画像虚高）
- 有跨领域学习记录（有课程/证书/书单证明）+10
- 项目复杂度明显递增（≥2个项目，后者明显更复杂）+10
- 技能多样且深度兼备（不同技术方向各有实质掌握）+10
- 有竞赛/开源/论文等可验证贡献 +15
- 上限85（100代表顶尖学习者，极少出现）
- 领域迁移约束：所引用的技能/项目须与JD领域有实际迁移关联；若候选人技术背景与JD领域无重叠，基准分上限50
- detail必须引用具体证据；禁止使用"成长空间大"等空洞表达

## 综合匹配度
match_score = basic×0.15 + skills×0.40 + qualities×0.25 + potential×0.20（四舍五入取整）

## 评分原则（必须遵守）
- 诚实优于奉承：准确的低分比虚假的高分对用户更有价值
- detail 必须具体：指出真实证据或真实差距，禁止使用"良好"、"优秀"、"齐全"等空洞词汇
- 当用户明显缺乏某项核心技能时，直接在 detail 中点名该技能，不要用模糊语言绕过
- gap_skills 要全面：JD 中明确要求但用户未掌握的技能均需列出

## 输出格式（严格 JSON，不要加注释或 markdown）
{{
  "company": "从JD中提取的招聘公司名，如'字节跳动'、'腾讯'、'阿里巴巴'。如果JD中多处提到同一公司，统一用常见中文名。JD未明确提及公司则留空字符串",
  "jd_title": "从JD提取的岗位名称，如'Java后端工程师'或'算法实习生'，不超过15字",
  "match_score": 综合匹配度整数(0-100),
  "dimensions": {{
    "basic": {{"score": 0-100整数, "label": "基础要求", "detail": "一句话说明匹配/差距"}},
    "skills": {{"score": 0-100整数, "label": "职业技能", "detail": "一句话说明匹配/差距"}},
    "qualities": {{"score": 0-100整数, "label": "职业素养", "detail": "一句话说明匹配/差距"}},
    "potential": {{"score": 0-100整数, "label": "发展潜力", "detail": "一句话说明匹配/差距"}}
  }},
  "extracted_skills": ["JD要求的技能1", "技能2", ...],
  "matched_skills": ["已匹配的技能1", ...],
  "gap_skills": [
    {{"skill": "缺失技能名", "priority": "high或medium", "match_delta": 预估补上后分数提升整数}},
    ...
  ],
  "resume_tips": ["建议1", "建议2", ...]
}}

只返回 JSON，不要有任何其他文字。"""


class JDService:
    """JD analysis: LLM-powered skill extraction + matching + gap analysis."""

    def diagnose(self, jd_text: str, profile: dict) -> dict:
        """LLM-powered JD diagnosis against user profile.

        Returns {match_score, matched_skills, gap_skills, extracted_skills, resume_tips}.
        """
        if not jd_text or not jd_text.strip():
            return {
                "match_score": 0,
                "matched_skills": [],
                "gap_skills": [],
                "extracted_skills": [],
                "resume_tips": [],
            }

        # Build user context
        skills = profile.get("skills", [])
        skill_names = []
        for s in skills:
            if isinstance(s, dict):
                name = s.get("name", "")
                level = s.get("level", "")
                skill_names.append(f"{name}({level})" if level else name)
            else:
                skill_names.append(str(s))

        knowledge = profile.get("knowledge_areas", [])
        projects = profile.get("projects", [])
        project_texts = []
        for p in projects:
            if isinstance(p, dict):
                project_texts.append(f"{p.get('name', '')} {p.get('description', '')}")
            else:
                project_texts.append(str(p))

        # Education info
        edu = profile.get("education", {})
        if isinstance(edu, dict):
            edu_text = f"学历: {edu.get('degree', '未知')}, 专业: {edu.get('major', '未知')}, 学校: {edu.get('school', '未知')}"
        elif isinstance(edu, list) and edu:
            parts = []
            for e in edu[:3]:
                if isinstance(e, dict):
                    parts.append(f"{e.get('degree', '')} {e.get('major', '')} {e.get('school', '')}")
                else:
                    parts.append(str(e))
            edu_text = "; ".join(parts)
        else:
            edu_text = "无"

        # Soft skills
        soft = profile.get("soft_skills", [])
        if not soft:
            soft = profile.get("qualities", [])
        soft_texts = []
        for s in soft:
            if isinstance(s, dict):
                soft_texts.append(s.get("name", str(s)))
            else:
                soft_texts.append(str(s))

        prompt = _DIAGNOSE_PROMPT.format(
            jd_text=jd_text[:3000],
            user_skills="、".join(skill_names) if skill_names else "无",
            knowledge_areas="、".join(knowledge) if knowledge else "无",
            projects="\n".join(project_texts) if project_texts else "无",
            education=edu_text,
            soft_skills="、".join(soft_texts) if soft_texts else "无",
        )

        try:
            from backend.llm import llm_chat, parse_json_response
            result_text = llm_chat(
                [{"role": "user", "content": prompt}],
                temperature=0,
                timeout=90,
            )
            result = parse_json_response(result_text)
        except Exception as e:
            logger.error("LLM JD diagnosis failed: %s", e)
            return {
                "match_score": 0,
                "matched_skills": [],
                "gap_skills": [],
                "extracted_skills": [],
                "resume_tips": [f"AI 分析暂时不可用: {e}"],
            }

        # Normalize output
        result.setdefault("company", "")
        result.setdefault("match_score", 0)
        result.setdefault("matched_skills", [])
        result.setdefault("gap_skills", [])
        result.setdefault("extracted_skills", [])
        result.setdefault("resume_tips", [])
        # Clean company field (strip whitespace, limit length)
        if isinstance(result.get("company"), str):
            result["company"] = result["company"].strip()[:64]
        else:
            result["company"] = ""

        # Ensure match_score is int
        try:
            result["match_score"] = int(result["match_score"])
        except (ValueError, TypeError):
            result["match_score"] = 0

        # Normalize 4-dimension scores
        _DIM_DEFAULTS = {
            "basic": {"score": 0, "label": "基础要求", "detail": ""},
            "skills": {"score": 0, "label": "职业技能", "detail": ""},
            "qualities": {"score": 0, "label": "职业素养", "detail": ""},
            "potential": {"score": 0, "label": "发展潜力", "detail": ""},
        }
        dims = result.get("dimensions", {})
        if not isinstance(dims, dict):
            dims = {}
        for key, default in _DIM_DEFAULTS.items():
            dim = dims.get(key, {})
            if not isinstance(dim, dict):
                dim = {}
            dim.setdefault("score", default["score"])
            dim.setdefault("label", default["label"])
            dim.setdefault("detail", default["detail"])
            try:
                dim["score"] = max(0, min(100, int(dim["score"])))
            except (ValueError, TypeError):
                dim["score"] = 0
            dims[key] = dim
        result["dimensions"] = dims

        # Recalculate match_score from dimensions for consistency
        result["match_score"] = round(
            dims["basic"]["score"] * 0.15
            + dims["skills"]["score"] * 0.40
            + dims["qualities"]["score"] * 0.25
            + dims["potential"]["score"] * 0.20
        )

        # Ensure gap_skills have required fields
        for g in result["gap_skills"]:
            g.setdefault("priority", "medium")
            g.setdefault("match_delta", 5)

        return result

    def generate_greeting(
        self,
        jd_title: str,
        extracted_skills: list[str],
        matched_skills: list[str],
        match_score: int,
        profile: dict,
    ) -> str:
        """Generate a personalized job-application greeting message."""
        edu = profile.get("education", {})
        if isinstance(edu, dict):
            edu_text = f"{edu.get('degree', '')} {edu.get('major', '')} {edu.get('school', '')}".strip()
        else:
            edu_text = str(edu) if edu else "无"

        projects = profile.get("projects", [])
        project_names = []
        for p in projects[:2]:
            if isinstance(p, dict):
                project_names.append(p.get("name", "") or p.get("description", "")[:20])
            else:
                project_names.append(str(p)[:20])

        prompt = (
            "你是一个职场求职顾问，请根据以下信息生成一条简洁、自然的求职打招呼消息"
            "（适用于招聘网站站内信/微信/邮件首次联系HR）。\n\n"
            f"岗位名称：{jd_title}\n"
            f"JD核心技能要求：{', '.join(extracted_skills[:8]) or '无'}\n"
            f"候选人已匹配技能：{', '.join(matched_skills[:6]) or '无'}\n"
            f"候选人教育背景：{edu_text or '无'}\n"
            f"候选人主要项目：{', '.join(project_names) or '无'}\n"
            f"与岗位匹配度：{match_score}分\n\n"
            "生成要求：\n"
            "- 长度80-120字，自然口语，不要官僚腔\n"
            "- 第一句点明应聘岗位\n"
            "- 核心亮出1-2个最强匹配点（用具体技能名而非泛泛描述）\n"
            "- 结尾表达希望沟通/约面试的意愿\n"
            "- 禁止使用：贵公司、不胜感激、冒昧打扰、诚挚等过时措辞\n"
            "- 直接输出打招呼文本，不要加任何前缀或解释"
        )
        try:
            from backend.llm import llm_chat
            text = llm_chat(
                [{"role": "user", "content": prompt}],
                temperature=0.7,
                timeout=90,
            )
            return text.strip() or "生成失败，请重试。"
        except Exception as e:
            logger.error("generate_greeting failed: %s", e)
            return "生成失败，请重试。"

    def match_to_graph_node(
        self, jd_skills: list[str], graph_service: Any
    ) -> dict | None:
        """Jaccard-style overlap to find the closest graph node."""
        if not jd_skills:
            return None

        jd_lower = {s.lower() for s in jd_skills}
        best_node = None
        best_score = 0.0

        for node_id in graph_service.node_ids:
            node = graph_service.get_node(node_id)
            if not node:
                continue
            must = node.get("must_skills", [])
            if not must:
                continue
            node_lower = {s.lower() for s in must}
            overlap = len(jd_lower & node_lower)
            score = overlap / max(len(jd_lower), len(node_lower), 1)
            if score > best_score:
                best_score = score
                best_node = node

        if not best_node or best_score < 0.1:
            return None

        return {
            "node_id": best_node.get("node_id", ""),
            "label": best_node.get("label", ""),
            "role_family": best_node.get("role_family", ""),
            "match_confidence": round(best_score * 100),
        }

