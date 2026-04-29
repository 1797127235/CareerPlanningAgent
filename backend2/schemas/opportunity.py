"""backend2/schemas/opportunity.py — 职位机会评估 v2 数据契约。"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ── JD 提取层 ───────────────────────────────────────────────────────────

class BasicRequirements(BaseModel):
    """JD 中的基本要求。"""

    education: str = ""        # 学历要求，如"本科及以上"
    experience: str = ""       # 年限要求，如"3年以上"
    location: str = ""         # 地点要求
    language: str = ""         # 语言要求
    certificates: list[str] = Field(default_factory=list)


class JDExtract(BaseModel):
    """从 JD 文本中提取的结构化信息。"""

    title: str = ""
    company: str = ""
    responsibilities: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    basic_requirements: BasicRequirements = Field(default_factory=BasicRequirements)
    seniority_hint: str = ""  # junior / mid / senior 等弱提示


# ── 诊断结果层 ───────────────────────────────────────────────────────────

class GapSkill(BaseModel):
    """技能缺口。"""

    skill: str = ""
    priority: Literal["high", "medium", "low"] = "medium"
    reason: str = ""           # 为什么判定为缺口
    evidence: str = ""         # JD 中的原文证据
    action_hint: str = ""      # 建议如何补强


class JDDiagnosisResult(BaseModel):
    """诊断结果：Profile vs JD 的匹配分析。"""

    schema_version: str = "opportunity_evaluation.v1"
    match_score: int = Field(0, ge=0, le=100)
    matched_skills: list[str] = Field(default_factory=list)
    gap_skills: list[GapSkill] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    resume_tips: list[str] = Field(default_factory=list)
    action_suggestions: list[str] = Field(default_factory=list)


# ── API 响应层 ───────────────────────────────────────────────────────────

class JDDiagnosisResponse(BaseModel):
    """单条诊断详情响应。"""

    id: int
    match_score: int = Field(0, ge=0, le=100)
    jd_title: str
    company: str
    jd_extract: JDExtract
    result: JDDiagnosisResult
    created_at: str
    warnings: list[str] = Field(default_factory=list)


class JDDiagnosisListItem(BaseModel):
    """历史列表项。"""

    id: int
    jd_title: str
    company: str
    match_score: int = Field(0, ge=0, le=100)
    created_at: str


# ── 请求层 ───────────────────────────────────────────────────────────────

class JDDiagnoseRequest(BaseModel):
    """请求 JD 诊断。"""

    jd_text: str = Field(..., min_length=10, description="JD 原文")
    jd_title: str = Field(default="", description="岗位名称（用户可选填写）")
