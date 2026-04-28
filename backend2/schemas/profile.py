"""画像解析的数据契约 — 跨 backend2 模块共享。

本模块定义的规范类型：
- ResumeDocument：文件提取的原始上下文
- ProfileData：标准化的用户画像输出
- ParseCandidate：单个解析策略产出的中间结果

设计说明：
- 原始文本由 ResumeDocument 持有，ProfileData 不再重复拥有
- ProfileData.raw_text 仅为兼容旧前端暂时保留，backend2 内部视为废弃
- 所有列表字段都有防御性校验，处理脏数据输入
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


# ── 子模型 ──────────────────────────────────────────────────────────────

class Skill(BaseModel):
    """单条技能，含熟练度等级。"""

    name: str = Field(..., min_length=1)
    level: Literal["beginner", "familiar", "intermediate", "advanced"] = "familiar"


class Education(BaseModel):
    """最高或最相关的一条教育经历。"""

    degree: str = ""
    major: str = ""
    school: str = ""
    graduation_year: int | None = None


class Internship(BaseModel):
    """实习或工作经历。"""

    company: str = ""
    role: str = ""
    duration: str = ""
    tech_stack: list[str] = Field(default_factory=list)
    highlights: str = ""


class CareerSignals(BaseModel):
    """从简历中提取的可观察职业信号。"""

    has_publication: bool = False
    publication_level: str = "无"
    competition_awards: list[str] = Field(default_factory=list)
    domain_specialization: str = ""
    research_vs_engineering: Literal["research", "engineering", "balanced"] = "balanced"
    open_source: bool = False
    internship_company_tier: str = "无"


# ── 核心契约 ────────────────────────────────────────────────────────────


class ResumeDocument(BaseModel):
    """原始文档提取结果 — 解析管线的不可变输入。

    由 TextExtractor 生成，在整个管线中传递。
    必须保留完整的原始文本，以便后续可基于原文重新解析，无需用户重新上传。
    """

    filename: str
    content_type: str | None = None
    raw_text: str
    extractor: str = ""  # 生成此文档的提取器名称，如 "pdfplumber"
    is_scanned: bool = False
    warnings: list[str] = Field(default_factory=list)
    # 保留原始文件字节，以便需要原始文件的策略（如 ResumeSDK）可直接使用。
    # 用 exclude=True 避免进入 JSON 序列化。
    file_bytes: bytes | None = Field(default=None, exclude=True)


class ProfileData(BaseModel):
    """标准用户画像 — 解析管线的最终输出。

    下游模块（职业机会评估、成长计划、报告、面试准备）只依赖此结构。
    """

    name: str = ""
    job_target: str = ""
    primary_domain: str = ""
    education: Education = Field(default_factory=Education)
    skills: list[Skill] = Field(default_factory=list)
    knowledge_areas: list[str] = Field(default_factory=list)
    internships: list[Internship] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    awards: list[str] = Field(default_factory=list)
    certificates: list[str] = Field(default_factory=list)
    career_signals: CareerSignals = Field(default_factory=CareerSignals)
    soft_skills: dict = Field(default_factory=dict)
    source_document_id: int | None = None
    # 向后兼容：暂时保留此字段，等待前端改造完成后移除
    raw_text: str = ""

    # ── 校验器 ──────────────────────────────────────────────────────────

    @field_validator("skills", mode="before")
    @classmethod
    def _normalize_skills(cls, v: list) -> list:
        """同时接受 dict 和字符串格式的技能，过滤空值。"""
        if not isinstance(v, list):
            return []
        out: list[dict] = []
        for item in v:
            if isinstance(item, dict) and item.get("name"):
                out.append(item)
            elif isinstance(item, str) and item.strip():
                out.append({"name": item.strip(), "level": "familiar"})
        return out

    @field_validator("projects", "awards", "certificates", "knowledge_areas", mode="before")
    @classmethod
    def _dedupe_strings(cls, v: list) -> list:
        """字符串列表去重，保持原始顺序。"""
        if not isinstance(v, list):
            return []
        seen: set[str] = set()
        out: list[str] = []
        for item in v:
            if isinstance(item, str):
                key = item.strip()
                if key and key not in seen:
                    seen.add(key)
                    out.append(key)
        return out

    def to_dict(self) -> dict:
        """序列化为纯字典，用于 JSON 存储和 API 响应。"""
        return self.model_dump(mode="json")


class ParseCandidate(BaseModel):
    """单个 ParseStrategy 产出的中间结果。

    Merger 接收多个候选结果，合并为最终的 ProfileData。
    """

    source: str  # 如 "resumesdk"、"llm_direct"、"resumesdk_llm_adapter"
    profile: ProfileData
    confidence: float = 0.0
    raw_output: dict | None = None  # 策略原始返回，用于调试
    warnings: list[str] = Field(default_factory=list)
